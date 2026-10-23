# Operação, backup e recuperação

Atualizado em 21/10/2026. Ferramentas verificadas localmente; agendamento e armazenamento externo ainda não configurados na hospedagem.

## Contas e acesso

Desde 23/10/2026, professores criam suas contas pelo link **Criar minha conta** na tela de login. Informam nome, usuário, e-mail e senha e entram no próprio diário, sem permissões administrativas. Não há confirmação de e-mail neste fluxo. O administrador também pode gerenciar contas em `/admin/`; criar o primeiro superusuário interativamente com `manage.py createsuperuser`. Para suspender novos cadastros, definir `PUBLIC_REGISTRATION_ENABLED=False` e reiniciar; contas existentes continuam acessíveis. Não apagar contas que possuam registros pedagógicos: desativar o acesso preservando o histórico.

Após cinco falhas de login na combinação usuário/IP, novas tentativas ficam bloqueadas por 15 minutos, inclusive no administrador. Uma tentativa correta durante o bloqueio não o ignora; novas falhas durante o bloqueio não prolongam o prazo. O login de outro professor na mesma rede continua disponível. No atendimento, conferir a identidade do solicitante antes de desbloquear. O comando `python manage.py axes_reset_username NOME_DO_USUARIO` limpa as tentativas daquele usuário; não usar reset global como rotina. Tentativas expiradas são limpas pelo Axes durante autenticações; entradas bem-sucedidas não criam logs adicionais de acesso nesta configuração. Falhas registram usuário/IP e horário no banco para o controle de bloqueio; controlar acesso e retenção dos backups que as contêm.

Logs devem ficar fora da área pública. Não registrar corpo de formulários, senhas, tokens de recuperação ou conteúdo de relatórios. Monitorar disponibilidade de `/saude/`, erros HTTP 5xx, falhas de banco, espaço em disco, expiração/renovação do certificado, falhas de backup e SMTP. Política de retenção e responsáveis devem ser definidos antes do uso real.

## Backup manual

Criar previamente uma pasta privada, nunca dentro do diretório público do site. A pasta `backups/` é ignorada pelo Git, assim como os bancos e dumps. Os comandos não criam a pasta nem sobrescrevem arquivos.

```powershell
# Na instalação local, criar a pasta uma única vez.
New-Item -ItemType Directory -Path backups -Force
.\.venv\Scripts\python.exe manage.py backup_diary backups/diario-20261021.sqlite3
```

No servidor com `DB_ENGINE=postgresql`:

```text
python manage.py backup_diary /caminho/privado/diario-20261021.dump
```

Usar nome exclusivo por execução, incluindo data/hora. O SQLite usa a API de backup consistente; não copiar um banco em uso como substituto desse comando. O PostgreSQL usa `pg_dump` em formato customizado, sem proprietário ou ACL do ambiente de origem. Exige `pg_dump` compatível com a versão do servidor, disponível no PATH ou em `PG_BIN`. No Windows, por exemplo, `PG_BIN=C:/Program Files/PostgreSQL/18/bin`. Credenciais são passadas por ambiente, não por argumentos de processo ou saída do comando.

Cada backup possui um arquivo adjacente `.json` com formato, data UTC e SHA-256. Guardar ambos. O checksum identifica corrupção acidental; não autentica a origem. Backups PostgreSQL podem conter código SQL: restaurar somente cópias confiáveis. O comando não criptografa os arquivos. Em Unix cria arquivos com modo 0600; no Windows, conferir ACL da pasta, pois chmod não substitui controle de acesso NTFS.

Não há cópia automática de `.env`, chave Django, configuração do host ou arquivos enviados por usuários. A versão atual não oferece anexos. Guardar segredos e configuração de infraestrutura separadamente, com acesso restrito. O dump contém o banco da aplicação, mas não cria papéis PostgreSQL nem replica configuração do servidor.

## Restauração em destino novo

Nunca testar restauração sobre o banco em uso. As ferramentas recusam destinos existentes e não trocam a configuração da aplicação.

```powershell
.\.venv\Scripts\python.exe manage.py restore_diary backups/diario-20261021.sqlite3 --sqlite-output backups/conferencia-20261021.sqlite3
```

Para PostgreSQL:

```text
python manage.py restore_diary /caminho/privado/diario-20261021.dump --postgres-database diario_restore_20261021
```

O nome deve começar com `diario_restore_`; o banco não pode existir e não pode ser o banco ativo. A conexão configurada precisa ter permissão para criar esse banco. A conta normal de produção não deve ganhar privilégios extras só para isso: usar um ambiente/conta administrativa de recuperação controlado. Se a hospedagem só permite criar bancos pelo painel e impõe outro padrão de nomes, utilizar o procedimento de recuperação do provedor em um banco vazio e separado, seguido de `pg_restore --no-owner --no-acl --exit-on-error --single-transaction`. Essa alternativa precisa ser validada com o suporte antes do uso, pois o comando protegido do projeto não aceita banco já criado.

Se o restore PostgreSQL falhar após criar o banco novo, ele fica isolado para diagnóstico; não há exclusão automática. O banco ativo não é substituído. Validar tabelas, contagens, usuários, históricos, matrículas, notas, frequência e relatórios; executar `manage.py migrate --check` apontando para a cópia e verificar as sequências antes de permitir novas gravações. Confirmar login e cálculos com dados conhecidos.

Para recuperação real: colocar a aplicação em manutenção, preservar o banco atual e seus registros de erro, escolher o backup, restaurar em banco novo, validar, solicitar aprovação da troca e só então atualizar a conexão/reiniciar. Registrar os dados posteriores ao backup que precisem ser recuperados; não afirmar perda zero com backups periódicos.

## Rotina proposta, a confirmar

- Backup diário e antes de cada atualização; horário compatível com o uso.
- Cópia criptografada fora do servidor, acesso restrito e verificação do checksum após transferência.
- Retenção inicial proposta: sete cópias diárias e quatro semanais, ajustada às regras da instituição e capacidade contratada.
- Teste de restauração mensal e após mudança de banco/infraestrutura.
- Alerta se o backup falhar ou ficar mais de 24 horas sem execução bem-sucedida.

Esses são parâmetros propostos, não um agendamento instalado. Definir responsável, local de armazenamento, frequência, perda máxima aceitável e prazo de recuperação antes da publicação. Nenhuma cópia foi enviada a serviço externo.

## Atualizações e retorno à versão anterior

1. Homologar o commit em ambiente separado e registrar versão Python/dependências/banco.
2. Criar backup e confirmar restauração. Planejar manutenção e preservar configurações secretas.
3. Instalar as dependências fixadas, executar migrações e `collectstatic`, depois `check --deploy` e `migrate --check`.
4. Reiniciar pelo mecanismo do provedor e conferir saúde, login, salvamento, relatórios e estáticos. Monitorar erros.
5. Se houver falha, interromper gravações e avaliar compatibilidade do código anterior com o schema atual. Não executar reversão de migração nem restore sobre o banco ativo sem analisar os efeitos. Preferir banco restaurado novo e troca aprovada da conexão.

A atualização da Etapa 7 acrescenta tabelas do django-axes. O banco local foi copiado antes da migração; contagens de contas e registros pedagógicos foram conferidas antes/depois. Os dados reais permanecem no SQLite local. A migração desses dados para PostgreSQL de produção ainda não foi realizada nem validada; planejar cópia, conferência de IDs/relacionamentos/auditoria e proteção de credenciais antes dessa transição.

Referências: [backup PostgreSQL](https://www.postgresql.org/docs/18/app-pgdump.html), [restauração PostgreSQL](https://www.postgresql.org/docs/18/app-pgrestore.html), [configuração django-axes](https://django-axes.readthedocs.io/en/latest/4_configuration.html).
