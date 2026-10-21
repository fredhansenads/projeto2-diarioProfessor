from datetime import timedelta
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
from unittest.mock import patch

from axes.models import AccessAttempt
from django.contrib.auth.models import User
from django.db import DatabaseError
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .backups import backup_database, restore_sqlite, validate_backup
from .checks import production_configuration
from .models import AcademicYear, Assessment, Attendance, Classroom, Enrollment, Grade, Gradebook, Lesson, School, Student, Subject, Term


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class SecurityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="prof", password="SenhaFicticia!2026")

    def test_public_signup_get_and_post_closed_and_login_has_no_signup_link(self):
        for response in (self.client.get(reverse("register")), self.client.post(reverse("register"), {
            "username": "invasor", "password1": "SenhaFicticia!2026", "password2": "SenhaFicticia!2026"})):
            self.assertEqual(response.status_code, 403)
            self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(User.objects.count(), 1)
        self.assertNotContains(self.client.get(reverse("login")), 'href="/criar-conta/"')

    def test_teacher_cannot_enter_account_admin_but_superuser_can(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/admin/auth/user/add/").status_code, 302)
        admin = User.objects.create_superuser("admin", password="SenhaFicticia!2026")
        self.client.force_login(admin)
        self.assertContains(self.client.get("/admin/auth/user/add/"), "username")

    def test_five_failures_lock_even_valid_password_and_spoofed_forwarded_ip(self):
        for _ in range(5):
            response = self.client.post(reverse("login"), {"username": "prof", "password": "errada"})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response["Retry-After"], "900")
        self.assertIn("no-store", response["Cache-Control"])
        response = self.client.post(reverse("login"), {"username": "prof", "password": "SenhaFicticia!2026"}, HTTP_X_FORWARDED_FOR="203.0.113.1")
        self.assertEqual(response.status_code, 429)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertTrue(AccessAttempt.objects.filter(ip_address="127.0.0.1").exists())

    def test_expired_lock_allows_login_and_clears_failure_count(self):
        for _ in range(5):
            self.client.post(reverse("login"), {"username": "prof", "password": "errada"})
        AccessAttempt.objects.update(attempt_time=timezone.now() - timedelta(minutes=16))
        self.assertEqual(self.client.post(reverse("login"), {"username": "prof", "password": "SenhaFicticia!2026"}).status_code, 302)
        self.assertFalse(AccessAttempt.objects.exists())

    def test_same_school_ip_does_not_lock_another_teacher(self):
        User.objects.create_user(username="colega", password="SenhaFicticia!2026")
        for _ in range(5):
            self.client.post(reverse("login"), {"username": "prof", "password": "errada"})
        self.assertEqual(self.client.post(reverse("login"), {"username": "colega", "password": "SenhaFicticia!2026"}).status_code, 302)

    def test_admin_login_is_also_throttled(self):
        for _ in range(5):
            response = self.client.post("/admin/login/", {"username": "admin", "password": "errada"})
        self.assertEqual(response.status_code, 429)

    def test_csrf_failure_has_help_and_no_technical_reason(self):
        response = Client(enforce_csrf_checks=True).post(reverse("login"), {"username": "prof"})
        self.assertContains(response, "Atualize sua sessão", status_code=403)
        self.assertNotContains(response, "CSRF cookie not set", status_code=403)
        self.assertIn("no-store", response["Cache-Control"])

    def test_health_checks_database_and_never_exposes_exception(self):
        self.assertEqual(self.client.get(reverse("health")).json(), {"status": "ok"})
        with patch("diary.security.connection.cursor", side_effect=DatabaseError("secret-host-password")):
            response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unavailable"})
        self.assertIn("no-store", response["Cache-Control"])


class BackupTests(SimpleTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.live = self.root / "live.sqlite3"
        with closing(sqlite3.connect(self.live)) as connection:
            connection.execute("CREATE TABLE record (name TEXT, score TEXT)")
            connection.execute("INSERT INTO record VALUES ('Júlia', '8.50')")
            connection.commit()
        self.database = {"ENGINE": "django.db.backends.sqlite3", "NAME": self.live}
        self.backup = self.root / "snapshot.sqlite3"

    def test_backup_restore_preserves_data_and_does_not_revert_live_database(self):
        backup_database(self.database, self.backup)
        with closing(sqlite3.connect(self.live)) as connection:
            connection.execute("UPDATE record SET score='9.00'")
            connection.commit()
        restored = self.root / "restored.sqlite3"
        restore_sqlite(self.backup, restored)
        with closing(sqlite3.connect(restored)) as connection:
            self.assertEqual(connection.execute("SELECT * FROM record").fetchone(), ("Júlia", "8.50"))
        with closing(sqlite3.connect(self.live)) as connection:
            self.assertEqual(connection.execute("SELECT score FROM record").fetchone()[0], "9.00")

    def test_backup_and_restore_refuse_existing_targets(self):
        backup_database(self.database, self.backup)
        for operation in (lambda: backup_database(self.database, self.backup),
                          lambda: restore_sqlite(self.backup, self.live)):
            with self.assertRaises((FileExistsError, ValueError)):
                operation()
        self.assertEqual(validate_backup(self.backup)["format"], "sqlite")

    def test_corrupted_backup_refused_before_creating_restore_target(self):
        backup_database(self.database, self.backup)
        with self.backup.open("ab") as handle:
            handle.write(b"corruption")
        restored = self.root / "restored.sqlite3"
        with self.assertRaises(ValueError):
            restore_sqlite(self.backup, restored)
        self.assertFalse(restored.exists())

    def test_missing_source_does_not_create_empty_live_database(self):
        missing = self.root / "missing.sqlite3"
        with self.assertRaises(ValueError):
            backup_database({**self.database, "NAME": missing}, self.backup)
        self.assertFalse(missing.exists())
        self.assertFalse(self.backup.exists())


class DeploymentChecksTests(SimpleTestCase):
    def test_development_profile_cannot_pass_release_gate(self):
        identifiers = {item.id for item in production_configuration(None)}
        self.assertIn("diary.E003", identifiers)
        self.assertIn("diary.E005", identifiers)

    @override_settings(DEBUG=False, DATABASES={"default": {"ENGINE": "django.db.backends.postgresql"}},
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend", EMAIL_HOST="smtp.example.test",
        EMAIL_USE_TLS=True, EMAIL_USE_SSL=False, DEFAULT_FROM_EMAIL="diario@example.test",
        ALLOWED_HOSTS=["diarioprofessor.santustech.com.br"], PUBLIC_REGISTRATION_ENABLED=False)
    def test_complete_configuration_passes_but_does_not_claim_external_services_validated(self):
        self.assertEqual(production_configuration(None), [])
        with override_settings(PUBLIC_REGISTRATION_ENABLED=True):
            self.assertEqual([item.id for item in production_configuration(None)], ["diary.E006"])


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class FullTeachingCycleTests(TestCase):
    def test_teacher_cycle_with_csrf_and_second_account_isolation(self):
        teacher = User.objects.create_user(username="ciclo", password="SenhaFicticia!2026")
        self.client = Client(enforce_csrf_checks=True)

        def submit(url, values):
            page = self.client.get(url)
            self.assertEqual(page.status_code, 200)
            form = page.context["form"]
            payload = {name: field.value() if field.value() is not None else "" for name, field in
                       ((name, form[name]) for name in form.fields)}
            payload.update(values)
            payload["csrfmiddlewaretoken"] = self.client.cookies["csrftoken"].value
            response = self.client.post(url, payload)
            self.assertEqual(response.status_code, 302, getattr(response, "context", None))

        submit(reverse("login"), {"username": "ciclo", "password": "SenhaFicticia!2026"})
        today = timezone.localdate()
        submit(reverse("record_create", args=["escolas"]), {"name": "Escola do ciclo", "city": "Teste"})
        school = School.objects.get(owner=teacher)
        submit(reverse("record_create", args=["anos-letivos"]), {"year": today.year})
        year = AcademicYear.objects.get(owner=teacher)
        submit(reverse("record_create", args=["periodos"]), {"school": school.pk, "academic_year": year.pk,
            "name": "Ano", "start_date": f"{today.year}-01-01", "end_date": f"{today.year}-12-31"})
        term = Term.objects.get(owner=teacher)
        submit(reverse("record_create", args=["disciplinas"]), {"name": "Matemática"})
        subject = Subject.objects.get(owner=teacher)
        submit(reverse("record_create", args=["turmas"]), {"school": school.pk, "academic_year": year.pk,
            "name": "Turma ciclo", "shift": "morning", "subjects": [subject.pk]})
        room = Classroom.objects.get(owner=teacher)
        submit(reverse("record_create", args=["alunos"]), {"name": "Aluno fictício"})
        student = Student.objects.get(owner=teacher)
        submit(reverse("record_create", args=["matriculas"]), {"student": student.pk, "classroom": room.pk,
            "status": "active", "starts_on": today.isoformat()})
        enrollment = Enrollment.objects.get(owner=teacher)
        submit(reverse("lesson_create", args=[room.pk]), {"subject": subject.pk, "date": today.isoformat(),
            "quantity": 2, "content": "Frações"})
        lesson = Lesson.objects.get(owner=teacher)
        submit(reverse("attendance_form", args=[lesson.pk]), {f"absences_{enrollment.pk}": 1,
            f"justified_{enrollment.pk}": 0})
        self.assertEqual(Attendance.objects.get().absences, 1)
        submit(reverse("book_create"), {"classroom": room.pk, "subject": subject.pk, "term": term.pk})
        book = Gradebook.objects.get(owner=teacher)
        submit(reverse("assessment_create", args=[book.pk]), {"title": "Prova", "date": today.isoformat(), "kind": "test"})
        assessment = Assessment.objects.get(owner=teacher)
        submit(reverse("grade_form", args=[assessment.pk]), {f"status_{enrollment.pk}": "submitted", f"score_{enrollment.pk}": "8,5"})
        self.assertEqual(str(Grade.objects.get().score), "8.50")
        parameters = {"classroom": room.pk, "term": term.pk, "subject": subject.pk}
        self.assertContains(self.client.get(reverse("report"), parameters), "8,5")
        csv = self.client.get(reverse("report"), {**parameters, "format": "csv"})
        self.assertIn(b"8,5", csv.content)
        pdf = self.client.get(reverse("report"), {**parameters, "format": "pdf"})
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        self.assertEqual(lesson.history.count(), 2)
        self.assertEqual(book.history.count(), 3)
        other = User.objects.create_user(username="outra")
        self.client.force_login(other)
        self.assertEqual(self.client.get(reverse("lesson_detail", args=[lesson.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("book_detail", args=[book.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("report"), {**parameters, "format": "csv"}).status_code, 400)
