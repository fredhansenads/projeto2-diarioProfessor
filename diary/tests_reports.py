import csv
from datetime import date
from decimal import Decimal
from io import BytesIO, StringIO

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from pypdf import PdfReader

from .grading_services import grade_summary
from .models import AcademicYear, Assessment, Attendance, Classroom, Enrollment, Grade, Gradebook, Lesson, School, Student, Subject, Term
from .report_exports import CSV_COLUMNS, csv_report, pdf_report, safe_cell
from .report_services import build_report
from .teaching_services import frequency_rows


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ReportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="relatorios", first_name="Professora Júlia")
        cls.other = User.objects.create_user(username="outra.conta")
        cls.school = School.objects.create(owner=cls.owner, name="Escola das Árvores")
        cls.year = AcademicYear.objects.create(owner=cls.owner, year=2026)
        cls.room = Classroom.objects.create(owner=cls.owner, school=cls.school, academic_year=cls.year, name="7º A")
        cls.subject = Subject.objects.create(owner=cls.owner, name="Matemática")
        cls.second_subject = Subject.objects.create(owner=cls.owner, name="História")
        cls.room.subjects.add(cls.subject, cls.second_subject)
        cls.term = Term.objects.create(owner=cls.owner, school=cls.school, academic_year=cls.year,
            name="1º bimestre", start_date=date(2026, 2, 1), end_date=date(2026, 4, 30))
        cls.pupil = Enrollment.objects.create(owner=cls.owner, classroom=cls.room, starts_on=date(2026, 2, 1),
            student=Student.objects.create(owner=cls.owner, name="Ana", reference="A001"))
        cls.second_pupil = Enrollment.objects.create(owner=cls.owner, classroom=cls.room, starts_on=date(2026, 2, 1),
            student=Student.objects.create(owner=cls.owner, name="Bruno"))
        cls.book = Gradebook.objects.create(owner=cls.owner, classroom=cls.room, term=cls.term, subject=cls.subject)
        cls.assessment = Assessment.objects.create(owner=cls.owner, gradebook=cls.book, title="Frações",
            date=date(2026, 3, 1), maximum=10)
        cls.grade = Grade.objects.create(owner=cls.owner, assessment=cls.assessment, enrollment=cls.pupil,
            status="submitted", score=Decimal("8.5"), note="Boa evolução em frações.")
        cls.lesson = Lesson.objects.create(owner=cls.owner, classroom=cls.room, subject=cls.subject,
            date=date(2026, 3, 1), quantity=2, content="Frações equivalentes.")
        Attendance.objects.create(owner=cls.owner, lesson=cls.lesson, enrollment=cls.pupil,
            absences=1, justified_absences=1, justification="Justificativa apresentada.")
        cls.pending_lesson = Lesson.objects.create(owner=cls.owner, classroom=cls.room, subject=cls.subject,
            date=date(2026, 3, 2), quantity=1, content="Revisão.")

    def setUp(self):
        self.client.force_login(self.owner)

    def data(self, **kwargs):
        return {"classroom": self.room.pk, "term": self.term.pk, **kwargs}

    def report(self, **kwargs):
        return build_report(owner=self.owner, classroom=self.room, term=self.term, **kwargs)

    def row(self):
        return next(row for row in self.report()["rows"] if row["subject"] == self.subject and row["enrollment"] == self.pupil)

    def test_report_reuses_source_values(self):
        row = self.row()
        original_grade = next(item for item in grade_summary(self.book)["rows"] if item["enrollment"] == self.pupil)
        original_frequency = next(item for item in frequency_rows(self.room, Lesson.objects.filter(subject=self.subject))
                                  if item["enrollment"] == self.pupil)
        self.assertEqual(row["grade"], original_grade)
        self.assertEqual(row["frequency"], original_frequency)
        self.assertEqual(row["frequency"]["percentage"], Decimal("50.0"))
        self.assertEqual(row["frequency"]["pending"], 1)

    def test_subject_and_student_filters(self):
        report = self.report(subject=self.subject, enrollment=self.pupil)
        self.assertEqual(len(report["rows"]), 1)
        self.assertEqual(report["student_count"], 1)

    def test_missing_book_and_no_calls_are_not_zeros(self):
        row = next(row for row in self.report()["rows"] if row["subject"] == self.second_subject)
        self.assertIsNone(row["grade"]["final"])
        self.assertIsNone(row["frequency"]["percentage"])
        self.assertEqual(row["status"], "Sem caderno de notas")
        response = self.client.get(reverse("report"), self.data(subject=self.second_subject.pk))
        self.assertContains(response, "Sem chamada")
        self.assertContains(response, "—")

    def test_unrecorded_student_has_pending_grades_and_calls(self):
        row = next(row for row in self.report(subject=self.subject)["rows"] if row["enrollment"] == self.second_pupil)
        self.assertEqual(row["grade"]["pending"], 1)
        self.assertEqual(row["frequency"]["pending"], 3)
        self.assertIn("Frações", row["pending_items"][0])
        self.assertIsNone(row["grade"]["final"])

    def test_explicit_zero_is_preserved_in_all_exports(self):
        self.grade.score = 0
        self.grade.save()
        report = self.report(subject=self.subject, enrollment=self.pupil)
        response = self.client.get(reverse("report"), self.data(subject=self.subject.pk, enrollment=self.pupil.pk))
        self.assertContains(response, "0,0")
        csv_rows = list(csv.DictReader(StringIO(csv_report(report).decode("utf-8-sig")), delimiter=";"))
        self.assertEqual(csv_rows[0]["Resultado"], "0,0")
        text = "".join(page.extract_text() for page in PdfReader(BytesIO(pdf_report(report))).pages)
        self.assertIn("Resultado: 0,0", text)

    def test_cancelled_records_excluded(self):
        self.lesson.is_cancelled = True
        self.lesson.save()
        self.assessment.is_cancelled = True
        self.assessment.save()
        row = self.row()
        self.assertEqual(row["frequency"]["total"], 1)
        self.assertEqual(row["frequency"]["absences"], 0)
        self.assertIsNone(row["grade"]["final"])
        self.assertEqual(row["observations"], [])
        self.assertEqual(row["assessments"], [])

    def test_outside_period_lesson_excluded(self):
        Lesson.objects.create(owner=self.owner, classroom=self.room, subject=self.subject,
                              date=date(2026, 5, 1), content="Fora do recorte", quantity=10)
        self.assertEqual(self.row()["frequency"]["total"], 3)

    def test_transfer_dates_and_future_enrollment(self):
        self.second_pupil.status = "transferred"
        self.second_pupil.ends_on = date(2026, 2, 28)
        self.second_pupil.save()
        row = next(row for row in self.report(subject=self.subject)["rows"] if row["enrollment"] == self.second_pupil)
        self.assertEqual(row["frequency"]["total"], 0)
        self.assertEqual(row["grade"]["pending"], 0)
        self.assertEqual(row["assessments"], [])
        self.second_pupil.status = "active"
        self.second_pupil.ends_on = None
        self.second_pupil.starts_on = date(2026, 5, 1)
        self.second_pupil.save()
        self.assertEqual(self.report()["student_count"], 1)

    def test_observations_include_grades_and_justification(self):
        row = self.row()
        self.assertTrue(any("Boa evolução" in text for text in row["observations"]))
        self.assertTrue(any("Justificativa apresentada" in text for text in row["observations"]))

    def test_recovery_appears_in_individual_detail(self):
        self.book.recovery = "higher"
        self.book.save()
        item = Assessment.objects.create(owner=self.owner, gradebook=self.book, title="Recuperação",
                                         kind="recovery", date=date(2026, 4, 15), maximum=10)
        Grade.objects.create(owner=self.owner, enrollment=self.pupil, assessment=item, score=9, status="submitted")
        row = self.row()
        self.assertEqual(row["grade"]["final"], Decimal("9.0"))
        self.assertEqual(len(row["assessments"]), 2)
        other_row = next(row for row in self.report(subject=self.subject)["rows"] if row["enrollment"] == self.second_pupil)
        self.assertEqual(other_row["assessments"][-1]["status"], "Não participante")
        self.assertEqual(len(other_row["pending_items"]), 1)

    def test_points_configuration_warning_is_exported(self):
        self.book.calculation = "points"
        self.book.save()
        self.assessment.is_cancelled = True
        self.assessment.save()
        report = self.report(subject=self.subject)
        self.assertFalse(report["groups"][0]["points_ready"])
        text = "".join(page.extract_text() for page in PdfReader(BytesIO(pdf_report(report))).pages)
        self.assertIn("Planejamento de pontos incompleto", text)

    def test_csv_metadata_numbers_observations_and_utf8(self):
        raw = csv_report(self.report(subject=self.subject, enrollment=self.pupil))
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
        rows = list(csv.DictReader(StringIO(raw.decode("utf-8-sig")), delimiter=";"))
        self.assertEqual(list(rows[0]), CSV_COLUMNS)
        self.assertEqual(rows[0]["Escola"], "Escola das Árvores")
        self.assertEqual(rows[0]["Aluno"], "Ana")
        self.assertEqual(rows[0]["Resultado"], "8,5")
        self.assertEqual(rows[0]["Frequência registrada (%)"], "50,0")
        self.assertEqual(rows[0]["Aulas com chamada pendente"], "1")
        self.assertIn("Boa evolução", rows[0]["Observações"])

    def test_csv_formula_injection_and_quotes(self):
        for payload in ("=1+1", "+CMD", "-CMD", "@SUM(A1)", "  =1", "\t1", "\r1", "\n1"):
            with self.subTest(payload=payload):
                self.assertTrue(safe_cell(payload).startswith("'"))
        student = self.pupil.student
        student.name = '=HYPERLINK("https://example.invalid";"x")'
        student.save()
        row = list(csv.DictReader(StringIO(csv_report(self.report(enrollment=self.pupil)).decode("utf-8-sig")),
                                  delimiter=";"))[0]
        self.assertEqual(row["Aluno"], "'" + student.name)

    def test_html_escapes_observations(self):
        self.grade.note = "<script>alert(1)</script>"
        self.grade.save()
        response = self.client.get(reverse("report"), self.data(enrollment=self.pupil.pk))
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(response, "<script>alert(1)")

    def test_pdf_escapes_markup_and_has_headers(self):
        self.grade.note = '<img src="https://example.invalid/track"/> & evolução'
        self.grade.save()
        report = self.report(enrollment=self.pupil)
        raw = pdf_report(report)
        self.assertTrue(raw.startswith(b"%PDF"))
        text = "".join(page.extract_text() for page in PdfReader(BytesIO(raw)).pages)
        self.assertIn("Ficha individual", text)
        self.assertIn("Escola das Árvores", text)
        self.assertIn("Faltas: 1", text)
        self.assertIn('<img src=', " ".join(text.split()))
        self.assertIn("Página 1", text)

    def test_pdf_pagination_preserves_all_students(self):
        for number in range(55):
            student = Student.objects.create(owner=self.owner, name=f"Estudante {number:02d} Sobrenome comprido")
            Enrollment.objects.create(owner=self.owner, student=student, classroom=self.room, starts_on=date(2026, 2, 1))
        pdf = PdfReader(BytesIO(pdf_report(self.report(subject=self.second_subject))))
        self.assertGreater(len(pdf.pages), 1)
        all_text = "".join(page.extract_text() for page in pdf.pages)
        for number in range(55):
            self.assertIn(f"Estudante {number:02d}", all_text)
        self.assertIn("Página", pdf.pages[-1].extract_text())

    def test_pdf_long_content_splits_instead_of_crashing(self):
        self.lesson.content = ("Conteúdo longo para conferir quebra de página. " * 100) + "MARCADOR-FINAL"
        self.lesson.save()
        raw = pdf_report(self.report(subject=self.subject, enrollment=self.pupil))
        text = "".join(page.extract_text() for page in PdfReader(BytesIO(raw)).pages)
        self.assertIn("MARCADOR-FINAL", text)

    def test_export_routes_and_privacy_headers(self):
        for output, mime in (("pdf", "application/pdf"), ("csv", "text/csv"), ("print", "text/html")):
            with self.subTest(output=output):
                response = self.client.get(reverse("report"), self.data(format=output))
                self.assertEqual(response.status_code, 200)
                self.assertIn(mime, response["Content-Type"])
                self.assertIn("no-store", response["Cache-Control"])
                if output != "print":
                    self.assertIn("attachment", response["Content-Disposition"])

    def test_anonymous_cannot_read_or_export(self):
        self.client.logout()
        for output in ("html", "pdf", "csv", "print"):
            self.assertEqual(self.client.get(reverse("report"), self.data(format=output)).status_code, 302)

    def test_other_owner_cannot_query_or_export_known_ids(self):
        self.client.force_login(self.other)
        for output in ("html", "pdf", "csv", "print"):
            response = self.client.get(reverse("report"), self.data(format=output))
            self.assertEqual(response.status_code, 200 if output == "html" else 400)
            self.assertIsNone(response.context["report"])
            self.assertNotContains(response, "Boa evolução", status_code=response.status_code)
            self.assertNotIn("Content-Disposition", response)
        with self.assertRaises(ValueError):
            build_report(owner=self.other, classroom=self.room, term=self.term)

    def test_mismatched_school_year_period_subject_and_student_rejected(self):
        school = School.objects.create(owner=self.owner, name="Outra escola")
        year = AcademicYear.objects.create(owner=self.owner, year=2025)
        term = Term.objects.create(owner=self.owner, school=school, academic_year=self.year,
                                    name="Outro período", start_date=date(2026, 2, 1), end_date=date(2026, 4, 1))
        subject = Subject.objects.create(owner=self.owner, name="Não vinculada")
        room = Classroom.objects.create(owner=self.owner, school=school, academic_year=self.year, name="Outra turma")
        enrollment = Enrollment.objects.create(owner=self.owner, student=self.pupil.student,
                                                classroom=room, starts_on=date(2026, 2, 1))
        for key, value in (("school", school.pk), ("year", year.pk), ("term", term.pk),
                           ("subject", subject.pk), ("enrollment", enrollment.pk)):
            with self.subTest(key=key):
                response = self.client.get(reverse("report"), self.data(**{key: value, "format": "csv"}))
                self.assertEqual(response.status_code, 400)
                self.assertIsNone(response.context["report"])

    def test_invalid_filters_never_fall_back_to_all_data(self):
        for data in ({}, {"classroom": "garbage"}, self.data(term="999999"),
                     self.data(classroom="9" * 200), self.data(subject="not-a-number")):
            response = self.client.get(reverse("report"), {**data, "format": "pdf"})
            self.assertEqual(response.status_code, 400)
            self.assertNotIn("Content-Disposition", response)

    def test_print_page_and_method_restriction(self):
        response = self.client.get(reverse("report"), self.data(format="print"))
        self.assertContains(response, "Imprimir agora")
        self.assertContains(response, "reports.js")
        self.assertEqual(self.client.post(reverse("report"), self.data()).status_code, 405)
        self.assertEqual(self.client.get(reverse("report"), self.data(format="../secrets")).status_code, 400)

    def test_report_does_not_write_or_change_sources(self):
        before = (Grade.objects.count(), Attendance.objects.count(), self.book.version)
        self.client.get(reverse("report"), self.data(format="pdf"))
        self.book.refresh_from_db()
        self.assertEqual(before, (Grade.objects.count(), Attendance.objects.count(), self.book.version))

    def test_empty_report_and_legacy_date_warning(self):
        self.pupil.starts_on = None
        self.pupil.save()
        self.assertTrue(self.report()["missing_dates"])
        room = Classroom.objects.create(owner=self.owner, school=self.school, academic_year=self.year, name="Vazia")
        report = build_report(owner=self.owner, classroom=room, term=self.term)
        self.assertEqual(report["rows"], [])
        self.assertTrue(pdf_report(report).startswith(b"%PDF"))
        self.assertEqual(len(list(csv.reader(StringIO(csv_report(report).decode("utf-8-sig")), delimiter=";"))), 1)
