"""Synthetic data, only in the explicitly named local validation database."""
from datetime import date, timedelta
from decimal import Decimal
from django.conf import settings
from django.contrib.auth.models import User
from diary.models import (AcademicYear, Assessment, Attendance, Classroom, Enrollment,
                          Grade, Gradebook, Lesson, School, Student, Subject, Term)

PASSWORD = "Teste-local-2026!"


def seed():
    database = settings.DATABASES["default"]
    if database["NAME"] != "diario_validation" or database["HOST"] != "db":
        raise RuntimeError("This fixture is restricted to the local validation stack.")
    if User.objects.exists():
        raise RuntimeError("Validation database is not empty; preserve review data.")
    teacher = User.objects.create_user("professor.teste", email="professor@example.test",
                                       first_name="Professor", last_name="de Teste", password=PASSWORD)
    User.objects.create_user("outro.professor", password=PASSWORD)
    User.objects.create_superuser("admin.teste", "admin@example.test", PASSWORD)
    school = School.objects.create(owner=teacher, name="Escola Fictícia de Homologação")
    year = AcademicYear.objects.create(owner=teacher, year=2026)
    term = Term.objects.create(owner=teacher, school=school, academic_year=year,
                               name="1º bimestre", start_date=date(2026, 2, 1), end_date=date(2026, 4, 30))
    subjects = [Subject.objects.create(owner=teacher, name=name) for name in ("Matemática", "História")]
    first = {}
    for room_index in range(3):
        room = Classroom.objects.create(owner=teacher, school=school, academic_year=year,
                                         name=f"7º {chr(65 + room_index)}", shift="morning")
        room.subjects.add(*subjects)
        roster = []
        for number in range(40):
            student = Student.objects.create(owner=teacher, name=f"Aluno fictício {room_index + 1}-{number + 1:02}")
            roster.append(Enrollment.objects.create(owner=teacher, classroom=room, student=student,
                                                      starts_on=date(2026, 2, 1)))
        for subject in subjects:
            book = Gradebook.objects.create(owner=teacher, classroom=room, subject=subject, term=term)
            for number in range(4):
                assessment = Assessment.objects.create(owner=teacher, gradebook=book,
                    title=f"Atividade {number + 1}", date=date(2026, 3, 1) + timedelta(days=number), maximum=10)
                # Fixture-only bulk inserts: relationships above belong to the same owner/room.
                Grade.objects.bulk_create([Grade(owner=teacher, assessment=assessment, enrollment=pupil,
                    status="submitted", score=Decimal("8.50")) for pupil in roster])
                if not first:
                    first = {"classroom": room.pk, "term": term.pk, "subject": subject.pk,
                             "book": book.pk, "assessment": assessment.pk, "enrollment": roster[0].pk}
            for number in range(12):
                lesson = Lesson.objects.create(owner=teacher, classroom=room, subject=subject,
                    date=date(2026, 2, 2) + timedelta(days=number), quantity=2, content="Conteúdo fictício para validação.")
                Attendance.objects.bulk_create([Attendance(owner=teacher, lesson=lesson, enrollment=pupil,
                    absences=1 if number == 0 else 0, justified_absences=0) for pupil in roster])
                if "lesson" not in first:
                    first["lesson"] = lesson.pk
    return {**first, "students": 120, "classrooms": 3, "subjects_per_class": 2,
            "lessons": Lesson.objects.count(), "grades": Grade.objects.count(),
            "attendance": Attendance.objects.count()}
