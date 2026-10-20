from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from .report_exports import csv_report, pdf_report
from .report_forms import ReportFilterForm
from .report_services import build_report, canonical_query


@login_required
@never_cache
@require_GET
def report_view(request):
    form = ReportFilterForm(request.GET if request.GET else None, owner=request.user)
    output = request.GET.get("format", "html")
    if output not in {"html", "print", "csv", "pdf"}:
        return HttpResponse("Formato de relatório inválido.", status=400, content_type="text/plain; charset=utf-8")
    report, query = None, ""
    valid = form.is_bound and form.is_valid()
    if valid:
        report = build_report(owner=request.user, **form.cleaned_data)
        query = canonical_query(form.cleaned_data)
        for row in report["rows"]:
            row["individual_query"] = canonical_query(form.cleaned_data, enrollment=row["enrollment"].pk)
        if output in {"pdf", "csv"}:
            data = pdf_report(report) if output == "pdf" else csv_report(report)
            response = HttpResponse(data, content_type="application/pdf" if output == "pdf" else "text/csv; charset=utf-8")
            kind = "aluno" if report["enrollment"] else "turma"
            filename = f"relatorio-{kind}-{report['classroom'].pk}-periodo-{report['term'].pk}.{output}"
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            response["X-Content-Type-Options"] = "nosniff"
            return response
    return render(request, "diary/report.html", {
        "active": "reports", "filter_form": form, "report": report, "report_query": query,
        "printing": output == "print",
    }, status=400 if output != "html" and not valid else 200)
