"""Exercise the real local HTTP/TLS/SMTP stack; refuses non-validation databases."""
import concurrent.futures
from email import policy
from email.parser import Parser
import hashlib
import http.cookiejar
import json
import math
import os
from pathlib import Path
import re
import ssl
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path('/tmp/diario-validation')
RESULTS = Path('/results')
BASE = 'https://localhost:18443'


def command(args, name, env=None):
    with (RESULTS / f'{name}.log').open('w') as log:
        result = subprocess.run(args, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=600)
    if result.returncode:
        raise RuntimeError(f'{name} failed; see /results/{name}.log')
    print(f'PASS {name}', flush=True)


class Browser:
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar),
            urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=str(ROOT / 'cert.pem'))))

    def request(self, path, data=None):
        url = path if path.startswith(BASE) else BASE + path
        if not url.startswith(BASE + '/'):
            raise ValueError('External requests are forbidden in this validation.')
        request = urllib.request.Request(url,
            data=urllib.parse.urlencode(data).encode() if data is not None else None,
            headers={'Referer': BASE + '/', 'Origin': BASE})
        try:
            response = self.opener.open(request, timeout=30)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.status, response.read(), response.headers, response.url

    def post_form(self, path, values):
        status, content, _, _ = self.request(path)
        assert status == 200, (path, status)
        hidden = dict(re.findall(r'<input[^>]*name="([^"]+)"[^>]*value="([^"]*)"', content.decode()))
        # Include hidden version and roster values, then explicitly supplied fields.
        payload = {key: value for key, value in hidden.items()
                   if key in ('csrfmiddlewaretoken', 'version', 'roster_token')}
        payload.update(values)
        return self.request(path, payload), payload

    def login(self, username='professor.teste', password='Teste-local-2026!'):
        response, _ = self.post_form('/conta/login/', {'username': username, 'password': password})
        assert response[0] == 200 and urllib.parse.urlparse(response[3]).path == '/', response[:1]


def snapshot(database, name):
    import psycopg
    from psycopg import sql
    with psycopg.connect(dbname=name, user=database['USER'], password=database['PASSWORD'],
                        host=database['HOST'], port=database['PORT']) as connection:
        tables = connection.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").fetchall()
        values = {}
        for (table,) in tables:
            records = connection.execute(sql.SQL('SELECT row_to_json(t) FROM {} t ORDER BY row_to_json(t)::text').format(sql.Identifier(table))).fetchall()
            values[table] = hashlib.sha256(json.dumps(records, sort_keys=True, default=str).encode()).hexdigest()
        return values


def main():
    if os.getenv('VALIDATION_ONLY') != '1' or os.getenv('POSTGRES_DB') != 'diario_validation' or os.getenv('POSTGRES_HOST') != 'db':
        raise RuntimeError('Run only with deploy/validation/compose.yaml')
    ROOT.mkdir(exist_ok=True)
    RESULTS.mkdir(exist_ok=True)
    report = {'status': 'running', 'python': sys.version, 'checks': []}
    (RESULTS / 'summary.json').write_text(json.dumps(report))
    test_env = {**os.environ, 'DJANGO_DEBUG': 'True', 'DJANGO_ALLOWED_HOSTS': 'localhost,127.0.0.1,testserver',
                'EMAIL_BACKEND': 'django.core.mail.backends.locmem.EmailBackend', 'EMAIL_HOST': ''}
    command(['python', 'manage.py', 'test', '--noinput'], 'tests-sqlite', {**test_env, 'DB_ENGINE': 'sqlite', 'SQLITE_PATH': str(ROOT / 'qa.sqlite3')})
    command(['python', 'manage.py', 'test', '--noinput'], 'tests-postgresql16', test_env)
    command(['python', '-m', 'pip', 'check'], 'dependencies')
    command(['python', 'manage.py', 'makemigrations', '--check', '--dry-run'], 'migration-drift')
    command(['python', 'manage.py', 'migrate', '--noinput'], 'migrate')
    command(['python', 'manage.py', 'collectstatic', '--noinput'], 'static')
    import django
    django.setup()
    from django.conf import settings
    from django.core.management import call_command
    from django.db import connection
    from diary.models import Attendance, Enrollment, Grade, Gradebook, Lesson
    from diary.grading_services import grade_summary
    from tools.validation.seed import seed
    with connection.cursor() as cursor:
        cursor.execute('SHOW server_version')
        report['postgresql'] = cursor.fetchone()[0]
    report['fixture'] = data = seed()
    (RESULTS / 'fixture.json').write_text(json.dumps(data, indent=2))
    report['checks'] += ['150 Django tests SQLite', '150 Django tests PostgreSQL 16', 'dependencies', 'migration-drift']
    # A public-domain-shaped Host is used solely for the deployment settings check.
    command(['python', 'manage.py', 'check', '--deploy', '--fail-level', 'WARNING'], 'deployment-check',
            {**os.environ, 'DJANGO_ALLOWED_HOSTS': 'validation.example.test'})
    command(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '7',
        '-keyout', str(ROOT / 'key.pem'), '-out', str(ROOT / 'cert.pem'), '-subj', '/CN=localhost',
        '-addext', 'subjectAltName=DNS:localhost,IP:127.0.0.1'], 'local-certificate')
    smtp_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    smtp_context.load_cert_chain(ROOT / 'cert.pem', ROOT / 'key.pem')
    from aiosmtpd.controller import Controller
    messages = []

    class MailSink:
        async def handle_DATA(self, server, session, envelope):
            assert session.ssl, 'SMTP must negotiate STARTTLS'
            messages.append(envelope.content.decode('utf-8'))
            return '250 Message captured locally; no delivery'

    smtp = Controller(MailSink(), hostname='127.0.0.1', port=1025, tls_context=smtp_context, require_starttls=True)
    smtp.start()
    nginx_conf = ROOT / 'nginx.conf'
    nginx_conf.write_text(f'''pid {ROOT}/nginx.pid;
worker_processes 1;
error_log {ROOT}/nginx-error.log;
events {{ worker_connections 128; }}
http {{
 access_log off;
 server {{ listen 18443 ssl; server_name localhost;
 ssl_certificate {ROOT}/cert.pem; ssl_certificate_key {ROOT}/key.pem;
 ssl_protocols TLSv1.2 TLSv1.3;
 client_max_body_size 2m;
 location / {{ proxy_pass http://127.0.0.1:8001; proxy_set_header Host $http_host;
 proxy_set_header X-Forwarded-For $remote_addr; proxy_set_header X-Forwarded-Proto $scheme;
 proxy_set_header Forwarded ""; proxy_cache off; }}
 }}
}}''')
    command(['nginx', '-t', '-c', str(nginx_conf)], 'nginx-config')
    processes = []
    log_handles = []
    memory = []
    stop_sampling = threading.Event()
    try:
        for name, args in [('waitress', ['python', 'serve.py']), ('nginx', ['nginx', '-c', str(nginx_conf), '-g', 'daemon off;'])]:
            handle = (RESULTS / f'{name}.log').open('w')
            log_handles.append(handle)
            processes.append(subprocess.Popen(args, stdout=handle, stderr=handle))
        def sample():
            while not stop_sampling.wait(0.1):
                try:
                    text = Path(f'/proc/{processes[0].pid}/status').read_text()
                    memory.append(int(re.search(r'VmRSS:\s+(\d+)', text).group(1)))
                except (OSError, AttributeError):
                    pass
        sampler = threading.Thread(target=sample, daemon=True)
        sampler.start()
        browser = Browser()
        for _ in range(60):
            try:
                if browser.request('/saude/')[0] == 200:
                    break
            except (OSError, urllib.error.URLError):
                pass
            time.sleep(0.25)
        else:
            raise RuntimeError('Local HTTPS server did not start')
        status, _, headers, _ = browser.request('/conta/login/')
        assert status == 200 and 'max-age=3600' in headers['Strict-Transport-Security']
        assert all(cookie.secure for cookie in browser.jar if cookie.name == 'csrftoken')
        assert browser.request('/criar-conta/')[0] == 403
        assert browser.request('/conta/login/', {'username': 'x'})[0] == 403
        browser.login()
        assert any(cookie.name == 'sessionid' and cookie.secure for cookie in browser.jar)
        assert '/admin/login/' in browser.request('/admin/')[3]
        report['checks'] += ['real HTTPS with verified local certificate', 'secure cookies', 'CSRF', 'registration closed', 'admin isolation']
        roster = list(Enrollment.objects.filter(classroom_id=data['classroom']).order_by('pk'))
        grades = {f'{field}_{pupil.pk}': value for pupil in roster
                  for field, value in [('status', 'submitted'), ('score', '8,5'), ('note', '')]}
        grades[f"score_{data['enrollment']}"] = '9,0'
        grades['reason'] = 'Correção fictícia para homologação HTTPS'
        response, stale = browser.post_form(f"/avaliacoes/{data['assessment']}/notas/", grades)
        assert response[0] == 200 and Grade.objects.get(assessment_id=data['assessment'], enrollment_id=data['enrollment']).score == 9
        history_count = Gradebook.objects.get(pk=data['book']).history.count()
        repeated = browser.request(f"/avaliacoes/{data['assessment']}/notas/", stale)
        assert 'Recarregue'.encode() in repeated[1]
        assert Gradebook.objects.get(pk=data['book']).history.count() == history_count
        attendance = {f'{field}_{pupil.pk}': value for pupil in roster
                      for field, value in [('absences', 1), ('justified', 0), ('note', '')]}
        attendance[f"absences_{data['enrollment']}"] = 0
        attendance['reason'] = 'Correção fictícia da chamada'
        response, _ = browser.post_form(f"/aulas/{data['lesson']}/chamada/", attendance)
        assert response[0] == 200 and Attendance.objects.get(lesson_id=data['lesson'], enrollment_id=data['enrollment']).absences == 0
        final_grade = next(row for row in grade_summary(Gradebook.objects.get(pk=data['book']))['rows']
                           if row['enrollment'].pk == data['enrollment'])['final']
        assert str(final_grade) == '8.6', final_grade
        report['checks'] += ['HTTP grade correction with comma', 'stale write rejected without duplicate audit', 'HTTP attendance correction', 'final grade 8.6']
        query = urllib.parse.urlencode({key: data[key] for key in ('classroom', 'term')})
        paths = ['/', '/aulas/', f"/notas/{data['book']}/", '/relatorios/?' + query,
                 '/relatorios/?' + query + '&format=csv', '/relatorios/?' + query + '&format=pdf']
        for path in paths:
            status, content, headers, _ = browser.request(path)
            assert status == 200 and 'no-store' in headers['Cache-Control'], (path, status)
            if path.endswith('pdf'):
                assert content.startswith(b'%PDF')
                (RESULTS / 'conselho-ficticio.pdf').write_bytes(content)
            if path.endswith('csv'):
                assert b'8,6' in content
                (RESULTS / 'conselho-ficticio.csv').write_bytes(content)
        other = Browser()
        other.login('outro.professor')
        assert other.request(f"/notas/{data['book']}/")[0] == 404
        denied = other.request('/relatorios/?' + query)
        assert denied[0] == 200 and b'Aluno fict' not in denied[1]
        for output in ('csv', 'pdf'):
            assert other.request('/relatorios/?' + query + '&format=' + output)[0] == 400
        report['checks'] += ['HTML CSV PDF consistent and private', 'second teacher denied']
        reset = Browser()
        response, _ = reset.post_form('/conta/password_reset/', {'email': 'professor@example.test'})
        assert response[0] == 200 and messages, 'SMTP message not captured'
        message = Parser(policy=policy.default).parsestr(messages[-1])
        body = message.get_body(preferencelist=('plain',)) if message.is_multipart() else message
        reset_link = re.search(r'https://localhost:18443/\S+', body.get_content()).group(0).strip()
        reset_path = reset_link.removeprefix(BASE)
        response = reset.request(reset_path)
        assert response[0] == 200 and '/set-password/' in response[3]
        changed, _ = reset.post_form(urllib.parse.urlparse(response[3]).path,
            {'new_password1': 'Nova-senha-local-2026!', 'new_password2': 'Nova-senha-local-2026!'})
        assert changed[0] == 200
        fresh = Browser()
        fresh.login(password='Nova-senha-local-2026!')
        assert b'name="new_password1"' not in Browser().request(reset_path)[1]
        # Restore only the fictional credential, so the manual acceptance guide stays stable.
        from django.contrib.auth.models import User
        teacher = User.objects.get(username='professor.teste')
        teacher.set_password('Teste-local-2026!')
        teacher.save()
        report['checks'] += ['SMTP STARTTLS captured locally', 'password reset complete and token single use']
        clients = [Browser() for _ in range(4)]
        for client in clients:
            client.login()
        def workload(index):
            results = []
            for _ in range(3):
                for path in paths:
                    start = time.perf_counter()
                    status, content, _, _ = clients[index].request(path)
                    assert status == 200, (path, status)
                    results.append({'path': path, 'milliseconds': round((time.perf_counter() - start) * 1000, 1), 'bytes': len(content)})
            return results
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            timings = [item for group in executor.map(workload, range(4)) for item in group]
        values = sorted(item['milliseconds'] for item in timings)
        report['load'] = {'concurrent_clients': 4, 'requests': len(values),
                          'p50_ms': values[len(values)//2], 'p95_ms': values[math.ceil(len(values)*.95)-1],
                          'max_ms': max(values), 'waitress_peak_rss_mib': round(max(memory)/1024, 1),
                          'note': 'Local synthetic workload, not a VPS capacity guarantee.'}
        (RESULTS / 'timings.json').write_text(json.dumps(timings, indent=2))
        # Backup after requests stop; compare all tables, then check restored sequences by inserting a user.
        database = settings.DATABASES['default']
        before = snapshot(database, database['NAME'])
        backup = RESULTS / 'synthetic.dump'
        call_command('backup_diary', str(backup))
        call_command('restore_diary', str(backup), postgres_database='diario_restore_validation')
        assert snapshot(database, 'diario_restore_validation') == before
        assert snapshot(database, database['NAME']) == before
        import psycopg
        with psycopg.connect(dbname='diario_restore_validation', user=database['USER'], password=database['PASSWORD'], host='db') as restored:
            previous_max = restored.execute('SELECT MAX(id) FROM auth_user').fetchone()[0]
            new_id = restored.execute("INSERT INTO auth_user (password, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) VALUES ('!', false, 'restore_sequence_probe', '', '', '', false, false, NOW()) RETURNING id").fetchone()[0]
            assert new_id > previous_max
            restored.rollback()
        report['checks'].append(f'PostgreSQL 16 backup restore: {len(before)} tables identical and user sequence valid')
        report['status'] = 'passed'
        report['limits'] = ['No external email delivery', 'No trusted public certificate', 'No real Android/iPhone',
                            'No teacher acceptance yet', 'No VPS accessed or modified']
        (RESULTS / 'summary.json').write_text(json.dumps(report, indent=2, ensure_ascii=False))
        print(json.dumps(report, indent=2, ensure_ascii=False), flush=True)
    finally:
        stop_sampling.set()
        for process in reversed(processes):
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        for handle in log_handles:
            handle.close()
        smtp.stop()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        summary = RESULTS / 'summary.json'
        if os.getenv('VALIDATION_ONLY') == '1' and summary.exists():
            report = json.loads(summary.read_text())
            report.update(status='failed', error=f'{type(error).__name__}: {error}')
            summary.write_text(json.dumps(report, indent=2, ensure_ascii=False))
        raise
