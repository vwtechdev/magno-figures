# Magno Figures

Loja virtual (vitrine) de action figures: o catálogo é público, o pedido é montado
no carrinho e finalizado pelo **WhatsApp** — não há pagamento online nem gateway de
pagamento. Toda a operação (catálogo, banners, textos institucionais, frete e SEO) é
gerenciada pelo admin do Django.

## Stack

| Camada | Tecnologias |
|---|---|
| Backend | Django 6.1 · Python 3.12+ |
| Admin | django-jazzmin · django-modeltranslation |
| Dados | PostgreSQL 15 · Redis 7 (produção) / SQLite + LocMemCache (dev) |
| Servidor | Gunicorn (2 workers) · nginx · Docker Compose · Traefik (TLS) |
| Frete | API SuperFrete (cotação por CEP, sandbox/produção) |
| E-mail | SMTP (Gmail) com envio assíncrono em pool de threads |
| Frontend | Templates Django + CSS/JS sem framework/build step |

## Estrutura do projeto

```text
magno-figures/
├── apps/                    # apps de domínio (sempre no plural; herdam BaseModel)
│   ├── accounts/            # usuários, login, verificação de e-mail, perfil
│   ├── addresses/           # endereços de entrega por usuário
│   ├── carts/               # carrinho de sessão + carrinho do usuário
│   ├── categories/          # categorias (MPTT) e bloqueio etário/NSFW
│   ├── figures/             # catálogo, imagens, frete por CEP, aviso de estoque
│   ├── newsletters/         # assinantes, campanhas e alertas de disponibilidade
│   ├── orders/              # pedido, checkout, status, rastreio
│   └── website/             # home, páginas institucionais, config do site, SEO
├── core/                    # settings, urls raiz, models base, e-mail, validadores
├── templates/               # templates globais + um diretório por app
├── static/                  # css/js/img (inclui customizações do admin)
├── nginx/                   # proxy + rate limiting de rotas de autenticação
├── docker-compose.yml · Dockerfile · deploy.sh · wait-for-database.sh
└── manage.py · requirements.txt
```

Rotas de topo (`core/urls.py`): `admin/`, `health/`, `robots.txt`, `sitemap.xml` e
os namespaces `website`, `categories`, `figures`, `carts`, `orders`, `addresses`,
`accounts` e `newsletter`.

## Funcionalidades

### Catálogo e vitrine

- Home com banners e três vitrines: **Catálogo** (sem lançamentos e sem promoções),
  **Lançamentos** (flag manual por peça) e **Promoções**.
- Catálogo com busca por nome/descrição, filtro por várias categorias (incluindo
  descendentes), faixa de preço, filtros de ofertas e lançamentos, ordenação
  (A-Z, Z-A, menor/maior preço considerando desconto) e paginação.
- Sidebar de categorias oculta categorias vazias, mas mantém os ancestrais de nós
  com conteúdo. Categorias marcadas como NSFW exigem confirmação de idade na sessão.
- Página da figure com galeria, desconto, disponibilidade, cálculo de frete por CEP
  e assinatura de aviso "avise-me quando chegar".

### Carrinho e checkout

- Carrinho de sessão para visitantes, carrinho persistente por usuário e *merge*
  automático no login. Re-adição incrementa a quantidade; remoção decrementa e
  apaga o item ao chegar em 1.
- Checkout atômico: pedido, itens e limpeza do carrinho na mesma transação; a
  mensagem no WhatsApp (subtotal, frete, total) é aberta só depois do commit.
- Preço do item é congelado no momento do checkout; totais são calculados, nunca
  persistidos.
- Pedidos na área do usuário (lista/detalhe), cancelamento e código de rastreio
  cadastrado no admin — que dispara e-mail de "pedido enviado".

### Conta, endereços e segurança

- Cadastro com verificação de e-mail obrigatória (usuário fica inativo até confirmar)
  e reenvio do link; login por e-mail (modelo de usuário próprio).
- reCAPTCHA v2 (checkbox) em login, cadastro e recuperação de senha; rate limiting
  no nginx por IP real (atrás do Traefik).
- Perfil com abas de dados, troca de senha, endereços, pedidos e exclusão da conta.
- Endereços com CRUD, endereço principal automático (o primeiro vira principal) e
  exclusão com reatribuição de principal.

### Newsletter e avisos

- Inscrição no rodapé (com resposta AJAX) e descadastro por token assinado.
- Alertas de disponibilidade por figure, disparados quando o item volta ao catálogo,
  com descadastro individual.
- Campanhas escritas no admin e enviadas por ação manual para os assinantes ativos.

### Conteúdo, SEO e LGPD

- Configuração do site em singleton no admin: dados da empresa, WhatsApp, CEP de
  origem do frete, cores do tema, textos institucionais (sobre, política, termos),
  SEO, Open Graph e Google Analytics.
- SEO gerado a partir do admin: canonical, Open Graph/Twitter Cards, JSON-LD,
  `sitemap.xml` e `robots.txt` dinâmicos; páginas de autenticação e institucionais
  marcadas como `noindex`.
- Barra de cookies opt-in (aceitar/recusar) que registra a escolha; o GA4 é
  carregado quando configurado no admin.

### Envio de e-mails

- Envio em background (`core/mail.py`) com pool de threads, retry com backoff e
  reutilização de conexão SMTP em lotes.
- Usado para verificação de conta, recuperação de senha, aviso de pedido enviado,
  alertas de disponibilidade e campanhas de newsletter.

## Configuração

As variáveis de ambiente ficam em um `.env` não versionado; `.env.example` serve de
referência com os valores de exemplo de cada grupo.

| Grupo | Chaves |
|---|---|
| Projeto | `COMPOSE_PROJECT_NAME`, `DOMAIN` |
| Django | `SECRET_KEY`, `DEBUG`, `DJANGO_ALLOWED_HOSTS` |
| PostgreSQL | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT` |
| Redis | `REDIS_URL` |
| SuperFrete | `SUPERFRETE_TOKEN`, `SUPERFRETE_SANDBOX`, `SUPERFRETE_USER_AGENT_EMAIL`, `SUPERFRETE_SERVICES` |
| reCAPTCHA v2 | `RECAPTCHA_SITE_KEY`, `RECAPTCHA_SECRET_KEY`, `RECAPTCHA_TIMEOUT` |
| SMTP | `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `EMAIL_TIMEOUT`, `EMAIL_MAX_WORKERS`, `EMAIL_MAX_RETRIES`, `EMAIL_RETRY_DELAY`, `DEFAULT_FROM_EMAIL` |

Observações:

- `SUPERFRETE_SANDBOX=1` usa o ambiente de sandbox; sem token em `DEBUG` o cálculo
  de frete responde com valores de demonstração.
- O backend de e-mail é configurável por `EMAIL_BACKEND` (padrão: SMTP). No Gmail é
  necessário **senha de app** (com 2FA ativado).
- Sem chaves de reCAPTCHA configuradas, a verificação é ignorada (útil em dev/test).
- Após editar o `.env` em produção, recrie o container (`docker compose up -d web`):
  o `env_file` só é lido na criação.

## Deploy

```bash
sh deploy.sh
# docker compose up -d --build → migrate → collectstatic
```

VPS com Docker Compose + Traefik (TLS automático), nginx na frente do Gunicorn e
PostgreSQL + Redis em containers separados. Mídia e logs ficam em volumes no host.

---

## Desenvolvido por

VWTech Dev | Soluções em Tecnologia
