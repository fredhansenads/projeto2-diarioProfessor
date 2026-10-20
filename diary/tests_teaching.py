from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import (
    AcademicYear, Attendance, Classroom, Enrollment, Lesson, LessonAudit,
    School, Student, Subject, Term,
)
from .teaching_forms import AttendanceForm
from .teaching_services import frequency_rows


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class TeachingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = User.objects.create_user(username="docente", password="Senha!2026")
        cls.other = User.objects.create_user(username="outro.docente", password="Senha!2026")
        cls.school = School.objects.create(owner=cls.teacher, name="Escola Horizonte")
        cls.year = AcademicYear.objects.create(owner=cls.teacher, year=2026)
        cls.subject = Subject.objects.create(owner=cls.teacher, name="Matemática")
        cls.unlinked = Subject.objects.create(owner=cls.teacher, name="Português")
        cls.classroom = Classroom.objects.create(
            owner=cls.teacher, school=cls.school, academic_year=cls.year, name="6º A"
        )
        cls.classroom.subjects.add(cls.subject)
        cls.student = Student.objects.create(owner=cls.teacher, name="Ana Exemplo")
        cls.enrollment = Enrollment.objects.create(
            owner=cls.teacher, student=cls.student, classroom=cls.classroom,
            starts_on=date(2026, 2, 1),
        )
        cls.term = Term.objects.create(
            owner=cls.teacher, school=cls.school, academic_year=cls.year,
            name="Primeiro bimestre", start_date=date(2026, 2, 1), end_date=date(2026, 4, 1),
        )
        school = School.objects.create(owner=cls.other, name="Escola sigilosa")
        year = AcademicYear.objects.create(owner=cls.other, year=2026)
        cls.other_subject = Subject.objects.create(owner=cls.other, name="Disciplina sigilosa")
        cls.other_classroom = Classroom.objects.create(
            owner=cls.other, school=school, academic_year=year, name="Turma sigilosa"
        )
        cls.other_classroom.subjects.add(cls.other_subject)
        student = Student.objects.create(owner=cls.other, name="Aluno sigiloso")
        cls.other_enrollment = Enrollment.objects.create(
            owner=cls.other, student=student, classroom=cls.other_classroom,
            starts_on=date(2026, 2, 1),
        )
        cls.other_lesson = Lesson.objects.create(
            owner=cls.other, classroom=cls.other_classroom, subject=cls.other_subject,
            date=date(2026, 3, 1), quantity=1, content="Conteúdo sigiloso",
        )

    def setUp(self):
        self.client.force_login(self.teacher)

    def lesson_data(self, **overrides):
        return {
            "subject": self.subject.pk, "date": "2026-03-01", "quantity": 2,
            "content": "Frações equivalentes", "notes": "Exercícios em duplas", "version": 0,
            **overrides,
        }

    def create_lesson(self, **overrides):
        response = self.client.post(reverse("lesson_create", args=[self.classroom.pk]),
                                    self.lesson_data(**overrides))
        self.assertEqual(response.status_code, 302, getattr(response, "context", None))
        return Lesson.objects.filter(owner=self.teacher).latest("pk")

    def attendance_data(self, lesson, **overrides):
        lesson.refresh_from_db()
        form = AttendanceForm(lesson=lesson)
        data = {
            "version": lesson.version, "roster_token": form.fields["roster_token"].initial,
            "reason": "",
        }
        for enrollment in form.roster:
            record = form.records.get(enrollment.pk)
            data.update({
                f"absences_{enrollment.pk}": record.absences if record else 0,
                f"justified_{enrollment.pk}": record.justified_absences if record else 0,
                f"note_{enrollment.pk}": record.justification if record else "",
            })
        data.update(overrides)
        return data

    def save_call(self, lesson, **overrides):
        response = self.client.post(reverse("attendance_form", args=[lesson.pk]),
                                    self.attendance_data(lesson, **overrides))
        self.assertEqual(response.status_code, 302)
        return Attendance.objects.get(lesson=lesson, enrollment=self.enrollment)

    def summary(self):
        return frequency_rows(self.classroom, Lesson.objects.filter(
            owner=self.teacher, classroom=self.classroom
        ))

    def test_register_lesson_and_content_creates_history_without_auto_presence(self):
        lesson = self.create_lesson()
        self.assertEqual(lesson.owner, self.teacher)
        self.assertEqual(lesson.quantity, 2)
        self.assertFalse(lesson.attendance_records.exists())
        event = lesson.history.get()
        self.assertEqual(event.actor, self.teacher)
        self.assertEqual(event.kind, LessonAudit.Kind.CREATED)
        response = self.client.get(reverse("lesson_detail", args=[lesson.pk]))
        self.assertContains(response, "Frações equivalentes")
        self.assertContains(response, "Chamada pendente")
        self.assertContains(response, "Nenhum aluno foi considerado presente automaticamente")

    def test_duplicate_lesson_is_rejected(self):
        self.create_lesson()
        response = self.client.post(reverse("lesson_create", args=[self.classroom.pk]),
                                    self.lesson_data())
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertEqual(Lesson.objects.filter(owner=self.teacher).count(), 1)

    def test_lesson_validates_dates_quantity_subject_and_required_content(self):
        cases = [
            {"quantity": 0}, {"quantity": 21}, {"quantity": "abc"}, {"quantity": ""},
            {"date": "2025-03-01"}, {"date": ""},
            {"date": str(timezone.localdate() + timedelta(days=1))},
            {"subject": self.unlinked.pk}, {"subject": self.other_subject.pk}, {"content": ""},
        ]
        for invalid in cases:
            with self.subTest(invalid=invalid):
                response = self.client.post(reverse("lesson_create", args=[self.classroom.pk]),
                                            self.lesson_data(**invalid))
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors)
        self.assertFalse(Lesson.objects.filter(owner=self.teacher).exists())

    def test_new_pages_render_and_require_authentication(self):
        lesson = self.create_lesson()
        urls = [
            reverse("lesson_list"), reverse("lesson_choose"),
            reverse("lesson_create", args=[self.classroom.pk]),
            reverse("classroom_frequency", args=[self.classroom.pk]),
            *[reverse(name, args=[lesson.pk]) for name in (
                "lesson_detail", "lesson_edit", "attendance_form", "lesson_cancel",
            )],
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
                anonymous = Client()
                self.assertEqual(anonymous.get(url).status_code, 302)
                self.assertEqual(anonymous.post(url, {}).status_code, 302)

    def test_all_object_routes_reject_other_teacher(self):
        urls = [
            reverse("lesson_create", args=[self.other_classroom.pk]),
            reverse("classroom_frequency", args=[self.other_classroom.pk]),
            *[reverse(name, args=[self.other_lesson.pk]) for name in (
                "lesson_detail", "lesson_edit", "attendance_form", "lesson_cancel",
            )],
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)
                self.assertEqual(self.client.post(url, {}).status_code, 404)
        self.assertNotContains(self.client.get(reverse("lesson_list")), "Conteúdo sigiloso")
        self.assertNotContains(self.client.get(reverse("lesson_choose")), "Turma sigilosa")

    def test_filters_scope_school_year_subject_and_period(self):
        march = self.create_lesson()
        self.create_lesson(date="2026-05-01")
        response = self.client.get(reverse("lesson_list"), {
            "term": self.term.pk, "classroom": self.classroom.pk, "subject": self.subject.pk,
        })
        self.assertEqual([item["lesson"].pk for item in response.context["items"]], [march.pk])
        response = self.client.get(reverse("classroom_frequency", args=[self.classroom.pk]), {
            "start": "2026-02-01", "end": "2026-04-01",
        })
        self.assertEqual(response.context["rows"][0]["pending"], 2)
        for query in [{"classroom": self.other_classroom.pk}, {"subject": "bad"},
                      {"start": "2026-04-01", "end": "2026-02-01"}]:
            response = self.client.get(reverse("lesson_list"), query)
            self.assertTrue(response.context["filter_form"].errors)
            self.assertEqual(len(response.context["items"]), 0)

    def test_same_day_different_subject_is_allowed(self):
        self.create_lesson()
        self.classroom.subjects.add(self.unlinked)
        self.create_lesson(subject=self.unlinked.pk)
        self.assertEqual(Lesson.objects.filter(owner=self.teacher).count(), 2)

    def test_pending_calls_are_not_counted_as_presence(self):
        self.create_lesson()
        row = self.summary()[0]
        self.assertEqual((row["total"], row["recorded"], row["pending"]), (2, 0, 2))
        self.assertIsNone(row["percentage"])
        self.assertEqual(row["present"], 0)

    def test_new_enrollment_is_pending_without_rewriting_previous_calls(self):
        lesson = self.create_lesson()
        self.save_call(lesson)
        enrollment = Enrollment.objects.create(
            owner=self.teacher, classroom=self.classroom, starts_on=date(2026, 2, 1),
            student=Student.objects.create(owner=self.teacher, name="Bruno Exemplo"),
        )
        rows = {row["enrollment"].pk: row for row in self.summary()}
        self.assertEqual(rows[self.enrollment.pk]["percentage"], Decimal("100.0"))
        self.assertIsNone(rows[enrollment.pk]["percentage"])
        self.assertEqual(rows[enrollment.pk]["pending"], 2)
        response = self.client.get(reverse("lesson_detail", args=[lesson.pk]))
        self.assertContains(response, "Chamada parcial")

    def test_partial_absence_justification_and_pending_totals(self):
        lesson = self.create_lesson()
        self.create_lesson(date="2026-03-02", quantity=1)
        record = self.save_call(lesson, **{
            f"absences_{self.enrollment.pk}": 1, f"justified_{self.enrollment.pk}": 1,
            f"note_{self.enrollment.pk}": "Declaração apresentada",
        })
        self.assertEqual(record.justified_absences, 1)
        row = self.summary()[0]
        self.assertEqual((row["total"], row["recorded"], row["pending"]), (3, 2, 1))
        self.assertEqual((row["present"], row["absences"], row["justified"]), (1, 1, 1))
        self.assertEqual(row["percentage"], Decimal("50.0"))

    def test_all_absent_is_zero_percent_not_missing(self):
        lesson = self.create_lesson()
        self.save_call(lesson, **{f"absences_{self.enrollment.pk}": 2})
        self.assertEqual(self.summary()[0]["percentage"], Decimal("0.0"))
        self.assertContains(self.client.get(reverse("classroom_frequency",
                                                   args=[self.classroom.pk])), "0,0%")

    def test_blank_calls_and_invalid_counts_do_not_save(self):
        lesson = self.create_lesson()
        for invalid in [
            {f"absences_{self.enrollment.pk}": ""}, {f"absences_{self.enrollment.pk}": -1},
            {f"absences_{self.enrollment.pk}": 3}, {f"absences_{self.enrollment.pk}": "1.5"},
            {f"justified_{self.enrollment.pk}": 1},
            {f"absences_{self.enrollment.pk}": 1, f"justified_{self.enrollment.pk}": 1},
            {f"note_{self.enrollment.pk}": "Sem falta"},
        ]:
            response = self.client.post(reverse("attendance_form", args=[lesson.pk]),
                                        self.attendance_data(lesson, **invalid))
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["form"].errors)
        self.assertFalse(Attendance.objects.filter(owner=self.teacher).exists())
        self.assertEqual(lesson.history.count(), 1)

    def test_resubmission_does_not_duplicate_calls_or_history(self):
        lesson = self.create_lesson()
        self.save_call(lesson)
        self.save_call(lesson)
        self.assertEqual(lesson.attendance_records.count(), 1)
        self.assertEqual(lesson.history.count(), 2)

    def test_correction_requires_reason_and_preserves_old_values_and_actor(self):
        lesson = self.create_lesson()
        self.save_call(lesson)
        data = self.attendance_data(lesson, **{f"absences_{self.enrollment.pk}": 1})
        response = self.client.post(reverse("attendance_form", args=[lesson.pk]), data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("reason", response.context["form"].errors)
        data["reason"] = "Correção após conferir o registro da aula."
        self.assertEqual(self.client.post(reverse("attendance_form", args=[lesson.pk]), data).status_code, 302)
        event = lesson.history.first()
        self.assertEqual(event.actor, self.teacher)
        self.assertEqual(event.reason, data["reason"])
        self.assertEqual(event.changes[0]["before"], "0")
        self.assertEqual(event.changes[0]["after"], "1")
        self.assertEqual(self.summary()[0]["percentage"], Decimal("50.0"))
        self.assertEqual(lesson.attendance_records.count(), 1)

    def test_stale_attendance_page_cannot_overwrite_newer_changes(self):
        lesson = self.create_lesson()
        stale = self.attendance_data(lesson)
        self.save_call(lesson, **{f"absences_{self.enrollment.pk}": 1})
        stale["reason"] = "Tela antiga"
        response = self.client.post(reverse("attendance_form", args=[lesson.pk]), stale)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "mudou em outra aba")
        self.assertEqual(lesson.attendance_records.get().absences, 1)
        self.assertEqual(lesson.history.count(), 2)

    def test_roster_changes_require_reload(self):
        lesson = self.create_lesson()
        stale = self.attendance_data(lesson)
        self.enrollment.starts_on = date(2026, 2, 2)
        self.enrollment.save()
        response = self.client.post(reverse("attendance_form", args=[lesson.pk]), stale)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "matrículas mudaram")
        self.assertFalse(lesson.attendance_records.exists())

    def test_joining_and_leaving_dates_bound_expected_lessons(self):
        self.enrollment.starts_on = date(2026, 3, 2)
        self.enrollment.ends_on = date(2026, 3, 3)
        self.enrollment.status = Enrollment.Status.TRANSFERRED
        self.enrollment.save()
        lessons = [self.create_lesson(date=f"2026-03-0{day}", quantity=1) for day in range(1, 5)]
        for index, lesson in enumerate(lessons):
            form = AttendanceForm(lesson=lesson)
            self.assertEqual(len(form.roster), 1 if index in (1, 2) else 0)
        self.save_call(lessons[1])
        row = self.summary()[0]
        self.assertEqual((row["total"], row["recorded"], row["pending"]), (2, 1, 1))

    def test_empty_roster_cannot_be_saved(self):
        self.enrollment.starts_on = date(2026, 3, 2)
        self.enrollment.save()
        lesson = self.create_lesson(date="2026-03-01")
        response = self.client.post(reverse("attendance_form", args=[lesson.pk]),
                                    self.attendance_data(lesson))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Não há alunos matriculados")
        self.assertEqual(lesson.history.count(), 1)

    def test_existing_calls_block_incompatible_enrollment_dates(self):
        lesson = self.create_lesson()
        self.save_call(lesson)
        self.enrollment.starts_on = date(2026, 3, 2)
        with self.assertRaises(ValidationError):
            self.enrollment.save()
        self.enrollment.refresh_from_db()
        self.enrollment.ends_on = date(2026, 2, 28)
        self.enrollment.status = Enrollment.Status.TRANSFERRED
        with self.assertRaises(ValidationError):
            self.enrollment.save()

    def test_legacy_active_enrollment_without_start_is_flagged_but_preserved(self):
        Enrollment.objects.filter(pk=self.enrollment.pk).update(starts_on=None)
        lesson = self.create_lesson()
        self.assertEqual(len(AttendanceForm(lesson=lesson).roster), 1)
        self.assertTrue(self.summary()[0]["dates_missing"])

    def test_legacy_inactive_without_end_is_not_added_to_new_calls(self):
        Enrollment.objects.filter(pk=self.enrollment.pk).update(
            starts_on=None, status=Enrollment.Status.TRANSFERRED
        )
        lesson = self.create_lesson()
        self.assertFalse(AttendanceForm(lesson=lesson).roster)
        self.assertTrue(self.summary()[0]["dates_missing"])

    def test_dates_are_required_in_enrollment_form(self):
        response = self.client.post(reverse("record_edit", args=["matriculas", self.enrollment.pk]), {
            "status": "transferred", "starts_on": "2026-02-01",
        })
        self.assertIn("ends_on", response.context["form"].errors)
        response = self.client.post(reverse("record_edit", args=["matriculas", self.enrollment.pk]), {
            "status": "active", "starts_on": "",
        })
        self.assertIn("starts_on", response.context["form"].errors)

    def test_correction_of_content_is_audited(self):
        lesson = self.create_lesson()
        data = self.lesson_data(content="Frações e comparação", version=lesson.version)
        response = self.client.post(reverse("lesson_edit", args=[lesson.pk]), data)
        self.assertIn("reason", response.context["form"].errors)
        data["reason"] = "Complementação do conteúdo ministrado"
        self.assertEqual(self.client.post(reverse("lesson_edit", args=[lesson.pk]), data).status_code, 302)
        lesson.refresh_from_db()
        self.assertEqual(lesson.content, data["content"])
        self.assertEqual(lesson.history.first().changes[0]["before"], "Frações equivalentes")

    def test_stale_lesson_edit_cannot_overwrite_newer_content(self):
        lesson = self.create_lesson()
        stale = self.lesson_data(content="Antigo", version=lesson.version, reason="Correção")
        fresh = self.lesson_data(content="Atualizado", version=lesson.version, reason="Correção")
        self.assertEqual(self.client.post(reverse("lesson_edit", args=[lesson.pk]), fresh).status_code, 302)
        response = self.client.post(reverse("lesson_edit", args=[lesson.pk]), stale)
        self.assertContains(response, "mudou em outra aba")
        lesson.refresh_from_db()
        self.assertEqual(lesson.content, "Atualizado")

    def test_date_and_quantity_can_change_before_call(self):
        lesson = self.create_lesson()
        self.assertEqual(self.client.post(reverse("lesson_edit", args=[lesson.pk]), self.lesson_data(
            date="2026-03-02", quantity=3, version=lesson.version, reason="Ajuste do encontro"
        )).status_code, 302)
        lesson.refresh_from_db()
        self.assertEqual((lesson.date, lesson.quantity), (date(2026, 3, 2), 3))
        self.assertEqual(self.summary()[0]["pending"], 3)

    def test_structure_cannot_change_after_attendance_even_with_forged_post(self):
        lesson = self.create_lesson()
        self.save_call(lesson)
        lesson.refresh_from_db()
        self.client.post(reverse("lesson_edit", args=[lesson.pk]), self.lesson_data(
            quantity=8, date="2026-03-02", version=lesson.version, reason="Tentativa"
        ))
        lesson.refresh_from_db()
        self.assertEqual((lesson.quantity, lesson.date), (2, date(2026, 3, 1)))
        lesson.quantity = 3
        with self.assertRaises(ValidationError):
            lesson.save()

    def test_used_subject_cannot_be_removed_and_class_year_is_preserved(self):
        self.create_lesson()
        response = self.client.post(reverse("record_edit", args=["turmas", self.classroom.pk]), {
            "name": self.classroom.name, "school": self.school.pk,
            "academic_year": self.year.pk, "shift": "morning", "subjects": [],
        })
        self.assertIn("subjects", response.context["form"].errors)
        self.year.year = 2027
        with self.assertRaises(ValidationError):
            self.year.save()

    def test_cancel_keeps_history_and_call_but_excludes_frequency(self):
        lesson = self.create_lesson()
        self.save_call(lesson, **{f"absences_{self.enrollment.pk}": 1})
        lesson.refresh_from_db()
        response = self.client.post(reverse("lesson_cancel", args=[lesson.pk]), {
            "version": lesson.version, "reason": "Encontro lançado na data errada",
        })
        self.assertEqual(response.status_code, 302)
        lesson.refresh_from_db()
        self.assertTrue(lesson.is_cancelled)
        self.assertEqual(lesson.attendance_records.count(), 1)
        self.assertEqual(lesson.history.count(), 3)
        self.assertEqual(self.summary()[0]["total"], 0)
        self.assertEqual(len(self.client.get(reverse("lesson_list")).context["items"]), 0)
        self.assertEqual(len(self.client.get(reverse("lesson_list"),
                                            {"state": "cancelled"}).context["items"]), 1)
        replacement = self.create_lesson()
        self.assertNotEqual(replacement.pk, lesson.pk)

    def test_cancel_requires_reason_and_current_version(self):
        lesson = self.create_lesson()
        response = self.client.post(reverse("lesson_cancel", args=[lesson.pk]),
                                    {"version": lesson.version})
        self.assertIn("reason", response.context["form"].errors)
        self.save_call(lesson)
        response = self.client.post(reverse("lesson_cancel", args=[lesson.pk]), {
            "version": 1, "reason": "Cancelamento em tela antiga",
        })
        self.assertContains(response, "mudou em outra aba")
        lesson.refresh_from_db()
        self.assertFalse(lesson.is_cancelled)

    def test_cancelled_lesson_is_read_only(self):
        lesson = self.create_lesson()
        data = self.attendance_data(lesson)
        self.client.post(reverse("lesson_cancel", args=[lesson.pk]),
                         {"version": lesson.version, "reason": "Correção"})
        for name in ("lesson_edit", "attendance_form"):
            self.assertRedirects(self.client.post(reverse(name, args=[lesson.pk]), data),
                                 reverse("lesson_detail", args=[lesson.pk]))
        self.assertFalse(lesson.attendance_records.exists())
        lesson.refresh_from_db()
        with self.assertRaises(ValidationError):
            lesson.save()

    def test_audit_is_immutable(self):
        lesson = self.create_lesson()
        event = lesson.history.get()
        event.reason = "Alteração indevida"
        with self.assertRaises(ValidationError):
            event.save()

    def test_attendance_and_audit_rollback_together_on_failure(self):
        lesson = self.create_lesson()
        with patch("diary.teaching_services.write_audit", side_effect=IntegrityError("simulated")):
            response = self.client.post(reverse("attendance_form", args=[lesson.pk]),
                                        self.attendance_data(lesson))
        self.assertEqual(response.status_code, 200)
        lesson.refresh_from_db()
        self.assertFalse(lesson.attendance_records.exists())
        self.assertEqual(lesson.version, 1)
        self.assertEqual(lesson.history.count(), 1)

    def test_lesson_creation_rolls_back_if_audit_cannot_be_saved(self):
        with patch("diary.teaching_services.write_audit", side_effect=IntegrityError("simulated")):
            response = self.client.post(reverse("lesson_create", args=[self.classroom.pk]),
                                        self.lesson_data())
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Lesson.objects.filter(owner=self.teacher).exists())

    def test_invalid_row_prevents_saving_any_student(self):
        enrollment = Enrollment.objects.create(
            owner=self.teacher, classroom=self.classroom,
            student=Student.objects.create(owner=self.teacher, name="Bruno"),
            starts_on=date(2026, 2, 1),
        )
        lesson = self.create_lesson()
        response = self.client.post(reverse("attendance_form", args=[lesson.pk]),
                                    self.attendance_data(lesson, **{f"absences_{enrollment.pk}": 9}))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(lesson.attendance_records.exists())

    def test_forged_extra_student_is_not_written(self):
        lesson = self.create_lesson()
        data = self.attendance_data(lesson, **{
            f"absences_{self.other_enrollment.pk}": 2,
            f"justified_{self.other_enrollment.pk}": 0,
            f"note_{self.other_enrollment.pk}": "",
            "owner": self.other.pk,
        })
        self.assertEqual(self.client.post(reverse("attendance_form", args=[lesson.pk]), data).status_code, 302)
        self.assertEqual(list(lesson.attendance_records.values_list("enrollment_id", flat=True)),
                         [self.enrollment.pk])
        self.assertFalse(Attendance.objects.filter(owner=self.other).exists())

    def test_model_blocks_cross_tenant_and_cross_class_attendance(self):
        lesson = self.create_lesson()
        with self.assertRaises(ValidationError):
            Attendance.objects.create(owner=self.teacher, lesson=lesson,
                                      enrollment=self.other_enrollment)
        classroom = Classroom.objects.create(owner=self.teacher, school=self.school,
                                            academic_year=self.year, name="6º B")
        enrollment = Enrollment.objects.create(owner=self.teacher, classroom=classroom,
                                               student=self.student, starts_on=date(2026, 2, 1))
        with self.assertRaises(ValidationError):
            Attendance.objects.create(owner=self.teacher, lesson=lesson, enrollment=enrollment)

    def test_csrf_protects_lesson_call_and_cancellation(self):
        lesson = self.create_lesson()
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.teacher)
        for name in ("lesson_edit", "attendance_form", "lesson_cancel"):
            self.assertEqual(csrf_client.post(reverse(name, args=[lesson.pk]), {}).status_code, 403)

    def test_content_and_justification_are_escaped(self):
        lesson = self.create_lesson(content="<script>alert(1)</script>")
        self.save_call(lesson, **{
            f"absences_{self.enrollment.pk}": 1, f"justified_{self.enrollment.pk}": 1,
            f"note_{self.enrollment.pk}": "<script>alert(2)</script>",
        })
        response = self.client.get(reverse("lesson_detail", args=[lesson.pk]))
        self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt;")
        self.assertNotContains(response, "<script>alert(2)</script>")
