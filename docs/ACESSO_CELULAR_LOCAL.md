# Testar pelo celular na mesma rede Wi-Fi

Configurado em **26/10/2026**, sem alterar a VPS. O laboratório continua usando somente dados fictícios.

## Acesso atual

No celular conectado à mesma rede do computador, abra no Chrome ou Safari:

**http://192.168.0.105:18080**

Use `professor.teste` / `Teste-local-2026!` ou crie uma conta de teste na tela de login. O computador precisa permanecer ligado, conectado ao Wi-Fi e com Docker e a demonstração ativos. O endereço pode mudar se o roteador atribuir outro IP.

Este acesso HTTP serve à avaliação local com dados fictícios. Use uma senha exclusiva de teste. Instalação PWA e recursos de service worker em celulares reais dependem de HTTPS; o teste atual é pelo navegador e não conclui essa homologação.

## Como retomar

Com Docker Desktop ativo, execute na raiz do projeto, usando o IPv4 atual do computador:

```powershell
$env:VALIDATION_LAN_IP='192.168.0.105'
docker compose -f deploy/validation/compose.yaml -f deploy/validation/compose.lan.yaml up -d --build
docker compose -f deploy/validation/compose.yaml -f deploy/validation/compose.lan.yaml exec -d lab python -m tools.validation.preview
```

Execute o último comando uma vez por início/recriação do contêiner. A composição adicional mantém o acesso em localhost e acrescenta exclusivamente o IP privado informado. Não publica o banco PostgreSQL. O modo LAN aceita apenas endereços IPv4 das faixas privadas 10/8, 172.16/12 e 192.168/16, limita os hosts aceitos e desativa as páginas de erro de depuração. As exceções necessárias ao HTTP ficam restritas ao processo de demonstração; a configuração de produção continua exigindo HTTPS.

Para parar mantendo os dados, use:

```powershell
docker compose -f deploy/validation/compose.yaml stop
```

Para voltar ao acesso exclusivo deste computador, sem apagar o volume:

```powershell
docker compose -f deploy/validation/compose.yaml up -d
docker compose -f deploy/validation/compose.yaml exec -d lab python -m tools.validation.preview
```

## Se não abrir no celular

1. Conferir que o celular está no mesmo Wi-Fi, sem usar uma rede de convidados que isole os dispositivos.
2. Conferir o IPv4 do computador com `ipconfig` e ajustar a variável acima caso tenha mudado.
3. Conferir que Docker e demonstração estão ativos e que o computador não entrou em suspensão.
4. Conferir o firewall. Nesta máquina, a rede Wi-Fi é privada e já existe uma regra TCP do Docker Desktop que inclui redes privadas. A tentativa de criar uma regra específica não teve permissão de administrador; nenhuma regra foi criada ou modificada. Não é necessário desativar o firewall nem abrir portas no roteador.

## Verificação realizada

Pelo IP Wi-Fi, a partir do próprio computador, foram conferidos: página de login HTTP 200, CSS, login com CSRF e Origin, painel autenticado, relatório e recusa de Host não autorizado. O banco de demonstração foi preservado. O acesso a partir de um celular físico ainda precisa ser confirmado pelo proprietário; a verificação no computador não comprova comunicação entre dispositivos nem ausência de isolamento no roteador.
