"""Serve fictional data on loopback, optionally on an explicit private LAN IP."""
from ipaddress import IPv4Address, IPv4Network
import os
import runpy


def main():
    if (os.getenv('VALIDATION_ONLY') != '1'
            or os.getenv('POSTGRES_DB') != 'diario_validation'
            or os.getenv('POSTGRES_HOST') != 'db'):
        raise RuntimeError('Use somente deploy/validation/compose.yaml.')
    lan_ip = os.getenv('VALIDATION_LAN_IP', '').strip()
    if lan_ip:
        address = IPv4Address(lan_ip)
        if not any(address in IPv4Network(network) for network in
                   ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')):
            raise ValueError('VALIDATION_LAN_IP deve ser um IPv4 privado da rede local.')
    os.environ.update(
        DJANGO_DEBUG='False' if lan_ip else 'True',
        DJANGO_ALLOWED_HOSTS=','.join(filter(None, ('localhost', '127.0.0.1', lan_ip))),
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        EMAIL_HOST='',
        WAITRESS_HOST='0.0.0.0',
        WAITRESS_TRUSTED_PROXY='',
        PORT='18080',
    )
    if lan_ip:
        # HTTP only for the fictional LAN demo; never change production settings.
        from django.conf import settings
        settings.SECURE_SSL_REDIRECT = False
        settings.SESSION_COOKIE_SECURE = False
        settings.CSRF_COOKIE_SECURE = False
        settings.SECURE_HSTS_SECONDS = 0
    import django
    django.setup()
    from django.core.management import call_command
    call_command('collectstatic', interactive=False, verbosity=0)
    print(f'Demonstração fictícia: http://{lan_ip or "localhost"}:18080 — sem envio de e-mails.', flush=True)
    # Compose limits published interfaces; the database has no published port.
    runpy.run_path('serve.py', run_name='__main__')


if __name__ == '__main__':
    main()
