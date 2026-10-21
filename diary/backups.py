"""Consistent snapshots and restores to NEW targets only. Never overwrite live data."""
import hashlib
from contextlib import closing
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
from datetime import datetime, timezone


def digest(path):
    with Path(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def metadata_path(path):
    return Path(str(path) + ".json")


def validate_backup(path):
    path = Path(path).resolve()
    metadata = json.loads(metadata_path(path).read_text(encoding="utf-8"))
    if metadata.get("format") not in ("sqlite", "postgresql") or digest(path) != metadata.get("sha256"):
        raise ValueError("Backup inválido ou checksum diferente. Restauração cancelada.")
    return metadata


def pg_environment(database):
    env = os.environ.copy()
    for key, setting in (("PGHOST", "HOST"), ("PGPORT", "PORT"), ("PGUSER", "USER"), ("PGPASSWORD", "PASSWORD"), ("PGDATABASE", "NAME")):
        env[key] = str(database.get(setting, ""))
    env["PGSSLMODE"] = database.get("OPTIONS", {}).get("sslmode", "prefer")
    env["PGCONNECT_TIMEOUT"] = "10"
    return env


def pg_tool(name):
    return str(Path(os.environ["PG_BIN"]) / name) if os.getenv("PG_BIN") else name


def run_pg(arguments, database, *, stdout=subprocess.DEVNULL):
    result = subprocess.run(arguments, env=pg_environment(database), stdout=stdout,
                            stderr=subprocess.PIPE, timeout=1800, check=False)
    if result.returncode:
        # Do not expose connection strings or credentials in command output.
        raise ValueError("A ferramenta PostgreSQL falhou. Confira conexão, permissões e versão do cliente.")


def backup_database(database, output):
    output = Path(output).resolve()
    sidecar = metadata_path(output)
    if sidecar.exists():
        raise ValueError("Já existe um manifesto de backup nesse destino.")
    engine = database["ENGINE"]
    if engine not in ("django.db.backends.sqlite3", "django.db.backends.postgresql"):
        raise ValueError("Banco não suportado para backup.")
    kind = "sqlite" if engine.endswith("sqlite3") else "postgresql"
    if kind == "sqlite":
        source = Path(database["NAME"]).resolve()
        if not source.is_file() or source == output:
            raise ValueError("Escolha um banco SQLite existente e outro arquivo de destino.")
    # Exclusive creation: a scheduled job must never truncate an earlier snapshot.
    with output.open("xb") as target:
        os.chmod(output, 0o600)
        try:
            if kind == "postgresql":
                run_pg([pg_tool("pg_dump"), "--format=custom", "--no-owner", "--no-acl", "--no-password"], database, stdout=target)
            else:
                target.close()
                with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as live:
                    with closing(sqlite3.connect(output)) as snapshot:
                        live.backup(snapshot)
                        if snapshot.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                            raise ValueError("Falha na integridade do SQLite.")
            metadata = {"format": kind, "sha256": digest(output),
                        "created_at": datetime.now(timezone.utc).isoformat()}
            with sidecar.open("x", encoding="utf-8") as handle:
                os.chmod(sidecar, 0o600)
                json.dump(metadata, handle, ensure_ascii=False, indent=2)
        except Exception:
            target.close()
            output.unlink(missing_ok=True)
            raise
    return metadata


def restore_sqlite(backup, output):
    backup, output = Path(backup).resolve(), Path(output).resolve()
    if validate_backup(backup)["format"] != "sqlite":
        raise ValueError("Este arquivo não é um backup SQLite.")
    with output.open("xb"):
        pass
    os.chmod(output, 0o600)
    try:
        with closing(sqlite3.connect(backup.as_uri() + "?mode=ro", uri=True)) as source:
            if source.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Falha na integridade do backup SQLite.")
            with closing(sqlite3.connect(output)) as target:
                source.backup(target)
    except Exception:
        output.unlink(missing_ok=True)
        raise


def restore_postgresql(backup, database, name):
    if validate_backup(backup)["format"] != "postgresql":
        raise ValueError("Este arquivo não é um backup PostgreSQL.")
    if not re.fullmatch(r"diario_restore_[a-z0-9_]{1,40}", name) or name == database["NAME"]:
        raise ValueError("Use um banco NOVO chamado diario_restore_<identificador>, diferente do banco atual.")
    import psycopg
    from psycopg import sql
    with psycopg.connect(dbname=database["NAME"], user=database["USER"], password=database["PASSWORD"],
                         host=database["HOST"], port=database["PORT"],
                         sslmode=database.get("OPTIONS", {}).get("sslmode", "prefer"),
                         connect_timeout=10, autocommit=True) as connection:
        if connection.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone():
            raise ValueError("O banco de destino já existe. Nenhum dado foi alterado.")
        connection.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(name)))
    # On failure retain the isolated database for diagnosis, never drop a database automatically.
    target = {**database, "NAME": name}
    run_pg([pg_tool("pg_restore"), "--dbname", name, "--no-owner", "--no-acl",
            "--no-password", "--exit-on-error", "--single-transaction", str(Path(backup).resolve())], target)
