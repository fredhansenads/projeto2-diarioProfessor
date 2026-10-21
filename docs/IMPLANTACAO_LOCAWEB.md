# Implantação — Diário do Professor / Locaweb

Atualizado em 21/10/2026. Destino escolhido pelo proprietário: **VPS já existente na Locaweb**, subdomínio **diarioprofessor.santustech.com.br**.

**Situação:** preparação e testes locais realizados; implantação na VPS ainda não executada. O proprietário informou que a Hospedagem Compartilhada Linux GO não oferece suporte a Python/Django e decidiu utilizar sua VPS. A confirmação de compatibilidade do GO deixou de ser uma pendência. Não houve acesso à VPS, alteração de DNS, envio de arquivos ou publicação.

## Identificação da VPS antes da configuração

Informações fornecidas pelo proprietário: **Ubuntu (versão ainda não informada), 1 GB de RAM, 2 vCPUs e disco de 40 GB**. A VPS já executa outro sistema Python semelhante, descrito como leve. Esses números são a capacidade informada, não uma medição de recursos livres.

Antes de instalar, conferir versão do Ubuntu, RAM disponível, swap, espaço livre, portas ocupadas, banco/proxy e como o sistema existente é iniciado. A capacidade para os dois sistemas precisa ser medida; ainda não foi validada. Preservar os ambientes virtuais, dependências, banco e serviço da aplicação existente. Evitar atualização global do Python ou substituição das configurações do proxy durante a instalação do diário.

Solicitado ao proprietário: IP/hostname, usuário e porta SSH, e se há chave de acesso já configurada neste computador; alternativamente, ele pode executar a consulta no próprio terminal. Não enviar senhas nem conteúdo de chaves na conversa. O destino e o método de acesso ainda não foram informados.

### Consulta inicial sem alterações

O arquivo `deploy/inspecionar-vps.sh` consulta sistema, CPU, memória/swap, disco, processos por consumo de RAM (sem argumentos), versões disponíveis no PATH, portas TCP e nomes/estados dos serviços ativos. Não instala pacotes, reinicia serviços ou lê arquivos de configuração da aplicação, variáveis de ambiente, logs e credenciais. Não requer sudo.

Com o arquivo disponível na VPS, executar pelo terminal Ubuntu:

```bash
bash deploy/inspecionar-vps.sh
```

Conferir a saída antes de compartilhá-la. Um programa ausente no PATH pode existir em ambiente virtual ou contêiner; será necessário identificar o serviço Python existente após essa primeira consulta. O script teve a sintaxe Bash verificada localmente, mas ainda não foi executado na VPS. Confirmar também o responsável pelo DNS do subdomínio e pelo SMTP.

## Roteiro da implantação na VPS

1. Inventariar o ambiente e preservar a configuração dos serviços existentes antes de qualquer mudança. Confirmar recursos disponíveis e permissões administrativas.
2. Definir a execução da aplicação conforme o ambiente: aproveitar a infraestrutura existente quando adequada. A escolha entre serviço do sistema e contêiner fica pendente desse inventário.
3. Preparar usuário/diretório próprios da aplicação, Python e dependências fixadas, PostgreSQL e armazenamento persistente. A versão Python 3.14.7 e o PostgreSQL 18 foram validados localmente; conferir disponibilidade e testar qualquer mudança de versão.
4. Integrar o diário ao proxy HTTPS no subdomínio, escolhendo uma porta interna livre e mantendo aplicação e banco sem exposição pública direta. Definir a confiança do proxy conforme a topologia real.
5. Configurar SMTP, backup agendado, cópia externa e recuperação; verificar os serviços com dados fictícios antes de migrar dados reais.
6. Executar a sequência de homologação abaixo e a validação em aparelhos reais. Apresentar os resultados ao proprietário para autorização final de disponibilização.

Os comandos específicos de instalação, serviço, firewall e proxy serão preparados após identificar o ambiente. A troca de destino mantém Python/Django e PostgreSQL; não exige reescrever o sistema. Nenhum novo serviço foi contratado.

## Preparação disponível

- `deploy/production.env.example`: modelo sem segredos, com o subdomínio informado, PostgreSQL, SMTP e cadastro público desligado.
- `config/wsgi.py`: entrada WSGI da aplicação.
- `serve.py`: Waitress para ambientes que permitem processo persistente. Usa **127.0.0.1:8000** por padrão. A porta definitiva depende dos serviços existentes na VPS.
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
7. Configurar o serviço WSGI. Se o inventário definir execução direta com Waitress supervisionado, iniciar `python serve.py` pelo supervisor do host. Quando houver exatamente um proxy reverso confiável, configurar `WAITRESS_TRUSTED_PROXY` com seu **IP exato**. O proxy deve sobrescrever os cabeçalhos de encaminhamento e ser o único acesso ao backend. Testar IP real, URLs HTTPS e ausência de redirecionamento em ciclo. O programa recusa `*`; não habilitar confiança irrestrita em cabeçalhos enviados pela internet.
8. Confirmar DNS, certificado válido e renovação HTTPS do subdomínio no ambiente escolhido. Configurar limites de requisições no proxy/serviço da hospedagem, inclusive recuperação de senha, sem impedir acesso normal dos professores da mesma rede. A limitação implementada no aplicativo cobre login de professor e administrador por combinação usuário/IP; não substitui proteção contra ataques distribuídos ou sobrecarga.
9. Testar recuperação de senha com uma conta de homologação e destinatário autorizado, validade do remetente e entrega real. Não usar o backend de console em produção; ele expõe links de recuperação nos logs locais por finalidade de desenvolvimento.
10. Configurar agendamento, armazenamento separado e alertas dos backups conforme `OPERACAO.md`. Restaurar uma cópia no ambiente final e conferir os relatórios. Testar reinício do serviço e persistência do banco.
11. Executar o ciclo pedagógico e a matriz de aparelhos de `ETAPA6.md`. Testar expiração da sessão, conta de outro professor, PDF/CSV, instalação, orientação da tela e perda de conexão.
12. Apresentar evidências e solicitar autorização do proprietário para disponibilizar. O início da Etapa 7 não foi tratado como aprovação de publicação de uma instalação ainda não validada.

## Cuidados específicos desta configuração

Com `DEBUG=False`, cookies de sessão/CSRF exigem HTTPS, HTTP redireciona para HTTPS e HSTS usa uma hora inicialmente. As verificações `security.W005` e `security.W021` foram deliberadamente silenciadas: não ativamos HSTS para possíveis subdomínios abaixo de diarioprofessor.santustech.com.br nem solicitamos preload antes de validar a infraestrutura e a política permanente de HTTPS. Um cabeçalho neste host não impõe HSTS ao domínio pai nem aos sites irmãos. Não há outros avisos silenciados.

Os checks exigem hosts exatos, PostgreSQL, SMTP seguro, remetente e cadastro fechado. Não validam senha do SMTP, autorização do remetente ou disponibilidade de recursos do plano. Há limite de 2 MiB por requisição no Waitress; anexos não fazem parte da versão atual. Reavaliar esse limite se o número de alunos ou campos de uma turma exigir, testando antes de alterar.

## Referências consultadas

- [Locaweb — família de produtos Cloud/VPS](https://www.locaweb.com.br/cloud/).
- [Django 5.2 — checklist de implantação](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/).
- [Waitress — proxy reverso](https://docs.pylonsproject.org/projects/waitress/en/stable/reverse-proxy.html).
- [WhiteNoise — integração com Django](https://whitenoise.readthedocs.io/en/stable/django.html).
