from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import School


@override_settings(PUBLIC_REGISTRATION_ENABLED=True,
                   PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class PublicRegistrationTests(TestCase):
    def setUp(self):
        self.payload = {
            'first_name': 'Professora Teste', 'username': 'professora.nova',
            'email': 'professora@example.test',
            'password1': 'UmaSenhaBoa!2026', 'password2': 'UmaSenhaBoa!2026',
        }

    def test_login_links_to_registration_and_registration_links_back(self):
        self.assertContains(self.client.get(reverse('login')), 'href="/criar-conta/"')
        response = self.client.get(reverse('register'))
        self.assertContains(response, 'Criar minha conta')
        self.assertContains(response, 'href="/conta/login/"')
        self.assertIn('no-store', response['Cache-Control'])

    def test_signup_requires_csrf_and_ignores_privilege_injection(self):
        other = User.objects.create_user('existente')
        school = School.objects.create(owner=other, name='Escola de outro professor')
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse('register'), self.payload).status_code, 403)
        self.assertFalse(User.objects.filter(username=self.payload['username']).exists())
        client.get(reverse('register'))
        response = client.post(reverse('register'), {
            **self.payload, 'csrfmiddlewaretoken': client.cookies['csrftoken'].value,
            'is_staff': 'true', 'is_superuser': 'true', 'user_permissions': '1',
        })
        self.assertRedirects(response, reverse('dashboard'))
        teacher = User.objects.get(username=self.payload['username'])
        self.assertFalse(teacher.is_staff)
        self.assertFalse(teacher.is_superuser)
        self.assertFalse(teacher.user_permissions.exists())
        self.assertTrue(teacher.check_password(self.payload['password1']))
        self.assertEqual(int(client.session['_auth_user_id']), teacher.pk)
        self.assertFalse(School.objects.filter(owner=teacher).exists())
        self.assertNotContains(client.get(reverse('record_list', args=['escolas'])), school.name)
        self.assertEqual(client.get('/admin/auth/user/add/').status_code, 302)

    def test_duplicate_username_and_mismatched_passwords_do_not_create_accounts(self):
        User.objects.create_user(self.payload['username'])
        duplicate = self.client.post(reverse('register'), self.payload)
        self.assertFormError(duplicate.context['form'], 'username', 'Um usuário com este nome de usuário já existe.')
        mismatch = self.client.post(reverse('register'), {
            **self.payload, 'username': 'outra.professora', 'password2': 'OutraSenhaBoa!2026',
        })
        self.assertIn('password2', mismatch.context['form'].errors)
        self.assertEqual(User.objects.count(), 1)
        self.assertNotIn('_auth_user_id', self.client.session)
