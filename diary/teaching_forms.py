from django import forms
from django.utils.crypto import constant_time_compare

from .forms import OwnedModelForm
from .models import Classroom, Lesson, Subject, Term
from .teaching_services import roster_for, roster_token


class ChooseClassroomForm(forms.Form):
    classroom = forms.ModelChoiceField(label="Turma", queryset=Classroom.objects.none())

    def __init__(self, *args, owner, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["classroom"].queryset = Classroom.objects.filter(owner=owner).select_related(
            "school", "academic_year"
        )


class LessonForm(OwnedModelForm):
    version = forms.IntegerField(widget=forms.HiddenInput, min_value=0)
    reason = forms.CharField(label="Motivo da correção", max_length=500, required=False,
                             widget=forms.Textarea(attrs={"rows": 2}))

    class Meta:
        model = Lesson
        fields = ("subject", "date", "quantity", "content", "notes")
        widgets = {
            "content": forms.Textarea(attrs={"rows": 5}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, classroom, **kwargs):
        kwargs["instance"] = kwargs.get("instance") or Lesson(classroom=classroom)
        super().__init__(*args, **kwargs)
        self.fields["subject"].queryset = classroom.subjects.filter(owner=self.instance.owner)
        self.fields["version"].initial = self.instance.version
        if not self.instance.pk:
            self.fields.pop("reason")
        elif self.instance.attendance_records.exists():
            for name in ("subject", "date", "quantity"):
                self.fields[name].disabled = True

    def _get_validation_exclusions(self):
        exclusions = super()._get_validation_exclusions()
        exclusions.difference_update({"classroom", "is_cancelled"})
        return exclusions

    def clean(self):
        cleaned = super().clean()
        if self.instance.pk and any(name in self.changed_data for name in self.Meta.fields):
            if not cleaned.get("reason"):
                self.add_error("reason", "Explique o que está sendo corrigido.")
        return cleaned


class AttendanceForm(forms.Form):
    version = forms.IntegerField(widget=forms.HiddenInput, min_value=0)
    roster_token = forms.CharField(widget=forms.HiddenInput)
    reason = forms.CharField(
        label="Motivo da correção", max_length=500, required=False,
        help_text="Obrigatório quando você altera uma chamada já registrada.",
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def __init__(self, *args, lesson, **kwargs):
        super().__init__(*args, **kwargs)
        self.lesson = lesson
        self.roster = roster_for(lesson)
        self.records = {row.enrollment_id: row for row in lesson.attendance_records.all()}
        self.fields["version"].initial = lesson.version
        self.fields["roster_token"].initial = roster_token(self.roster)
        choices = [("", "Selecione…"), (0, "Presente em todas")]
        choices.extend((number, f"{number} falta" + ("s" if number > 1 else ""))
                       for number in range(1, lesson.quantity + 1))
        self.rows = []
        for enrollment in self.roster:
            pk, name = enrollment.pk, str(enrollment.student)
            record = self.records.get(pk)
            self.fields[f"absences_{pk}"] = forms.TypedChoiceField(
                label=f"Faltas de {name}", choices=choices, coerce=int,
                initial=record.absences if record else "",
                widget=forms.Select(attrs={"data-absence": ""}),
            )
            self.fields[f"justified_{pk}"] = forms.IntegerField(
                label=f"Faltas justificadas de {name}", min_value=0, max_value=lesson.quantity,
                initial=record.justified_absences if record else 0,
                widget=forms.NumberInput(attrs={"inputmode": "numeric"}),
            )
            self.fields[f"note_{pk}"] = forms.CharField(
                label=f"Justificativa de {name}", max_length=500, required=False,
                initial=record.justification if record else "",
                widget=forms.Textarea(attrs={"rows": 2}),
            )
            self.rows.append({
                "enrollment": enrollment, "saved": bool(record),
                "absences": self[f"absences_{pk}"], "justified": self[f"justified_{pk}"],
                "note": self[f"note_{pk}"],
            })

    def clean(self):
        data = super().clean()
        if not constant_time_compare(data.get("roster_token", ""), roster_token(self.roster)):
            self.add_error(None, "As matrículas mudaram. Recarregue a página antes de salvar.")
        corrections = False
        for enrollment in self.roster:
            pk = enrollment.pk
            absent = data.get(f"absences_{pk}")
            justified = data.get(f"justified_{pk}")
            note = data.get(f"note_{pk}", "")
            if absent is None or justified is None:
                continue
            if justified > absent:
                self.add_error(f"justified_{pk}", "Não pode superar o total de faltas.")
            if justified and not note:
                self.add_error(f"note_{pk}", "Informe a justificativa.")
            if not absent and note:
                self.add_error(f"note_{pk}", "Registre justificativas somente quando houver falta.")
            record = self.records.get(pk)
            if record and (record.absences, record.justified_absences, record.justification) != (
                absent, justified, note
            ):
                corrections = True
        if corrections and not data.get("reason"):
            self.add_error("reason", "Explique o motivo da alteração da chamada.")
        return data


class CancelLessonForm(forms.Form):
    version = forms.IntegerField(widget=forms.HiddenInput, min_value=0)
    reason = forms.CharField(label="Motivo do cancelamento", max_length=500,
                             widget=forms.Textarea(attrs={"rows": 3}))


class LessonFilterForm(forms.Form):
    classroom = forms.ModelChoiceField(label="Turma", queryset=Classroom.objects.none(), required=False)
    subject = forms.ModelChoiceField(label="Disciplina", queryset=Subject.objects.none(), required=False)
    term = forms.ModelChoiceField(label="Período letivo", queryset=Term.objects.none(), required=False)
    start = forms.DateField(label="De", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    end = forms.DateField(label="Até", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    state = forms.ChoiceField(label="Situação", required=False, choices=[
        ("", "Aulas registradas"), ("all", "Incluir canceladas"), ("cancelled", "Somente canceladas"),
    ])

    def __init__(self, *args, owner, classroom=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.classroom = classroom
        self.fields["classroom"].queryset = Classroom.objects.filter(owner=owner).select_related(
            "school", "academic_year"
        )
        self.fields["subject"].queryset = Subject.objects.filter(owner=owner)
        self.fields["term"].queryset = Term.objects.filter(owner=owner).select_related(
            "school", "academic_year"
        )
        self.fields["term"].label_from_instance = lambda term: f"{term.school} · {term}"
        if classroom:
            self.fields.pop("classroom")
            self.fields.pop("state")
            self.fields["subject"].queryset = classroom.subjects.filter(owner=owner)
            self.fields["term"].queryset = self.fields["term"].queryset.filter(
                school=classroom.school, academic_year=classroom.academic_year
            )
        for name in ("start", "end"):
            self.fields[name].input_formats = ["%Y-%m-%d", "%d/%m/%Y"]

    def clean(self):
        data = super().clean()
        if data.get("start") and data.get("end") and data["start"] > data["end"]:
            self.add_error("end", "O fim não pode ser anterior ao início.")
        classroom = self.classroom or data.get("classroom")
        term = data.get("term")
        if classroom and term and (
            classroom.school_id != term.school_id or classroom.academic_year_id != term.academic_year_id
        ):
            self.add_error("term", "Escolha um período da escola e do ano desta turma.")
        return data

    def apply(self, queryset):
        if not self.is_valid():
            return queryset.none()
        data = self.cleaned_data
        classroom = self.classroom or data.get("classroom")
        if classroom:
            queryset = queryset.filter(classroom=classroom)
        if data.get("subject"):
            queryset = queryset.filter(subject=data["subject"])
        if data.get("term"):
            term = data["term"]
            queryset = queryset.filter(
                classroom__school=term.school, classroom__academic_year=term.academic_year,
                date__range=(term.start_date, term.end_date),
            )
        if data.get("start"):
            queryset = queryset.filter(date__gte=data["start"])
        if data.get("end"):
            queryset = queryset.filter(date__lte=data["end"])
        if data.get("state") != "all":
            queryset = queryset.filter(is_cancelled=data.get("state") == "cancelled")
        return queryset
