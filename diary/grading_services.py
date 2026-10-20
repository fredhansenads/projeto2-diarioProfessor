"""Cálculos decimais e gravações atômicas do caderno de notas."""
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import Assessment, Grade, GradeAudit, Gradebook
from .teaching_services import CONFLICT_MESSAGE, differences, roster_token


def grade_roster(assessment):
    existing = set(assessment.grades.values_list("enrollment_id", flat=True))
    return [enrollment for enrollment in assessment.gradebook.classroom.enrollments.filter(
        owner_id=assessment.owner_id).select_related("student", "classroom__academic_year")
        if enrollment.covers(assessment.date) or enrollment.pk in existing]


def snapshot(instance, fields):
    values = {}
    for name in fields:
        field = instance._meta.get_field(name)
        value = getattr(instance, f"get_{name}_display")() if field.choices else getattr(instance, name)
        values[str(field.verbose_name)] = str(value) if value is not None and value != "" else "—"
    return values


POLICY_FIELDS = ("calculation", "scale", "minimum", "precision", "rounding", "recovery")
ASSESSMENT_FIELDS = ("title", "kind", "date", "maximum", "weight", "instructions")
GRADE_FIELDS = ("status", "score", "note")


def lock_book(pk, actor, version):
    book = Gradebook.objects.select_for_update().select_related(
        "classroom__academic_year", "term", "subject").get(pk=pk, owner=actor)
    if book.version != version:
        raise ValidationError(CONFLICT_MESSAGE)
    return book


def claim_book(book):
    changed = Gradebook.objects.filter(pk=book.pk, owner_id=book.owner_id, version=book.version).update(
        version=F("version") + 1, updated_at=timezone.now())
    if changed != 1:
        raise ValidationError(CONFLICT_MESSAGE)
    book.version += 1


def audit(book, actor, action, changes, reason=""):
    GradeAudit.objects.create(owner=actor, actor=actor, gradebook=book,
                              action=action, changes=changes, reason=reason)


@transaction.atomic
def save_book(form, actor):
    book = form.instance
    if book.pk:
        current = lock_book(book.pk, actor, form.cleaned_data["version"])
        changes = differences(snapshot(current, POLICY_FIELDS), snapshot(book, POLICY_FIELDS))
        if not changes:
            return book
        if not form.cleaned_data.get("reason"):
            raise ValidationError("Informe o motivo da alteração das regras.")
        claim_book(current)
        book.version = current.version
    else:
        book.version = 1
        changes = differences({}, snapshot(book, ("classroom", "subject", "term") + POLICY_FIELDS))
    book.owner = actor
    book.save()
    audit(book, actor, "Regras do caderno salvas", changes, form.cleaned_data.get("reason", ""))
    return book


@transaction.atomic
def save_assessment(form, actor):
    item = form.instance
    book = lock_book(item.gradebook_id, actor, form.cleaned_data["version"])
    item.gradebook = book
    before = {}
    if item.pk:
        current = Assessment.objects.get(pk=item.pk, owner=actor, gradebook=book)
        if current.is_cancelled:
            raise ValidationError("Avaliação cancelada.")
        before = snapshot(current, ASSESSMENT_FIELDS)
    changes = differences(before, snapshot(item, ASSESSMENT_FIELDS))
    if not changes:
        return item
    if item.pk and not form.cleaned_data.get("reason"):
        raise ValidationError("Informe o motivo da correção.")
    claim_book(book)
    item.owner = actor
    item.save()
    audit(book, actor, "Avaliação salva", changes, form.cleaned_data.get("reason", ""))
    return item


@transaction.atomic
def save_grades(form, actor):
    book = lock_book(form.assessment.gradebook_id, actor, form.cleaned_data["version"])
    assessment = Assessment.objects.get(pk=form.assessment.pk, owner=actor, gradebook=book)
    if assessment.is_cancelled:
        raise ValidationError("Avaliação cancelada.")
    roster = grade_roster(assessment)
    if roster_token(roster) != form.cleaned_data["roster_token"]:
        raise ValidationError("As matrículas mudaram. Recarregue a página antes de salvar.")
    if not roster:
        raise ValidationError("Não há alunos matriculados na data da avaliação.")
    stored = {row.enrollment_id: row for row in assessment.grades.filter(owner=actor)}
    changes, records = [], []
    correction = False
    for enrollment in roster:
        record = stored.get(enrollment.pk)
        before = snapshot(record, GRADE_FIELDS) if record else {}
        values = {field: form.cleaned_data[f"{field}_{enrollment.pk}"] for field in GRADE_FIELDS}
        if record is None and values == {"status": "pending", "score": None, "note": ""}:
            continue
        record = record or Grade(owner=actor, assessment=assessment, enrollment=enrollment)
        for field, value in values.items():
            setattr(record, field, value)
        delta = differences(before, snapshot(record, GRADE_FIELDS), f"{assessment.title} · {enrollment.student} — ")
        if delta:
            correction = correction or bool(record.pk)
            record.full_clean()
            changes.extend(delta)
            records.append(record)
    if not changes:
        return False
    if correction and not form.cleaned_data["reason"]:
        raise ValidationError("Informe o motivo da correção dos lançamentos.")
    claim_book(book)
    for record in records:
        record.save()
    audit(book, actor, "Notas e entregas salvas", changes, form.cleaned_data["reason"])
    return True


@transaction.atomic
def cancel_assessment(pk, actor, version, reason):
    item = Assessment.objects.get(pk=pk, owner=actor)
    book = lock_book(item.gradebook_id, actor, version)
    item.refresh_from_db()
    if item.is_cancelled or not reason.strip():
        raise ValidationError("Informe um motivo e verifique se a avaliação está ativa.")
    claim_book(book)
    item.is_cancelled = True
    item.save()
    audit(book, actor, "Avaliação cancelada", [
        {"label": item.title, "before": "Ativa", "after": "Cancelada; excluída dos cálculos"}
    ], reason)


def round_score(book, value):
    return value.quantize(Decimal(1).scaleb(-book.precision),
                          rounding=ROUND_HALF_UP if book.rounding == "half_up" else ROUND_DOWN)


def grade_summary(book):
    """Ausências de nota nunca são zeros. Recuperação só produz resultado com base completa."""
    assessments = list(book.assessments.filter(is_cancelled=False))
    regular = [item for item in assessments if item.kind != "recovery"]
    recovery = next((item for item in assessments if item.kind == "recovery"), None)
    records = {(record.enrollment_id, record.assessment_id): record for record in Grade.objects.filter(
        owner_id=book.owner_id, assessment__in=assessments)}
    planned = sum((item.maximum for item in regular), Decimal(0))
    points_ready = book.calculation != "points" or planned == book.scale
    rows = []
    for enrollment in book.classroom.enrollments.filter(owner_id=book.owner_id).select_related(
            "student", "classroom__academic_year"):
        relevant = [item for item in regular if enrollment.covers(item.date) or (enrollment.pk, item.pk) in records]
        # Keep students in the period, including those with no assessments yet.
        start = enrollment.starts_on or book.term.start_date
        end = enrollment.ends_on or book.term.end_date
        if not relevant and (start > book.term.end_date or end < book.term.start_date or
                             (enrollment.status != "active" and not enrollment.ends_on)):
            continue
        pending = missing = exempt = 0
        values, cells = [], []
        for item in relevant:
            record = records.get((enrollment.pk, item.pk))
            cells.append({"assessment": item, "record": record})
            if record and record.status == "exempt":
                exempt += 1
            elif not record or record.score is None:
                pending += 1
            else:
                values.append((item, record.score))
            if record and record.status == "missing":
                missing += 1
        original = None
        if values:
            if book.calculation == "points":
                original = sum((score for _, score in values), Decimal(0))
            else:
                denominator = sum((item.weight if book.calculation == "weighted" else Decimal(1)
                                   for item, _ in values), Decimal(0))
                original = sum((score / item.maximum * book.scale *
                                (item.weight if book.calculation == "weighted" else Decimal(1))
                                for item, score in values), Decimal(0)) / denominator
        complete = bool(values) and pending == 0 and points_ready
        final = original if complete else None
        recovered = records.get((enrollment.pk, recovery.pk)) if recovery else None
        recovery_score = None
        recovery_pending = bool(recovered and recovered.status != "exempt" and recovered.score is None)
        if recovered and recovered.score is not None:
            recovery_score = recovered.score / recovery.maximum * book.scale
            if complete:
                if book.recovery == "higher":
                    final = max(original, recovery_score)
                elif book.recovery == "replace":
                    final = recovery_score
                elif book.recovery == "average":
                    final = (original + recovery_score) / 2
        if recovery_pending:
            final = None
        final = round_score(book, final) if final is not None else None
        status = ("Atingiu a referência" if final >= book.minimum else "Abaixo da referência") if final is not None else (
            "Recuperação pendente" if recovery_pending else "Parcial / pendente" if pending or not points_ready else "Sem notas")
        rows.append({"enrollment": enrollment, "original": round_score(book, original) if original is not None else None,
                     "final": final, "pending": pending + int(recovery_pending),
                     "missing": missing + int(bool(recovered and recovered.status == "missing")), "exempt": exempt,
                     "recovery": round_score(book, recovery_score) if recovery_score is not None else None,
                     "status": status, "cells": cells})
    return {"rows": rows, "points_ready": points_ready, "planned": planned, "assessments": assessments}
