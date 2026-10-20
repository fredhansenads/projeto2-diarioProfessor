from django.contrib import admin

# Pedagogical records are managed through owner-scoped views.
# The Django admin is reserved for account administration by trusted superusers.
admin.site.site_header = "Diário do Professor — Administração"
admin.site.site_title = "Diário do Professor"

