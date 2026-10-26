# Validação local antes da VPS

Data: **21/10/2026**. Resultado: **verificações locais aprovadas; aguardando avaliação do proprietário**. A Etapa 7 continua aberta. Nenhum comando desta rodada foi executado na VPS.

## Atualização de 23/10/2026

Cadastro público habilitado a pedido do proprietário. Na tela de login, **Criar minha conta** abre o formulário de nome, usuário, e-mail e senha; a nova conta entra em um diário próprio vazio, sem acesso administrativo. Os resultados abaixo documentam o ensaio de 21/10, quando o cadastro ainda estava fechado. Não é necessário apagar ou recriar o banco para aplicar esta melhoria.

## Abrir a demonstração

Com o laboratório em execução, abra **http://localhost:18080** neste computador.

| Conta fictícia | Usuário | Senha somente de demonstração |
| --- | --- | --- |
| Professor com turmas e registros | `professor.teste` | `Teste-local-2026!` |
| Outro professor, sem acesso às turmas da primeira conta | `outro.professor` | `Teste-local-2026!` |
| Administrador, em `/admin/` | `admin.teste` | `Teste-local-2026!` |

Este ambiente contém apenas dados inventados: uma escola, três turmas de 40 alunos, duas disciplinas por turma, 72 encontros de duas aulas, 960 notas e 2.880 registros de chamada. Use somente dados fictícios na demonstração. O banco real `db.sqlite3`, seu `.env`, contas e backups não foram copiados para o laboratório nem alterados nesta rodada.

A demonstração padrão usa HTTP local e DEBUG ativado, com acesso publicado em `127.0.0.1`. Desde 26/10/2026, há um modo opcional para celular na mesma rede Wi-Fi, com IP privado explícito e DEBUG desativado, conforme [ACESSO_CELULAR_LOCAL.md](ACESSO_CELULAR_LOCAL.md). Não é uma configuração de produção. O envio de e-mail fica desabilitado na demonstração; o ensaio automatizado de recuperação de senha foi feito separadamente com SMTP local e STARTTLS.

## O que foi comprovado

O laboratório usa Ubuntu 24.04, Python **3.12.3**, Django **5.2.18**, PostgreSQL **16.15**, Nginx e Waitress com duas threads. A distribuição do servidor PostgreSQL é a imagem oficial Debian; não reproduz integralmente a VPS Ubuntu nem seus outros sistemas.

| Verificação | Resultado observado |
| --- | --- |
| Suíte Django em SQLite / Python 3.12 | 150 aprovados; 8,155 s |
| Mesma suíte em PostgreSQL 16 / Python 3.12 | 150 aprovados; 18,267 s |
| PWA e conexão em JavaScript | 12 aprovados |
| Dependências, migrações e `check --deploy` | Aprovados; dois avisos HSTS deliberadamente silenciados, conforme guia de implantação |
| HTTPS com Nginx → Waitress → PostgreSQL | Certificado local verificado pelo cliente; cookies seguros e HSTS presentes |
| Acesso e integridade | Cadastro público fechado; CSRF inválido recusado; professor sem acesso administrativo; conta diferente sem acesso às notas/exportações |
| Correção de nota e chamada por HTTP com CSRF | Nota com vírgula salva, média 8,6, falta corrigida, formulário antigo recusado sem duplicar auditoria |
| Relatórios | HTML/CSV/PDF gerados com dados fictícios, respostas privadas sem cache e nota corrigida no CSV |
| Recuperação de senha | Mensagem capturada no SMTP local com STARTTLS; link utilizado, login com nova senha e recusa de reutilização do token; senha fictícia restaurada ao final |
| Backup PostgreSQL 16 | Dump restaurado em outro banco; conteúdo das 29 tabelas idêntico; origem preservada; sequência de usuários verificada |
| Navegador | Login e painel com 120 alunos; ficha individual conferida, inclusive em viewport 390 × 844; média 8,6 e frequência 100,0% no caso conhecido |

Os 150 casos Django são os mesmos executados em cada banco. Não são 300 casos distintos. O HTTPS do ensaio usou um certificado próprio confiado explicitamente pelo cliente de teste, sem desativar sua verificação. O e-mail ficou dentro do laboratório, sem entrega a terceiros. Não foram encontradas falhas na aplicação nessa rodada; foram ajustadas as verificações do novo roteiro de teste.

### Uso simultâneo

Foram utilizados quatro clientes autenticados simultâneos, com 18 consultas por cliente, alternando painel, aulas, notas e relatórios HTML, CSV e PDF: **72 respostas HTTP 200**.

| Medida | Resultado |
| --- | --- |
| Mediana de resposta (p50) | 600,2 ms |
| Percentil 95 (p95) | 1.645,8 ms |
| Maior tempo observado | 1.908,4 ms |
| Maior RSS observado do processo Waitress | 84,9 MiB |

O RSS foi amostrado a cada 100 ms e não inclui PostgreSQL, Nginx, Docker nem outros processos. Houve fila de até duas tarefas no Waitress, sem erro nas respostas. Os limites do laboratório foram 512 MiB/2 CPUs para a aplicação e 192 MiB/1 CPU para o banco. Este ensaio curto mede somente a carga descrita: não é teste prolongado, de limite de capacidade, de gravações concorrentes ou garantia de desempenho na VPS de 1 GB compartilhada com outros sistemas.

## Roteiro para avaliação do professor

Os itens abaixo aguardam sua conferência. Registrar o resultado e qualquer dificuldade antes de retomar a preparação da VPS.

- [ ] Entrar com `professor.teste` e conferir escolas, turmas, alunos e matrículas.
- [ ] Em **Relatórios e conselho**, selecionar **7º A / 1º bimestre / Matemática / Aluno fictício 1-01**. Antes de qualquer alteração manual, conferir média **8,6**, frequência **100,0%**, 24 aulas com chamada e nenhuma falta. As quatro notas são **9,0; 8,5; 8,5; 8,5**.
- [ ] Consultar o mesmo aluno em História: média **8,5**, uma falta em 24 aulas e frequência **95,8%**. Baixar PDF/CSV e conferir se o formato atende ao conselho da escola.
- [ ] Registrar uma nova aula fictícia, preencher a chamada, salvar, sair da tela e voltar para conferir. Use uma data dentro do período selecionado para aparecer no relatório.
- [ ] Criar uma atividade fictícia, lançar notas, testar uma pendência e corrigir um valor informando o motivo. Conferir cálculo, histórico e relatório resultantes.
- [ ] Conferir as regras configuráveis do caderno com as regras reais da escola, incluindo recuperação e arredondamento, usando exemplos fictícios.
- [ ] Sair e entrar como `outro.professor`; confirmar que os registros da primeira conta não aparecem.
- [ ] Informar as telas que precisam de ajustes e aprovar o fluxo local antes de autorizar qualquer preparação da VPS.

Adicionar registros à demonstração muda os valores esperados acima. As alterações manuais ficam no volume Docker; não recriar o banco durante a avaliação.

## Iniciar e parar sem perder a avaliação

Requer Docker Desktop já instalado, ativo e configurado para contêineres Linux. Execute da raiz do repositório.

Se a demonstração já estiver aberta, não inicie uma segunda cópia. Para parar e depois retomar, preservando os registros fictícios:

```powershell
docker compose -f deploy/validation/compose.yaml stop
docker compose -f deploy/validation/compose.yaml up -d
docker compose -f deploy/validation/compose.yaml exec -d lab python -m tools.validation.preview
```

O último comando deve ser executado uma vez após iniciar/recriar o contêiner. A demonstração permanece ativa até parar o laboratório ou o Docker. As senhas acima nunca devem ser usadas em produção.

### Primeira execução do ensaio em banco vazio

```powershell
docker compose -f deploy/validation/compose.yaml up -d --build
docker compose -f deploy/validation/compose.yaml exec -T lab python -m tools.validation.run
node --test tests/pwa.test.cjs
docker compose -f deploy/validation/compose.yaml exec -d lab python -m tools.validation.preview
```

O ensaio exige `VALIDATION_ONLY=1`, banco `diario_validation` e host interno `db`. A carga fictícia recusa banco com usuários. Backup e restauração recusam destinos existentes. Não repetir o ensaio sobre a avaliação já iniciada: preservar primeiro seus resultados e preparar uma nova base de laboratório por decisão explícita. Não usar remoção de volume como procedimento normal de retomada.

O projeto Docker se chama `diario-validacao`, usa o volume `diario-validacao_validation_db` e não publica a porta do PostgreSQL. O banco de restauração se chama `diario_restore_validation`. A porta HTTPS 18443 fica ativa apenas durante o ensaio; a demonstração fica em 18080. `.dockerignore` permite apenas fontes e dependências necessárias, excluindo bancos, `.env` e backups.

Os logs e evidências desta máquina ficam em `tmp/validation-results/` (fora do Git): `summary.json`, `timings.json`, logs das suítes, PDF/CSV fictícios e dump com manifesto. `summary.json` com `status: passed` confirma o término; retorno zero dos testes JavaScript confirma a suíte PWA. Os scripts reproduzíveis e este relatório ficam versionados.

## Pendências antes do uso real

1. Avaliação e aprovação do professor sobre o ambiente local, com correção dos problemas que identificar.
2. Instalação/uso em Android e iPhone físicos, incluindo perda de conexão e retomada. A simulação de viewport não substitui os aparelhos.
3. Somente após autorização: homologação da hospedagem com HTTPS público, SMTP externo, supervisão, consumo conjunto de memória, backups agendados e cópias fora do servidor.
4. Se houver dados reais a transferir, ensaiar a migração preservando usuários, vínculos e auditoria.
5. Autorizar a disponibilização após os testes do ambiente definitivo. Nenhum teste local comprova sozinho o funcionamento dos serviços externos.

A preparação da VPS permanece adiada conforme solicitado. Este laboratório é uma ferramenta local de validação, não uma proposta para instalar Docker na VPS.

## Verificação da melhoria de cadastro — 23/10/2026

153 testes aprovados em SQLite e PostgreSQL 16/Python 3.12, incluindo cadastro com CSRF, login automático, rejeição de usuário duplicado e senhas divergentes, isolamento e recusa de privilégios enviados no formulário. `check --deploy --fail-level WARNING` aprovado no laboratório (dois avisos HSTS já documentados). Login e formulário conferidos no navegador. A demonstração foi atualizada preservando o banco; nenhuma migração necessária. A tentativa inicial de testes no Windows encontrou restrições de permissão na pasta temporária do sandbox; as suítes completas foram concluídas no laboratório Linux.
