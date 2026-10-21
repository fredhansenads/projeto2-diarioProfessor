# Etapa 7 — Validação e preparação para produção

Data: 21/10/2026. **Em andamento: preparação local entregue; publicação não realizada.**

## Decisões do proprietário

- Etapa 7 autorizada.
- **VPS já existente na Locaweb**, escolhida pelo proprietário após informar que o plano compartilhado Linux GO não suporta Python/Django.
- VPS informada: Ubuntu (versão pendente), 1 GB RAM, 2 vCPUs, disco de 40 GB; já executa outro sistema Python. Recursos livres ainda não medidos.
- Subdomínio: **diarioprofessor.santustech.com.br**.
- Contas criadas **somente pelo administrador**.
- Permanecem as decisões anteriores: Python, internet obrigatória, Android e iPhone, dados isolados por professor, aprovação antes de avançar de etapa.

## Implementado

- Cadastro público fechado, inclusive POST direto, e orientação para solicitar acesso ao administrador.
- django-axes protege login do professor e do administrador: cinco falhas por combinação usuário/IP, bloqueio de 15 minutos, sem confiar diretamente em X-Forwarded-For enviado pelo cliente.
- WhiteNoise com estáticos comprimidos e nomes por conteúdo em produção; servidor Waitress com proxy explícito e limite de requisição.
- Checks de publicação para DEBUG, banco, hosts, SMTP, remetente e política de contas; tratamento de sessão/CSRF inválida e erro interno sem detalhes técnicos.
- Endpoint de saúde com verificação simples do banco e resposta sem dados internos.
- Backup SQLite/PostgreSQL com checksum e restauração exclusivamente para novo destino; operações existentes não sobrescrevem o banco ativo.
- Modelo de ambiente para o subdomínio e documentos de implantação, operação, atualização e recuperação.
- Dependências fixadas: django-axes 8.3.1, WhiteNoise 6.12.0, Waitress 3.0.2 e psycopg 3.3.6. A base continua Django 5.2.18/Python 3.14.7.

## Verificações realizadas

| Verificação | Resultado |
| --- | --- |
| Suíte Django completa em SQLite | 150 testes aprovados |
| Mesma suíte em PostgreSQL 18 isolado | 150 testes aprovados |
| Testes JavaScript de PWA/conexão | 12 aprovados |
| Ciclo com CSRF: login → cadastros → matrícula → aula → chamada → prova → nota → relatório HTML/PDF/CSV | Aprovado nos dois bancos; outro professor não acessa os registros |
| Cadastro fechado, permissões de administrador, limite/expiração de login e cabeçalho IP falso | Aprovados |
| SQLite: backup, restauração, corrupção, origem ausente e recusa de sobrescrita | Aprovados |
| PostgreSQL: migração inicial, dump e restauração de dados fictícios | 29 tabelas comparadas, conteúdos idênticos, origem preservada e destinos existentes recusados |
| Perfil DEBUG=False, check --deploy, migrações, cookies/redirecionamento HTTPS, estáticos com hash, PWA e relatórios privados | Aprovado localmente; TLS do navegador simulado no cliente Django, sem servidor HTTPS externo |
| Waitress + PostgreSQL local, tela de entrada e cadastro administrado | Conferidos no navegador |
| Banco SQLite real do projeto | Backup antes das migrações do Axes; contagens de usuários/registros pedagógicos preservadas |

São 150 casos Django executados em cada banco, não 300 casos distintos. Os dois avisos de HSTS para subdomínios/preload estão deliberadamente silenciados e justificados em IMPLANTACAO_LOCAWEB.md. SMTP foi configurado com valores fictícios apenas para validar settings; nenhum e-mail real foi enviado. O ensaio PostgreSQL usa instância temporária local em porta separada; não houve acesso a bancos da Locaweb ou a outra instância existente.

## O que ainda impede declarar pronto para uso real

- Confirmar versão do Ubuntu, recursos livres, serviços existentes e acesso à VPS escolhida; preparar a implantação conforme IMPLANTACAO_LOCAWEB.md.
- Preparar a infraestrutura confirmada, verificar HTTPS real/DNS, supervisão do processo e confiança do proxy.
- Configurar e testar SMTP com destinatário autorizado.
- Agendar e verificar backups fora do servidor, alertas e restauração no ambiente contratado; definir responsáveis e política de retenção.
- Planejar e validar eventual migração do SQLite real para PostgreSQL sem perder usuários, vínculos ou auditoria.
- Concluir a matriz Android/Chrome e iPhone/Safari em aparelhos reais, inclusive instalação, suspensão/retomada e perda de conexão.
- Validar com o professor o ciclo pedagógico e obter autorização final de disponibilização.

Os itens externos permanecem abertos no plano. Não criar uma Etapa 8 fictícia nem marcar a Etapa 7 como concluída para ocultar essas pendências. O próximo trabalho é inventariar a VPS e preparar sua configuração e continuar a mesma etapa, mediante as informações/acessos necessários.

## Continuidade

1. Ler `IMPLANTACAO_LOCAWEB.md`, obter o destino/método de acesso SSH ou a saída da consulta `deploy/inspecionar-vps.sh`, e identificar os recursos livres e o serviço Python existente. A consulta ao suporte sobre o GO foi superada pela escolha da VPS.
2. Adaptar a configuração ao mecanismo de execução confirmado, sem substituir o requisito Python ou contratar outro serviço por conta própria.
3. Seguir a homologação e operação documentadas em `OPERACAO.md` e `ETAPA6.md`.
4. Salvar cada entrega no Git/GitHub e apresentar a implantação validada ao proprietário antes da disponibilização.
