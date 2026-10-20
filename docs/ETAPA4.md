# Etapa 4 — Avaliações e notas

Implementada em 19/10/2026. O usuário autorizou regras configuráveis por turma, disciplina e período. Os valores iniciais do formulário são sugestões editáveis, não regras oficiais da escola.

## Como usar

1. Cadastre escola, ano, período, disciplina, turma e matrículas com datas de entrada/saída.
2. Abra **Avaliações e notas → Novo caderno**. Escolha turma, disciplina vinculada e período da mesma escola/ano.
3. Configure cálculo, escala, média mínima de referência, casas decimais, arredondamento e recuperação.
4. Cadastre provas, trabalhos ou atividades, com data, valor máximo, peso e orientações.
5. Abra **Notas e entregas**. Informe situação, nota e observação pedagógica por aluno. O campo de nota aceita vírgula.
6. Consulte os resultados no caderno. Correções exigem motivo e ficam no histórico.

Há um caderno por combinação turma/disciplina/período. A data da avaliação também funciona como prazo de entrega e determina os alunos participantes. Datas futuras permitem planejamento; notas e situações conclusivas só podem ser lançadas a partir da data prevista. Os formulários usam as datas de matrícula, inclusive entrada e saída; registros antigos sem datas seguem a compatibilidade da Etapa 3.

## Regras de cálculo

Todos os cálculos usam Decimal. Notas, valores e pesos aceitam duas casas decimais. Escala e valor máximo: 0,01 a 10.000; pesos: 0,01 a 1.000. Resultado com 0, 1 ou 2 casas, arredondamento convencional (5 sobe) ou truncamento.

Considere S a escala do caderno, n a nota e v o valor máximo de uma avaliação:

- **Média simples:** média de n / v × S nas avaliações participantes.
- **Média ponderada:** soma de (n / v × S × peso), dividida pela soma dos pesos participantes.
- **Soma de pontos:** soma direta das notas. A soma dos valores máximos das avaliações regulares deve ser igual a S para produzir resultado final. Não é permitido planejar mais pontos que a escala.
- **Dispensa:** exclui a avaliação do aluno. Nas médias, também exclui seu peso; na soma de pontos não redistribui os pontos dispensados.
- **Alunos transferidos:** só participam das avaliações em suas datas de matrícula. Na soma de pontos não há redistribuição automática de avaliações fora do vínculo.
- O arredondamento é aplicado depois da recuperação, sem arredondar a base intermediária. A coluna de base mostra sua versão arredondada apenas para leitura.
- A comparação com a média mínima usa o resultado arredondado. As situações “Atingiu a referência” e “Abaixo da referência” não decidem aprovação oficial ou frequência mínima.

### Ausências, zero e pendências

| Situação | Tratamento |
| --- | --- |
| Sem lançamento / pendente | Sem nota, não vira zero; resultado final pendente |
| Realizada / entregue, sem nota | Entrega registrada; correção pendente |
| Não realizada / não entregue, sem nota | Pendência e não entrega identificadas separadamente |
| Não entregue com zero digitado | Zero entra no cálculo; não entrega continua identificada |
| Dispensada | Sem nota, observação obrigatória, excluída do cálculo |

A base parcial calcula apenas notas existentes. O resultado fica vazio enquanto faltar alguma nota regular aplicável, enquanto o planejamento da soma de pontos estiver incompleto ou enquanto houver recuperação registrada sem nota. Se não há notas aplicáveis (inclusive todas dispensadas), não existe resultado.

## Recuperação

É uma avaliação específica do caderno, no máximo uma ativa por período, com nota normalizada para a escala. Não entra na média das avaliações regulares e não usa peso.

Configurações disponíveis:

- Sem recuperação.
- Maior entre base e recuperação.
- Substituir a base pela recuperação, mesmo se for menor.
- Média aritmética entre base e recuperação.

O professor decide os participantes. Um aluno sem lançamento de recuperação mantém a base completa. Ao registrar situação ou observação de recuperação sem nota, a recuperação fica pendente; apenas deixar todos os campos no padrão não cria um lançamento. Para retirar uma participação já registrada, use dispensa com motivo. Recuperação com nota zero é válida.

Recuperação não resolve notas regulares ausentes. Não há teto especial, várias recuperações no período, recuperação por avaliação ou combinação automática entre períodos. Se uma escola exigir isso, a regra precisa ser ampliada antes de utilizar seus resultados oficialmente.

## Exemplos conferidos nos testes

| Exemplo | Resultado |
| --- | --- |
| Simples: 16/20 e 6/10; escala 10 | 7,0 |
| Ponderada: 8/10 com peso 3 e 4/10 com peso 1 | 7,0 |
| Pontos: 3/4 e 5/6; escala 10 | 8,0 |
| 8 e uma nota ausente | Base parcial 8,0; resultado pendente |
| Zero explicitamente registrado | Resultado 0,0, sem pendência de nota |
| 5,95 com uma casa e arredondamento convencional | 6,0 |
| 5,95 com uma casa e truncamento | 5,9 |
| Base 4 e recuperação 8: maior / substituir / média | 8,0 / 8,0 / 6,0 |
| Base 5,94 e recuperação 5,95, média, uma casa | 5,9 (sem arredondamento intermediário) |
| Base 8 e recuperação 4, regra maior | 8,0 |

## Correções e preservação

- Regras podem ser alteradas com motivo, recalculando resultados e registrando diferenças. A escala fica fixa depois de cadastrar avaliações; turma, disciplina e período do caderno são imutáveis.
- Depois de qualquer lançamento, tipo, data, valor e peso da avaliação ficam fixos. Título e orientações continuam corrigíveis com motivo.
- Para corrigir estrutura, cancele a avaliação e cadastre outra. Cancelamento preserva notas/histórico e exclui a avaliação dos cálculos; não há restauração pela interface.
- Escola/ano da turma, vínculo da disciplina e datas/escola/ano do período ficam protegidos quando há caderno. Datas da matrícula não podem excluir lançamentos ativos.
- Todas as gravações de notas, avaliações, regras e cancelamentos usam uma versão compartilhada do caderno, transação e histórico com autor/data/motivo/antes/depois.
- Uma aba desatualizada deve ser recarregada. Alterações de matrículas também invalidam formulários antigos. Se ocorrer erro de gravação, lançamento e histórico são revertidos juntos.
- Consultas e ações ficam restritas ao professor autenticado. Não há edição/exclusão de histórico pela interface.
- As garantias valem para os serviços da aplicação; alterações diretas no banco ou uso de QuerySet.update/bulk_create fora deles podem contornar validações e auditoria.

## Verificação e limites

A suíte contém 103 testes (39 novos de avaliações/notas), incluindo exemplos acima, isolamento, CSRF, escape de HTML, formulários desatualizados, correções, cancelamento e rollback em falha de auditoria. O navegador foi usado para criar caderno e prova, salvar notas com vírgula e não entrega sem nota, e conferir resultados. O formulário foi usado em janela de 390 × 844 pixels, sem transbordamento horizontal da página. Isso não substitui teste em aparelhos físicos.

Migração 0003 adiciona as tabelas de cadernos, avaliações, notas e auditoria sem substituir os cadastros existentes. O banco principal recebe backup SQLite antes da aplicação. Dados fictícios de verificação ficam em banco separado e são removidos ao finalizar.

Relatórios de conselho, exportações, instalação PWA e implantação continuam em etapas seguintes. A Etapa 5 só começa após nova autorização.
