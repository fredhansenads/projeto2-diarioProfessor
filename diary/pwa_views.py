from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


@require_GET
def manifest(request):
    response = JsonResponse({
        "id": "/", "name": "Diário do Professor", "short_name": "Meu Diário",
        "lang": "pt-BR", "start_url": "/", "scope": "/",
        "display": "standalone", "background_color": "#f6f7f3",
        "theme_color": "#244e43",
        "description": "Turmas, aulas, frequência e notas. Requer internet.",
        "icons": [
            {"src": static(f"diary/icon-{size}.png"), "sizes": f"{size}x{size}",
             "type": "image/png", "purpose": "any maskable"}
            for size in (192, 512)
        ],
    }, content_type="application/manifest+json")
    response["Cache-Control"] = "public, max-age=3600"
    return response


@require_GET
def service_worker(request):
    response = HttpResponse(
        (settings.BASE_DIR / "static/diary/service-worker.js").read_text(encoding="utf-8"),
        content_type="application/javascript",
    )
    response["Cache-Control"] = "no-cache"
    response["Service-Worker-Allowed"] = "/"
    return response


@require_GET
def offline(request):
    # Deliberately independent of sessions, templates and student data.
    response = HttpResponse(
        (settings.BASE_DIR / "static/diary/offline.html").read_text(encoding="utf-8")
    )
    response["Cache-Control"] = "public, max-age=3600"
    return response


@never_cache
@require_GET
def install(request):
    return render(request, "diary/install.html")
