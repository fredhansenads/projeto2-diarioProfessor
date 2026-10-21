# Implantação — Diário do Professor / Locaweb

Atualizado em 21/10/2026. Destino informado pelo proprietário: **Hospedagem de Sites compartilhada**, subdomínio **diarioprofessor.santustech.com.br**.

**Situação:** preparação e testes locais realizados. Não houve acesso à conta da Locaweb, alteração de DNS, envio de arquivos, contratação, abertura de chamado ou publicação. A compatibilidade do plano compartilhado ainda não foi confirmada. Não basta enviar os arquivos Python por FTP.

## Confirmação necessária do provedor

A documentação pública consultada da Locaweb descreve bancos PostgreSQL na Hospedagem de Sites, mas não confirma a versão de Python e o mecanismo WSGI disponíveis no plano contratado. A página de VPS descreve um ambiente administrável; isso é outro produto, não prova compatibilidade da hospedagem compartilhada. Não foi decidido nem contratado upgrade.

Texto pronto para o proprietário enviar ao suporte:

> Tenho Hospedagem de Sites compartilhada na Locaweb e quero executar uma aplicação Django em diarioprofessor.santustech.com.br. A versão validada usa Python 3.14, Django 5.2, PostgreSQL e dependências instaladas por pip em ambiente virtual. O plano permite essa versão de Python e uma aplicação WSGI persistente (Passenger, mod_wsgi ou processo supervisionado)? Qual é a versão do PostgreSQL, o limite de conexões e a disponibilidade de TLS e de pg_dump/pg_restore? Posso executar comandos de migração, collectstatic e tarefas agendadas por SSH? Como configurar variáveis secretas fora do diretório público, HTTPS do subdomínio, reinício da aplicação e logs? Há SMTP autenticado com TLS e backups restauráveis? Se Python 3.14 não estiver disponível, informem as versões suportadas para avaliarmos e testarmos a compatibilidade antes de alterar o projeto.

Não compartilhar senhas ou chaves na conversa. A resposta técnica do suporte deve orientar os arquivos específicos do servidor. Se o plano não oferecer os recursos, apresentar alternativas ao proprietário antes de qualquer mudança contratual. Não usar um banco do plano compartilhado a partir de outro provedor sem confirmar as regras contratuais e de acesso.

## Preparação disponível

- `deploy/production.env.example`: modelo sem segredos, com o subdomínio informado, PostgreSQL, SMTP e cadastro público desligado.
- `config/wsgi.py`: entrada WSGI para integração oferecida pela hospedagem.
- `serve.py`: Waitress para ambientes que permitem processo persistente. Usa **127.0.0.1:8000** por padrão. Não é uma solução para contornar restrições do plano compartilhado.
- WhiteNoise fornece os arquivos coletados, comprimidos e identificados pelo conteúdo, inclusive os do administrador. O app pressupõe publicação na raiz do subdomínio.
- `/saude/`: testa comunicação com o banco e retorna apenas `ok` ou `unavailable`, sem detalhes internos e sem cache. Não verifica SMTP, migrações, espaço em disco ou integridade do backup.
- `manage.py check --deploy --fail-level WARNING`: bloqueia configurações essenciais incompletas; não comprova conectividade externa.

## Sequência no ambiente confirmado

Comandos abaixo são um roteiro para execução no ambiente correto, não ações já executadas na Locaweb. Usar primeiro uma instalação de homologação com dados fictícios e acesso restrito.

1. Definir diretório privado do projeto, serviço WSGI, proxy/HTTPS e banco PostgreSQL suportado pelo Django. Usar uma conta de banco dedicada, sem superusuário, com permissões necessárias apenas para o banco do diário. O PostgreSQL 18 foi validado localmente; outra versão precisa ser conferida com o Django e testada.
2. Criar um ambiente Python, instalar `requirements-production.txt` e configurar as variáveis do modelo. Não copiar banco local, `.env`, `.local-secret`, backups ou dados de teste para o diretório público.
3. Gerar uma chave exclusiva de produção e mantê-la no gerenciador de segredos do provedor ou em arquivo privado acessível apenas ao serviço. Nunca versionar ou imprimir essa chave em logs. Preencher banco, remetente autorizado e SMTP. TLS e SSL de e-mail são opções alternativas; não ativar ambos.
4. Validar TLS do banco remoto. O modelo usa `POSTGRES_SSLMODE=verify-full`; obter CA/hostname corretos do provedor e, se preciso, configurar `PGSSLROOTCERT`. Não desativar a verificação para resolver erros de certificado.
5. Executar, com o ambiente de homologação configurado:

```text
python -m pip install -r requirements-production.txt
python manage.py check
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py migrate --check
python manage.py check --deploy --fail-level WARNING
python -m pip check
```

6. Criar a conta administrativa com `python manage.py createsuperuser`, digitando a senha interativamente. Não há credencial padrão. Em `/admin/`, criar as contas de professores, preencher nome e e-mail correto e manter `is_staff` e `is_superuser` desligados para professores. O administrador permanece restrito a pessoas de confiança.
7. Configurar o serviço WSGI. Se o provedor permitir Waitress supervisionado, iniciar `python serve.py` pelo supervisor do host. Quando houver exatamente um proxy reverso confiável, configurar `WAITRESS_TRUSTED_PROXY` com seu **IP exato**. O proxy deve sobrescrever os cabeçalhos de encaminhamento e ser o único acesso ao backend. Testar IP real, URLs HTTPS e ausência de redirecionamento em ciclo. O programa recusa `*`; não habilitar confiança irrestrita em cabeçalhos enviados pela internet.
8. Confirmar DNS, certificado válido e renovação HTTPS do subdomínio com o provedor. Configurar limites de requisições no proxy/serviço da hospedagem, inclusive recuperação de senha, sem impedir acesso normal dos professores da mesma rede. A limitação implementada no aplicativo cobre login de professor e administrador por combinação usuário/IP; não substitui proteção contra ataques distribuídos ou sobrecarga.
9. Testar recuperação de senha com uma conta de homologação e destinatário autorizado, validade do remetente e entrega real. Não usar o backend de console em produção; ele expõe links de recuperação nos logs locais por finalidade de desenvolvimento.
10. Configurar agendamento, armazenamento separado e alertas dos backups conforme `OPERACAO.md`. Restaurar uma cópia no ambiente final e conferir os relatórios. Testar reinício do serviço e persistência do banco.
11. Executar o ciclo pedagógico e a matriz de aparelhos de `ETAPA6.md`. Testar expiração da sessão, conta de outro professor, PDF/CSV, instalação, orientação da tela e perda de conexão.
12. Apresentar evidências e solicitar autorização do proprietário para disponibilizar. O início da Etapa 7 não foi tratado como aprovação de publicação de uma instalação ainda não validada.

## Cuidados específicos desta configuração

Com `DEBUG=False`, cookies de sessão/CSRF exigem HTTPS, HTTP redireciona para HTTPS e HSTS usa uma hora inicialmente. As verificações `security.W005` e `security.W021` foram deliberadamente silenciadas: não ativamos HSTS para possíveis subdomínios abaixo de diarioprofessor.santustech.com.br nem solicitamos preload antes de validar a infraestrutura e a política permanente de HTTPS. Um cabeçalho neste host não impõe HSTS ao domínio pai nem aos sites irmãos. Não há outros avisos silenciados.

Os checks exigem hosts exatos, PostgreSQL, SMTP seguro, remetente e cadastro fechado. Não validam senha do SMTP, autorização do remetente ou disponibilidade de recursos do plano. Há limite de 2 MiB por requisição no Waitress; anexos não fazem parte da versão atual. Reavaliar esse limite se o número de alunos ou campos de uma turma exigir, testando antes de alterar.

## Referências consultadas

- [Locaweb — bancos na Hospedagem de Sites](https://www.locaweb.com.br/ajuda/wiki/como-instalar-um-banco-de-dados-hospedagem-de-sites/).
- [Locaweb — família de produtos Cloud/VPS](https://www.locaweb.com.br/cloud/).
- [Django 5.2 — checklist de implantação](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/).
- [Waitress — proxy reverso](https://docs.pylonsproject.org/projects/waitress/en/stable/reverse-proxy.html).
- [WhiteNoise — integração com Django](https://whitenoise.readthedocs.io/en/stable/django.html).
