# Plano do projeto — Diário do Professor

Criado em: 19/10/2026  
Última atualização: 20/10/2026
Status: Etapa 5 implementada e validada; aguardar autorização antes da Etapa 6.

## 1. Objetivo

Criar um sistema web e uma experiência de aplicativo para celular que ajudem o professor a substituir suas planilhas de papel. O sistema deve organizar notas, conteúdos, faltas, trabalhos e atividades dos alunos, oferecendo dados para preencher posteriormente o sistema da escola e participar dos conselhos de classe.

## 2. Requisitos confirmados e situação atual

- O sistema deve utilizar Python.
- Deve atender ao uso no computador e no celular.
- Deve permitir o acompanhamento pedagógico dos alunos.
- O usuário já criou a pasta do projeto, o ambiente virtual e o repositório Git.
- O usuário solicitou um plano antes de iniciar qualquer implementação.
- Após a documentação, o usuário autorizou: “Agora pode iniciar o projeto, pode execultar.”
- A primeira entrega implementa contas, painel e os cadastros da Etapa 2.
- A Etapa 3 acrescenta aulas, conteúdos, frequência por aula e histórico de correções.
- A Etapa 4 acrescenta cadernos, avaliações, entregas, notas e recuperação com regras configuráveis por turma/disciplina/período.
- A Etapa 5 acrescenta relatórios de turma e aluno para conselho, com filtros, PDF, CSV e impressão.
- Regra de continuidade do usuário: concluir uma etapa por vez, salvar no Git e enviar ao GitHub, e sempre perguntar antes de iniciar a seguinte.
- Premissas adotadas para iniciar: Django, contas separadas, uso conectado e interface responsiva. Regras pedagógicas específicas continuam abertas.

## 3. Direção técnica e situação

| Componente | Proposta | Finalidade |
| --- | --- | --- |
| Aplicação | Python com Django | Regras de negócio, autenticação, acesso aos dados e administração |
| Interface | HTML, CSS e JavaScript quando necessário | Uso pelo navegador no computador e no celular |
| Banco de produção | PostgreSQL | Armazenamento persistente dos registros |
| Aplicativo inicial | PWA com interface responsiva | Instalação pelo navegador nos dispositivos compatíveis |
| Relatórios | Impressão, PDF e CSV | Consulta, conselho de classe e apoio ao preenchimento do sistema escolar |

Python/Django já é a base do backend, com HTML/CSS na interface. O desenvolvimento local utiliza SQLite; a configuração para PostgreSQL está preparada, mas ainda não foi validada nesse banco. A instalação como PWA é uma evolução prevista e ainda não está implementada. Aplicativo nativo nas lojas não está incluído na entrega atual.

A proposta inicial depende de internet. Caso o uso sem conexão seja essencial, o planejamento deverá incluir armazenamento no aparelho, sincronização, proteção dos dados locais e resolução de conflitos antes da implementação dos registros diários.

## 4. Decisões pendentes

O início foi autorizado. As premissas abaixo permitem avançar na base; confirmar as regras pedagógicas antes de implementar os módulos dependentes delas.

| Decisão | Resposta / situação |
| --- | --- |
| Será usado por um professor ou por vários, com contas separadas? | Base preparada para vários professores, com dados isolados; sem compartilhamento entre contas |
| Qual nível de ensino será atendido? | Pendente |
| É necessário fazer chamada e lançar dados sem internet? | Premissa inicial: uso conectado. Necessidade de offline ainda não informada |
| PWA atende ou é necessário publicar nas lojas de aplicativos? | Direção inicial: web responsiva, depois PWA. Necessidade de lojas ainda não informada |
| Quais períodos letivos serão usados: bimestres, trimestres, semestres ou outros? | Cadastro livre de nome e datas por escola/ano implementado; regras pedagógicas a definir |
| Quais regras de notas, pesos, arredondamento, aprovação e recuperação devem ser atendidas? | Usuário escolheu configuração por turma/disciplina/período. Cálculos e limites implementados em docs/ETAPA4.md; não há decisão oficial de aprovação |
| A frequência será registrada por aula, por dia ou por outro critério? | Confirmada pelo usuário: por aula, com várias aulas no encontro e faltas parciais |
| Quais informações e formatos são necessários para o conselho de classe e o sistema da escola? | Modelo geral aprovado: notas, frequência, pendências e observações por turma/disciplina/período; PDF e CSV. Modelos específicos e integração com a escola não informados |
| Onde será hospedado e como serão mantidos e restaurados os backups? | Definir antes da implantação |

## 5. Escopo proposto para a primeira versão

### Acesso e organização

- Login e recuperação de senha.
- Separação dos dados de cada professor, se houver múltiplas contas.
- Cadastro de escolas, anos letivos, períodos, turmas e disciplinas.
- Cadastro de alunos e matrícula nas turmas.
- Registro da situação da matrícula, preservando o histórico do aluno.

### Rotina de aulas

- Registro de data, quantidade de aulas, conteúdo ministrado e observações.
- Chamada, faltas e justificativas conforme a regra de frequência aprovada.
- Consulta dos registros por turma, disciplina e período.

### Avaliações e acompanhamento

- Cadastro de provas, trabalhos e atividades com datas, valores e pesos.
- Situação de entrega e pendências.
- Lançamento de notas e cálculo das médias conforme regras aprovadas.
- Distinção entre nota zero, nota não lançada e atividade não entregue.
- Observações pedagógicas por aluno.
- Histórico de alterações relevantes, com data e autoria, para notas e frequência.

### Relatórios

- Resumo individual do aluno e visão da turma.
- Desempenho, frequência, atividades pendentes e observações para conselho de classe.
- Filtros por escola, ano, turma, disciplina e período, conforme a tela.
- Impressão e exportação em PDF e CSV.
- Apoio à transferência manual das informações para o sistema escolar.

## 6. Etapas e critérios de conclusão

As caixas abaixo registram conclusão, não apenas início. Atualizar este documento ao encerrar cada etapa.

### Etapa 0 — Aprovar o planejamento

- [x] Registrar o plano e as decisões pendentes neste documento.
- [ ] Responder às perguntas essenciais de uso, ensino, conexão e formato do aplicativo.
- [x] Confirmar o escopo inicial para começar a base, com premissas registradas.
- [x] Registrar a aprovação explícita do usuário.

**Situação:** início autorizado. Perguntas ainda sem resposta permanecem registradas; não impedem a base, mas devem orientar os módulos seguintes.

### Etapa 1 — Definir regras, dados e telas

- [ ] Detalhar períodos letivos, avaliação, recuperação e frequência.
- [x] Definir os vínculos entre professor, escola, turma, disciplina, aluno e matrícula.
- [x] Definir o tratamento de transferências e mudança de ano letivo sem perda de histórico.
- [x] Criar as telas principais da base para uso no celular e no computador.
- [ ] Validar exemplos fictícios de chamada, lançamento de notas e conselho.

**Critério de conclusão:** regras documentadas e fluxo de telas revisado pelo usuário.

### Etapa 2 — Preparar a base do sistema

- [x] Verificar o ambiente virtual e o repositório existentes antes de alterá-los.
- [x] Criar a estrutura Django e registrar as dependências.
- [x] Configurar ambiente de desenvolvimento, banco e variáveis de ambiente.
- [x] Evitar o versionamento de segredos e arquivos locais desnecessários.
- [x] Implementar autenticação e permissões por professor.
- [x] Implementar escolas, anos, períodos, turmas, disciplinas, alunos e matrículas.
- [x] Documentar como instalar e iniciar o projeto localmente.

**Critério de conclusão:** aplicação inicia seguindo a documentação e os cadastros respeitam as permissões definidas.

### Etapa 3 — Implementar aulas, conteúdos e frequência

- [x] Criar registro e edição de aulas e conteúdos.
- [x] Implementar chamada e justificativas.
- [x] Calcular os totais de frequência conforme a frequência por aula confirmada.
- [x] Permitir consulta e correção dos registros com histórico das alterações relevantes.
- [x] Validar o fluxo de chamada no celular com dados fictícios.

**Critério de conclusão:** o professor consegue registrar e consultar uma aula completa; correções não duplicam ou distorcem os totais.

**Entrega:** registro por turma/disciplina/data, quantidade de aulas, faltas parciais e justificativas; consultas por turma, disciplina, período e datas; datas de entrada/saída das matrículas; cancelamento sem exclusão e histórico com autor, motivo e valores anteriores/novos. Chamadas pendentes não contam como presença. Justificativas não abonam faltas automaticamente. Detalhes em docs/ETAPA3.md.

### Etapa 4 — Implementar avaliações e notas

- [x] Criar provas, trabalhos e atividades.
- [x] Registrar entregas e pendências.
- [x] Implementar lançamento e edição de notas.
- [x] Implementar médias, pesos, arredondamentos e recuperação aprovados.
- [x] Testar cálculos com exemplos conhecidos e situações de notas ausentes.

**Critério de conclusão:** resultados conferem com os exemplos aprovados e situações diferentes de avaliação permanecem identificáveis.

**Entrega:** cadernos por turma/disciplina/período, média simples/ponderada/soma de pontos, escala e referência configuráveis, arredondamento/truncamento, quatro opções de recuperação, entregas/pendências/dispensas, observações e auditoria. Exemplos numéricos documentados e testados; revisão do professor com as regras reais da escola ainda integra a validação de uso. Detalhes em docs/ETAPA4.md.

### Etapa 5 — Implementar relatórios e conselho de classe

- [x] Criar visão da turma e ficha individual do aluno.
- [x] Reunir notas, frequência, pendências e observações pedagógicas.
- [x] Implementar filtros, impressão e exportações previstas.
- [x] Conferir os relatórios com os registros de origem.
- [x] Revisar a legibilidade dos arquivos exportados e da impressão.

**Critério de conclusão:** relatórios consistentes e utilizáveis para conselho e preenchimento do sistema escolar.

**Entrega:** visão da turma por disciplina e ficha individual por matrícula/período; notas e frequência usam os mesmos cálculos das Etapas 3/4. Observações consolidadas de avaliações e justificativas de frequência. PDF paginado, CSV protegido contra fórmulas e versão de impressão; dados fictícios verificados no navegador e PDFs renderizados. Impressora física não validada. Detalhes em docs/ETAPA5.md.

### Etapa 6 — Finalizar a experiência no celular

A adaptação das telas ao celular deve ocorrer desde a Etapa 1; esta etapa consolida e verifica a experiência.

- [ ] Revisar navegação, formulários, tabelas e botões em telas pequenas.
- [ ] Configurar os recursos de instalação como PWA, se aprovada.
- [ ] Deixar claro quando um registro foi salvo ou quando ocorreu falha de conexão.
- [ ] Validar a instalação e o uso nos dispositivos e navegadores definidos para o projeto.
- [ ] Caso o uso offline tenha sido aprovado, validar sincronização, conflitos e ausência de perda ou duplicação de dados.

**Critério de conclusão:** fluxos principais funcionam nos celulares definidos, respeitando o modo de conexão aprovado.

### Etapa 7 — Validar e disponibilizar

- [ ] Testar as regras críticas de notas, frequência e relatórios.
- [ ] Verificar permissões e isolamento entre contas, quando aplicável.
- [ ] Executar um ciclo completo com dados fictícios: cadastros, aulas, chamada, avaliações e conselho.
- [ ] Corrigir falhas identificadas na validação com o usuário.
- [ ] Preparar hospedagem, HTTPS e configuração de produção.
- [ ] Configurar backups e verificar a restauração.
- [ ] Documentar operação, atualização e recuperação do sistema.
- [ ] Apresentar a versão validada para autorização de disponibilização.

**Critério de conclusão:** versão validada, restauração verificada e disponibilização autorizada pelo usuário.

## 7. Funcionalidades reservadas para evolução

Não incluir automaticamente na primeira versão:

- Acesso de alunos e responsáveis.
- Mensagens e notificações externas.
- Anexos de trabalhos e materiais.
- Integração automática com sistemas escolares, dependente dos recursos de cada sistema.
- Aplicativos nativos publicados nas lojas.
- Uso offline, se não for definido como requisito inicial.

## 8. Como retomar o trabalho

1. Ler este documento antes de iniciar uma nova sessão de desenvolvimento.
2. Conferir as decisões aprovadas, a etapa atual e a próxima ação registrada abaixo.
3. Inspecionar o estado real dos arquivos e do Git para preservar trabalho existente.
4. Executar a próxima atividade autorizada da etapa atual.
5. Fazer verificações proporcionais à mudança, com foco nas regras e nos riscos relevantes.
6. Atualizar as caixas de conclusão e registrar alterações, validações, pendências e próximo passo.
7. Registrar mudanças de escopo explicitamente, sem tratar propostas como decisões aprovadas.
8. Ao concluir cada etapa, atualizar a documentação, executar as validações e salvar as alterações em um commit.
9. Enviar o commit ao repositório GitHub configurado e verificar a sincronização.
10. Perguntar ao usuário se deve iniciar a próxima etapa e aguardar sua resposta. Não iniciar automaticamente outra etapa.

## 9. Ponto de continuidade

**Etapa atual:** Etapa 5 concluída; próxima entrega é a Etapa 6.

**Última entrega:** relatórios de turma e aluno para conselho, reunindo notas, frequência, pendências e observações; PDF, CSV e impressão.

**Próxima ação:** perguntar se o usuário autoriza a Etapa 6 (experiência no celular/PWA). Após autorização, confirmar dispositivos, instalação e necessidade de offline antes dos recursos dependentes dessas decisões.

**Autorização:** Etapa 5 autorizada e concluída. Salvar no Git/GitHub e perguntar antes de avançar. A Etapa 6 depende de nova confirmação. Disponibilização pública não realizada.
**Implementação:** Python 3.14.7, Django 5.2.18, SQLite local e configuração futura para PostgreSQL.  
**Testes da aplicação:** 128 testes automatizados aprovados (25 novos de relatórios/exportações). Fluxos das etapas anteriores preservados. Relatórios, ficha individual e downloads verificados no navegador; PDFs de turma/aluno renderizados e inspecionados. Ficha conferida em janela de 390 × 844 pixels, sem transbordamento horizontal da página; tabelas com rolagem própria.

**Limitações atuais:** sem instalação PWA/offline; e-mail de recuperação apenas no terminal por padrão; PostgreSQL, SMTP real e produção não validados. Sem impressão física validada, ata de conselho, integração automática ou modelos específicos de escolas. Notas não decidem aprovação oficial; recuperação limitada às opções em docs/ETAPA4.md.

**Como executar:** consultar README.md e aplicar as migrações. Não há conta ou senha padrão. Matrículas antigas permanecem preservadas; revisar datas de entrada e saída. Dados fictícios de verificação usam banco temporário separado.

### Registro de sessões

| Data | Trabalho realizado | Validação / resultado | Próximo passo |
| --- | --- | --- | --- |
| 19/10/2026 | Criação do plano, etapas, critérios de conclusão e roteiro de continuidade | Documento registrado; desenvolvimento não iniciado | Resolver decisões essenciais e aprovar o plano |
| 19/10/2026 | Início autorizado; entrega da base Django, interface responsiva, autenticação, cadastros e isolamento de dados | 26 testes aprovados e verificação visual de computador/celular | Etapa 3: aulas, conteúdos e frequência |
| 19/10/2026 | Etapa 3: aulas, conteúdos, chamada por aula, justificativas, consultas e histórico; continuidade condicionada a autorização por etapa | 64 testes aprovados e fluxo de chamada validado em computador/celular | Salvar no Git/GitHub e solicitar autorização para a Etapa 4 |
| 19/10/2026 | Etapa 4 autorizada: cadernos, avaliações, entregas, notas e recuperação configuráveis; auditoria e proteção contra sobrescrita | 103 testes aprovados; criação e lançamento no navegador com dados fictícios e tamanho de celular | Salvar no Git/GitHub e solicitar autorização para a Etapa 5 |
| 20/10/2026 | Etapa 5: relatórios de conselho e ficha individual, filtros e exportação PDF/CSV/impressão | 128 testes aprovados; downloads verificados, PDFs renderizados e ficha conferida no celular simulado | Salvar no Git/GitHub e solicitar autorização para a Etapa 6 |

### Decisões aprovadas

| Data | Decisão | Origem |
| --- | --- | --- |
| 19/10/2026 | Utilizar Python e atender computador e celular | Solicitação inicial do usuário |
| 19/10/2026 | Documentar o planejamento antes de implementar | Solicitações do usuário |
| 19/10/2026 | Autorizar o início e a execução do projeto | “Agora pode iniciar o projeto, pode execultar.” |
| 19/10/2026 | Trabalhar uma etapa por vez, salvar no Git e GitHub e perguntar antes da seguinte | Solicitação explícita do usuário |
| 19/10/2026 | Frequência por aula, com múltiplas aulas no encontro e faltas parciais | Resposta “Sim, frequência por aula (recomendado)” |
| 19/10/2026 | Executar a Etapa 4; regras de notas configuráveis por turma, disciplina e período | “sim, pode. etapa 4.” e resposta à pergunta sobre regras |
| 20/10/2026 | Executar a Etapa 5 e utilizar modelo geral de relatório com PDF e CSV | “pode iniciar 5 etapa” e “Sim, usar esse modelo geral” |

Django, SQLite local, preparação para PostgreSQL, contas isoladas e uso conectado foram adotados como decisões iniciais de implementação dentro da autorização para começar. PWA é uma etapa futura. Detalhes e limitações estão em docs/ARQUITETURA.md.
