from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .grading_forms import GradeForm
from .grading_services import grade_summary
from .models import AcademicYear, Assessment, Classroom, Enrollment, Grade, GradeAudit, Gradebook, School, Student, Subject, Term


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class GradingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="professor.notas", password="Teste-local-2026")
        cls.other = User.objects.create_user(username="outro.notas", password="Teste-local-2026")
        cls.school = School.objects.create(owner=cls.owner, name="Escola de testes")
        cls.year = AcademicYear.objects.create(owner=cls.owner, year=2026)
        cls.subject = Subject.objects.create(owner=cls.owner, name="Matemática")
        cls.room = Classroom.objects.create(owner=cls.owner, school=cls.school, academic_year=cls.year, name="6º A")
        cls.room.subjects.add(cls.subject)
        cls.term = Term.objects.create(owner=cls.owner, school=cls.school, academic_year=cls.year,
                                       name="1º semestre", start_date=date(2026, 1, 1), end_date=date(2026, 6, 30))
        cls.enrollment = Enrollment.objects.create(owner=cls.owner, classroom=cls.room,
            student=Student.objects.create(owner=cls.owner, name="Ana Teste"), starts_on=date(2026, 1, 1))
        cls.book = Gradebook.objects.create(owner=cls.owner, classroom=cls.room, subject=cls.subject,
                                            term=cls.term, version=1)

    def setUp(self):
        self.client.force_login(self.owner)

    def assessment(self, **kwargs):
        defaults = dict(owner=self.owner, gradebook=self.book, title="Prova de teste", date=date(2026, 3, 1),
                        maximum=Decimal("10"), weight=Decimal("1"))
        defaults.update(kwargs)
        return Assessment.objects.create(**defaults)

    def grade(self, assessment, score="8", **kwargs):
        values = dict(owner=self.owner, assessment=assessment, enrollment=self.enrollment,
                      status="submitted", score=Decimal(score) if score is not None else None)
        values.update(kwargs)
        return Grade.objects.create(**values)

    def result(self):
        self.book.refresh_from_db()
        return grade_summary(self.book)["rows"][0]

    def grades_data(self, assessment, **kwargs):
        assessment.refresh_from_db()
        assessment.gradebook.refresh_from_db()
        form = GradeForm(assessment=assessment)
        data = {"version": assessment.gradebook.version, "roster_token": form.fields["roster_token"].initial, "reason": ""}
        for enrollment in form.roster:
            data.update({f"status_{enrollment.pk}": "pending", f"score_{enrollment.pk}": "", f"note_{enrollment.pk}": ""})
        data.update(kwargs)
        return data

    def post_grade(self, assessment, score="8", status="submitted", **kwargs):
        data = self.grades_data(assessment, **{
            f"status_{self.enrollment.pk}": status, f"score_{self.enrollment.pk}": score, **kwargs})
        return self.client.post(reverse("grade_form", args=[assessment.pk]), data)

    def policy_data(self, **kwargs):
        self.book.refresh_from_db()
        data = {"classroom": self.room.pk, "subject": self.subject.pk, "term": self.term.pk,
                "calculation": "simple", "scale": "10", "minimum": "6", "precision": 1,
                "rounding": "half_up", "recovery": "none", "version": self.book.version, "reason": "Regra da escola"}
        data.update(kwargs)
        return data

    def test_simple_normalizes_different_maxima(self):
        self.grade(self.assessment(maximum=Decimal("20")), "16")
        self.grade(self.assessment(), "6")
        self.assertEqual(self.result()["final"], Decimal("7.0"))

    def test_weighted_known_example(self):
        self.book.calculation = "weighted"
        self.book.save()
        self.grade(self.assessment(weight=Decimal("3")), "8")
        self.grade(self.assessment(weight=Decimal("1")), "4")
        self.assertEqual(self.result()["final"], Decimal("7.0"))

    def test_missing_grade_is_partial_not_zero(self):
        self.grade(self.assessment(), "8")
        self.assessment()
        result = self.result()
        self.assertEqual(result["original"], Decimal("8.0"))
        self.assertIsNone(result["final"])
        self.assertEqual(result["pending"], 1)

    def test_explicit_zero_counts_and_missing_delivery_stays_distinct(self):
        self.grade(self.assessment(), "0", status="missing")
        result = self.result()
        self.assertEqual(result["final"], Decimal("0.0"))
        self.assertEqual(result["missing"], 1)
        self.assertEqual(result["pending"], 0)

    def test_missing_delivery_without_grade_is_pending(self):
        self.grade(self.assessment(), None, status="missing")
        self.assertEqual(self.result()["pending"], 1)
        self.assertIsNone(self.result()["final"])

    def test_exempt_omits_weight_and_requires_reason(self):
        self.grade(self.assessment(), "8")
        second = self.assessment(weight=Decimal("3"))
        with self.assertRaises(ValidationError):
            self.grade(second, None, status="exempt")
        self.grade(second, None, status="exempt", note="Dispensa autorizada")
        self.assertEqual(self.result()["final"], Decimal("8.0"))
        self.assertEqual(self.result()["exempt"], 1)

    def test_all_exempt_has_no_result(self):
        self.grade(self.assessment(), None, status="exempt", note="Dispensa")
        self.assertIsNone(self.result()["final"])

    def test_points_requires_full_plan_and_sums_raw_scores(self):
        self.book.calculation = "points"
        self.book.save()
        self.grade(self.assessment(maximum=Decimal("4")), "3")
        self.assertFalse(grade_summary(self.book)["points_ready"])
        self.assertIsNone(self.result()["final"])
        self.grade(self.assessment(maximum=Decimal("6")), "5")
        self.assertEqual(self.result()["final"], Decimal("8.0"))

    def test_points_rejects_excess_maxima(self):
        self.book.calculation = "points"
        self.book.save()
        self.assessment(maximum=Decimal("8"))
        with self.assertRaises(ValidationError):
            self.assessment(maximum=Decimal("3"))

    def test_rounding_and_threshold_use_final_decimal(self):
        self.grade(self.assessment(), "5.95")
        self.assertEqual(self.result()["final"], Decimal("6.0"))
        self.assertEqual(self.result()["status"], "Atingiu a referência")
        self.book.rounding = "truncate"
        self.book.save()
        self.assertEqual(self.result()["final"], Decimal("5.9"))
        self.assertEqual(self.result()["status"], "Abaixo da referência")

    def test_recovery_variants(self):
        self.grade(self.assessment(), "4")
        for rule, expected in (("higher", "8.0"), ("replace", "8.0"), ("average", "6.0")):
            with self.subTest(rule=rule):
                self.book.recovery = rule
                self.book.save()
                recovery = Assessment.objects.filter(kind="recovery").first()
                if not recovery:
                    recovery = self.assessment(kind="recovery", maximum=Decimal("20"))
                    self.grade(recovery, "16")
                self.assertEqual(self.result()["final"], Decimal(expected))

    def test_recovery_does_not_round_intermediate(self):
        self.book.recovery = "average"
        self.book.save()
        self.grade(self.assessment(), "5.94")
        self.grade(self.assessment(kind="recovery"), "5.95")
        self.assertEqual(self.result()["final"], Decimal("5.9"))

    def test_higher_recovery_cannot_reduce_result(self):
        self.book.recovery = "higher"
        self.book.save()
        self.grade(self.assessment(), "8")
        self.grade(self.assessment(kind="recovery"), "4")
        self.assertEqual(self.result()["final"], Decimal("8.0"))

    def test_recovery_is_optional_unless_recorded_pending(self):
        self.book.recovery = "replace"
        self.book.save()
        self.grade(self.assessment(), "8")
        recovery = self.assessment(kind="recovery")
        self.assertEqual(self.result()["final"], Decimal("8.0"))
        self.grade(recovery, None)
        self.assertIsNone(self.result()["final"])
        self.assertEqual(self.result()["pending"], 1)
        self.assertEqual(self.result()["status"], "Recuperação pendente")

    def test_recovery_cannot_hide_missing_regular_grade(self):
        self.book.recovery = "replace"
        self.book.save()
        self.assessment()
        self.grade(self.assessment(kind="recovery"), "8")
        self.assertIsNone(self.result()["final"])

    def test_recovery_disabled_and_duplicate_rejected(self):
        with self.assertRaises(ValidationError):
            self.assessment(kind="recovery")
        self.book.recovery = "higher"
        self.book.save()
        self.assessment(kind="recovery")
        with self.assertRaises(ValidationError):
            self.assessment(kind="recovery")

    def test_grade_range_and_incompatible_status(self):
        item = self.assessment()
        for score, status in (("-1", "submitted"), ("11", "submitted"), ("8", "pending"), ("8", "exempt")):
            with self.subTest(score=score, status=status), self.assertRaises(ValidationError):
                self.grade(item, score, status=status)

    def test_future_assessment_planning_without_results(self):
        item = self.assessment()
        with patch("diary.models.timezone.localdate", return_value=date(2026, 2, 28)):
            with self.assertRaises(ValidationError):
                self.grade(item)
            self.grade(item, None, status="pending")

    def test_dates_inside_period(self):
        with self.assertRaises(ValidationError):
            self.assessment(date=date(2026, 7, 1))

    def test_only_eligible_enrollments(self):
        self.enrollment.starts_on = date(2026, 4, 1)
        self.enrollment.save()
        item = self.assessment()
        self.assertEqual(GradeForm(assessment=item).roster, [])
        with self.assertRaises(ValidationError):
            self.grade(item)

    def test_post_grade_and_comma_decimal(self):
        item = self.assessment()
        response = self.post_grade(item, score="7,25")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Grade.objects.get().score, Decimal("7.25"))
        self.assertEqual(GradeAudit.objects.count(), 1)

    def test_unchanged_pending_is_not_saved_as_zero(self):
        item = self.assessment()
        response = self.client.post(reverse("grade_form", args=[item.pk]), self.grades_data(item))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Grade.objects.exists())

    def test_correction_requires_reason_and_retains_previous_values(self):
        item = self.assessment()
        self.post_grade(item, "8")
        self.assertEqual(self.post_grade(item, "5").status_code, 200)
        self.assertEqual(Grade.objects.get().score, Decimal("8"))
        self.assertEqual(self.post_grade(item, "5", reason="Conferência da prova").status_code, 302)
        changes = GradeAudit.objects.first().changes
        self.assertTrue(any(change["before"] == "8.00" and change["after"] == "5" for change in changes))
        self.assertEqual(GradeAudit.objects.first().reason, "Conferência da prova")

    def test_stale_grade_form_cannot_overwrite(self):
        item = self.assessment()
        data = self.grades_data(item, **{f"status_{self.enrollment.pk}": "submitted", f"score_{self.enrollment.pk}": "2",
                                      "reason": "Tela antiga"})
        self.post_grade(item, "8")
        response = self.client.post(reverse("grade_form", args=[item.pk]), data)
        self.assertContains(response, "mudou em outra aba")
        self.assertEqual(Grade.objects.get().score, Decimal("8"))

    def test_roster_changes_reject_old_form(self):
        item = self.assessment()
        data = self.grades_data(item)
        self.enrollment.starts_on = date(2026, 2, 1)
        self.enrollment.save()
        response = self.client.post(reverse("grade_form", args=[item.pk]), data)
        self.assertContains(response, "matrículas mudaram")
        self.assertFalse(Grade.objects.exists())

    def test_audit_failure_rolls_back_grade_and_version(self):
        item = self.assessment()
        self.book.refresh_from_db()
        version = self.book.version
        with patch("diary.grading_services.audit", side_effect=ValidationError("Falha simulada")):
            response = self.post_grade(item)
        self.assertContains(response, "Falha simulada")
        self.assertFalse(Grade.objects.exists())
        self.book.refresh_from_db()
        self.assertEqual(self.book.version, version)

    def test_invalid_row_does_not_save_other_students(self):
        second = Enrollment.objects.create(owner=self.owner, classroom=self.room, starts_on=date(2026, 1, 1),
            student=Student.objects.create(owner=self.owner, name="Bruno Teste"))
        item = self.assessment()
        response = self.post_grade(item, **{f"status_{second.pk}": "submitted", f"score_{second.pk}": "11"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Grade.objects.exists())

    def test_cancel_preserves_grades_excludes_results_and_blocks_post(self):
        item = self.assessment()
        self.post_grade(item)
        self.book.refresh_from_db()
        response = self.client.post(reverse("assessment_cancel", args=[item.pk]),
                                    {"version": self.book.version, "reason": "Avaliação substituída"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Grade.objects.count(), 1)
        self.assertIsNone(self.result()["final"])
        self.post_grade(item, "2")
        self.assertEqual(Grade.objects.get().score, Decimal("8"))
        self.assertContains(self.client.get(reverse("grade_form", args=[item.pk])), "Avaliação cancelada")

    def test_links_and_rules_are_protected(self):
        item = self.assessment()
        self.grade(item)
        for obj, field, value in ((self.enrollment, "starts_on", date(2026, 4, 1)),
                                  (self.term, "end_date", date(2026, 2, 1)),
                                  (item, "maximum", Decimal("5")), (self.book, "scale", Decimal("20"))):
            with self.subTest(field=field), self.assertRaises(ValidationError):
                setattr(obj, field, value)
                obj.save()

    def test_policy_changes_audited_and_recalculate(self):
        self.grade(self.assessment(), "5.95")
        response = self.client.post(reverse("book_edit", args=[self.book.pk]),
                                    self.policy_data(rounding="truncate"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.result()["final"], Decimal("5.9"))
        self.assertEqual(GradeAudit.objects.first().reason, "Regra da escola")

    def test_policy_changes_require_reason_and_current_version(self):
        data = self.policy_data(rounding="truncate", reason="")
        self.assertEqual(self.client.post(reverse("book_edit", args=[self.book.pk]), data).status_code, 200)
        data["reason"] = "Ajuste"
        data["version"] = 0
        self.assertContains(self.client.post(reverse("book_edit", args=[self.book.pk]), data), "mudou em outra aba")

    def test_cross_owner_views_are_404_and_lists_private(self):
        item = self.assessment()
        self.client.force_login(self.other)
        for name, pk in (("book_detail", self.book.pk), ("book_edit", self.book.pk),
                         ("assessment_create", self.book.pk), ("assessment_edit", item.pk),
                         ("grade_form", item.pk), ("assessment_cancel", item.pk)):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name, args=[pk])).status_code, 404)
                self.assertEqual(self.client.post(reverse(name, args=[pk]), {}).status_code, 404)
        self.assertNotContains(self.client.get(reverse("book_list")), "Matemática")

    def test_cross_owner_book_form_and_model_rejected(self):
        self.client.force_login(self.other)
        response = self.client.post(reverse("book_create"), self.policy_data())
        self.assertEqual(response.status_code, 200)
        with self.assertRaises(ValidationError):
            Gradebook.objects.create(owner=self.other, classroom=self.room, subject=self.subject, term=self.term)

    def test_wrong_school_period_rejected(self):
        another_school = School.objects.create(owner=self.owner, name="Outra escola")
        self.term.school = another_school
        # New period, not modifying the existing linked period.
        self.term.pk = None
        self.term.save()
        with self.assertRaises(ValidationError):
            Gradebook.objects.create(owner=self.owner, classroom=self.room, subject=self.subject, term=self.term)

    def test_duplicate_book_is_form_error(self):
        response = self.client.post(reverse("book_create"), self.policy_data())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Gradebook.objects.count(), 1)

    def test_assessment_creation_and_edit_from_ui(self):
        data = {"title": "Trabalho novo", "kind": "work", "date": "2026-03-20", "maximum": "10",
                "weight": "2", "instructions": "Em dupla", "version": 1}
        response = self.client.post(reverse("assessment_create", args=[self.book.pk]), data)
        self.assertEqual(response.status_code, 302)
        item = Assessment.objects.get()
        self.book.refresh_from_db()
        data.update(title="Trabalho revisado", version=self.book.version, reason="Título correto")
        self.assertEqual(self.client.post(reverse("assessment_edit", args=[item.pk]), data).status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.title, "Trabalho revisado")

    def test_safe_html_and_no_cache(self):
        item = self.assessment(title="<script>alert(1)</script>")
        self.grade(item, note="<img src=x onerror=alert(1)>")
        response = self.client.get(reverse("grade_form", args=[item.pk]))
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(response, "<script>alert")
        self.assertIn("no-store", response["Cache-Control"])

    def test_auth_csrf_and_get_does_not_cancel(self):
        item = self.assessment()
        self.client.get(reverse("assessment_cancel", args=[item.pk]))
        item.refresh_from_db()
        self.assertFalse(item.is_cancelled)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.owner)
        self.assertEqual(csrf_client.post(reverse("grade_form", args=[item.pk]), {}).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(reverse("book_list")).status_code, 302)

    def test_page_templates_render(self):
        item = self.assessment()
        for name, args in (("book_list", []), ("book_create", []), ("book_detail", [self.book.pk]),
                           ("book_edit", [self.book.pk]), ("assessment_create", [self.book.pk]),
                           ("assessment_edit", [item.pk]), ("grade_form", [item.pk]), ("assessment_cancel", [item.pk])):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 200)
