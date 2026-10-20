from django import forms

from .models import AcademicYear, Classroom, Enrollment, School, Subject, Term


class ReportFilterForm(forms.Form):
    school = forms.ModelChoiceField(label="Escola", queryset=School.objects.none(), required=False)
    year = forms.ModelChoiceField(label="Ano letivo", queryset=AcademicYear.objects.none(), required=False)
    classroom = forms.ModelChoiceField(label="Turma", queryset=Classroom.objects.none())
    term = forms.ModelChoiceField(label="Período", queryset=Term.objects.none())
    subject = forms.ModelChoiceField(label="Disciplina", queryset=Subject.objects.none(), required=False,
                                     empty_label="Todas as disciplinas da turma")
    enrollment = forms.ModelChoiceField(label="Aluno / matrícula", queryset=Enrollment.objects.none(),
                                        required=False, empty_label="Toda a turma")

    def __init__(self, *args, owner, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["school"].queryset = School.objects.filter(owner=owner)
        self.fields["year"].queryset = AcademicYear.objects.filter(owner=owner)
        self.fields["classroom"].queryset = Classroom.objects.filter(owner=owner).select_related("school", "academic_year")
        self.fields["term"].queryset = Term.objects.filter(owner=owner).select_related("school", "academic_year")
        self.fields["term"].label_from_instance = lambda item: f"{item.school} · {item}"
        self.fields["subject"].queryset = Subject.objects.filter(owner=owner)
        self.fields["enrollment"].queryset = Enrollment.objects.filter(owner=owner).select_related("student", "classroom")
        self.fields["enrollment"].label_from_instance = lambda item: f"{item.student} · {item.classroom.name}"
        # Narrow choices only through records that already belong to this account.
        room_id = self.data.get("classroom") if self.is_bound else self.initial.get("classroom")
        room = None
        if room_id and str(room_id).isascii() and str(room_id).isdecimal() and len(str(room_id)) < 12:
            room = self.fields["classroom"].queryset.filter(pk=room_id).first()
        if room:
            self.fields["term"].queryset = self.fields["term"].queryset.filter(
                school_id=room.school_id, academic_year_id=room.academic_year_id)
            self.fields["subject"].queryset = room.subjects.filter(owner=owner)
            self.fields["enrollment"].queryset = self.fields["enrollment"].queryset.filter(classroom=room)

    def clean(self):
        data = super().clean()
        room, term = data.get("classroom"), data.get("term")
        if room:
            if data.get("school") and data["school"].pk != room.school_id:
                self.add_error("school", "A escola deve ser a mesma da turma.")
            if data.get("year") and data["year"].pk != room.academic_year_id:
                self.add_error("year", "O ano deve ser o mesmo da turma.")
            if term and (term.school_id != room.school_id or term.academic_year_id != room.academic_year_id):
                self.add_error("term", "Escolha um período da escola e do ano da turma.")
            if data.get("enrollment") and data["enrollment"].classroom_id != room.pk:
                self.add_error("enrollment", "Escolha uma matrícula desta turma.")
            if data.get("subject") and not room.subjects.filter(pk=data["subject"].pk).exists():
                self.add_error("subject", "Escolha uma disciplina desta turma.")
        return data
