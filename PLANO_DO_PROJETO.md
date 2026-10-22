# Plano do projeto — Diário do Professor

Criado em: 19/10/2026  
Última atualização: 21/10/2026
Status: Etapa 7 autorizada e em andamento; preparação e validação locais entregues. Hospedagem, serviços externos e homologação física pendentes.

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
- A Etapa 6 acrescenta recursos de instalação como PWA e melhorias no celular; usuário confirmou Android/iPhone e internet obrigatória.
- A Etapa 7 acrescenta contas somente pelo administrador, proteção de login, configuração de produção, backup/restauração e validação local com PostgreSQL. A disponibilização pública permanece pendente.
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

Python/Django já é a base do backend, com HTML/CSS na interface. O desenvolvimento local utiliza SQLite; a suíte e os procedimentos de backup/restauração também foram validados em PostgreSQL 18 local. O banco da hospedagem ainda não foi provisionado. Os recursos de instalação como PWA estão implementados; homologação em aparelhos reais e HTTPS permanecem pendentes. Aplicativo nativo nas lojas não está incluído na entrega atual.

O usuário aprovou internet obrigatória nesta versão. Uma eventual versão offline exigirá nova definição de armazenamento no aparelho, sincronização, proteção dos dados locais e resolução de conflitos.

## 4. Decisões pendentes

O início foi autorizado. As premissas abaixo permitem avançar na base; confirmar as regras pedagógicas antes de implementar os módulos dependentes delas.

| Decisão | Resposta / situação |
| --- | --- |
| Será usado por um professor ou por vários, com contas separadas? | Base preparada para vários professores, com dados isolados; sem compartilhamento entre contas |
| Qual nível de ensino será atendido? | Pendente |
| É necessário fazer chamada e lançar dados sem internet? | Confirmado: exigir internet nesta versão, inclusive para consultar e salvar |
| PWA atende ou é necessário publicar nas lojas de aplicativos? | Etapa de PWA autorizada para Android e iPhone; necessidade de lojas ainda não informada |
| Quais períodos letivos serão usados: bimestres, trimestres, semestres ou outros? | Cadastro livre de nome e datas por escola/ano implementado; regras pedagógicas a definir |
| Quais regras de notas, pesos, arredondamento, aprovação e recuperação devem ser atendidas? | Usuário escolheu configuração por turma/disciplina/período. Cálculos e limites implementados em docs/ETAPA4.md; não há decisão oficial de aprovação |
| A frequência será registrada por aula, por dia ou por outro critério? | Confirmada pelo usuário: por aula, com várias aulas no encontro e faltas parciais |
| Quais informações e formatos são necessários para o conselho de classe e o sistema da escola? | Modelo geral aprovado: notas, frequência, pendências e observações por turma/disciplina/período; PDF e CSV. Modelos específicos e integração com a escola não informados |
| Onde será hospedado e como serão mantidos e restaurados os backups? | VPS existente na Locaweb; diarioprofessor.santustech.com.br. Ubuntu 24.04.4, 1 GB RAM, 2 vCPUs e 40 GB de disco; PostgreSQL 16.15, Nginx e dois sistemas existentes. Medidos 307 MiB RAM disponíveis; capacidade conjunta ainda não validada. Execução pelo terminal do proprietário. GO descartado pelo proprietário por falta de suporte a Python/Django. Backup/restauração local validados; agendamento e armazenamento externo pendentes |
| Quem cria as contas? | Confirmado: somente o administrador |

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

- [x] Revisar navegação, formulários, tabelas e botões em telas pequenas.
- [x] Configurar os recursos de instalação como PWA, se aprovada.
- [x] Deixar claro quando um registro foi salvo ou quando ocorreu falha de conexão.
- [ ] Validar a instalação e o uso nos dispositivos e navegadores definidos para o projeto.
- Não aplicável: uso offline não solicitado; usuário escolheu exigir internet nesta versão. Não há sincronização nem fila de gravações.

**Critério de conclusão:** fluxos principais funcionam nos celulares definidos, respeitando o modo de conexão aprovado.

**Entrega local:** manifesto, ícones, instruções de instalação, ajustes de toque/tabelas e avisos de formulário/conexão. 135 testes Django e 12 testes JavaScript aprovados. Login, chamada e notas salvas no navegador em tamanhos de celular; queda real do servidor exibiu a página pública de conexão. **Critério físico ainda pendente:** instalar e homologar em Android/Chrome e iPhone/Safari reais com HTTPS, conforme docs/ETAPA6.md. Manter essa pendência na validação da Etapa 7, se autorizada; não considerar o sistema pronto para produção.

### Etapa 7 — Validar e disponibilizar

- [x] Testar as regras críticas de notas, frequência e relatórios.
- [x] Verificar permissões e isolamento entre contas, quando aplicável.
- [x] Executar um ciclo completo com dados fictícios: cadastros, aulas, chamada, avaliações e conselho.
- [x] Validar localmente Python 3.12/PostgreSQL 16, HTTPS/SMTP locais, restauração e consultas simultâneas; preparar demonstração fictícia para avaliação.
- [ ] Concluir a homologação física da Etapa 6 em Android/Chrome e iPhone/Safari com HTTPS.
- [ ] Corrigir falhas identificadas na validação com o usuário.
- [ ] Preparar hospedagem, HTTPS e configuração de produção.
- [ ] Configurar backups e verificar a restauração.
- [x] Documentar operação, atualização e recuperação do sistema.
- [ ] Apresentar a versão validada para autorização de disponibilização.

**Critério de conclusão:** versão validada, restauração verificada e disponibilização autorizada pelo usuário.

**Entrega parcial:** 150 testes Django aprovados em SQLite e PostgreSQL 18 local, 12 testes JavaScript aprovados, restauração conferida nos dois bancos, cadastro restrito ao administrador e proteção contra tentativas de login. Modelo de produção e guias de implantação/operação criados. Backup do SQLite existente realizado antes das migrações; contagens de usuários e registros pedagógicos preservadas. Os itens de hospedagem e backups permanecem abertos porque faltam provisionamento, HTTPS, SMTP, agendamento e cópia externa. Ver docs/ETAPA7.md.

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

**Etapa atual:** Etapa 7 em andamento; preparação local validada, sem publicação.

**Última entrega:** laboratório local Ubuntu/Python 3.12.3/PostgreSQL 16.15 com 120 alunos fictícios; ensaios de HTTPS/SMTP, recuperação de senha, restauração e desempenho aprovados. Demonstração em http://localhost:18080 e roteiro em docs/VALIDACAO_LOCAL.md, aguardando avaliação do professor. Contas administradas, proteção de login e guias operacionais já entregues.

**Próxima ação:** proprietário testar a demonstração seguindo docs/VALIDACAO_LOCAL.md; registrar dificuldades e ajustar os fluxos afetados. Preservar seu banco fictício de avaliação. Não preparar nem alterar a VPS enquanto a validação e a aprovação não forem concluídas.

**Autorização:** Etapa 7 autorizada pelo usuário; orientação mais recente: testar primeiro, sem alterar a VPS. A preparação do servidor foi adiada expressamente. VPS existente na Locaweb escolhida e subdomínio mantido; contas somente pelo administrador. Salvar no Git/GitHub e perguntar antes de outra etapa. Disponibilização pública não realizada; aprovação final continua pendente.
**Implementação:** Python 3.14.7 no Windows e 3.12.3 no laboratório Ubuntu, Django 5.2.18, SQLite e PostgreSQL 18/16.15 validados localmente.
**Testes da aplicação:** 150 testes Django aprovados por banco, repetidos em SQLite/PostgreSQL 16 com Python 3.12; 12 JavaScript aprovados. Recuperação por SMTP STARTTLS local, HTTPS com certificado verificado e restauração de 29 tabelas PostgreSQL 16 conferidos. Quatro clientes/72 consultas sem erro; p95 1,65 s e Waitress RSS observado 84,9 MiB. Login, painel e ficha em viewport de celular conferidos no navegador. São dados fictícios; não substituem capacidade na VPS, serviços externos e aparelhos reais. Evidências e limites em docs/VALIDACAO_LOCAL.md e docs/ETAPA7.md.

**Limitações atuais:** avaliação do professor e instalação/uso em Android e iPhone físicos ainda pendentes; sem consulta ou gravação offline. SMTP/HTTPS locais testados, mas entrega externa de e-mail, certificado público e hospedagem não validados. Inventário inicial recebido; configuração e capacidade conjunta da VPS pendentes; PostgreSQL validado somente em ambiente local. Agendamento de backups e cópias externas não configurados. Sem impressão física validada, ata de conselho, integração automática ou modelos específicos de escolas. Notas não decidem aprovação oficial; recuperação limitada às opções em docs/ETAPA4.md.

**Como executar:** consultar README.md e aplicar as migrações. Não há conta ou senha padrão. Matrículas antigas permanecem preservadas; revisar datas de entrada e saída. Dados fictícios de verificação usam banco temporário separado.

### Registro de sessões

| Data | Trabalho realizado | Validação / resultado | Próximo passo |
| --- | --- | --- | --- |
| 19/10/2026 | Criação do plano, etapas, critérios de conclusão e roteiro de continuidade | Documento registrado; desenvolvimento não iniciado | Resolver decisões essenciais e aprovar o plano |
| 19/10/2026 | Início autorizado; entrega da base Django, interface responsiva, autenticação, cadastros e isolamento de dados | 26 testes aprovados e verificação visual de computador/celular | Etapa 3: aulas, conteúdos e frequência |
| 19/10/2026 | Etapa 3: aulas, conteúdos, chamada por aula, justificativas, consultas e histórico; continuidade condicionada a autorização por etapa | 64 testes aprovados e fluxo de chamada validado em computador/celular | Salvar no Git/GitHub e solicitar autorização para a Etapa 4 |
| 19/10/2026 | Etapa 4 autorizada: cadernos, avaliações, entregas, notas e recuperação configuráveis; auditoria e proteção contra sobrescrita | 103 testes aprovados; criação e lançamento no navegador com dados fictícios e tamanho de celular | Salvar no Git/GitHub e solicitar autorização para a Etapa 5 |
| 20/10/2026 | Etapa 5: relatórios de conselho e ficha individual, filtros e exportação PDF/CSV/impressão | 128 testes aprovados; downloads verificados, PDFs renderizados e ficha conferida no celular simulado | Salvar no Git/GitHub e solicitar autorização para a Etapa 6 |
| 20/10/2026 | Etapa 6: PWA conectado, instruções Android/iPhone e revisão mobile | 135 testes Django, 12 JavaScript, salvamentos em telas pequenas e fallback com servidor parado; aparelhos reais pendentes | Salvar no Git/GitHub e solicitar autorização para a Etapa 7, levando a homologação física pendente |
| 21/10/2026 | Etapa 7: preparação local, proteção de acesso, backup/restauração e guias de implantação/operação | 150 testes em cada banco, 12 JavaScript e restauração conferida; serviços externos pendentes | Confirmar compatibilidade com a Locaweb e continuar a Etapa 7 |
| 21/10/2026 | Proprietário confirmou o plano Hospedagem Compartilhada Linux GO; documentação e mensagem ao suporte atualizadas | Proposta pública indica diferença de banco e não confirma Python/WSGI; contrato específico ainda precisa de confirmação | Obter resposta técnica da Locaweb antes da implantação |
| 21/10/2026 | Proprietário informou falta de suporte a Python/Django no GO e escolheu sua VPS da Locaweb; roteiro atualizado | Alteração documental; nenhum acesso remoto ou publicação | Identificar sistema/versão, RAM, serviços existentes e acesso à VPS |
| 21/10/2026 | Proprietário informou Ubuntu, 1 GB RAM, 2 vCPUs, disco de 40 GB e outro sistema Python em uso; consulta somente leitura preparada | Sintaxe Bash conferida; recursos livres e funcionamento na VPS ainda não verificados | Obter acesso identificado ou saída da consulta antes de definir a instalação |
| 21/10/2026 | Inventário recebido: Ubuntu 24.04.4, Python 3.12.3, PostgreSQL 16.15, Nginx/Certbot e dois sistemas em uso; modelos de implantação isolada preparados | Metadados permitem Python 3.12; configuração Waitress e 15 testes operacionais locais conferidos. Binários Linux, carga e implantação pendentes | Executar somente o primeiro bloco de docs/VPS_UBUNTU.md pelo terminal do proprietário |
| 21/10/2026 | Proprietário adiou a VPS; validação local ampliada e demonstração fictícia entregues | Python 3.12/PostgreSQL 16, 150 testes por banco, 12 PWA, HTTPS/SMTP locais, recuperação, 29 tabelas restauradas e 72 consultas simultâneas aprovados | Professor avaliar localhost:18080 conforme docs/VALIDACAO_LOCAL.md; VPS permanece adiada |

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
| 20/10/2026 | Executar a Etapa 6; internet obrigatória nesta versão; atender Android e iPhone | “pode iniciar 6 etapa” e respostas às perguntas sobre conexão e aparelhos |
| 21/10/2026 | Executar a Etapa 7; contas somente pelo administrador; Locaweb Hospedagem Compartilhada Linux GO e diarioprofessor.santustech.com.br | “pode iniciar etapa 7” e respostas às perguntas de implantação |
| 21/10/2026 | Implantar na VPS já existente na Locaweb, mantendo o subdomínio e Python/Django | Escolha explícita do usuário após informar que o GO não suporta Python/Django |
| 21/10/2026 | Validar e testar localmente antes de qualquer preparação da VPS | Usuário pediu subir somente quando pronto/testado e respondeu “pode” à validação sem alterar a VPS |

Django, SQLite local, PostgreSQL e contas isoladas foram adotados como decisões de implementação. O uso conectado foi confirmado pelo usuário e os recursos PWA implementados na Etapa 6. Detalhes e limitações estão em docs/ARQUITETURA.md, docs/ETAPA6.md e docs/ETAPA7.md.
