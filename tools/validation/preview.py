"""Serve the fictional acceptance database through a loopback-only Docker port."""
import os
import runpy


def main():
    if (os.getenv('VALIDATION_ONLY') != '1'
            or os.getenv('POSTGRES_DB') != 'diario_validation'
            or os.getenv('POSTGRES_HOST') != 'db'):
        raise RuntimeError('Use somente deploy/validation/compose.yaml.')
    os.environ.update(
        DJANGO_DEBUG='True',
        DJANGO_ALLOWED_HOSTS='localhost,127.0.0.1',
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        EMAIL_HOST='',
        WAITRESS_HOST='0.0.0.0',
        WAITRESS_TRUSTED_PROXY='',
        PORT='18080',
    )
    import django
    django.setup()
    from django.core.management import call_command
    call_command('collectstatic', interactive=False, verbosity=0)
    print('Demonstração fictícia: http://localhost:18080 — sem envio de e-mails.', flush=True)
    # 0.0.0.0 inside the container; compose publishes exclusively on host 127.0.0.1.
    runpy.run_path('serve.py', run_name='__main__')


if __name__ == '__main__':
    main()
