# Implantação na VPS Ubuntu existente

**Preparação da VPS adiada pelo proprietário em 21/10/2026. Não executar os comandos deste roteiro agora. Concluir primeiro a validação local e a aprovação de uso.**

Preparação em 21/10/2026. **Arquivos preparados localmente; instalação não executada na VPS.** Continuamos na Etapa 7.

## Ambiente observado

Saídas fornecidas pelo proprietário: Ubuntu 24.04.4 x86_64, Python 3.12.3, Nginx 1.24.0, PostgreSQL 16.15 e Certbot instalado. Há dois sites configurados, um serviço Flask/Gunicorn na porta 8000 e um serviço Node/PM2 na 3000. PostgreSQL escuta somente em loopback. O serviço Flask usa aproximadamente 231 MiB e executa como root; sua configuração não será alterada nesta entrega.

A consulta mostrou 957 MiB de RAM total, 307 MiB disponíveis, 157 MiB de swap utilizados e 28 GB livres em disco. São medições pontuais. Não constituem teste de capacidade para adicionar o diário. Há atualizações e reinicialização pendentes; planejar manutenção dos serviços existentes separadamente.

## Configuração preparada

| Item | Diário do Professor |
| --- | --- |
| Conta do sistema | `diarioprofessor`, sem login interativo |
| Código / ambiente virtual | `/opt/diarioprofessor/app` e `/opt/diarioprofessor/venv` |
| Configuração privada | `/etc/diarioprofessor/production.env` (root:root, 0600) |
| Serviço | `diarioprofessor.service`, um processo Waitress, duas threads |
| Endereço interno | `127.0.0.1:8001`; reconferir antes de iniciar |
| Banco e papel dedicados | `diarioprofessor`, no PostgreSQL 16 existente; verificar nomes livres |
| Proxy | Novo arquivo exclusivo no Nginx, para `diarioprofessor.santustech.com.br` |

Não reutilizar usuário/banco do Flask, sua porta 8000 ou seu ambiente virtual. Não instalar outro PostgreSQL nem alterar parâmetros globais do cluster. Não substituir o Python do Ubuntu. A documentação do Django 5.2 aceita Python 3.12 e PostgreSQL 16; os metadados das dependências fixadas permitem Python 3.12. A instalação dos binários Linux e a suíte nessa combinação ainda precisam ser executadas.

Arquivos em `deploy/vps/`: serviço systemd, exemplo de ambiente local e dois exemplos de Nginx. A diretiva `ProtectSystem=strict` deixa o serviço sem escrita no sistema de arquivos, exceto seu diretório temporário privado; migrações, collectstatic e backups serão tarefas administrativas separadas. A versão atual não recebe anexos.

## Primeiro bloco — preparar somente diretórios e ambiente virtual

Executar no terminal Ubuntu já autenticado como root. O bloco não inicia o diário, não cria bancos, não altera Nginx nem reinicia serviços. Para evitar sobrescrita, interrompe se a conta, o grupo ou os diretórios já existirem. Não repetir cegamente se houver falha parcial.

```bash
(
  set -eu
  test "$(id -u)" -eq 0
  if getent passwd diarioprofessor >/dev/null || getent group diarioprofessor >/dev/null; then
    echo 'Conta/grupo ja existe. Pare e confira antes de continuar.'
    exit 1
  fi
  for destino in /opt/diarioprofessor /etc/diarioprofessor; do
    if [ -e "$destino" ] || [ -L "$destino" ]; then
      echo "Destino ja existe: $destino. Nenhum arquivo sera substituido."
      exit 1
    fi
  done
  python3 -c 'import venv, ensurepip; print("Suporte a venv disponivel")'
  command -v git >/dev/null
  useradd --system --user-group --home-dir /opt/diarioprofessor --shell /usr/sbin/nologin diarioprofessor
  install -d -o root -g diarioprofessor -m 0750 /opt/diarioprofessor
  install -d -o root -g root -m 0700 /etc/diarioprofessor
  python3 -m venv /opt/diarioprofessor/venv
  /opt/diarioprofessor/venv/bin/python --version
  echo 'Diretorios e ambiente virtual preparados. Nenhum servico foi iniciado.'
)
```

Se faltar `ensurepip`, `venv` ou Git, enviar a mensagem para definir a instalação mínima necessária; não executar atualização geral do servidor. O ambiente pertence a root para que o serviço não possa modificar suas dependências. A conta do diário terá leitura/execução pelos diretórios preparados.

## Passos seguintes, após conferir o primeiro bloco

1. Obter uma cópia do repositório em `/opt/diarioprofessor/app`, fixar o commit revisado, instalar `requirements-production.txt` e as dependências de teste no ambiente próprio. Validar a suíte com SQLite temporário, sem apontar para o banco do sistema antigo. Conferir disponibilidade de memória durante a instalação/testes.
2. Verificar nomes de papel e banco no cluster 16. Criar somente os novos recursos do diário, com usuário sem superusuário/CREATEDB/CREATEROLE e senha exclusiva inserida interativamente. Validar PostgreSQL 16 em banco de teste separado; não conceder CREATEDB à conta de produção para rodar a suíte. Configurar backup e restauração com credenciais de recuperação separadas.
3. Preencher o modelo `deploy/vps/production.env.example` no arquivo privado. O uso de `sslmode=prefer` se limita ao loopback desse host; banco remoto exige `verify-full` e CA correta. Informar SMTP autorizado antes de liberar recuperação de senha. Não carregar o arquivo com `source`: ele segue o formato de `EnvironmentFile` do systemd, não é um script shell.
4. Executar migrações, collectstatic, `check --deploy` e criação de administrador com o ambiente privado carregado. O serviço systemd carrega esse arquivo; comandos administrativos precisam receber a mesma configuração por um mecanismo controlado. Nunca executar migrações como root sem conferir explicitamente banco/usuário de destino. Ainda não há migração dos dados SQLite reais do computador.
5. Verificar a porta 8001 e os paths; validar a unidade com `systemd-analyze verify` antes de instalar/iniciar somente `diarioprofessor.service`. Medir memória e comportamento com chamadas, salvamentos e geração de PDF. Duas threads são um ponto inicial, não garantia de capacidade. Se houver pressão de memória, interromper somente o diário e avaliar recursos; não reduzir serviços existentes sem análise.
6. Confirmar DNS A/AAAA, renovação dos certificados atuais e ausência de bloco Nginx duplicado para o subdomínio. Preservar a configuração existente. Criar apenas o arquivo do diário com `nginx-acme.conf.example` para emissão via webroot; ele responde 404 fora do desafio e não expõe a aplicação. Conferir `nginx -t` antes de recarregar Nginx; não usar `certbot --nginx` para modificar automaticamente outros sites.
7. Após emitir o certificado específico, substituir apenas o arquivo do diário pelo exemplo HTTPS. Confirmar os caminhos reais do certificado; o nome pode ter sufixo se já existir outro certificado. Nunca habilitar os dois exemplos ao mesmo tempo. A homologação HTTPS começa restrita a loopback; adicionar o IP autorizado do avaliador antes de `deny all`. Testar IP real e esquema HTTPS; os cabeçalhos de encaminhamento são sobrescritos pelo Nginx.
8. Validar acesso e comportamento dos dois sites existentes após qualquer reload. Conferir backup externo, restauração, SMTP, relatórios e aparelhos Android/iPhone. Configurar limites de recuperação de senha no Nginx antes da abertura geral. Só retirar a restrição de homologação depois da autorização final de disponibilização.

O desligamento do diário deve afetar somente sua unidade e seu arquivo Nginx. Não apagar bancos como procedimento de retorno. Preservar evidências e seguir OPERACAO.md para recuperação. Os exemplos de Nginx e systemd ainda precisam de validação pelos binários da VPS; este computador não tem esses serviços Linux.

Referências: [Python no Django 5.2](https://docs.djangoproject.com/en/5.2/faq/install/), [PostgreSQL no Django](https://docs.djangoproject.com/en/5.2/ref/databases/), [threads e proxy do Waitress](https://docs.pylonsproject.org/projects/waitress/en/stable/arguments.html), [proxy Nginx](https://nginx.org/en/docs/http/ngx_http_proxy_module.html) e [isolamento do serviço systemd](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html).
