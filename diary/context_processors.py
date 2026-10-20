from .catalog import CATALOG

def navigation(request):
    return {"navigation": [
        {"key": key, "title": config.title} for key, config in CATALOG.items()
    ]}

