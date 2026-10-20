"""Regras de frequência e gravações atômicas com histórico de alterações."""
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils.crypto import salted_hmac

from .models import Attendance, Enrollment, Lesson, LessonAudit


CONFLICT_MESSAGE = (
    "Este registro mudou em outra aba ou dispositivo. Recarregue a página antes de salvar."
)


def roster_for(lesson):
    existing_ids = set(lesson.attendance_records.values_list("enrollment_id", flat=True))
    enrollments = Enrollment.objects.filter(
        owner_id=lesson.owner_id, classroom_id=lesson.classroom_id
    ).select_related("student", "classroom__academic_year")
    return [item for item in enrollments if item.covers(lesson.date) or item.pk in existing_ids]


def roster_token(roster):
    payload = "|".join(f"{item.pk}:{item.updated_at.isoformat()}" for item in roster)
    return salted_hmac("attendance-roster", payload).hexdigest()


def attendance_state(lesson):
    roster = roster_for(lesson)
    saved = lesson.attendance_records.count()
    if lesson.is_cancelled:
        label = "Cancelada"
    elif not roster:
        label = "Sem alunos na data"
    elif saved == len(roster):
        label = "Chamada completa"
    elif saved:
        label = "Chamada parcial"
    else:
        label = "Chamada pendente"
    return {"label": label, "saved": saved, "expected": len(roster)}


def lesson_snapshot(lesson):
    return {
        "Disciplina": str(lesson.subject),
        "Data": lesson.date.strftime("%d/%m/%Y"),
        "Quantidade de aulas": str(lesson.quantity),
        "Conteúdo": lesson.content,
        "Observações": lesson.notes or "—",
    }


def differences(before, after, prefix=""):
    return [
        {"label": prefix + key, "before": str(before.get(key, "Não lançado")),
         "after": str(value)}
        for key, value in after.items() if before.get(key) != value
    ]


def claim_version(lesson, expected):
    # Compare-and-swap also prevents stale writes on SQLite, where row locks are unavailable.
    changed = Lesson.objects.filter(
        pk=lesson.pk, owner_id=lesson.owner_id, version=expected, is_cancelled=False
    ).update(version=F("version") + 1)
    if changed != 1:
        raise ValidationError(CONFLICT_MESSAGE)
    lesson.version = expected + 1


def check_version(lesson, expected):
    if lesson.is_cancelled:
        raise ValidationError("Esta aula foi cancelada e permanece apenas para consulta.")
    if lesson.version != expected:
        raise ValidationError(CONFLICT_MESSAGE)


def write_audit(lesson, actor, kind, changes, reason=""):
    LessonAudit.objects.create(
        owner=actor, actor=actor, lesson=lesson, kind=kind, changes=changes, reason=reason
    )


@transaction.atomic
def save_lesson(form, actor):
    lesson = form.instance
    if lesson.pk:
        current = Lesson.objects.select_for_update().get(pk=lesson.pk, owner=actor)
        check_version(current, form.cleaned_data["version"])
        changes = differences(lesson_snapshot(current), lesson_snapshot(lesson))
        if not changes:
            return lesson, False
        claim_version(lesson, current.version)
        kind = LessonAudit.Kind.EDITED
    else:
        lesson.version = 1
        changes = differences({}, lesson_snapshot(lesson))
        kind = LessonAudit.Kind.CREATED
    lesson.owner = actor
    lesson.save()
    write_audit(lesson, actor, kind, changes, form.cleaned_data.get("reason", ""))
    return lesson, True


def attendance_snapshot(record):
    return {
        "Faltas": str(record.absences),
        "Faltas justificadas": str(record.justified_absences),
        "Justificativa": record.justification or "—",
    }


@transaction.atomic
def save_attendance(form, actor):
    lesson = Lesson.objects.select_for_update().get(pk=form.lesson.pk, owner=actor)
    check_version(lesson, form.cleaned_data["version"])
    roster = roster_for(lesson)
    if roster_token(roster) != form.cleaned_data["roster_token"]:
        raise ValidationError("As matrículas mudaram. Recarregue a chamada antes de salvar.")
    if not roster:
        raise ValidationError("Não há alunos matriculados na data desta aula.")
    stored = {row.enrollment_id: row for row in
              lesson.attendance_records.select_for_update().filter(owner=actor)}
    changes, records = [], []
    has_corrections = False
    for enrollment in roster:
        record = stored.get(enrollment.pk)
        before = attendance_snapshot(record) if record else {}
        record = record or Attendance(owner=actor, lesson=lesson, enrollment=enrollment)
        record.absences = form.cleaned_data[f"absences_{enrollment.pk}"]
        record.justified_absences = form.cleaned_data[f"justified_{enrollment.pk}"]
        record.justification = form.cleaned_data[f"note_{enrollment.pk}"]
        delta = differences(before, attendance_snapshot(record), f"{enrollment.student} — ")
        if delta:
            has_corrections = has_corrections or bool(record.pk)
            changes.extend(delta)
            records.append(record)
    if not changes:
        return False
    if has_corrections and not form.cleaned_data["reason"]:
        raise ValidationError("Informe o motivo da correção da chamada.")
    claim_version(lesson, lesson.version)
    for record in records:
        record.save()
    lesson.save(update_fields=["version", "updated_at"])
    write_audit(lesson, actor, LessonAudit.Kind.ATTENDANCE, changes, form.cleaned_data["reason"])
    return True


@transaction.atomic
def cancel_lesson(lesson_id, actor, version, reason):
    lesson = Lesson.objects.select_for_update().get(pk=lesson_id, owner=actor)
    check_version(lesson, version)
    if not reason.strip():
        raise ValidationError("Informe o motivo do cancelamento.")
    claim_version(lesson, version)
    lesson.is_cancelled = True
    lesson.save()
    write_audit(lesson, actor, LessonAudit.Kind.CANCELLED, [
        {"label": "Situação", "before": "Registrada", "after": "Cancelada"}
    ], reason)


def frequency_rows(classroom, lessons):
    """Percentual somente sobre aulas com chamada; pendências nunca viram presença."""
    lessons = list(lessons.filter(is_cancelled=False))
    records = {
        (record.enrollment_id, record.lesson_id): record
        for record in Attendance.objects.filter(
            owner_id=classroom.owner_id, lesson__in=lessons,
            enrollment__classroom=classroom,
        )
    }
    rows = []
    enrollments = classroom.enrollments.filter(owner_id=classroom.owner_id).select_related(
        "student", "classroom__academic_year"
    )
    for enrollment in enrollments:
        total = recorded = absences = justified = 0
        for lesson in lessons:
            record = records.get((enrollment.pk, lesson.pk))
            if record or enrollment.covers(lesson.date):
                total += lesson.quantity
                if record:
                    recorded += lesson.quantity
                    absences += record.absences
                    justified += record.justified_absences
        presence = recorded - absences
        percentage = (
            (Decimal(presence) * 100 / Decimal(recorded)).quantize(
                Decimal("0.1"), rounding=ROUND_HALF_UP
            ) if recorded else None
        )
        rows.append({
            "enrollment": enrollment, "total": total, "recorded": recorded,
            "pending": total - recorded, "present": presence, "absences": absences,
            "justified": justified, "percentage": percentage,
            "dates_missing": not enrollment.starts_on or (
                enrollment.status != Enrollment.Status.ACTIVE and not enrollment.ends_on
            ),
        })
    return rows
