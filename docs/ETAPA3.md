# Etapa 3 — Aulas, conteúdos e frequência

Entrega de 19/10/2026. Frequência por aula confirmada pelo usuário.

## Rotina de uso

1. Revise as datas reais de entrada e saída nas matrículas.
2. Abra uma turma e escolha **Registrar aula**.
3. Informe disciplina, data, quantidade de aulas, conteúdo e observações.
4. Abra **Fazer chamada** e preencha as faltas de todos os alunos.
5. Quando houver faltas justificadas, informe quantas e descreva a justificativa.
6. Salve a chamada. A tela da aula confirma o salvamento e mostra o histórico.
7. Use **Consultar frequência** para escolher disciplina, período e intervalo de datas.

O botão **Preencher pendentes como presentes** só preenche campos vazios. Não altera faltas já selecionadas e não grava dados sozinho. Sem JavaScript, os campos podem ser preenchidos individualmente.

## Regras implementadas

- Uma aula registrada representa um encontro de uma turma/disciplina/data, com 1 a 20 aulas.
- Encontros da mesma turma/disciplina/data devem ser agrupados em um registro, evitando duplicação. Disciplinas diferentes podem ter registros no mesmo dia.
- A data deve pertencer ao ano letivo da turma e não pode estar no futuro.
- A disciplina deve estar vinculada à turma.
- Cada aluno tem de zero à quantidade de aulas em faltas.
- Justificadas são um subconjunto das faltas e exigem texto explicativo.
- Justificativas não abonam faltas automaticamente. Não há cálculo automático de aprovação ou reprovação por frequência.
- A ausência de chamada significa pendência, nunca presença automática.
- Todos os alunos elegíveis devem estar preenchidos para salvar o formulário. Uma linha inválida impede a gravação de todas.

## Matrículas e transferências

Entrada e saída são inclusivas. Um aluno com entrada em 10/03 e saída em 20/03 participa das chamadas de 10/03 a 20/03, independentemente de sua matrícula estar atualmente transferida.

Formulários novos e edições exigem a data de entrada. Transferências e encerramentos também exigem o último dia na turma. Não se pode alterar datas de forma a excluir chamadas já gravadas em aulas não canceladas.

Para preservar registros anteriores à Etapa 3, a migração aceita datas vazias:

- Matrícula ativa sem entrada: considera o início do ano, com aviso para revisar.
- Matrícula encerrada/transferida sem saída: não é incluída em novas chamadas, com aviso na consulta de frequência.
- Os dados e vínculos anteriores não são apagados.

## Cálculo

Para cada matrícula, considerando os filtros e as datas do vínculo:

- **Aulas no vínculo:** soma da quantidade de aulas elegíveis.
- **Com chamada:** soma das quantidades dos encontros em que existe registro do aluno.
- **Presenças:** aulas com chamada menos faltas.
- **Pendentes:** aulas no vínculo menos aulas com chamada.
- **Frequência registrada:** presenças ÷ aulas com chamada × 100.

O percentual é apresentado com uma casa decimal. Sem chamada, mostra **Sem chamada**, em vez de 0% ou 100%.

Exemplo: dois encontros com 2 e 1 aulas. No primeiro, o aluno teve 1 falta justificada; o segundo ainda não tem chamada. O resultado é 3 aulas no vínculo, 2 com chamada, 1 presença, 1 falta, 1 falta justificada, 1 aula pendente e 50,0% de frequência registrada.

## Correções e cancelamento

- Conteúdo e observações podem ser corrigidos com motivo.
- Alterar faltas ou justificativas já gravadas exige motivo.
- Reenviar uma chamada sem mudanças não duplica registros nem histórico.
- Após a primeira chamada, data, disciplina e quantidade de aulas ficam preservadas. Para corrigir esses dados, cancele o encontro e registre outro com uma nova chamada.
- Cancelamentos exigem motivo, preservam dados e retiram o encontro dos totais.
- Uma aula cancelada fica disponível somente para consulta.
- A listagem permite incluir canceladas ou mostrar somente canceladas.
- O histórico registra autor, data/hora, motivo e valores anteriores/novos.

Ao salvar, o sistema rejeita telas cuja versão da aula ou conjunto de matrículas mudou. É necessário recarregar antes de tentar novamente. A gravação é atômica: chamada e histórico são confirmados juntos ou desfeitos juntos.

## Validação e limites

- 64 testes automatizados no projeto, incluindo os fluxos desta etapa.
- Verificação no navegador com conta e dados fictícios em banco separado.
- Chamada preenchida e salva na largura de celular de 390 × 844 pixels.
- Sem dependências novas.
- Testes realizados com SQLite. PostgreSQL e aparelhos físicos permanecem na validação de implantação.
- O histórico desta etapa cobre aulas e chamada; ainda não é uma auditoria geral de todos os cadastros.
- Avaliações, notas e conselho de classe não foram iniciados.

## Continuidade

Ao encerrar a etapa, salvar no Git, enviar ao GitHub e perguntar se o usuário autoriza a Etapa 4. Não avançar automaticamente.
