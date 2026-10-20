"""Um mesmo conjunto de dados alimenta tela, impressão, CSV e PDF."""
from urllib.parse import urlencode

from django.db import transaction
from django.utils import timezone

from .grading_services import grade_summary
from .models import Attendance, Grade, Gradebook, Lesson
from .teaching_services import frequency_rows


def in_period(enrollment, term):
    if enrollment.status != "active" and not enrollment.ends_on:
        return False
    return (not enrollment.starts_on or enrollment.starts_on <= term.end_date) and (
        not enrollment.ends_on or enrollment.ends_on >= term.start_date)


def canonical_query(data, **overrides):
    values = {key: value.pk for key, value in data.items() if value is not None}
    values.update(overrides)
    return urlencode(values)


@transaction.atomic
def build_report(*, owner, classroom, term, subject=None, enrollment=None, **unused):
    # Only called with validated, owner-scoped filter values.
    if any(item.owner_id != owner.pk for item in (classroom, term, subject, enrollment) if item is not None):
        raise ValueError("Relatório fora da conta.")
    subjects = classroom.subjects.filter(owner=owner)
    if subject:
        subjects = subjects.filter(pk=subject.pk)
    books = {book.subject_id: book for book in Gradebook.objects.filter(
        owner=owner, classroom=classroom, term=term).select_related("classroom__academic_year", "subject", "term")}
    enrollments = list(classroom.enrollments.filter(owner=owner).select_related("student", "classroom__academic_year"))
    if enrollment:
        enrollments = [item for item in enrollments if item.pk == enrollment.pk]
    lessons = Lesson.objects.filter(owner=owner, classroom=classroom, is_cancelled=False,
                                    date__range=(term.start_date, term.end_date)).select_related("subject")
    if subject:
        lessons = lessons.filter(subject=subject)
    attendance = {(record.enrollment_id, record.lesson_id): record for record in Attendance.objects.filter(
        owner=owner, lesson__in=lessons, enrollment__in=enrollments)}
    grades = {(record.enrollment_id, record.assessment_id): record for record in Grade.objects.filter(
        owner=owner, assessment__gradebook__in=list(books.values()), assessment__is_cancelled=False,
        enrollment__in=enrollments).select_related("assessment")}
    groups, rows = [], []
    for discipline in subjects:
        book = books.get(discipline.pk)
        summary = grade_summary(book) if book else None
        grade_rows = {item["enrollment"].pk: item for item in summary["rows"]} if summary else {}
        subject_lessons = lessons.filter(subject=discipline).order_by("date", "pk")
        frequencies = {item["enrollment"].pk: item for item in frequency_rows(classroom, subject_lessons)}
        group = {"subject": discipline, "book": book, "rows": [], "points_ready": summary["points_ready"] if summary else True,
                 "planned": summary["planned"] if summary else None}
        lesson_items = list(subject_lessons)
        for pupil in enrollments:
            frequency = frequencies[pupil.pk]
            grade = grade_rows.get(pupil.pk)
            if not in_period(pupil, term) and not frequency["total"] and not grade:
                continue
            grade = grade or {"original": None, "recovery": None, "final": None, "pending": None,
                              "missing": None, "exempt": None,
                              "status": "Sem notas" if book else "Sem caderno de notas"}
            assessment_items, attendance_items, observations, pending_items = [], [], [], []
            for assessment in summary["assessments"] if summary else []:
                record = grades.get((pupil.pk, assessment.pk))
                if not record and not pupil.covers(assessment.date):
                    continue
                optional = assessment.kind == "recovery" and record is None
                status = record.get_status_display() if record else ("Não participante" if optional else "Sem lançamento")
                item = {"assessment": assessment, "record": record, "status": status,
                        "score": record.score if record else None, "note": record.note if record else ""}
                assessment_items.append(item)
                if not optional and (not record or (record.score is None and record.status != "exempt")):
                    pending_items.append(f"{assessment.date:%d/%m/%Y} · {assessment.title} ({status})")
                if record and record.note:
                    observations.append(f"Avaliação {assessment.date:%d/%m/%Y} · {assessment.title}: {record.note}")
            for lesson in lesson_items:
                record = attendance.get((pupil.pk, lesson.pk))
                if not record and not pupil.covers(lesson.date):
                    continue
                attendance_items.append({"lesson": lesson, "record": record})
                if record and record.justification:
                    observations.append(f"Frequência {lesson.date:%d/%m/%Y}: {record.justification}")
            row = {"enrollment": pupil, "subject": discipline, "book": book, "grade": grade,
                   "frequency": frequency, "assessments": assessment_items, "attendance": attendance_items,
                   "observations": observations, "pending_items": pending_items,
                   "status": grade["status"] if grade else "Sem caderno / sem notas",
                   "dates_missing": frequency["dates_missing"]}
            rows.append(row)
            group["rows"].append(row)
        groups.append(group)
    return {"classroom": classroom, "term": term, "subject": subject, "enrollment": enrollment,
            "groups": groups, "rows": rows, "generated_at": timezone.localtime(),
            "teacher": owner.get_full_name() or owner.username,
            "student_count": len({row["enrollment"].pk for row in rows}),
            "missing_dates": any(row["dates_missing"] for row in rows)}
