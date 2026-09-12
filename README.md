# Magno Figures

Sistema web para a Magno-Figures: catálogo de action figures em uma vitrine online, com carrinho e checkout iniciado direto pelo WhatsApp.

## Stack

- Django 6.1 · Python 3.12+
- django-jazzmin (admin) · django-mptt (categorias) · django-modeltranslation
- SQLite (dev) / PostgreSQL + Redis (produção, via Docker Compose + Traefik)
- Frete: API SuperFrete (sandbox/produção)

## Funcionalidades

- Catálogo com busca, filtros (categoria, preço, ofertas, lançamentos), ordenação e paginação
- Home com vitrines Lançamentos (flag manual por peça), Catálogo e Promoções
- Carrinho (sessão/usuário) e checkout atômico → mensagem pré-formatada no WhatsApp
- Cálculo de frete por CEP (SuperFrete) com CEP persistido em cookie e cotações em cache
- Auth com verificação de email, reCAPTCHA v2 e rate limiting no nginx
- Aviso de cookies (aceitar/recusar, GA só com consentimento) — textos de política/termos/sobre via admin (LGPD)
- SEO via admin (título, descrição, redes): Open Graph/Twitter Cards, canonical, JSON-LD, `sitemap.xml` e `robots.txt`
- Emails em background (thread daemon) para notificação de pedido e reset de senha

## Configuração

As variáveis de ambiente são gerenciadas pelo usuário via `.env` (não versionado) — veja `.env-example` para a referência.

## Deploy

```bash
sh deploy.sh
# docker compose up -d --build, migrate, collectstatic
```

VPS com Docker Compose + Traefik (nginx + gunicorn, PostgreSQL + Redis).

---

## Desenvolvido por

VWTech Dev | Soluções em Tecnologia
