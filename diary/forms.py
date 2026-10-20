from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Classroom, Enrollment


class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(label="Como você quer ser chamado(a)?", max_length=150)
    email = forms.EmailField(label="E-mail", help_text="Usado para recuperação de senha.")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("first_name", "username", "email", "password1", "password2")


class OwnedModelForm(forms.ModelForm):
    def __init__(self, *args, owner, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.owner = owner
        for field in self.fields.values():
            if isinstance(field, (forms.ModelChoiceField, forms.ModelMultipleChoiceField)):
                field.queryset = field.queryset.filter(owner=owner)
            if isinstance(field, forms.DateField):
                field.widget = forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})
                field.input_formats = ["%Y-%m-%d", "%d/%m/%Y"]
        if isinstance(self.instance, Enrollment) and self.instance.pk:
            self.fields["student"].disabled = True
            self.fields["classroom"].disabled = True
        if isinstance(self.instance, Enrollment):
            self.fields["starts_on"].required = True

    def clean(self):
        cleaned = super().clean()
        if isinstance(self.instance, Classroom) and self.instance.pk and "subjects" in cleaned:
            if self.instance.lessons.exclude(subject__in=cleaned["subjects"]).exists():
                self.add_error("subjects", "Preserve disciplinas que já possuem aulas registradas.")
        return cleaned

    def _get_validation_exclusions(self):
        exclusions = super()._get_validation_exclusions()
        # Ownership is supplied by the authenticated session, never by form input.
        # Include it in constraint validation so duplicate records become form errors.
        exclusions.discard("owner")
        return exclusions

