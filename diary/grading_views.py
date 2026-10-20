from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, OperationalError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from .grading_forms import AssessmentForm, BookForm, GradeForm
from .grading_services import cancel_assessment, grade_summary, save_assessment, save_book, save_grades
from .models import Assessment, Gradebook
from .teaching_forms import CancelLessonForm
from .teaching_views import save_error

ERRORS = (ValidationError, IntegrityError, OperationalError)


def own_book(user, pk):
    return get_object_or_404(Gradebook.objects.select_related(
        "classroom__school", "classroom__academic_year", "subject", "term"), pk=pk, owner=user)


def own_assessment(user, pk):
    return get_object_or_404(Assessment.objects.select_related(
        "gradebook__classroom__school", "gradebook__classroom__academic_year",
        "gradebook__subject", "gradebook__term"), pk=pk, owner=user)


@login_required
@never_cache
def book_list(request):
    books = Gradebook.objects.filter(owner=request.user).select_related(
        "classroom__school", "classroom__academic_year", "subject", "term")
    classroom = request.GET.get("classroom", "")
    if classroom:
        books = books.filter(classroom_id=int(classroom)) if classroom.isdecimal() and len(classroom) < 12 else books.none()
    return render(request, "diary/book_list.html", {
        "active": "grades", "page_obj": Paginator(books, 20).get_page(request.GET.get("page")),
        "classroom_filter": classroom,
    })


@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def book_form(request, pk=None):
    book = own_book(request.user, pk) if pk else None
    form = BookForm(request.POST if request.method == "POST" else None, instance=book, owner=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            saved = save_book(form, request.user)
        except ERRORS as error:
            save_error(form, error)
        else:
            messages.success(request, "Regras do caderno salvas.")
            return redirect("book_detail", pk=saved.pk)
    return render(request, "diary/grading_form.html", {
        "active": "grades", "form": form, "book": book,
        "title": "Configurar caderno" if book else "Novo caderno de notas", "policy": True,
    })


@login_required
@never_cache
def book_detail(request, pk):
    book = own_book(request.user, pk)
    summary = grade_summary(book)
    return render(request, "diary/book_detail.html", {
        "active": "grades", "book": book, **summary,
        "all_assessments": book.assessments.all(),
        "history": Paginator(book.history.select_related("actor"), 10).get_page(request.GET.get("historico")),
    })


@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def assessment_form(request, book_pk=None, pk=None):
    assessment = own_assessment(request.user, pk) if pk else None
    book = assessment.gradebook if assessment else own_book(request.user, book_pk)
    if assessment and assessment.is_cancelled:
        return redirect("grade_form", pk=assessment.pk)
    form = AssessmentForm(request.POST if request.method == "POST" else None, owner=request.user,
                          instance=assessment, gradebook=book)
    if request.method == "POST" and form.is_valid():
        try:
            saved = save_assessment(form, request.user)
        except ERRORS as error:
            save_error(form, error)
        else:
            messages.success(request, "Avaliação salva.")
            return redirect("grade_form", pk=saved.pk)
    return render(request, "diary/grading_form.html", {
        "active": "grades", "form": form, "book": book, "assessment": assessment,
        "title": "Corrigir avaliação" if assessment else "Nova avaliação",
    })


@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def grade_form(request, pk):
    assessment = own_assessment(request.user, pk)
    form = GradeForm(request.POST if request.method == "POST" else None, assessment=assessment)
    if request.method == "POST" and assessment.is_cancelled:
        messages.error(request, "Avaliação cancelada: disponível apenas para consulta.")
        return redirect("grade_form", pk=pk)
    if request.method == "POST" and form.is_valid():
        try:
            changed = save_grades(form, request.user)
        except ERRORS as error:
            save_error(form, error)
        else:
            messages.success(request, "Notas e entregas salvas." if changed else "Nenhuma alteração necessária.")
            return redirect("book_detail", pk=assessment.gradebook_id)
    return render(request, "diary/grade_form.html", {
        "active": "grades", "form": form, "assessment": assessment, "book": assessment.gradebook,
        "records": assessment.grades.select_related("enrollment__student").order_by("enrollment__student__name"),
    })


@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def assessment_cancel(request, pk):
    assessment = own_assessment(request.user, pk)
    if assessment.is_cancelled:
        return redirect("grade_form", pk=pk)
    form = CancelLessonForm(request.POST if request.method == "POST" else None,
                            initial={"version": assessment.gradebook.version})
    if request.method == "POST" and form.is_valid():
        try:
            cancel_assessment(pk, request.user, form.cleaned_data["version"], form.cleaned_data["reason"])
        except ERRORS as error:
            save_error(form, error)
        else:
            messages.success(request, "Avaliação cancelada. Lançamentos preservados e excluídos dos cálculos.")
            return redirect("book_detail", pk=assessment.gradebook_id)
    return render(request, "diary/grading_form.html", {
        "active": "grades", "form": form, "book": assessment.gradebook,
        "title": f"Cancelar: {assessment.title}", "cancelling": True,
    })
