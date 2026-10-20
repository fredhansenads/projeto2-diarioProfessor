from django import forms
from django.core.exceptions import ValidationError

from .forms import OwnedModelForm
from .models import Assessment, Grade, Gradebook
from .grading_services import ASSESSMENT_FIELDS, POLICY_FIELDS, grade_roster
from .teaching_services import roster_token


class BookForm(OwnedModelForm):
    version = forms.IntegerField(widget=forms.HiddenInput, min_value=0)
    reason = forms.CharField(label="Motivo da alteração", max_length=500, required=False,
                             help_text="Alterar regras recalcula os resultados existentes; explique a mudança.")

    class Meta:
        model = Gradebook
        fields = ("classroom", "subject", "term") + POLICY_FIELDS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["version"].initial = self.instance.version
        self.fields["precision"].widget = forms.Select(choices=[(0, "0"), (1, "1"), (2, "2")])
        if self.instance.pk:
            for name in ("classroom", "subject", "term"):
                self.fields[name].disabled = True
            if self.instance.assessments.exists():
                self.fields["scale"].disabled = True
        else:
            self.fields.pop("reason")


class AssessmentForm(OwnedModelForm):
    version = forms.IntegerField(widget=forms.HiddenInput, min_value=0)
    reason = forms.CharField(label="Motivo da correção", max_length=500, required=False)

    class Meta:
        model = Assessment
        fields = ASSESSMENT_FIELDS
        widgets = {"instructions": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, gradebook, **kwargs):
        kwargs["instance"] = kwargs.get("instance") or Assessment(gradebook=gradebook, maximum=gradebook.scale)
        super().__init__(*args, **kwargs)
        self.fields["version"].initial = gradebook.version
        if not self.instance.pk:
            self.fields.pop("reason")
        elif self.instance.grades.exists():
            for name in ("kind", "date", "maximum", "weight"):
                self.fields[name].disabled = True

    def _get_validation_exclusions(self):
        exclusions = super()._get_validation_exclusions()
        exclusions.difference_update({"gradebook", "is_cancelled"})
        return exclusions


class GradeForm(forms.Form):
    version = forms.IntegerField(widget=forms.HiddenInput, min_value=0)
    roster_token = forms.CharField(widget=forms.HiddenInput)
    reason = forms.CharField(label="Motivo da correção", required=False, max_length=500,
                             help_text="Obrigatório ao corrigir notas, situações ou observações já salvas.")

    def __init__(self, *args, assessment, **kwargs):
        super().__init__(*args, **kwargs)
        self.assessment = assessment
        self.roster = grade_roster(assessment)
        self.records = {item.enrollment_id: item for item in assessment.grades.all()}
        self.fields["version"].initial = assessment.gradebook.version
        self.fields["roster_token"].initial = roster_token(self.roster)
        self.rows = []
        for enrollment in self.roster:
            record = self.records.get(enrollment.pk)
            fields = {
                "status": forms.ChoiceField(label=f"Situação — {enrollment.student}", choices=Grade.Status.choices,
                                             initial=record.status if record else "pending"),
                "score": forms.DecimalField(label=f"Nota — {enrollment.student}", required=False, min_value=0,
                                            max_value=assessment.maximum, max_digits=7, decimal_places=2,
                                            initial=record.score if record else None, localize=True,
                                            widget=forms.TextInput(attrs={"inputmode": "decimal"})),
                "note": forms.CharField(label=f"Observação — {enrollment.student}", required=False, max_length=500,
                                        initial=record.note if record else "",
                                        widget=forms.Textarea(attrs={"rows": 2})),
            }
            for name, field in fields.items():
                self.fields[f"{name}_{enrollment.pk}"] = field
            self.rows.append({"enrollment": enrollment, **{
                name: self[f"{name}_{enrollment.pk}"] for name in fields}})

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("roster_token") != roster_token(self.roster):
            raise ValidationError("As matrículas mudaram. Recarregue a página.")
        for enrollment in self.roster:
            keys = {name: f"{name}_{enrollment.pk}" for name in ("status", "score", "note")}
            if not all(key in cleaned for key in keys.values()):
                continue
            values = {name: cleaned[key] for name, key in keys.items()}
            record = Grade(owner=self.assessment.owner, assessment=self.assessment, enrollment=enrollment, **values)
            try:
                record.clean()
            except ValidationError as error:
                if hasattr(error, "message_dict"):
                    for name, messages in error.message_dict.items():
                        self.add_error(keys.get(name), messages)
                else:
                    self.add_error(None, f"{enrollment.student}: {' '.join(error.messages)}")
        return cleaned
