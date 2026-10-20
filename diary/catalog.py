from dataclasses import dataclass
from .models import AcademicYear, Classroom, Enrollment, School, Student, Subject, Term


@dataclass(frozen=True)
class Catalog:
    model: type
    title: str
    singular: str
    description: str
    fields: tuple
    columns: tuple


CATALOG = {
    "escolas": Catalog(School, "Escolas", "escola", "As escolas onde você ensina.",
                       ("name", "city"), (("name", "Escola"), ("city", "Cidade"))),
    "anos-letivos": Catalog(AcademicYear, "Anos letivos", "ano letivo",
                            "Organize os registros de cada ano sem perder o histórico.",
                            ("year",), (("year", "Ano"),)),
    "periodos": Catalog(Term, "Períodos", "período",
                        "Bimestres, trimestres ou semestres: use a organização da sua escola.",
                        ("school", "academic_year", "name", "start_date", "end_date"),
                        (("name", "Período"), ("school", "Escola"), ("academic_year", "Ano"),
                         ("start_date", "Início"), ("end_date", "Fim"))),
    "disciplinas": Catalog(Subject, "Disciplinas", "disciplina", "O que você ensina em cada turma.",
                           ("name",), (("name", "Disciplina"),)),
    "turmas": Catalog(Classroom, "Turmas", "turma", "Seu ponto de partida para acompanhar os alunos.",
                      ("name", "school", "academic_year", "shift", "subjects"),
                      (("name", "Turma"), ("school", "Escola"), ("academic_year", "Ano"),
                       ("get_shift_display", "Turno"))),
    "alunos": Catalog(Student, "Alunos", "aluno", "Cadastre uma vez e preserve o histórico a cada ano.",
                      ("name", "reference"), (("name", "Aluno"), ("reference", "Identificação"))),
    "matriculas": Catalog(Enrollment, "Matrículas", "matrícula",
                          "Vincule alunos às turmas. Em transferências, preserve a matrícula anterior.",
                          ("student", "classroom", "status"),
                          (("student", "Aluno"), ("classroom", "Turma"),
                           ("get_status_display", "Situação"))),
}

