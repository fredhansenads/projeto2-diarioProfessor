from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.staticfiles import finders
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class PWATests(TestCase):
    def test_manifest_icons_have_real_matching_sizes_and_opaque_background(self):
        response = self.client.get(reverse("manifest"))
        self.assertEqual(response["Content-Type"], "application/manifest+json")
        manifest = response.json()
        self.assertEqual(manifest["start_url"], "/")
        self.assertEqual(manifest["scope"], "/")
        self.assertEqual(manifest["display"], "standalone")
        self.assertEqual({icon["sizes"] for icon in manifest["icons"]}, {"192x192", "512x512"})
        for icon in manifest["icons"]:
            with Image.open(finders.find(icon["src"].removeprefix("/static/"))) as image:
                self.assertEqual("x".join(map(str, image.size)), icon["sizes"])
                self.assertEqual(image.mode, "RGB")
        with Image.open(finders.find("diary/icon-180.png")) as apple:
            self.assertEqual(apple.size, (180, 180))

    def test_public_offline_assets_never_include_session_information(self):
        routes = [reverse("offline"), reverse("manifest"), reverse("service_worker")]
        anonymous = {url: self.client.get(url).content for url in routes}
        user = User.objects.create_user(username="PRIVATE_TEACHER", first_name="PRIVATE_NAME")
        self.client.force_login(user)
        for url in routes:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.content, anonymous[url])
                self.assertNotContains(response, "PRIVATE_")
                self.assertNotContains(response, "csrfmiddlewaretoken")
                self.assertFalse(response.cookies)
                self.assertNotIn("Cookie", response.get("Vary", ""))

    def test_worker_root_scope_mime_and_revalidation(self):
        response = self.client.get(reverse("service_worker"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/javascript")
        self.assertEqual(response["Service-Worker-Allowed"], "/")
        self.assertEqual(response["Cache-Control"], "no-cache")
        self.assertEqual(response.content.decode(), (Path(settings.BASE_DIR) / "static/diary/service-worker.js").read_text(encoding="utf-8"))

    def test_install_help_available_signed_in_and_out_but_never_cached(self):
        for user in [None, User.objects.create_user(username="teacher")]:
            if user:
                self.client.force_login(user)
            response = self.client.get(reverse("install"))
            self.assertContains(response, "Android")
            self.assertContains(response, "iPhone")
            self.assertContains(response, "internet para consultar e salvar")
            self.assertIn("no-store", response["Cache-Control"])

    def test_new_routes_reject_mutations(self):
        for route in ("manifest", "offline", "service_worker", "install"):
            self.assertEqual(self.client.post(reverse(route)).status_code, 405)

    def test_pwa_entrypoint_preserves_authentication_boundary(self):
        self.assertRedirects(self.client.get("/"), "/conta/login/?next=/", fetch_redirect_response=False)
        response = self.client.get(reverse("login"))
        self.assertContains(response, 'rel="manifest"')
        self.assertContains(response, 'rel="apple-touch-icon"')
        self.assertContains(response, 'id="connection-status"')
        self.assertContains(response, "/static/diary/pwa.js")

    def test_offline_page_is_self_contained_and_never_promises_save(self):
        response = self.client.get(reverse("offline"))
        self.assertContains(response, "Não foi possível confirmar o resultado")
        self.assertContains(response, "Nenhum envio será repetido automaticamente")
        self.assertNotContains(response, "<script")
        self.assertNotContains(response, '<link rel="stylesheet"')
