from django.apps import AppConfig

class DiaryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "diary"
    verbose_name = "Diário do Professor"

    def ready(self):
        from . import checks  # noqa: F401

