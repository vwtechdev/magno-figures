# Magno Figures

Sistema web para a Magno-Figures: catálogo de action figures em uma vitrine online, com carrinho e checkout iniciado direto pelo WhatsApp.

## Stack

- Django 6.1 · Python 3.12+
- django-jazzmin (admin) · django-mptt (categorias) · django-modeltranslation
- SQLite (dev) / PostgreSQL + Redis (produção, via Docker Compose + Traefik)
- Frete: API SuperFrete (sandbox/produção)

## Funcionalidades

- Catálogo com busca, categorias hierárquicas e paginação
- Carrinho (sessão/usuário) e checkout atômico → mensagem pré-formatada no WhatsApp
- Cálculo de frete por CEP (SuperFrete, PAC/SEDEX) com destino exibido
- SEO: Open Graph/Twitter Cards, canonical, JSON-LD (WebSite/Product/Breadcrumb), `sitemap.xml` e `robots.txt`
- Emails em background (thread daemon) para notificação de pedido e reset de senha

## Desenvolvimento

```bash
# requirements-dev.txt é local-only (gitignored)
pip install -r requirements-dev.txt

python manage.py migrate --settings=core.settings_dev
python manage.py runserver --settings=core.settings_dev
```

Testes: `python manage.py test --settings=core.settings_dev apps`

Configuração via `.env` (não versionado, gerenciado pelo usuário) — veja `.env-example`.

## Deploy

```bash
sh scripts/deploy.sh
# docker compose up -d --build, migrate, collectstatic
```

VPS com Docker Compose + Traefik (nginx + gunicorn, PostgreSQL + Redis).