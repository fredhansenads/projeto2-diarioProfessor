# Etapa 7 — Validação e preparação para produção

Data: 21/10/2026. **Em andamento: validação técnica local aprovada; demonstração entregue para avaliação do professor; publicação não realizada.**

## Decisões do proprietário

- Etapa 7 autorizada.
- **VPS já existente na Locaweb**, escolhida pelo proprietário após informar que o plano compartilhado Linux GO não suporta Python/Django.
- VPS: Ubuntu 24.04.4, 1 GB RAM, 2 vCPUs, disco de 40 GB. Inventário recebido: Python 3.12.3, PostgreSQL 16.15, Nginx/Certbot, Flask e Node/PM2. Medição pontual de 307 MiB RAM disponíveis; capacidade conjunta ainda não validada.
- Subdomínio: **diarioprofessor.santustech.com.br**.
- **Decisão atual de 23/10/2026:** cada professor pode criar sua conta na tela de login. Substitui a decisão anterior de contas somente pelo administrador.
- **Preparação da VPS adiada:** o proprietário pediu o sistema testado localmente primeiro e autorizou essa validação. Nenhuma alteração remota nesta rodada.
- Permanecem as decisões anteriores: Python, internet obrigatória, Android e iPhone, dados isolados por professor, aprovação antes de avançar de etapa.

## Implementado

- Cadastro público habilitado com opção **Criar minha conta** no login; pode ser fechado pela configuração. Novas contas não recebem privilégios administrativos.
- django-axes protege login do professor e do administrador: cinco falhas por combinação usuário/IP, bloqueio de 15 minutos, sem confiar diretamente em X-Forwarded-For enviado pelo cliente.
- WhiteNoise com estáticos comprimidos e nomes por conteúdo em produção; servidor Waitress com proxy explícito e limite de requisição.
- Checks de publicação para DEBUG, banco, hosts, SMTP, remetente e política de contas; tratamento de sessão/CSRF inválida e erro interno sem detalhes técnicos.
- Endpoint de saúde com verificação simples do banco e resposta sem dados internos.
- Backup SQLite/PostgreSQL com checksum e restauração exclusivamente para novo destino; operações existentes não sobrescrevem o banco ativo.
- Modelo de ambiente para o subdomínio e documentos de implantação, operação, atualização e recuperação.
- Dependências fixadas: django-axes 8.3.1, WhiteNoise 6.12.0, Waitress 3.0.2 e psycopg 3.3.6. A base continua Django 5.2.18/Python 3.14.7.
- Laboratório Docker exclusivamente local com Ubuntu 24.04/Python 3.12.3/PostgreSQL 16.15, carga fictícia, ensaio HTTPS/SMTP e demonstração em localhost. Instruções e resultados em [VALIDACAO_LOCAL.md](VALIDACAO_LOCAL.md).

## Verificações realizadas

| Verificação | Resultado |
| --- | --- |
| Suíte Django completa em SQLite | 150 testes aprovados |
| Mesma suíte em PostgreSQL 18 isolado | 150 testes aprovados |
| Compatibilidade Ubuntu/Python 3.12.3 com SQLite e PostgreSQL 16.15 | 150 testes aprovados em cada banco |
| Testes JavaScript de PWA/conexão | 12 aprovados |
| Ciclo com CSRF: login → cadastros → matrícula → aula → chamada → prova → nota → relatório HTML/PDF/CSV | Aprovado nos dois bancos; outro professor não acessa os registros |
| Cadastro fechado quando configurado, permissões de administrador, limite/expiração de login e cabeçalho IP falso | Aprovados; cadastro público reaberto por decisão de 23/10/2026 |
| SQLite: backup, restauração, corrupção, origem ausente e recusa de sobrescrita | Aprovados |
| PostgreSQL: migração inicial, dump e restauração de dados fictícios | 29 tabelas comparadas, conteúdos idênticos, origem preservada e destinos existentes recusados |
| Perfil DEBUG=False, check --deploy, migrações, cookies/redirecionamento HTTPS, estáticos com hash, PWA e relatórios privados | Aprovado localmente; também exercitado com Nginx/HTTPS e certificado local verificado, sem servidor HTTPS externo |
| SMTP STARTTLS e recuperação de senha por HTTP | Mensagem capturada localmente; alteração, login e token de uso único conferidos; sem envio externo |
| Restauração PostgreSQL 16 | 29 tabelas idênticas à origem, origem preservada e sequência de usuários válida |
| Quatro clientes simultâneos, 72 consultas | Sem erro HTTP; p95 1,65 s; RSS máximo observado do Waitress 84,9 MiB; não garante capacidade da VPS |
| Demonstração para avaliação | 120 alunos fictícios, três turmas, login e ficha conferidos no navegador; viewport de celular verificado |
| Waitress + PostgreSQL local, tela de entrada e cadastro administrado | Conferidos no navegador |
| Banco SQLite real do projeto | Backup antes das migrações do Axes; contagens de usuários/registros pedagógicos preservadas |

São 150 casos Django executados em cada banco, não 300 casos distintos. Os dois avisos de HSTS para subdomínios/preload estão deliberadamente silenciados e justificados em IMPLANTACAO_LOCAWEB.md. A rodada mais recente validou conexão SMTP com STARTTLS dentro do laboratório, sem entrega externa. PostgreSQL 16 foi executado em contêiner sem porta publicada, com dados fictícios. Não houve acesso a bancos da Locaweb ou a outra instância existente. Metodologia, limites de desempenho e evidências em [VALIDACAO_LOCAL.md](VALIDACAO_LOCAL.md).

## O que ainda impede declarar pronto para uso real

- Receber a avaliação do professor na demonstração local, ajustar o necessário e obter autorização para retomar a hospedagem. Compatibilidade Python 3.12/PostgreSQL 16 já validada localmente; execução na VPS e memória sob uso conjunto continuam pendentes.
- Preparar a infraestrutura confirmada, verificar HTTPS real/DNS, supervisão do processo e confiança do proxy.
- Configurar e testar SMTP com destinatário autorizado.
- Agendar e verificar backups fora do servidor, alertas e restauração no ambiente contratado; definir responsáveis e política de retenção.
- Planejar e validar eventual migração do SQLite real para PostgreSQL sem perder usuários, vínculos ou auditoria.
- Concluir a matriz Android/Chrome e iPhone/Safari em aparelhos reais, inclusive instalação, suspensão/retomada e perda de conexão.
- Validar com o professor o ciclo pedagógico e obter autorização final de disponibilização.

Os itens externos permanecem abertos no plano. Não criar uma Etapa 8 fictícia nem marcar a Etapa 7 como concluída para ocultar essas pendências. O próximo trabalho é a avaliação local pelo professor, seguindo VALIDACAO_LOCAL.md; a preparação da VPS permanece adiada.

## Continuidade

1. Abrir a demonstração e executar o roteiro de `VALIDACAO_LOCAL.md` com o professor. Preservar as alterações fictícias feitas durante a avaliação.
2. Registrar problemas, corrigir e testar os fluxos afetados antes de solicitar aprovação local.
3. Somente após autorização para retomar a VPS, seguir `VPS_UBUNTU.md`, `OPERACAO.md` e a homologação física em `ETAPA6.md`.
4. Salvar cada entrega no Git/GitHub e obter autorização antes da disponibilização ou de outra etapa.

## Verificação da melhoria de cadastro — 23/10/2026

153 testes aprovados em SQLite e PostgreSQL 16/Python 3.12, incluindo cadastro com CSRF, login automático, rejeição de usuário duplicado e senhas divergentes, isolamento e recusa de privilégios enviados no formulário. `check --deploy --fail-level WARNING` aprovado no laboratório (dois avisos HSTS já documentados). Login e formulário conferidos no navegador. A demonstração foi atualizada preservando o banco; nenhuma migração necessária. A tentativa inicial de testes no Windows encontrou restrições de permissão na pasta temporária do sandbox; as suítes completas foram concluídas no laboratório Linux.
