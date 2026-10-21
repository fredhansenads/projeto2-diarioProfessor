from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


def client_ip(request):
    # WSGI server must validate the proxy before setting REMOTE_ADDR.
    # Never trust client-supplied X-Forwarded-For in application code.
    return request.META.get("REMOTE_ADDR") or None


@never_cache
def login_locked(request, credentials=None, *args, **kwargs):
    response = render(request, "registration/locked.html", status=429)
    response["Retry-After"] = "900"
    return response


@never_cache
def csrf_failure(request, reason=""):
    return render(request, "403_csrf.html", status=403)


@never_cache
@require_GET
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})
