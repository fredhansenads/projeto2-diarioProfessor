# Etapa 5 — Relatórios e conselho

Implementada em 20/10/2026. O usuário aprovou um modelo geral com notas, frequência, pendências e observações, filtrado por turma, disciplina e período, com PDF e CSV.

## Uso

1. Abra **Relatórios e conselho** na navegação, na turma ou pelo atalho do caderno de notas.
2. Escolha **turma e período**. Disciplina e aluno/matrícula são opcionais.
3. Escola e ano permitem conferir o recorte: devem corresponder à turma. O período deve pertencer à mesma escola e ano. A seleção de uma turma limita as opções de período, disciplina e matrícula na próxima consulta.
4. Use **Consultar relatório**. Sem selecionar aluno, aparece a visão da turma, separada por disciplina.
5. Clique no nome do aluno, ou escolha sua matrícula no filtro, para abrir a ficha individual.
6. Use **Baixar PDF**, **Baixar CSV** ou **Versão para impressão → Imprimir agora**. Os filtros são preservados.
7. Corrija dados nas telas de origem (cadernos, avaliações, chamadas ou matrículas) e consulte novamente.

Ao trocar de turma, limpe seleções anteriores incompatíveis. Filtros inválidos não são ignorados e não ampliam a consulta. O relatório é somente leitura e não altera notas, chamadas, regras ou históricos.

## Conteúdo e consistência

- Identificação de professor, escola, ano, turma, período e momento de emissão.
- Resultados separados por disciplina: base/parcial, recuperação, resultado, referência, situação, notas pendentes, não entregues e dispensas.
- Frequência: aulas no vínculo, aulas com chamada, presenças, faltas, justificadas, pendentes e percentual registrado.
- Relação de avaliações pendentes e observações pedagógicas já registradas nas notas e justificativas de frequência.
- Ficha individual: avaliações com situação/nota/valor/observação e aulas com conteúdo/faltas/justificativa.
- Matrículas fora do período e sem registros aplicáveis são excluídas. Transferências respeitam datas inclusivas de entrada e saída.
- Datas ausentes em matrículas participantes geram aviso. Matrículas antigas inativas sem data de saída e sem registros aplicáveis não têm vínculo inferido.
- Aulas e avaliações canceladas são excluídas; o histórico permanece nas telas de origem.

Os relatórios chamam os mesmos serviços de cálculo das Etapas 3 e 4. Não recalculam médias por fórmulas independentes nem somam percentuais entre disciplinas. A consulta usa uma transação de leitura para montar os dados. A geração é sob demanda: cada novo download reflete o estado atual, com horário de emissão próprio; não é um fechamento imutável.

**Ausência de dados não é zero.** Zero explicitamente lançado continua sendo exibido. Sem caderno não há resultado de notas. Sem chamada não há percentual. Frequência usa apenas aulas registradas com chamada; justificativas não abonam faltas. A base parcial não é resultado final. Não há decisão oficial de aprovação.

## Formatos

### PDF

Gerado no servidor com ReportLab, sem serviço externo. Relatório de turma em A4 paisagem; ficha individual em A4 retrato. Cada disciplina inicia uma seção em nova página, com cabeçalho de contexto, tabelas com títulos repetidos e numeração de páginas. Textos longos podem continuar na página seguinte.

A fonte Vera distribuída com ReportLab preserva acentos do português. Textos são tratados como texto literal, sem interpretar imagens, links ou HTML inseridos em observações. Fontes e suporte a outros alfabetos podem exigir ampliação futura.

### CSV

UTF-8 com BOM, separador ponto e vírgula, números decimais com vírgula e cabeçalho explícito. Uma linha por aluno/matrícula/disciplina, com dados de identificação, regras, resultados, totais de frequência, pendências e observações. Não exporta uma linha por aula ou por avaliação; esse detalhamento está na ficha individual em tela/PDF.

Campos vazios representam ausência de nota/percentual/caderno, conforme a coluna de situação. Campos textuais que poderiam iniciar fórmulas ao abrir em planilhas recebem apóstrofo de proteção. Vírgulas, aspas, ponto e vírgula e quebras de linha são preservados pela biblioteca CSV.

### Impressão

Página própria com botão para abrir a impressão do navegador. O CSS remove navegação, filtros e botões da impressão, usa A4 paisagem e repete cabeçalhos de tabelas. A saída pode variar conforme navegador, margens e opções da impressora; confira a prévia. Impressora física não foi validada.

## Segurança e operação

- Login obrigatório em tela, impressão e downloads.
- Todas as opções e dados são limitados à conta atual.
- Exportações com filtros ausentes/incompatíveis retornam erro HTTP 400 sem gerar arquivo.
- Formato desconhecido é rejeitado; nomes de arquivos não usam texto livre.
- Respostas são marcadas para não serem armazenadas em cache.
- Não há compartilhamento externo, envio automático à escola ou armazenamento permanente de exportações pelo sistema. O usuário decide onde salvar seus downloads.
- Nenhuma migração nova: a Etapa 5 consulta as tabelas existentes.
- Relatórios refletem a conta do professor; não consolidam dados de outros professores.

## Dependências e verificações

Para executar: instalar requirements-lock.txt, que inclui ReportLab, Pillow e charset-normalizer. Para os testes de exportação: instalar requirements-test.txt, que acrescenta pypdf para reabrir e conferir os PDFs.

A suíte contém 128 testes (25 novos nesta etapa), com conferência dos cálculos de origem, zero versus ausência, recuperações, transferências, cancelamentos, filtros, isolamento, CSV, escape de HTML, PDF com acentos, paginação com 57 alunos e conteúdo longo.

No navegador foram verificados consulta por turma/disciplina/período, acesso à ficha individual, downloads PDF/CSV e acesso à versão de impressão. A ficha foi conferida em janela de 390 × 844 pixels, sem transbordamento horizontal da página; tabelas mantêm rolagem própria. PDFs de exemplo foram renderizados com Poppler e revisados visualmente, incluindo todas as páginas da amostra final.

## Continuidade

Etapa 5 concluída. Próxima: Etapa 6, experiência no celular/PWA, somente após autorização. Instalação em dispositivos reais, offline, PostgreSQL, SMTP e produção continuam pendentes. Ata do conselho, observações livres desvinculadas de avaliações, modelos específicos de escolas, importação para sistemas escolares e fechamento anual não fazem parte desta entrega.
