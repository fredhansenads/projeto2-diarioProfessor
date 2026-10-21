#!/usr/bin/env bash
# Read-only Ubuntu inventory. Run as the usual SSH user; no sudo required.
# Does not read environments, credentials, logs or application configuration.
set -u

section() { printf '\n== %s ==\n' "$1"; }

section 'Sistema operacional'
if [ -r /etc/os-release ]; then
    grep -E '^(NAME|VERSION|VERSION_ID|PRETTY_NAME)=' /etc/os-release
fi
uname -m

section 'CPU, memoria e swap'
getconf _NPROCESSORS_ONLN
free -m

section 'Espaco em disco'
df -h / /var /home

section 'Processos com maior consumo de RAM (sem argumentos)'
ps -eo comm=,rss= --sort=-rss | head -n 12

section 'Versoes disponiveis no PATH'
for binary in python3 python3.14 psql docker; do
    if command -v "$binary" >/dev/null 2>&1; then
        "$binary" --version
    else
        printf '%s: nao encontrado no PATH\n' "$binary"
    fi
done

section 'Portas TCP em escuta'
if command -v ss >/dev/null 2>&1; then
    ss -ltn
else
    printf 'ss nao disponivel; verificar portas manualmente.\n'
fi

section 'Servicos ativos (apenas nomes e estados)'
if command -v systemctl >/dev/null 2>&1; then
    systemctl list-units --type=service --state=running --no-pager --no-legend --plain |
        awk '{print $1, $2, $3, $4}'
else
    printf 'systemctl nao disponivel; identificar o supervisor existente.\n'
fi

printf '\nConsulta concluida. A ausencia no PATH nao comprova ausencia em ambientes virtuais ou conteineres.\n'
