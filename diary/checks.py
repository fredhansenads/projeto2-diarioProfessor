from django.conf import settings
from django.core.checks import Error, Tags, register


@register(Tags.security, deploy=True)
def production_configuration(app_configs, **kwargs):
    errors = []
    if settings.DEBUG:
        errors.append(Error("Desative DEBUG antes de disponibilizar.", id="diary.E001"))
    if settings.DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
        errors.append(Error("A implantação aprovada exige PostgreSQL.", id="diary.E002"))
    if settings.EMAIL_BACKEND != "django.core.mail.backends.smtp.EmailBackend" or not settings.EMAIL_HOST:
        errors.append(Error("Configure SMTP real antes de disponibilizar.", id="diary.E003"))
    if not (settings.EMAIL_USE_TLS or settings.EMAIL_USE_SSL) or (settings.EMAIL_USE_TLS and settings.EMAIL_USE_SSL):
        errors.append(Error("Escolha exatamente um transporte seguro de e-mail: TLS ou SSL.", id="diary.E004"))
    if not settings.ALLOWED_HOSTS or any(host in ("*", "localhost", "127.0.0.1", "[::1]") or host.startswith(".") for host in settings.ALLOWED_HOSTS):
        errors.append(Error("Configure somente os nomes exatos dos hosts de produção.", id="diary.E005"))
    if settings.PUBLIC_REGISTRATION_ENABLED:
        errors.append(Error("A política aprovada permite criação de contas somente pelo administrador.", id="diary.E006"))
    if not settings.DEFAULT_FROM_EMAIL or "@" not in settings.DEFAULT_FROM_EMAIL or settings.DEFAULT_FROM_EMAIL.endswith("@localhost"):
        errors.append(Error("Configure um remetente autorizado no serviço de e-mail.", id="diary.E007"))
    return errors
