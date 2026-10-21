from .catalog import CATALOG
from django.conf import settings

def navigation(request):
    return {"public_registration_enabled": settings.PUBLIC_REGISTRATION_ENABLED, "navigation": [
        {"key": key, "title": config.title} for key, config in CATALOG.items()
    ]}

