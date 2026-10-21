from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from diary.backups import backup_database


class Command(BaseCommand):
    help = "Cria backup consistente com checksum, sem sobrescrever arquivos existentes."
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("output")

    def handle(self, *args, **options):
        try:
            metadata = backup_database(settings.DATABASES["default"], options["output"])
        except Exception as error:
            raise CommandError("Backup não concluído. Verifique destino livre, permissões, banco e ferramentas PostgreSQL.") from error
        self.stdout.write(self.style.SUCCESS(f"Backup concluído ({metadata['format']}) com manifesto SHA-256."))
