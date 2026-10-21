from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from diary.backups import restore_postgresql, restore_sqlite


class Command(BaseCommand):
    help = "Restaura backup confiável para um arquivo/banco NOVO. Nunca substitui o banco ativo."
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("backup")
        targets = parser.add_mutually_exclusive_group(required=True)
        targets.add_argument("--sqlite-output")
        targets.add_argument("--postgres-database")

    def handle(self, *args, **options):
        try:
            if options["sqlite_output"]:
                restore_sqlite(options["backup"], options["sqlite_output"])
            else:
                if settings.DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
                    raise ValueError("Configure conexão PostgreSQL para restaurar nesse formato.")
                restore_postgresql(options["backup"], settings.DATABASES["default"], options["postgres_database"])
        except Exception as error:
            raise CommandError("Restauração não concluída. Confira manifesto/checksum, destino novo e permissões. O banco ativo não foi substituído.") from error
        self.stdout.write(self.style.SUCCESS("Backup restaurado em destino novo. Valide antes de alterar a configuração do sistema."))
