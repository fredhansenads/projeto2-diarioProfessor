from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, OperationalError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from .models import Classroom, Lesson
from .teaching_forms import (
    AttendanceForm, CancelLessonForm, ChooseClassroomForm, LessonFilterForm, LessonForm,
)
from .teaching_services import (
    attendance_state, cancel_lesson, frequency_rows, save_attendance, save_lesson,
)


def own_lesson(user, pk):
    return get_object_or_404(
        Lesson.objects.select_related("classroom__school", "classroom__academic_year", "subject"),
        owner=user, pk=pk,
    )


def save_error(form, error):
    if isinstance(error, ValidationError):
        message = " ".join(error.messages)
    elif isinstance(error, IntegrityError):
        message = "Não foi possível salvar: há um registro duplicado ou os dados foram alterados. Recarregue a página."
    else:
        message = "Não foi possível gravar agora. Recarregue a página e tente novamente."
    form.add_error(None, message)


@login_required
@never_cache
def lesson_list(request):
    form = LessonFilterForm(request.GET, owner=request.user)
    queryset = form.apply(Lesson.objects.filter(owner=request.user).select_related(
        "classroom__school", "classroom__academic_year", "subject"
    ))
    page = Paginator(queryset, 20).get_page(request.GET.get("page"))
    query = request.GET.copy()
    query.pop("page", None)
    return render(request, "diary/lesson_list.html", {
        "active": "lessons", "filter_form": form, "page_obj": page,
        "items": [{"lesson": lesson, "state": attendance_state(lesson)} for lesson in page],
        "filter_query": query.urlencode(),
    })


@login_required
@never_cache
def lesson_choose(request):
    form = ChooseClassroomForm(request.GET if request.GET else None, owner=request.user)
    if form.is_bound and form.is_valid():
        return redirect("lesson_create", classroom_pk=form.cleaned_data["classroom"].pk)
    return render(request, "diary/lesson_choose.html", {"active": "lessons", "form": form})


@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def lesson_form(request, classroom_pk=None, pk=None):
    lesson = own_lesson(request.user, pk) if pk else None
    classroom = lesson.classroom if lesson else get_object_or_404(
        Classroom.objects.select_related("school", "academic_year"), owner=request.user, pk=classroom_pk
    )
    if lesson and lesson.is_cancelled:
        messages.error(request, "Esta aula foi cancelada e permanece apenas para consulta.")
        return redirect("lesson_detail", pk=lesson.pk)
    form = LessonForm(request.POST if request.method == "POST" else None,
                      instance=lesson, classroom=classroom, owner=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            saved, changed = save_lesson(form, request.user)
        except (ValidationError, IntegrityError, OperationalError) as error:
            save_error(form, error)
        else:
            messages.success(request, "Aula salva." if changed else "Nenhuma alteração necessária.")
            return redirect("lesson_detail", pk=saved.pk)
    return render(request, "diary/lesson_form.html", {
        "active": "lessons", "form": form, "classroom": classroom, "lesson": lesson,
        "locked": bool(lesson and lesson.attendance_records.exists()),
    })


@login_required
@never_cache
def lesson_detail(request, pk):
    lesson = own_lesson(request.user, pk)
    history = Paginator(lesson.history.filter(owner=request.user).select_related("actor"), 10).get_page(
        request.GET.get("historico")
    )
    return render(request, "diary/lesson_detail.html", {
        "active": "lessons", "lesson": lesson, "state": attendance_state(lesson),
        "records": lesson.attendance_records.filter(owner=request.user).select_related("enrollment__student"),
        "history": history,
    })


@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def attendance_form(request, pk):
    lesson = own_lesson(request.user, pk)
    if lesson.is_cancelled:
        messages.error(request, "A chamada desta aula cancelada permanece apenas para consulta.")
        return redirect("lesson_detail", pk=pk)
    form = AttendanceForm(request.POST if request.method == "POST" else None, lesson=lesson)
    if request.method == "POST" and form.is_valid():
        try:
            changed = save_attendance(form, request.user)
        except (ValidationError, IntegrityError, OperationalError) as error:
            save_error(form, error)
        else:
            messages.success(request, "Chamada salva." if changed else "A chamada já está atualizada.")
            return redirect("lesson_detail", pk=pk)
    return render(request, "diary/attendance_form.html", {
        "active": "lessons", "lesson": lesson, "form": form,
    })


@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def lesson_cancel(request, pk):
    lesson = own_lesson(request.user, pk)
    if lesson.is_cancelled:
        return redirect("lesson_detail", pk=pk)
    form = CancelLessonForm(request.POST if request.method == "POST" else None,
                            initial={"version": lesson.version})
    if request.method == "POST" and form.is_valid():
        try:
            cancel_lesson(pk, request.user, form.cleaned_data["version"], form.cleaned_data["reason"])
        except (ValidationError, IntegrityError, OperationalError) as error:
            save_error(form, error)
        else:
            messages.success(request, "Aula cancelada. Os registros foram preservados no histórico.")
            return redirect("lesson_detail", pk=pk)
    return render(request, "diary/lesson_cancel.html", {
        "active": "lessons", "form": form, "lesson": lesson,
    })


@login_required
@never_cache
def classroom_frequency(request, pk):
    classroom = get_object_or_404(
        Classroom.objects.select_related("school", "academic_year"), owner=request.user, pk=pk
    )
    form = LessonFilterForm(request.GET, owner=request.user, classroom=classroom)
    lessons = form.apply(Lesson.objects.filter(owner=request.user, classroom=classroom))
    rows = frequency_rows(classroom, lessons)
    return render(request, "diary/frequency.html", {
        "active": "lessons", "classroom": classroom, "filter_form": form,
        "rows": rows, "lesson_count": lessons.count(),
        "missing_dates": any(row["dates_missing"] for row in rows),
    })
