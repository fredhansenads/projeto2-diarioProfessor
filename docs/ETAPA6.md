# Etapa 6 — Celular e instalação como PWA

Implementação em 20/10/2026. O usuário autorizou a etapa, escolheu **internet obrigatória nesta versão** e **Android e iPhone**. O backend continua em Python/Django; o navegador usa HTML, CSS e um pequeno script de melhoria progressiva.

## Entrega

- Manifesto com identidade estável, abertura na raiz, modo independente e ícones PNG opacos de 192 e 512 pixels, adequados também a máscaras. Ícone Apple de 180 pixels.
- Página **Usar no celular** (`/instalar/`), acessível pelo rodapé, com orientações para Chrome/Android e Safari/iPhone. O botão de instalação aparece somente quando o navegador oferece essa possibilidade.
- Campos com fonte de 16 pixels no celular, alvos de toque maiores, respeito às áreas seguras da tela e botões que se acomodam à largura.
- Tabelas com rolagem própria, indicação de colunas fora da tela e acesso por teclado. Corrigido transbordamento dos textos auxiliares para leitores de tela na lista de aulas.
- Avisos de alterações ainda não enviadas, envio em andamento e conexão indisponível. A confirmação de gravação continua sendo a mensagem emitida pelo Django depois de salvar.
- Proteção contra cliques repetidos no mesmo formulário durante o envio e aviso do navegador ao tentar abandonar alterações, inclusive ao sair da conta. Essa proteção complementa as versões/auditoria das etapas anteriores; não é uma garantia universal de idempotência entre abas.
- Texto do painel atualizado com links para notas e relatórios já disponíveis.

## Conexão e dados

O service worker na raiz (`/service-worker.js`) envia navegações diretamente ao servidor. Guarda no Cache Storage **somente `/offline/`**, uma página pública, sem sessão, aluno, turma, notas ou token CSRF. Não há cache de páginas autenticadas, relatórios ou downloads pelo service worker. Recursos estáticos públicos podem usar o cache HTTP normal do navegador. Arquivos baixados voluntariamente permanecem no dispositivo até o professor removê-los.

Não há IndexedDB, localStorage de formulários, fila de operações, sincronização, repetição automática de POST ou envio em segundo plano. Se o navegador informar que está offline, o script impede o envio e mantém os campos na página aberta. Esse indicador não confirma que o servidor está acessível.

Se a conexão falhar **durante** um envio, não é possível garantir se o servidor recebeu e gravou. A página de falha orienta consultar o registro antes de tentar novamente. Ela responde com HTTP 503 e `no-store`. Não transforma falhas HTTP do servidor (por exemplo, CSRF 403) em confirmação ou tela offline: a resposta original é preservada.

Os valores não enviados só existem na página aberta. Voltar no navegador pode recuperar o formulário, mas isso depende do navegador; fechar o app, recarregar ou encerrar sua execução pode perdê-los. Ao restaurar uma página pelo histórico, o aviso recomenda conferir o registro antes de reenviar. O aviso ao sair também depende do suporte e da política do navegador, especialmente no celular.

O worker não chama `skipWaiting()` nem `clients.claim()`: uma atualização não toma o controle das páginas abertas nem força recarga. Salvar, fechar todas as janelas do diário e abrir novamente permite ativar a atualização. Ao alterar a página offline, incrementar a versão do cache no worker. Os scripts/estilos novos têm revisão na URL; atualizar a revisão quando mudar esses arquivos. Em produção, definir cache e versionamento de todos os estáticos na Etapa 7.

## Instalar e usar

Abra **Usar no celular** no diário. No Android, use o Chrome e o botão oferecido pelo navegador ou seu menu de instalação. No iPhone, abra no Safari, use Compartilhar → Adicionar à Tela de Início e, quando disponível, Abrir como App da Web. Os nomes e posições podem variar entre versões.

A implantação precisa de HTTPS confiável para o service worker e os recursos de instalação. `localhost` e `127.0.0.1` permitem desenvolvimento no próprio computador. O endereço local do computador não abre esse servidor no celular; HTTP por um IP da rede não substitui uma implantação HTTPS. Não foi criado túnel nem disponibilizado o banco na rede nesta etapa. O app pressupõe implantação na raiz de uma origem dedicada (escopo `/`).

O aplicativo usa a mesma conta e o mesmo banco do acesso web. A instalação não cria uma cópia offline, não publica nas lojas e não resolve hospedagem, backups ou envio de e-mail.

## Validação executada

- **135 testes Django**, incluindo sete novos para manifesto/ícones, limite de autenticação, páginas públicas sem dados de sessão, cache, tipos de resposta e rotas somente de leitura.
- **12 testes JavaScript** com o runner nativo do Node: somente conteúdo genérico no cache, POST enviado uma vez, falhas e respostas originais, limpeza seletiva de caches, ausência de tomada de controle das abas, indicadores de conexão, proteção de formulário e instalação condicional. Simulações de APIs não certificam navegadores físicos.
- Verificações Django, migrações sem alterações e dependências consistentes.
- Navegador com banco SQLite separado e dados fictícios: login, chamada salva em 320 × 740, nota com vírgula salva em 390 × 844, caderno e relatório; tabela de aulas corrigida com largura de página igual à largura disponível (305 pixels, descontada a barra de rolagem).
- Servidor de teste efetivamente parado: uma navegação exibiu o fallback público do service worker; após reiniciar o servidor, a mesma página voltou a consultar os registros.
- A instalação em dispositivos físicos e o funcionamento em Safari/iOS não foram executados neste ambiente. A homologação abaixo continua aberta; a etapa não representa aprovação para uso real.

Para repetir os testes:

```powershell
.\.venv\Scripts\python.exe manage.py test
node --test tests/pwa.test.cjs
```

Node 24 foi usado somente nos testes; não é necessário para executar o servidor Python. Os ícones podem ser regenerados com `tools/build_pwa_icons.py`, passando o caminho de uma fonte TTF serifada em negrito; nesta entrega foi usada Georgia Bold disponível no Windows, sem redistribuir o arquivo da fonte.

## Homologação pendente antes de disponibilizar

| Verificação | Android / Chrome real | iPhone / Safari real |
| --- | --- | --- |
| Instalar pelo endereço HTTPS e abrir pela tela inicial | Pendente | Pendente |
| Login, sair e entrar em outra conta sem exibir dados anteriores | Pendente | Pendente |
| Chamada, notas, teclado decimal, validações e mensagens de sucesso | Pendente | Pendente |
| Relatórios, downloads PDF/CSV e navegação em retrato/paisagem | Pendente | Pendente |
| Modo avião antes de salvar, queda durante envio, retorno de conexão | Pendente | Pendente |
| Suspender/retomar app, histórico e sessão expirada | Pendente | Pendente |
| Atualizar a aplicação sem interromper um formulário aberto | Pendente | Pendente |

Registrar modelo, versão do sistema e navegador, data e resultado de cada teste quando houver HTTPS e acesso aos aparelhos. Esses itens devem acompanhar a validação da Etapa 7, se ela for autorizada. Nenhuma implantação pública foi realizada.

## Referências consultadas

- [Apple — transformar um site em app no Safari do iPhone](https://support.apple.com/pt-br/guide/iphone/iphea86e5236/ios).
- [Google web.dev — instalação de PWA](https://web.dev/learn/pwa/installation).
- [Google web.dev — página alternativa para falhas de conexão](https://web.dev/articles/offline-fallback-page).
