from django.contrib import admin
from django.urls import include, path
from diary import pwa_views, security

urlpatterns = [
    path("saude/", security.health, name="health"),
    path("manifest.webmanifest", pwa_views.manifest, name="manifest"),
    path("service-worker.js", pwa_views.service_worker, name="service_worker"),
    path("offline/", pwa_views.offline, name="offline"),
    path("instalar/", pwa_views.install, name="install"),
    path("admin/", admin.site.urls),
    path("conta/", include("django.contrib.auth.urls")),
    path("", include("diary.urls")),
]

