from datetime import date
from django.conf import settings

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.forms import modelform_factory
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from .catalog import CATALOG
from .forms import OwnedModelForm, RegistrationForm
from .models import AcademicYear, Classroom, Enrollment, School, Student, Subject


@never_cache
@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if not settings.PUBLIC_REGISTRATION_ENABLED:
        return render(request, "registration/registration_closed.html", status=403)
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, "Sua conta está pronta. Vamos organizar seu diário!")
        return redirect("dashboard")
    return render(request, "registration/register.html", {"form": form})


@login_required
@never_cache
def dashboard(request):
    owner = request.user
    classrooms = Classroom.objects.filter(owner=owner).select_related(
        "school", "academic_year"
    ).annotate(student_count=Count("enrollments", filter=Q(enrollments__status="active")))
    school_count = School.objects.filter(owner=owner).count()
    student_count = Student.objects.filter(owner=owner).count()
    subject_count = Subject.objects.filter(owner=owner).count()
    return render(request, "diary/dashboard.html", {
        "active": "dashboard",
        "stats": [
            {"label": "Escolas", "value": school_count, "key": "escolas"},
            {"label": "Turmas", "value": classrooms.count(), "key": "turmas"},
            {"label": "Alunos cadastrados", "value": student_count, "key": "alunos"},
            {"label": "Matrículas ativas", "value": Enrollment.objects.filter(
                owner=owner, status="active").count(), "key": "matriculas"},
        ],
        "classrooms": classrooms[:6],
        "steps": [
            {"title": "Cadastre sua escola", "key": "escolas", "done": school_count > 0},
            {"title": "Defina o ano letivo", "key": "anos-letivos",
             "done": AcademicYear.objects.filter(owner=owner).exists()},
            {"title": "Adicione suas disciplinas", "key": "disciplinas", "done": subject_count > 0},
            {"title": "Crie a primeira turma", "key": "turmas", "done": classrooms.exists()},
            {"title": "Cadastre e matricule os alunos", "key": "matriculas",
             "done": Enrollment.objects.filter(owner=owner).exists()},
        ],
    })


def get_catalog(kind):
    if kind not in CATALOG:
        raise Http404
    return CATALOG[kind]


def display_value(record, name):
    value = getattr(record, name)
    value = value() if callable(value) else value
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    return str(value) if value not in (None, "") else "—"


@login_required
@never_cache
def record_list(request, kind):
    config = get_catalog(kind)
    records = config.model.objects.filter(owner=request.user).select_related()
    query = request.GET.get("q", "").strip()[:150]
    if query:
        search_field = {"anos-letivos": "year", "matriculas": "student__name"}.get(kind, "name")
        records = records.filter(**{f"{search_field}__icontains": query})
    page = Paginator(records, 20).get_page(request.GET.get("page"))
    rows = [{
        "pk": record.pk,
        "values": [display_value(record, name) for name, _ in config.columns],
    } for record in page]
    return render(request, "diary/record_list.html", {
        "active": kind, "kind": kind, "config": config,
        "rows": rows, "page_obj": page, "query": query,
    })


@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def record_form(request, kind, pk=None):
    config = get_catalog(kind)
    instance = get_object_or_404(config.model, pk=pk, owner=request.user) if pk else None
    form_class = modelform_factory(config.model, form=OwnedModelForm, fields=config.fields)
    form = form_class(request.POST if request.method == "POST" else None,
                      instance=instance, owner=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                form.save()
        except (ValidationError, IntegrityError):
            form.add_error(None, "Não foi possível salvar. Verifique se o registro já existe "
                                 "ou se os dados vinculados foram alterados.")
        else:
            messages.success(request, "Alterações salvas." if pk else "Cadastro realizado.")
            return redirect("record_list", kind=kind)
    return render(request, "diary/record_form.html", {
        "active": kind, "kind": kind, "config": config, "form": form, "editing": bool(pk),
    })


@login_required
@never_cache
def classroom_detail(request, pk):
    classroom = get_object_or_404(
        Classroom.objects.select_related("school", "academic_year"), pk=pk, owner=request.user
    )
    return render(request, "diary/classroom_detail.html", {
        "active": "turmas", "classroom": classroom,
        "subjects": classroom.subjects.filter(owner=request.user),
        "enrollments": classroom.enrollments.filter(
            owner=request.user).select_related("student"),
    })

