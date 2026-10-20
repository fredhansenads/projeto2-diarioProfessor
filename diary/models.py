from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


def current_year():
    return date.today().year


class OwnedRecord(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                              verbose_name="professor")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def clean(self):
        super().clean()
        errors = {}
        if self.pk:
            previous = type(self).objects.filter(pk=self.pk).values("owner_id").first()
            if previous and previous["owner_id"] != self.owner_id:
                errors["owner"] = "Não é permitido transferir este registro para outra conta."
        for field in self._meta.fields:
            if (isinstance(field, models.ForeignKey) and field.name != "owner"
                    and getattr(self, field.attname, None)):
                related = field.related_model.objects.filter(
                    pk=getattr(self, field.attname)
                ).first()
                if related and getattr(related, "owner_id", self.owner_id) != self.owner_id:
                    errors[field.name] = "Selecione um registro da sua conta."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class School(OwnedRecord):
    name = models.CharField("nome da escola", max_length=160)
    city = models.CharField("cidade", max_length=120, blank=True)

    class Meta:
        ordering = ["name", "pk"]
        verbose_name = "escola"
        constraints = [
            models.UniqueConstraint(fields=["owner", "name"], name="unique_school_per_owner")
        ]

    def __str__(self):
        return self.name


class AcademicYear(OwnedRecord):
    year = models.PositiveIntegerField("ano", default=current_year,
                                      validators=[MinValueValidator(2000), MaxValueValidator(2100)])

    class Meta:
        ordering = ["-year", "pk"]
        verbose_name = "ano letivo"
        constraints = [
            models.UniqueConstraint(fields=["owner", "year"], name="unique_year_per_owner")
        ]

    def clean(self):
        super().clean()
        if self.pk and self.periods.exclude(start_date__year=self.year,
                                           end_date__year=self.year).exists():
            raise ValidationError({"year": "Há períodos vinculados com datas de outro ano."})

    def __str__(self):
        return str(self.year)


class Term(OwnedRecord):
    school = models.ForeignKey(School, on_delete=models.PROTECT,
                               related_name="periods", verbose_name="escola")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.PROTECT,
                                     related_name="periods", verbose_name="ano letivo")
    name = models.CharField("nome do período", max_length=80,
                            help_text="Ex.: 1º bimestre ou 1º semestre.")
    start_date = models.DateField("início")
    end_date = models.DateField("fim")

    class Meta:
        ordering = ["-academic_year__year", "start_date", "pk"]
        verbose_name = "período letivo"
        constraints = [
            models.UniqueConstraint(fields=["owner", "school", "academic_year", "name"],
                                    name="unique_term_per_year"),
            models.CheckConstraint(condition=models.Q(end_date__gte=models.F("start_date")),
                                   name="term_dates_in_order"),
        ]

    def clean(self):
        super().clean()
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValidationError({"end_date": "O fim deve ser igual ou posterior ao início."})
            if self.academic_year_id:
                year = self.academic_year.year
                if self.start_date.year != year or self.end_date.year != year:
                    raise ValidationError("As datas devem pertencer ao ano letivo selecionado.")

    def __str__(self):
        return f"{self.name} · {self.academic_year}"


class Subject(OwnedRecord):
    name = models.CharField("nome da disciplina", max_length=100)

    class Meta:
        ordering = ["name", "pk"]
        verbose_name = "disciplina"
        constraints = [
            models.UniqueConstraint(fields=["owner", "name"], name="unique_subject_per_owner")
        ]

    def __str__(self):
        return self.name


class Classroom(OwnedRecord):
    class Shift(models.TextChoices):
        MORNING = "morning", "Manhã"
        AFTERNOON = "afternoon", "Tarde"
        EVENING = "evening", "Noite"
        FULL = "full", "Integral"

    name = models.CharField("nome da turma", max_length=80, help_text="Ex.: 6º ano A.")
    school = models.ForeignKey(School, on_delete=models.PROTECT,
                               related_name="classrooms", verbose_name="escola")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.PROTECT,
                                      related_name="classrooms", verbose_name="ano letivo")
    shift = models.CharField("turno", max_length=12, choices=Shift.choices, default=Shift.MORNING)
    subjects = models.ManyToManyField(Subject, blank=True, verbose_name="disciplinas",
                                      related_name="classrooms")

    class Meta:
        ordering = ["-academic_year__year", "name", "pk"]
        verbose_name = "turma"
        constraints = [
            models.UniqueConstraint(fields=["owner", "school", "academic_year", "name", "shift"],
                                    name="unique_classroom_per_school_year_shift")
        ]

    def clean(self):
        super().clean()
        if self.pk and self.enrollments.exists():
            previous = Classroom.objects.get(pk=self.pk)
            if (previous.school_id, previous.academic_year_id) != (
                    self.school_id, self.academic_year_id):
                raise ValidationError(
                    "Turmas com matrículas devem preservar escola e ano. Crie uma nova turma."
                )

    def __str__(self):
        return f"{self.name} · {self.school} · {self.academic_year}"


class Student(OwnedRecord):
    name = models.CharField("nome completo", max_length=160)
    reference = models.CharField("identificação interna", max_length=40, blank=True,
                                help_text="Opcional. Use para diferenciar alunos com o mesmo nome.")

    class Meta:
        ordering = ["name", "pk"]
        verbose_name = "aluno"

    def __str__(self):
        return f"{self.name} ({self.reference})" if self.reference else self.name


class Enrollment(OwnedRecord):
    class Status(models.TextChoices):
        ACTIVE = "active", "Ativa"
        TRANSFERRED = "transferred", "Transferida"
        CLOSED = "closed", "Encerrada"

    student = models.ForeignKey(Student, on_delete=models.PROTECT,
                                related_name="enrollments", verbose_name="aluno")
    classroom = models.ForeignKey(Classroom, on_delete=models.PROTECT,
                                  related_name="enrollments", verbose_name="turma")
    status = models.CharField("situação", max_length=12, choices=Status.choices,
                              default=Status.ACTIVE)

    class Meta:
        ordering = ["student__name", "pk"]
        verbose_name = "matrícula"
        constraints = [
            models.UniqueConstraint(fields=["student", "classroom"], name="unique_enrollment")
        ]

    def clean(self):
        super().clean()
        if self.pk:
            previous = Enrollment.objects.get(pk=self.pk)
            if (previous.student_id, previous.classroom_id) != (
                    self.student_id, self.classroom_id):
                raise ValidationError(
                    "Preserve o histórico: encerre esta matrícula e crie outra para a nova turma."
                )

    def __str__(self):
        return f"{self.student} · {self.classroom.name}"

