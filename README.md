# Diário do Professor

Sistema em Python/Django para organizar o trabalho do professor no computador e no celular.

**Entrega atual:** contas, cadastros, aulas, frequência, avaliações, entregas, notas configuráveis, relatórios com PDF/CSV/impressão e recursos de instalação como PWA. A versão exige internet. Instalação em Android/iPhone físicos e produção ainda precisam de validação. O roteiro está em [PLANO_DO_PROJETO.md](PLANO_DO_PROJETO.md).

## Executar no Windows / PowerShell

Na pasta do projeto, use o ambiente virtual já existente:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Crie o primeiro administrador com `python manage.py createsuperuser`, usando o Python do ambiente virtual. Abra **http://127.0.0.1:8000/admin/** para cadastrar as contas dos professores, sem permissões administrativas. Não há usuário ou senha padrão; o cadastro público está desativado.

Para parar o servidor, use Ctrl+C no terminal. Não é necessário ativar o ambiente virtual para executar esses comandos.

Se o ambiente precisar ser recriado, use Python 3.14 e `python -m venv .venv` antes de instalar as dependências. A versão instalada e verificada neste projeto é Django 5.2.18.

## Primeiro uso

1. Entre com a conta de professor criada pelo administrador.
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
13. Abra **Avaliações e notas → Novo caderno**, escolha turma/disciplina/período e configure as regras.
14. Cadastre provas, trabalhos e atividades; use **Notas e entregas** para registrar cada aluno.
15. Confira resultados, pendências e histórico no caderno. Regras e exemplos em [docs/ETAPA4.md](docs/ETAPA4.md).
16. Abra **Relatórios e conselho**, selecione turma e período e consulte notas, frequência, pendências e observações.
17. Clique no aluno para abrir a ficha individual. Use **Baixar PDF**, **Baixar CSV** ou **Versão para impressão**. Detalhes em [docs/ETAPA5.md](docs/ETAPA5.md).
18. Abra **Usar no celular** no rodapé para ver como instalar pelo Chrome/Android ou Safari/iPhone. A instalação nos aparelhos depende do endereço HTTPS; consulte [docs/ETAPA6.md](docs/ETAPA6.md).

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

Somente o administrador cria contas nesta versão. Para criar o primeiro administrador:

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

Acesse `/admin/`. Ao criar professores, mantenha desmarcados os privilégios de equipe e superusuário. Essa conta administrativa deve ser restrita a pessoas de confiança. Os cadastros pedagógicos são gerenciados nas telas do diário, que filtram os dados pelo professor. Contas existentes continuam válidas. Procedimentos em [docs/OPERACAO.md](docs/OPERACAO.md).

## Verificação

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-test.txt
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe -m pip check
```

A suíte atual contém 150 testes Django, aprovados tanto em SQLite quanto em PostgreSQL 18 local: autenticação, cadastros, aulas/frequência, avaliações/notas, cálculos, isolamento, auditoria, relatórios/exportações, instalação, segurança e recuperação. Também passaram os 12 testes JavaScript da PWA. Para estes últimos, use Node 24 e execute `node --test tests/pwa.test.cjs`; Node é necessário apenas para esses testes, não para executar o sistema.

Também foram verificados no navegador a criação de uma aula, o preenchimento de faltas parciais com justificativa, o atalho que marca somente pendências como presença e a consulta por período. A chamada foi preenchida e salva em janela de 390 × 844 pixels; essa simulação não substitui testes em aparelhos reais.

Na Etapa 4, caderno e prova foram criados no navegador; notas com vírgula e não entrega sem nota foram salvas no tamanho de celular e conferidas no caderno. Dados fictícios ficam em banco separado.

Na Etapa 5, consultas e downloads PDF/CSV foram verificados no navegador; a ficha individual foi conferida no tamanho de celular. PDFs foram renderizados e inspecionados visualmente. Impressora física não foi validada. Atualize as dependências com requirements-lock.txt antes de iniciar a nova versão; requirements-test.txt acrescenta a ferramenta de conferência dos PDFs para rodar a suíte.

A Etapa 6 foi conferida em tamanhos de celular com dados fictícios e com interrupção real do servidor local. Não há gravação offline: mantenha o formulário aberto ao perder conexão. Se a falha ocorrer durante o envio, consulte o registro antes de repetir. Só a mensagem retornada pelo servidor confirma o salvamento. O cache do service worker contém apenas uma página genérica de conexão, sem dados dos alunos. Limites e checklist para aparelhos reais em [docs/ETAPA6.md](docs/ETAPA6.md).

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
- `diary/grading_forms.py`, `grading_views.py`, `grading_services.py`: cadernos, avaliações, notas, cálculos e auditoria.
- `diary/tests_grading.py`: testes da etapa de avaliações e notas.
- `diary/report_forms.py`, `report_services.py`, `report_views.py`, `report_exports.py`: filtros, consolidação e exportação dos relatórios.
- `diary/tests_reports.py`: conferência dos relatórios, segurança e arquivos exportados.
- `diary/pwa_views.py`, `diary/tests_pwa.py` e `tests/pwa.test.cjs`: instalação, manifesto e testes do comportamento de conexão.
- `diary/security.py`, `checks.py` e `tests_operations.py`: proteção de acesso, diagnóstico de produção e testes operacionais.
- `diary/backups.py` e `diary/management/commands/`: backup e restauração em destino novo.
- `serve.py` e `deploy/production.env.example`: servidor Waitress e modelo de configuração de produção.
- `docs/ETAPA7.md`, `docs/IMPLANTACAO_LOCAWEB.md` e `docs/OPERACAO.md`: validações, pendências de hospedagem e operação.
- `templates/`: interface em português.
- `static/diary/`: estilos responsivos, ícones, avisos de formulário e service worker.
- `docs/ARQUITETURA.md`: decisões e vínculos do modelo.
- `PLANO_DO_PROJETO.md`: progresso e próxima etapa.

Ao concluir cada etapa, atualizar os documentos, validar, fazer commit e enviar ao GitHub. Aguardar confirmação do usuário antes de começar a seguinte.

## Etapa 7 — preparação local validada, implantação pendente

O usuário escolheu sua **VPS existente na Locaweb**, mantendo o subdomínio `diarioprofessor.santustech.com.br`, após informar que a hospedagem compartilhada Linux GO não suporta Python/Django. A VPS tem Ubuntu 24.04.4, 1 GB RAM, 2 vCPUs e disco de 40 GB, com Flask e Node em uso. Foram medidos 307 MiB RAM disponíveis. Os modelos de serviço e proxy isolados estão preparados; instalação, testes nessa VPS e capacidade conjunta continuam pendentes. O primeiro bloco para execução pelo terminal está em [docs/VPS_UBUNTU.md](docs/VPS_UBUNTU.md). Roteiro em [docs/IMPLANTACAO_LOCAWEB.md](docs/IMPLANTACAO_LOCAWEB.md).

O arquivo `requirements-production.txt` acrescenta o driver PostgreSQL e o servidor Waitress. Foram validados localmente PostgreSQL 18, migrações, backup/restauração, contas criadas pelo administrador, bloqueio após tentativas repetidas e um ciclo pedagógico completo. As verificações de configuração de produção passaram; isso não comprova o funcionamento de HTTPS ou SMTP externos. Antes de disponibilizar o sistema, será necessário:

- Inventariar e configurar a VPS e provisionar PostgreSQL; planejar separadamente a migração dos dados reais do SQLite.
- Agendar backups, guardar cópias fora do servidor e testar a recuperação no ambiente contratado.
- Definir `DJANGO_DEBUG=False`, uma `DJANGO_SECRET_KEY` própria e `DJANGO_ALLOWED_HOSTS` com o domínio.
- Configurar HTTPS, proxy, serviço da aplicação e entrega de arquivos estáticos.
- Configurar e testar o serviço de e-mail.
- Executar `manage.py check --deploy` com as configurações reais e resolver os apontamentos.
- Homologar Android/iPhone físicos e o uso pelo professor; obter autorização para disponibilizar a versão.

A Etapa 7 continua em andamento. Resultados e limites estão em [docs/ETAPA7.md](docs/ETAPA7.md); backup, restauração e atualização estão em [docs/OPERACAO.md](docs/OPERACAO.md).

O servidor `runserver` usado acima serve ao desenvolvimento local. O endereço `127.0.0.1` só abre neste computador; acesso pelo celular físico dependerá de configuração de rede ou hospedagem.

Referências técnicas: [Django 5.2](https://docs.djangoproject.com/en/5.2/releases/5.2/) e [checklist de implantação](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/).

