from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


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
        if self.pk and AcademicYear.objects.get(pk=self.pk).year != self.year:
            if self.classrooms.filter(models.Q(enrollments__isnull=False) |
                                      models.Q(lessons__isnull=False)).exists():
                raise ValidationError({"year": "Crie outro ano para preservar matrículas e aulas existentes."})

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
        if self.pk and (self.enrollments.exists() or self.lessons.exists()):
            previous = Classroom.objects.get(pk=self.pk)
            if (previous.school_id, previous.academic_year_id) != (
                    self.school_id, self.academic_year_id):
                raise ValidationError(
                    "Turmas com matrículas ou aulas devem preservar escola e ano. Crie uma nova turma."
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
    starts_on = models.DateField(
        "primeiro dia na turma", null=True, blank=True,
        help_text="Data real de entrada. Cadastros antigos sem data consideram o início do ano.",
    )
    ends_on = models.DateField(
        "último dia na turma", null=True, blank=True,
        help_text="Obrigatório ao transferir ou encerrar. Inclui este dia na frequência.",
    )

    class Meta:
        ordering = ["student__name", "pk"]
        verbose_name = "matrícula"
        constraints = [
            models.UniqueConstraint(fields=["student", "classroom"], name="unique_enrollment"),
            models.CheckConstraint(
                condition=models.Q(ends_on__isnull=True) | models.Q(starts_on__isnull=True) |
                          models.Q(ends_on__gte=models.F("starts_on")),
                name="enrollment_dates_in_order",
            )
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.status != self.Status.ACTIVE and not self.ends_on:
            errors["ends_on"] = "Informe o último dia na turma para preservar a frequência anterior."
        if self.status == self.Status.ACTIVE and self.ends_on:
            errors["ends_on"] = "Para informar a saída, altere a situação para transferida ou encerrada."
        if self.starts_on and self.ends_on and self.ends_on < self.starts_on:
            errors["ends_on"] = "A saída não pode ser anterior à entrada."
        if self.classroom_id:
            year = self.classroom.academic_year.year
            for field in ("starts_on", "ends_on"):
                value = getattr(self, field)
                if value and value.year != year:
                    errors[field] = "A data deve pertencer ao ano letivo da turma."
        if errors:
            raise ValidationError(errors)
        if self.pk:
            previous = Enrollment.objects.get(pk=self.pk)
            if (previous.student_id, previous.classroom_id) != (
                    self.student_id, self.classroom_id):
                raise ValidationError(
                    "Preserve o histórico: encerre esta matrícula e crie outra para a nova turma."
                )
            records = self.attendance_records.filter(lesson__is_cancelled=False)
            if (self.starts_on and records.filter(lesson__date__lt=self.starts_on).exists()) or (
                self.ends_on and records.filter(lesson__date__gt=self.ends_on).exists()
            ):
                raise ValidationError("Estas datas excluem chamadas já registradas. Revise as aulas antes de alterar.")

    def covers(self, lesson_date):
        if lesson_date.year != self.classroom.academic_year.year:
            return False
        if self.starts_on and lesson_date < self.starts_on:
            return False
        if self.ends_on:
            return lesson_date <= self.ends_on
        return self.status == self.Status.ACTIVE

    def __str__(self):
        return f"{self.student} · {self.classroom.name}"


class Lesson(OwnedRecord):
    classroom = models.ForeignKey(Classroom, on_delete=models.PROTECT,
                                  related_name="lessons", verbose_name="turma")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT,
                                related_name="lessons", verbose_name="disciplina")
    date = models.DateField("data", default=timezone.localdate)
    quantity = models.PositiveSmallIntegerField(
        "quantidade de aulas", default=1,
        validators=[MinValueValidator(1), MaxValueValidator(20)],
        help_text="Some as aulas desta disciplina no mesmo dia. Ex.: duas aulas seguidas = 2.",
    )
    content = models.TextField("conteúdo ministrado", max_length=5000)
    notes = models.TextField("observações da aula", max_length=2000, blank=True)
    is_cancelled = models.BooleanField(default=False)
    version = models.PositiveIntegerField(default=0, editable=False)

    class Meta:
        ordering = ["-date", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["classroom", "subject", "date"],
                condition=models.Q(is_cancelled=False), name="unique_active_lesson_per_day",
            ),
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1, quantity__lte=20),
                name="lesson_quantity_range",
            ),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.date and self.date > timezone.localdate():
            errors["date"] = "Registre somente aulas já realizadas."
        if self.classroom_id:
            if self.date and self.date.year != self.classroom.academic_year.year:
                errors["date"] = "A data deve pertencer ao ano letivo da turma."
            if self.subject_id and not self.classroom.subjects.filter(pk=self.subject_id).exists():
                errors["subject"] = "Vincule esta disciplina à turma antes de registrar a aula."
        if errors:
            raise ValidationError(errors)
        if self.pk:
            previous = Lesson.objects.get(pk=self.pk)
            if previous.is_cancelled:
                raise ValidationError("Aula cancelada: o registro permanece apenas para consulta.")
            if previous.classroom_id != self.classroom_id:
                raise ValidationError("A turma de uma aula existente não pode ser alterada.")
            if self.attendance_records.exists() and any(
                getattr(previous, field) != getattr(self, field)
                for field in ("subject_id", "date", "quantity")
            ):
                raise ValidationError(
                    "Após a chamada, preserve disciplina, data e quantidade. "
                    "Se esses dados estiverem incorretos, cancele a aula e registre outra."
                )

    def __str__(self):
        return f"{self.classroom.name} · {self.subject} · {self.date:%d/%m/%Y}"


class Attendance(OwnedRecord):
    lesson = models.ForeignKey(Lesson, on_delete=models.PROTECT,
                               related_name="attendance_records")
    enrollment = models.ForeignKey(Enrollment, on_delete=models.PROTECT,
                                   related_name="attendance_records")
    absences = models.PositiveSmallIntegerField("faltas", default=0)
    justified_absences = models.PositiveSmallIntegerField("faltas justificadas", default=0)
    justification = models.CharField("justificativa", max_length=500, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["lesson", "enrollment"], name="unique_attendance"),
            models.CheckConstraint(
                condition=models.Q(justified_absences__lte=models.F("absences")),
                name="justified_absences_within_total",
            ),
        ]

    def clean(self):
        super().clean()
        if self.pk:
            previous = Attendance.objects.get(pk=self.pk)
            if (previous.lesson_id, previous.enrollment_id) != (self.lesson_id, self.enrollment_id):
                raise ValidationError("Uma chamada existente deve preservar a aula e a matrícula.")
        if self.lesson_id and self.enrollment_id:
            if self.enrollment.classroom_id != self.lesson.classroom_id:
                raise ValidationError("A matrícula deve pertencer à turma da aula.")
            if self.lesson.is_cancelled:
                raise ValidationError("Não é possível alterar chamada de aula cancelada.")
            if not self.enrollment.covers(self.lesson.date):
                raise ValidationError("O aluno não estava matriculado nesta data. Revise as datas da matrícula.")
            if self.absences is not None and self.absences > self.lesson.quantity:
                raise ValidationError({"absences": "As faltas não podem superar a quantidade de aulas."})
        if self.absences is not None and self.justified_absences is not None:
            if self.justified_absences > self.absences:
                raise ValidationError({"justified_absences": "O número não pode superar o total de faltas."})
            if self.justified_absences and not self.justification.strip():
                raise ValidationError({"justification": "Descreva a justificativa das faltas."})
            if not self.absences and self.justification.strip():
                raise ValidationError({"justification": "Registre justificativas somente quando houver falta."})


class LessonAudit(OwnedRecord):
    class Kind(models.TextChoices):
        CREATED = "created", "Aula registrada"
        EDITED = "edited", "Aula corrigida"
        ATTENDANCE = "attendance", "Chamada registrada ou corrigida"
        CANCELLED = "cancelled", "Aula cancelada"

    lesson = models.ForeignKey(Lesson, on_delete=models.PROTECT, related_name="history")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                              related_name="lesson_changes")
    kind = models.CharField(max_length=12, choices=Kind.choices)
    reason = models.CharField("motivo", max_length=500, blank=True)
    changes = models.JSONField(default=list)

    class Meta:
        ordering = ["-created_at", "-pk"]

    def clean(self):
        super().clean()
        if self.actor_id != self.owner_id:
            raise ValidationError("O autor deve ser o professor responsável pelo registro.")
        if self.pk:
            raise ValidationError("O histórico não pode ser editado.")

