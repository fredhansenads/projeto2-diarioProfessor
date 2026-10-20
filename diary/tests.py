from datetime import date
import re

from django.contrib.auth.models import User
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .catalog import CATALOG
from .models import AcademicYear, Classroom, Enrollment, School, Student, Subject, Term


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class DiaryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = User.objects.create_user(
            username="professora", email="professora@example.com", password="SenhaTeste!2026"
        )
        cls.other = User.objects.create_user(username="outro", password="OutraSenha!2026")
        cls.school = School.objects.create(owner=cls.teacher, name="Escola Horizonte")
        cls.other_school = School.objects.create(owner=cls.other, name="Escola Privada Outro")
        cls.year = AcademicYear.objects.create(owner=cls.teacher, year=2026)
        cls.other_year = AcademicYear.objects.create(owner=cls.other, year=2026)
        cls.subject = Subject.objects.create(owner=cls.teacher, name="Matemática")
        cls.other_subject = Subject.objects.create(owner=cls.other, name="Disciplina Secreta")
        cls.classroom = Classroom.objects.create(
            owner=cls.teacher, name="6º A", school=cls.school, academic_year=cls.year
        )
        cls.other_classroom = Classroom.objects.create(
            owner=cls.other, name="Turma Secreta", school=cls.other_school,
            academic_year=cls.other_year
        )
        cls.student = Student.objects.create(owner=cls.teacher, name="Ana Exemplo")
        cls.other_student = Student.objects.create(owner=cls.other, name="Aluno Secreto")
        cls.enrollment = Enrollment.objects.create(
            owner=cls.teacher, student=cls.student, classroom=cls.classroom
        )
        cls.other_enrollment = Enrollment.objects.create(
            owner=cls.other, student=cls.other_student, classroom=cls.other_classroom
        )
        cls.term = Term.objects.create(owner=cls.teacher, school=cls.school, academic_year=cls.year,
                                      name="1º bimestre", start_date=date(2026, 2, 1),
                                      end_date=date(2026, 4, 1))
        cls.other_term = Term.objects.create(owner=cls.other, school=cls.other_school, academic_year=cls.other_year,
                                            name="Período Secreto", start_date=date(2026, 2, 1),
                                            end_date=date(2026, 4, 1))

    def setUp(self):
        self.client.force_login(self.teacher)

    def test_anonymous_cannot_access_diary_or_any_catalog(self):
        self.client.logout()
        urls = [reverse("dashboard"), reverse("classroom_detail", args=[self.classroom.pk])]
        for kind in CATALOG:
            urls.extend([reverse("record_list", args=[kind]), reverse("record_create", args=[kind])])
        for url in urls:
            with self.subTest(url=url):
                self.assertRedirects(self.client.get(url), f"/conta/login/?next={url}",
                                     fetch_redirect_response=False)

    def test_all_lists_and_forms_render(self):
        for kind, config in CATALOG.items():
            with self.subTest(kind=kind):
                for name in ("record_list", "record_create"):
                    self.assertEqual(self.client.get(reverse(name, args=[kind])).status_code, 200)
                obj = config.model.objects.filter(owner=self.teacher).first()
                self.assertEqual(self.client.get(
                    reverse("record_edit", args=[kind, obj.pk])).status_code, 200)

    def test_dashboard_counts_only_own_records(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual([stat["value"] for stat in response.context["stats"]], [1, 1, 1, 1])
        self.assertNotContains(response, "Turma Secreta")
        self.assertContains(response, "6º A")
        self.assertIn("no-store", response.headers["Cache-Control"])

    def test_every_catalog_isolates_records_and_rejects_foreign_edit(self):
        for kind, config in CATALOG.items():
            with self.subTest(kind=kind):
                obj = config.model.objects.filter(owner=self.other).first()
                response = self.client.get(reverse("record_list", args=[kind]))
                self.assertEqual([row["pk"] for row in response.context["rows"]],
                                 list(config.model.objects.filter(owner=self.teacher)
                                      .values_list("pk", flat=True)))
                url = reverse("record_edit", args=[kind, obj.pk])
                self.assertEqual(self.client.get(url).status_code, 404)
                self.assertEqual(self.client.post(url, {"name": "Ataque"}).status_code, 404)

    def test_classroom_detail_is_private(self):
        self.assertEqual(self.client.get(reverse("classroom_detail",
                                                args=[self.other_classroom.pk])).status_code, 404)
        response = self.client.get(reverse("classroom_detail", args=[self.classroom.pk]))
        self.assertContains(response, "Ana Exemplo")
        self.assertNotContains(response, "Aluno Secreto")

    def test_owner_cannot_be_supplied_by_browser(self):
        response = self.client.post(reverse("record_create", args=["escolas"]),
                                    {"name": "Nova Escola", "owner": self.other.pk})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(School.objects.get(name="Nova Escola").owner, self.teacher)

    def test_full_registration_flow(self):
        steps = [
            ("escolas", {"name": "Escola Nova", "city": "Recife"}),
            ("anos-letivos", {"year": 2027}),
            ("disciplinas", {"name": "Português"}),
            ("alunos", {"name": "Bruno Exemplo", "reference": "B-01"}),
        ]
        for kind, data in steps:
            self.assertEqual(self.client.post(reverse("record_create", args=[kind]), data).status_code, 302)
        school = School.objects.get(name="Escola Nova")
        year = AcademicYear.objects.get(owner=self.teacher, year=2027)
        subject = Subject.objects.get(name="Português")
        response = self.client.post(reverse("record_create", args=["turmas"]), {
            "name": "7º A", "school": school.pk, "academic_year": year.pk,
            "shift": "afternoon", "subjects": [subject.pk],
        })
        self.assertEqual(response.status_code, 302)
        classroom = Classroom.objects.get(name="7º A")
        self.assertEqual(list(classroom.subjects.all()), [subject])
        self.assertEqual(self.client.post(reverse("record_create", args=["periodos"]), {
            "name": "Semestre 1", "school": school.pk, "academic_year": year.pk,
            "start_date": "2027-02-01", "end_date": "2027-06-30",
        }).status_code, 302)
        self.assertEqual(self.client.post(reverse("record_create", args=["matriculas"]), {
            "student": Student.objects.get(name="Bruno Exemplo").pk,
            "classroom": classroom.pk, "status": "active", "starts_on": "2027-02-01",
        }).status_code, 302)

    def test_forged_relations_are_rejected(self):
        cases = [
            ("turmas", {"name": "Invasão", "school": self.other_school.pk,
                        "academic_year": self.year.pk, "shift": "morning"}, "school"),
            ("turmas", {"name": "Invasão", "school": self.school.pk,
                        "academic_year": self.other_year.pk, "shift": "morning"}, "academic_year"),
            ("turmas", {"name": "Invasão", "school": self.school.pk,
                        "academic_year": self.year.pk, "shift": "morning",
                        "subjects": [self.other_subject.pk]}, "subjects"),
            ("matriculas", {"student": self.other_student.pk,
                            "classroom": self.classroom.pk, "status": "active"}, "student"),
            ("matriculas", {"student": self.student.pk,
                            "classroom": self.other_classroom.pk, "status": "active"}, "classroom"),
            ("periodos", {"name": "Invasão", "school": self.school.pk, "academic_year": self.other_year.pk,
                          "start_date": "2026-01-01", "end_date": "2026-03-01"}, "academic_year"),
        ]
        for kind, data, field in cases:
            with self.subTest(kind=kind, field=field):
                count = CATALOG[kind].model.objects.count()
                response = self.client.post(reverse("record_create", args=[kind]), data)
                self.assertEqual(response.status_code, 200)
                self.assertIn(field, response.context["form"].errors)
                self.assertEqual(CATALOG[kind].model.objects.count(), count)

    def test_empty_forms_show_errors_instead_of_crashing(self):
        for kind in CATALOG:
            response = self.client.post(reverse("record_create", args=[kind]), {})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["form"].errors)

    def test_duplicate_records_are_form_errors(self):
        cases = [
            ("escolas", {"name": self.school.name}),
            ("anos-letivos", {"year": self.year.year}),
            ("disciplinas", {"name": self.subject.name}),
            ("matriculas", {"student": self.student.pk,
                            "classroom": self.classroom.pk, "status": "active"}),
        ]
        for kind, data in cases:
            response = self.client.post(reverse("record_create", args=[kind]), data)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["form"].errors)

    def test_period_rejects_reversed_dates_and_wrong_year(self):
        for start, end in [("2026-04-01", "2026-02-01"), ("2025-02-01", "2026-04-01")]:
            response = self.client.post(reverse("record_create", args=["periodos"]), {
                "name": "Inválido", "school": self.school.pk, "academic_year": self.year.pk,
                "start_date": start, "end_date": end,
            })
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["form"].errors)

    def test_year_with_existing_periods_cannot_move_to_another_year(self):
        response = self.client.post(reverse("record_edit", args=["anos-letivos", self.year.pk]),
                                    {"year": 2027})
        self.assertEqual(response.status_code, 200)
        self.year.refresh_from_db()
        self.assertEqual(self.year.year, 2026)

    def test_schools_can_have_different_calendars_in_same_year(self):
        second_school = School.objects.create(owner=self.teacher, name="Segunda escola")
        term = Term.objects.create(owner=self.teacher, school=second_school,
                                   academic_year=self.year, name="1º bimestre",
                                   start_date=date(2026, 2, 15), end_date=date(2026, 4, 15))
        self.assertNotEqual(term.start_date, self.term.start_date)

    def test_period_cannot_reference_another_teachers_school(self):
        response = self.client.post(reverse("record_create", args=["periodos"]), {
            "name": "Invasão", "school": self.other_school.pk, "academic_year": self.year.pk,
            "start_date": "2026-02-01", "end_date": "2026-04-01",
        })
        self.assertIn("school", response.context["form"].errors)

    def test_model_rejects_cross_owner_relationships(self):
        with self.assertRaises(ValidationError):
            Enrollment.objects.create(owner=self.teacher, student=self.other_student,
                                      classroom=self.classroom)
        with self.assertRaises(ValidationError):
            Classroom.objects.create(owner=self.teacher, name="Inválida",
                                     school=self.other_school, academic_year=self.year)

    def test_owner_cannot_be_reassigned(self):
        self.school.owner = self.other
        with self.assertRaises(ValidationError):
            self.school.save()

    def test_enrollment_changes_status_without_changing_student_or_class(self):
        response = self.client.post(reverse("record_edit", args=["matriculas", self.enrollment.pk]), {
            "status": "transferred", "student": self.other_student.pk,
            "classroom": self.other_classroom.pk, "starts_on": "2026-02-01", "ends_on": "2026-04-01",
        })
        self.assertEqual(response.status_code, 302)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, "transferred")
        self.assertEqual(self.enrollment.student_id, self.student.pk)
        self.assertEqual(self.enrollment.classroom_id, self.classroom.pk)
        self.assertEqual(Enrollment.objects.filter(owner=self.teacher).count(), 1)

    def test_classroom_with_enrollments_preserves_school_and_year(self):
        next_year = AcademicYear.objects.create(owner=self.teacher, year=2027)
        response = self.client.post(reverse("record_edit", args=["turmas", self.classroom.pk]), {
            "name": "6º A", "school": self.school.pk,
            "academic_year": next_year.pk, "shift": "morning",
        })
        self.assertEqual(response.status_code, 200)
        self.classroom.refresh_from_db()
        self.assertEqual(self.classroom.academic_year, self.year)

    def test_search_and_pagination_remain_scoped(self):
        response = self.client.get(reverse("record_list", args=["alunos"]), {"q": "Secreto"})
        self.assertEqual(response.context["page_obj"].paginator.count, 0)
        for index in range(22):
            Student.objects.create(owner=self.teacher, name=f"Aluno de teste {index:02d}")
        response = self.client.get(reverse("record_list", args=["alunos"]), {"page": "2"})
        self.assertEqual(len(response.context["rows"]), 3)
        self.assertEqual(response.context["page_obj"].paginator.count, 23)

    def test_html_content_is_escaped(self):
        Student.objects.create(owner=self.teacher, name="<script>alert(1)</script>")
        response = self.client.get(reverse("record_list", args=["alunos"]))
        self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt;")
        self.assertNotContains(response, "<script>alert(1)</script>")

    def test_csrf_is_required_for_writes(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.teacher)
        self.assertEqual(csrf_client.post(reverse("record_create", args=["escolas"]),
                                         {"name": "Sem token"}).status_code, 403)

    def test_unknown_catalog_returns_not_found(self):
        self.assertEqual(self.client.get("/cadastros/desconhecido/").status_code, 404)

    def test_account_creation_and_login(self):
        self.client.logout()
        response = self.client.post(reverse("register"), {
            "username": "nova.professora", "first_name": "Marina", "email": "marina@example.com",
            "password1": "UmaSenhaBoa!2026", "password2": "UmaSenhaBoa!2026",
        })
        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(User.objects.get(username="nova.professora").first_name, "Marina")
        self.client.post(reverse("logout"))
        response = self.client.post(reverse("login"), {
            "username": "nova.professora", "password": "UmaSenhaBoa!2026",
            "next": "https://example.org/",
        })
        self.assertRedirects(response, reverse("dashboard"))

    def test_weak_password_is_rejected(self):
        self.client.logout()
        response = self.client.post(reverse("register"), {
            "username": "new", "first_name": "Nova", "email": "nova@example.com",
            "password1": "12345678", "password2": "12345678",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="new").exists())

    def test_password_recovery_end_to_end(self):
        self.client.logout()
        response = self.client.post(reverse("password_reset"),
                                    {"email": "professora@example.com"})
        self.assertRedirects(response, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        reset_url = re.search(r"http://testserver([^\s]+)", mail.outbox[0].body).group(1)
        response = self.client.get(reset_url)
        self.assertEqual(response.status_code, 302)
        response = self.client.post(response.url, {
            "new_password1": "SenhaRenovada!2027", "new_password2": "SenhaRenovada!2027",
        })
        self.assertRedirects(response, reverse("password_reset_complete"))
        self.teacher.refresh_from_db()
        self.assertTrue(self.teacher.check_password("SenhaRenovada!2027"))

    def test_unknown_email_does_not_disclose_account_existence(self):
        self.client.logout()
        self.assertRedirects(self.client.post(reverse("password_reset"),
                                             {"email": "inexistente@example.com"}),
                             reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 0)
