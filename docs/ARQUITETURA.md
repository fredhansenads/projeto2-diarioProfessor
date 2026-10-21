# Arquitetura inicial e decisões de implementação

Criado em 19/10/2026; atualizado em 21/10/2026.

O usuário autorizou o início do projeto. Para avançar sem bloquear a base, foram adotadas as premissas abaixo. As regras pedagógicas ainda devem ser detalhadas antes das respectivas funcionalidades.

## Estrutura da aplicação

- Monólito Django com páginas renderizadas no servidor.
- Interface responsiva em HTML/CSS, sem dependência de serviços externos para fontes ou scripts.
- Contas de professores com autenticação do Django e senha armazenada como hash.
- SQLite no desenvolvimento; aplicação e backup/restauração validados em PostgreSQL 18 local.
- Funcionamento conectado aprovado na Etapa 6. Service worker com cache exclusivo de página genérica de conexão; nenhum registro pedagógico é armazenado para uso offline.

## Vínculos

```mermaid
erDiagram
    PROFESSOR ||--o{ ESCOLA : possui
    PROFESSOR ||--o{ ANO_LETIVO : organiza
    PROFESSOR ||--o{ DISCIPLINA : cadastra
    PROFESSOR ||--o{ ALUNO : acompanha
    ESCOLA ||--o{ PERIODO : define
    ANO_LETIVO ||--o{ PERIODO : agrupa
    ESCOLA ||--o{ TURMA : possui
    ANO_LETIVO ||--o{ TURMA : organiza
    TURMA }o--o{ DISCIPLINA : oferece
    TURMA ||--o{ MATRICULA : recebe
    ALUNO ||--o{ MATRICULA : possui
    TURMA ||--o{ AULA : registra
    DISCIPLINA ||--o{ AULA : identifica
    AULA ||--o{ FREQUENCIA : registra
    MATRICULA ||--o{ FREQUENCIA : participa
    AULA ||--o{ HISTORICO : preserva
    TURMA ||--o{ CADERNO : organiza
    DISCIPLINA ||--o{ CADERNO : identifica
    PERIODO ||--o{ CADERNO : delimita
    CADERNO ||--o{ AVALIACAO : planeja
    AVALIACAO ||--o{ NOTA : recebe
    MATRICULA ||--o{ NOTA : participa
    CADERNO ||--o{ HISTORICO_NOTAS : preserva
```

Todos os registros possuem professor proprietário, data de criação e data da última alteração. Um ano letivo identifica o ano civil na conta do professor. Os períodos pertencem a uma escola e ano, permitindo calendários diferentes entre escolas.

A turma identifica escola, ano, nome e turno, com uma ou mais disciplinas opcionais. O aluno é independente do ano: suas matrículas registram os vínculos com as turmas.

## Isolamento e validação

- Listas, detalhes e edições filtram pelo usuário autenticado.
- IDs de outro professor retornam 404 nas telas de consulta e edição.
- O proprietário é atribuído no servidor e não pode ser escolhido pelo formulário.
- As opções de relacionamentos dos formulários só mostram registros da própria conta.
- Validações do modelo verificam a propriedade dos relacionamentos por chave estrangeira.
- Disciplinas da turma são filtradas e validadas pelo formulário de múltipla seleção.
- Restrições no banco impedem duplicação de escolas, anos, disciplinas, períodos, turmas e matrículas conforme suas respectivas chaves.
- Alunos podem ter o mesmo nome. A identificação interna opcional ajuda a distinguir homônimos.
- Datas dos períodos pertencem ao ano escolhido, com fim igual ou posterior ao início.
- Páginas autenticadas enviam cabeçalhos para evitar armazenamento em cache.
- Não há exclusão de registros pedagógicos pela interface nesta etapa.

Ao criar novas telas, APIs, importadores ou comandos, manter as mesmas verificações de propriedade. Operações em lote do ORM podem ignorar validações de `save()`; não utilizá-las como atalho para alterações sem validar os vínculos.

## Preservação de histórico

- Matrículas existentes preservam aluno e turma; a situação pode ser alterada.
- Transferências devem encerrar o vínculo anterior e criar um novo.
- Turmas com matrículas preservam escola e ano letivo.
- Anos com períodos existentes não podem ser alterados se as datas ficarem incompatíveis.
- Relacionamentos usam proteção contra exclusão dos registros referenciados.

Datas de atualização não constituem auditoria completa. Aulas/frequência e cadernos/notas possuem históricos próprios com autor, momento, motivo e diferenças entre valores anteriores e novos.

Chamadas e histórico são gravados na mesma transação. A versão da aula e um identificador do conjunto de matrículas detectam telas desatualizadas. Uma atualização condicional de versão impede sobrescrita silenciosa, inclusive no SQLite. O registro de histórico não possui tela de edição e seu modelo rejeita alterações em registros existentes.

A frequência respeita as datas de entrada e saída, inclusive. Matrículas antigas mantêm datas vazias até revisão; nenhuma data real é inferida na migração. As regras de compatibilidade, cálculo e cancelamento estão em ETAPA3.md.

Cadernos são únicos por turma/disciplina/período e guardam regras configuráveis. A versão compartilhada do caderno serializa alterações de regras, avaliações, notas e cancelamentos; um identificador das matrículas detecta mudança do conjunto de alunos. Escritas e auditoria são atômicas. Notas usam Decimal; resultados são calculados na consulta. Regras e limites da recuperação estão em ETAPA4.md. Cancelamentos preservam dados e deixam de participar dos cálculos.

## Telas existentes

1. Entrada e recuperação de senha; contas criadas pelo administrador em `/admin/`.
2. Visão geral com contagens reais, turmas e primeiros passos.
3. Lista com busca e paginação para cada cadastro.
4. Criação e edição com mensagens de validação.
5. Detalhe da turma com disciplinas e alunos matriculados.
6. Troca de senha pelas rotas de autenticação do Django.
7. Registro de aulas, listagem com filtros, chamada e consulta de frequência da turma.
8. Correção de conteúdos/chamadas, cancelamento sem apagar dados e histórico de alterações.
9. Cadernos com regras configuráveis, provas/trabalhos/atividades, notas, entregas, recuperação, resultados e histórico.
10. Relatórios de turma e ficha individual por turma/disciplina/período, com PDF, CSV e impressão.

## Relatórios

A Etapa 5 adiciona consultas sem novas tabelas. ReportFilterForm valida conta e compatibilidade dos vínculos; report_services monta os dados chamando grade_summary e frequency_rows, preservando as regras das etapas anteriores. Um mesmo conjunto de dados alimenta HTML, impressão, PDF e CSV. Downloads são privados e sem cache. ReportLab gera PDFs no servidor; CSV usa a biblioteca padrão, com proteção contra fórmulas. pypdf é dependência exclusiva dos testes de exportação. Detalhes e limites em ETAPA5.md.

## Experiência no celular

A Etapa 6 adiciona manifesto, ícones e instalação como PWA, com instruções para Android/Chrome e iPhone/Safari. O worker na raiz intercepta somente navegações da mesma origem e usa a rede; falhas de transporte retornam uma página genérica com status 503. Nenhum POST é repetido ou enfileirado. O script de interface bloqueia envios quando o navegador indica offline e informa alterações não enviadas; as gravações continuam nos formulários tradicionais do Django. Atualizações do worker aguardam o fechamento das janelas anteriores. Não há alteração de banco nesta etapa. Regras, limitações e homologação pendente em ETAPA6.md.

## Operação e implantação

A Etapa 7 está autorizada e em andamento. Cadastro público desativado por padrão; a configuração de produção rejeita sua habilitação. Django Axes limita as tentativas por combinação de usuário e IP: cinco falhas causam bloqueio por 15 minutos. O IP vem de REMOTE_ADDR; somente um proxy explicitamente confiável pode normalizar os cabeçalhos no Waitress. Formulários continuam protegidos por CSRF, com páginas de erro sem detalhes internos.

WhiteNoise entrega os arquivos estáticos coletados com nomes versionados em produção. `serve.py` inicia o Waitress em endereço local; a hospedagem deve oferecer um mecanismo de execução persistente e HTTPS. `/saude/` verifica a conexão com o banco sem expor detalhes. Verificações de implantação exigem PostgreSQL, SMTP configurado, domínio explícito e cadastro público fechado; não substituem testes reais de conectividade e certificado.

Os comandos `backup_diary` e `restore_diary` usam backup consistente do SQLite ou pg_dump/pg_restore no PostgreSQL, com manifesto SHA-256. Restauram somente em destino novo e recusam sobrescrita. Agendamento, retenção e cópias externas ainda dependem da hospedagem. A migração dos dados reais de SQLite para PostgreSQL é uma atividade separada, ainda pendente. Procedimentos em OPERACAO.md; validações em ETAPA7.md.

## Limites e decisões abertas

- Nível de ensino ainda não informado; a base permite nomes livres de turmas e disciplinas.
- Regras de notas e recuperação configuráveis implementadas conforme ETAPA4.md; não há fechamento anual, múltiplas recuperações ou decisão oficial de aprovação. Frequência não aplica abono automático.
- O recorte por ano civil é uma premissa inicial; calendários que atravessam anos exigirão ajuste.
- Compartilhamento entre professores, aplicativo nativo e sincronização offline não estão implementados. PWA preparado; instalação e uso em aparelhos Android/iPhone reais aguardam homologação com HTTPS.
- PostgreSQL 18 foi validado localmente; hospedagem, HTTPS e SMTP real permanecem pendentes.
- Continuar a Etapa 7 identificando o sistema operacional e os serviços da VPS existente na Locaweb, escolhida pelo proprietário, e preparando a implantação; incluir a homologação física pendente da Etapa 6. Ver IMPLANTACAO_LOCAWEB.md. O sistema ainda não foi disponibilizado em produção.

