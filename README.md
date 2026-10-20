# Diário do Professor

Sistema em Python/Django para organizar o trabalho do professor no computador e no celular.

**Entrega atual:** contas, painel, cadastros, aulas, conteúdos e frequência por aula com histórico de correções. Avaliações, notas, relatórios de conselho/exportação e instalação como PWA ainda serão implementados. O roteiro está em [PLANO_DO_PROJETO.md](PLANO_DO_PROJETO.md).

## Executar no Windows / PowerShell

Na pasta do projeto, use o ambiente virtual já existente:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Abra **http://127.0.0.1:8000/** e clique em **Criar minha conta**. Não há usuário ou senha padrão.

Para parar o servidor, use Ctrl+C no terminal. Não é necessário ativar o ambiente virtual para executar esses comandos.

Se o ambiente precisar ser recriado, use Python 3.14 e `python -m venv .venv` antes de instalar as dependências. A versão instalada e verificada neste projeto é Django 5.2.18.

## Primeiro uso

1. Crie sua conta de professor.
2. Cadastre uma escola e o ano letivo.
3. Cadastre os períodos de cada escola, com suas datas.
4. Cadastre as disciplinas.
5. Crie uma turma, escolhendo escola, ano, turno e disciplinas.
6. Cadastre os alunos.
7. Crie as matrículas para vincular alunos às turmas e informe o primeiro dia na turma.
8. Abra uma turma para consultar seus alunos e situações de matrícula.
9. Use **Registrar aula** para informar disciplina, data, quantidade de aulas e conteúdo.
10. Abra **Fazer chamada**, marque as faltas de cada aluno e clique em **Salvar chamada**.
11. Consulte a **Frequência da turma**, com filtros por disciplina, período e datas.
12. Para corrigir registros, informe o motivo. A aula mostra o histórico com autor e valores anteriores/novos.

Em uma transferência, altere a matrícula anterior para **Transferida**, informe o último dia na turma (inclusive) e crie a matrícula na nova turma. Ao mudar de ano, crie outra turma e outras matrículas. Não reutilize registros antigos para representar um novo ano.

**Atualização de uma instalação anterior:** execute `manage.py migrate` antes de reiniciar o servidor. As matrículas existentes são preservadas, mas suas datas não são inventadas: revise entrada e saída. Matrícula ativa antiga sem entrada considera o início do ano; matrícula encerrada sem saída fica fora de novas chamadas e é sinalizada para revisão.

**Como a frequência é calculada:** faltas parciais respeitam a quantidade de aulas do encontro. O percentual usa somente aulas com chamada registrada; pendências aparecem separadamente. Justificativas são identificadas, mas não abonam faltas automaticamente. Consulte as regras e exemplos em [docs/ETAPA3.md](docs/ETAPA3.md).

Os registros de cada professor são independentes, inclusive quando dois professores trabalham na mesma escola. Não há compartilhamento entre contas nesta entrega.

## Configuração local

O SQLite funciona sem instalar um servidor de banco. O arquivo `db.sqlite3` é criado por `migrate`.

As configurações podem ser ajustadas por variáveis de ambiente ou por um arquivo `.env`. Para começar:

```powershell
Copy-Item .env.example .env
```

Execute a cópia apenas se ainda não houver um `.env`. O arquivo é carregado automaticamente; variáveis já definidas no ambiente têm prioridade.

Em desenvolvimento, uma chave aleatória é criada em `.local-secret` e reutilizada entre reinicializações. Esse arquivo, o banco, o ambiente virtual e o `.env` são ignorados pelo Git.

A variável opcional `SQLITE_PATH` permite selecionar um banco local separado para testes manuais. Os testes automatizados usam um banco temporário próprio.

### Recuperação de senha

O fluxo de recuperação já funciona. Por padrão, o e-mail aparece **no terminal do servidor**, sem envio externo. Use o link apresentado no terminal para testar localmente.

Para envio real, configure `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, servidor SMTP, credenciais e remetente no `.env`. O envio real ainda não foi validado.

### Administração

A conta normal do professor é criada pela interface. Se precisar administrar contas de usuários pelo Django:

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

Acesse `/admin/`. Essa conta administrativa deve ser restrita a pessoas de confiança. Os cadastros pedagógicos são gerenciados nas telas do diário, que filtram os dados pelo professor.

## Verificação

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe -m pip check
```

A suíte atual contém 64 testes: autenticação e cadastros; isolamento de contas; validação de aulas e matrículas; faltas parciais; justificativas; pendências; filtros; cancelamento; correções com histórico; rejeição de gravação por uma tela desatualizada; transações que preservam chamada e histórico juntos; escape de HTML e CSRF.

Também foram verificados no navegador a criação de uma aula, o preenchimento de faltas parciais com justificativa, o atalho que marca somente pendências como presença e a consulta por período. A chamada foi preenchida e salva em janela de 390 × 844 pixels; essa simulação não substitui testes em aparelhos reais.

## Estrutura

- `config/`: configurações e rotas principais do Django.
- `diary/models.py`: entidades, validações e restrições.
- `diary/forms.py`: formulários com relacionamentos limitados à conta atual.
- `diary/catalog.py`: definição dos cadastros disponíveis.
- `diary/views.py`: painel, listagens, criação, edição e detalhe da turma.
- `diary/tests.py`: testes das regras e do isolamento de dados.
- `diary/teaching_forms.py` e `diary/teaching_views.py`: telas de aulas, chamadas e frequência.
- `diary/teaching_services.py`: cálculos, gravações atômicas, controle de versão e histórico.
- `diary/tests_teaching.py`: testes da etapa de aulas e frequência.
- `templates/`: interface em português.
- `static/diary/`: estilos responsivos e ícone.
- `docs/ARQUITETURA.md`: decisões e vínculos do modelo.
- `PLANO_DO_PROJETO.md`: progresso e próxima etapa.

Ao concluir cada etapa, atualizar os documentos, validar, fazer commit e enviar ao GitHub. Aguardar confirmação do usuário antes de começar a seguinte.

## Preparação para produção — etapa futura

Há configuração para PostgreSQL por variáveis de ambiente; a implantação e o banco PostgreSQL ainda não foram testados.

O arquivo `requirements-production.txt` acrescenta o driver PostgreSQL e o servidor Waitress. Antes de disponibilizar o sistema, será necessário:

- Provisionar e validar PostgreSQL, migrações e backups com restauração.
- Definir `DJANGO_DEBUG=False`, uma `DJANGO_SECRET_KEY` própria e `DJANGO_ALLOWED_HOSTS` com o domínio.
- Configurar HTTPS, proxy, serviço da aplicação e entrega de arquivos estáticos.
- Configurar e testar o serviço de e-mail.
- Definir a política de criação de contas e proteção contra tentativas repetidas de autenticação.
- Executar `manage.py check --deploy` com as configurações reais e resolver os apontamentos.
- Validar o ciclo completo da aplicação antes de disponibilizar a versão.

O servidor `runserver` usado acima serve ao desenvolvimento local. O endereço `127.0.0.1` só abre neste computador; acesso pelo celular físico dependerá de configuração de rede ou hospedagem.

Referências técnicas: [Django 5.2](https://docs.djangoproject.com/en/5.2/releases/5.2/) e [checklist de implantação](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/).

