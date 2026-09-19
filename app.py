# Nossa Loja — versão definitiva
# Base validada: cadastro de cliente + pedidos + Mercado Pago + RLS via SUPABASE_SECRET_KEY
# Produtos próprios: Mercado Pago | Amazon/Mercado Livre: checkout externo

import os
from functools import wraps
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse, quote, unquote
import re
import html
import json
import uuid
import hmac
import hashlib
import urllib.request
import urllib.error

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
    g,
)

from supabase import create_client


# ==========================================================
# CONFIGURAÇÃO
# ==========================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "chave-temporaria-trocar-em-producao",
)

SUPABASE_URL = os.environ["SUPABASE_URL"]
# Chave antiga/publicável continua aceita como fallback.
# Para gravações do backend, prefira SUPABASE_SECRET_KEY (sb_secret_...).
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY", "").strip()

# O Flask roda no servidor Render, portanto este cliente pode usar a
# secret key para operações de backend (clientes, pedidos e itens).
# Ela bypassa o RLS e NUNCA deve ser enviada ao navegador.
SUPABASE_BACKEND_KEY = SUPABASE_SECRET_KEY or SUPABASE_KEY

if not SUPABASE_BACKEND_KEY:
    raise RuntimeError(
        "Supabase não configurado: adicione SUPABASE_SECRET_KEY no Render "
        "(recomendado) ou SUPABASE_KEY como fallback."
    )

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_BACKEND_KEY,
)

ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin")

# Mercado Pago — credencial somente no backend/Render.
MERCADOPAGO_ACCESS_TOKEN = os.environ.get("MERCADOPAGO_ACCESS_TOKEN", "").strip()
MERCADOPAGO_PERMITIR_AFILIADOS = os.environ.get("MERCADOPAGO_PERMITIR_AFILIADOS", "false").lower() in ("1", "true", "sim", "yes")
MERCADOPAGO_WEBHOOK_SECRET = os.environ.get("MERCADOPAGO_WEBHOOK_SECRET", "").strip()


# ==========================================================
# ESTILO DO PAINEL
# ----------------------------------------------------------
# O CSS abaixo é aplicado pelo próprio app.py somente nas
# páginas administrativas. Assim, não é necessário alterar
# templates/admin.html ou templates/produto_form.html.
# ==========================================================

PAINEL_STYLE = r"""
<style id="nossa-loja-painel-style">
:root {
    --nl-bg: #f3f5f8;
    --nl-card: rgba(255,255,255,.96);
    --nl-dark: #111827;
    --nl-dark-2: #1b2537;
    --nl-text: #182230;
    --nl-muted: #697586;
    --nl-border: #e5e9ef;
    --nl-shadow: 0 12px 30px rgba(17,24,39,.09);
    --nl-shadow-hover: 0 16px 34px rgba(17,24,39,.14);
    --nl-radius: 20px;
}

body {
    background:
        radial-gradient(circle at top right, rgba(17,24,39,.045), transparent 35%),
        var(--nl-bg) !important;
    color: var(--nl-text) !important;
}

header {
    background: linear-gradient(145deg, #111827, #182338) !important;
    padding: 28px 0 24px !important;
    box-shadow: 0 8px 24px rgba(17,24,39,.14);
}

header h1 {
    font-size: clamp(28px, 6vw, 42px) !important;
    letter-spacing: -.8px;
}

nav {
    display: flex !important;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 20px !important;
}

nav a {
    margin-right: 0 !important;
    padding: 10px 16px;
    border-radius: 999px;
    background: rgba(255,255,255,.08);
    transition: .2s ease;
}

nav a:hover {
    background: rgba(255,255,255,.16);
    transform: translateY(-1px);
}

main.container {
    padding-top: 30px;
    padding-bottom: 45px;
}

.admin-top {
    display: flex !important;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
    margin: 0 0 25px !important;
    padding: 24px;
    background: var(--nl-card);
    border: 1px solid rgba(255,255,255,.8);
    border-radius: var(--nl-radius);
    box-shadow: var(--nl-shadow);
}

.admin-top h2 {
    margin: 0 0 5px;
    font-size: 30px;
    letter-spacing: -.5px;
}

.admin-top p {
    margin: 0;
    color: var(--nl-muted);
    font-size: 16px;
}

.botao {
    display: inline-flex !important;
    align-items: center;
    justify-content: center;
    gap: 8px;
    width: auto !important;
    min-height: 50px;
    margin-top: 0 !important;
    padding: 13px 20px !important;
    border: 0;
    border-radius: 15px !important;
    background: linear-gradient(145deg, #111827, #1e293b) !important;
    color: #fff !important;
    text-decoration: none !important;
    font-weight: 700;
    box-shadow: 0 8px 18px rgba(17,24,39,.20);
    transition: transform .2s ease, box-shadow .2s ease, filter .2s ease;
    cursor: pointer;
}

.botao:hover {
    transform: translateY(-2px);
    box-shadow: 0 13px 25px rgba(17,24,39,.25);
    filter: brightness(1.05);
}

.tabela-container {
    overflow-x: auto;
    background: var(--nl-card);
    border-radius: var(--nl-radius);
    box-shadow: var(--nl-shadow);
    border: 1px solid var(--nl-border);
    padding: 8px;
}

.tabela-container table {
    width: 100%;
    min-width: 720px;
    border-collapse: separate !important;
    border-spacing: 0 7px !important;
}

.tabela-container thead th {
    border: 0 !important;
    color: var(--nl-muted);
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: .7px;
    padding: 14px 14px !important;
    background: transparent !important;
}

.tabela-container tbody tr {
    background: #fff;
    box-shadow: 0 4px 12px rgba(17,24,39,.055);
    transition: transform .18s ease, box-shadow .18s ease;
}

.tabela-container tbody tr:hover {
    transform: translateY(-1px);
    box-shadow: 0 8px 18px rgba(17,24,39,.09);
}

.tabela-container tbody td {
    border: 0 !important;
    padding: 17px 14px !important;
    vertical-align: middle;
}

.tabela-container tbody td:first-child {
    border-radius: 14px 0 0 14px;
}

.tabela-container tbody td:last-child {
    border-radius: 0 14px 14px 0;
}

.tabela-container td a:not(.botao) {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 40px;
    padding: 9px 14px;
    margin: 3px 5px 3px 0;
    border-radius: 12px;
    background: #eef2f7;
    color: #111827;
    text-decoration: none;
    font-weight: 700;
    transition: .2s ease;
}

.tabela-container td a:not(.botao):hover {
    background: #111827;
    color: #fff;
    transform: translateY(-1px);
}

.botao-pequeno {
    border: 0;
    min-height: 40px;
    padding: 9px 14px;
    margin: 3px 0;
    border-radius: 12px;
    background: #fff0f0;
    color: #a61b1b;
    font-weight: 700;
    cursor: pointer;
    transition: .2s ease;
}

.botao-pequeno:hover {
    background: #ffe0e0;
    transform: translateY(-1px);
}

.status {
    display: inline-flex;
    align-items: center;
    padding: 6px 11px;
    border-radius: 999px;
    font-size: 13px;
    font-weight: 700;
}

.status.ativo {
    background: #e9f8ef !important;
    color: #137a3d !important;
}

.status.inativo {
    background: #f1f3f5 !important;
    color: #68717d !important;
}


/* ----------------------------------------------------------
   FORMULÁRIO NOVO / EDITAR PRODUTO
   ---------------------------------------------------------- */

.formulario {
    max-width: 780px;
    margin: 5px auto 0;
    padding: clamp(22px, 5vw, 38px);
    background: var(--nl-card);
    border: 1px solid rgba(255,255,255,.9);
    border-radius: 24px;
    box-shadow: var(--nl-shadow);
}

.formulario h2 {
    margin: 0 0 28px;
    padding-bottom: 18px;
    border-bottom: 1px solid var(--nl-border);
    font-size: clamp(27px, 6vw, 36px);
    letter-spacing: -.7px;
}

.formulario form {
    display: flex;
    flex-direction: column;
    gap: 9px;
}

.formulario label {
    margin-top: 8px;
    color: #344054;
    font-size: 14px;
    font-weight: 700;
}

.formulario input:not([type="checkbox"]),
.formulario textarea,
.formulario select {
    width: 100%;
    min-height: 50px;
    padding: 13px 15px;
    border: 1px solid #d9dee7;
    border-radius: 14px;
    background: #fff;
    color: #172033;
    font: inherit;
    outline: none;
    box-shadow: 0 3px 10px rgba(17,24,39,.035);
    transition: border-color .2s ease, box-shadow .2s ease, transform .2s ease;
}

.formulario textarea {
    min-height: 135px;
    resize: vertical;
    line-height: 1.5;
}

.formulario input:not([type="checkbox"]):focus,
.formulario textarea:focus,
.formulario select:focus {
    border-color: #7b8798;
    box-shadow: 0 0 0 4px rgba(17,24,39,.07);
}

.formulario .check {
    display: flex;
    align-items: center;
    gap: 11px;
    margin-top: 12px;
    padding: 13px 15px;
    background: #f8fafc;
    border: 1px solid var(--nl-border);
    border-radius: 14px;
    font-weight: 600;
    cursor: pointer;
}

.formulario .check input[type="checkbox"] {
    width: 20px;
    height: 20px;
    accent-color: #111827;
}

.formulario .botao {
    width: 100% !important;
    margin-top: 18px !important;
    min-height: 54px;
    border-radius: 15px !important;
    font-size: 16px;
}

.formulario > a {
    display: inline-flex;
    margin-top: 16px;
    padding: 10px 14px;
    border-radius: 12px;
    background: #eef2f7;
    color: #111827;
    text-decoration: none;
    font-weight: 700;
}


/* ----------------------------------------------------------
   MENSAGENS
   ---------------------------------------------------------- */

.flash,
.alert,
.erro {
    max-width: 780px;
    margin: 0 auto 18px;
    padding: 13px 16px;
    border-radius: 14px;
    background: #fff;
    border: 1px solid var(--nl-border);
}


/* ----------------------------------------------------------
   RESPONSIVO
   ---------------------------------------------------------- */

@media (max-width: 700px) {
    main.container {
        padding-top: 20px;
    }

    .admin-top {
        align-items: stretch !important;
        flex-direction: column;
        padding: 20px;
    }

    .admin-top .botao {
        width: 100% !important;
    }

    .formulario {
        padding: 22px 17px;
        border-radius: 20px;
    }

    header {
        padding: 23px 0 20px !important;
    }

    nav {
        gap: 7px;
    }

    nav a {
        padding: 9px 13px;
    }
}
</style>
"""


# ==========================================================
# ESTILO DA LOJA / LOGIN
# ==========================================================

LOJA_STYLE = r"""
<style id="nossa-loja-public-style">
:root {
    --nl-bg: #f3f5f8;
    --nl-card: rgba(255,255,255,.97);
    --nl-dark: #111827;
    --nl-dark-2: #1e293b;
    --nl-text: #182230;
    --nl-muted: #697586;
    --nl-border: #e5e9ef;
    --nl-shadow: 0 12px 30px rgba(17,24,39,.09);
    --nl-shadow-hover: 0 16px 34px rgba(17,24,39,.14);
    --nl-radius: 20px;
}

body {
    background:
        radial-gradient(circle at top right, rgba(17,24,39,.055), transparent 35%),
        var(--nl-bg) !important;
    color: var(--nl-text) !important;
}

header {
    background: linear-gradient(145deg, #111827, #182338) !important;
    padding: 28px 0 24px !important;
    box-shadow: 0 8px 24px rgba(17,24,39,.14);
}

header h1 {
    font-size: clamp(30px, 7vw, 46px) !important;
    letter-spacing: -.9px;
}

header p {
    color: rgba(255,255,255,.76) !important;
}

nav {
    display: flex !important;
    flex-wrap: wrap;
    gap: 9px;
    margin-top: 20px !important;
}

nav a {
    margin-right: 0 !important;
    padding: 10px 16px !important;
    border-radius: 999px !important;
    background: rgba(255,255,255,.09) !important;
    color: #fff !important;
    text-decoration: none !important;
    transition: .2s ease;
}

nav a:hover {
    background: rgba(255,255,255,.18) !important;
    transform: translateY(-1px);
}

nav .botao-admin {
    width: auto !important;
    min-height: auto;
}

main.container {
    padding-top: 28px;
    padding-bottom: 45px;
}

.hero {
    padding: clamp(25px, 6vw, 42px) !important;
    margin-bottom: 26px;
    background: var(--nl-card) !important;
    border: 1px solid var(--nl-border);
    border-radius: 24px !important;
    box-shadow: var(--nl-shadow);
}

.hero h2 {
    font-size: clamp(28px, 6vw, 40px) !important;
    margin-top: 0;
    letter-spacing: -.7px;
}

main.container > section:not(.hero) {
    margin-bottom: 30px;
}

main.container > section:not(.hero) > h2 {
    margin: 0 0 15px;
    font-size: clamp(24px, 5vw, 32px);
    letter-spacing: -.5px;
}

/* Cartões flutuantes de categoria */
.categorias-modernas {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(145px, 1fr));
    gap: 13px;
}

.categoria-botao {
    display: flex !important;
    align-items: center;
    justify-content: center;
    min-height: 58px;
    padding: 13px 15px;
    border-radius: 16px !important;
    background: linear-gradient(145deg, #111827, #1e293b) !important;
    color: #fff !important;
    text-decoration: none !important;
    text-align: center;
    font-weight: 750;
    box-shadow: 0 8px 18px rgba(17,24,39,.18);
    transition: transform .2s ease, box-shadow .2s ease, filter .2s ease;
}

.categoria-botao:hover {
    transform: translateY(-2px);
    box-shadow: 0 13px 25px rgba(17,24,39,.24);
    filter: brightness(1.05);
}

.produtos {
    display: grid !important;
    grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
    gap: 18px !important;
}

.produto {
    overflow: hidden;
    background: var(--nl-card) !important;
    border: 1px solid var(--nl-border);
    border-radius: 20px !important;
    box-shadow: var(--nl-shadow) !important;
    transition: transform .2s ease, box-shadow .2s ease;
}

.produto:hover {
    transform: translateY(-3px);
    box-shadow: var(--nl-shadow-hover) !important;
}

.produto img,
.produto .sem-imagem {
    width: 100%;
    height: 205px;
    object-fit: contain;
    background: #f8fafc;
}

.produto-conteudo {
    padding: 19px !important;
}

.produto-conteudo h3 {
    margin-top: 0;
    font-size: 20px;
}

.produto-conteudo p {
    color: var(--nl-muted);
    line-height: 1.55;
}

.produto-conteudo strong {
    display: block;
    margin: 12px 0;
    font-size: 20px;
}

/* Botão flutuante preto padrão da Nossa Loja */
.produto-conteudo .botao,
.botao-comprar,
.botao-admin,
.login-box .botao {
    display: inline-flex !important;
    align-items: center;
    justify-content: center;
    width: 100% !important;
    min-height: 50px;
    padding: 13px 20px !important;
    border: 0 !important;
    border-radius: 15px !important;
    background: linear-gradient(145deg, #111827, #1e293b) !important;
    color: #fff !important;
    text-decoration: none !important;
    font-weight: 750;
    box-shadow: 0 8px 18px rgba(17,24,39,.20);
    transition: transform .2s ease, box-shadow .2s ease, filter .2s ease;
    cursor: pointer;
}

.produto-conteudo .botao:hover,
.botao-comprar:hover,
.botao-admin:hover,
.login-box .botao:hover {
    transform: translateY(-2px);
    box-shadow: 0 13px 25px rgba(17,24,39,.25);
    filter: brightness(1.05);
}

/* Página de produtos */
main.container > h2 {
    background: var(--nl-card);
    border-radius: 20px;
    padding: 22px 24px;
    box-shadow: var(--nl-shadow);
    border: 1px solid var(--nl-border);
}

.filtro-categorias {
    display: flex;
    flex-wrap: wrap;
    gap: 9px;
    margin: 0 0 25px;
}

.filtro-categorias a {
    display: inline-flex;
    align-items: center;
    min-height: 42px;
    padding: 9px 14px;
    border-radius: 13px;
    background: #fff;
    border: 1px solid var(--nl-border);
    color: var(--nl-dark);
    text-decoration: none;
    font-weight: 700;
    box-shadow: 0 5px 14px rgba(17,24,39,.05);
}

.filtro-categorias a:hover,
.filtro-categorias a.ativo {
    background: var(--nl-dark);
    color: #fff;
}

/* Login */
.login-container {
    min-height: 100vh;
    display: flex !important;
    align-items: center;
    justify-content: center;
    padding: 24px !important;
    background:
        radial-gradient(circle at top right, rgba(17,24,39,.09), transparent 35%),
        var(--nl-bg) !important;
}

.login-box {
    width: min(100%, 460px);
    padding: clamp(25px, 7vw, 40px) !important;
    background: var(--nl-card) !important;
    border: 1px solid var(--nl-border);
    border-radius: 24px !important;
    box-shadow: 0 18px 45px rgba(17,24,39,.13) !important;
}

.login-box h1 {
    margin-top: 0;
    font-size: clamp(30px, 7vw, 42px);
}

.login-box h2 {
    margin-bottom: 25px;
}

.login-box form {
    display: flex;
    flex-direction: column;
    gap: 9px;
}

.login-box label {
    margin-top: 8px;
    color: #344054;
    font-size: 14px;
    font-weight: 700;
}

.login-box input {
    width: 100% !important;
    min-height: 52px !important;
    box-sizing: border-box;
    padding: 13px 15px !important;
    border: 1px solid #d9dee7 !important;
    border-radius: 14px !important;
    background: #fff !important;
    color: #172033 !important;
    font: inherit;
    outline: none;
    box-shadow: 0 3px 10px rgba(17,24,39,.035);
    transition: .2s ease;
}

.login-box input:focus {
    border-color: #7b8798 !important;
    box-shadow: 0 0 0 4px rgba(17,24,39,.07) !important;
}

.login-box .botao {
    margin-top: 17px !important;
}

.login-box > a {
    display: flex;
    justify-content: center;
    margin-top: 18px;
    padding: 12px 14px;
    border-radius: 13px;
    background: #eef2f7;
    color: #111827;
    text-decoration: none;
    font-weight: 700;
}

.erro {
    padding: 13px 15px !important;
    margin-bottom: 15px !important;
    border-radius: 14px !important;
    background: #fff0f0 !important;
    color: #a61b1b !important;
    border: 1px solid #ffd5d5 !important;
}

footer {
    margin-top: 30px;
    padding: 28px 20px !important;
    background: #111827 !important;
    color: rgba(255,255,255,.72) !important;
}

@media (max-width: 650px) {
    header {
        padding: 22px 0 19px !important;
    }

    nav a {
        flex: 1 1 auto;
        text-align: center;
    }

    .categorias-modernas {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .produto img,
    .produto .sem-imagem {
        height: 185px;
    }

    .login-container {
        padding: 15px !important;
    }

    .login-box {
        border-radius: 20px !important;
    }
}
</style>
"""


CARRINHO_STYLE = r'''<style id="nossa-loja-carrinho-style">
.menu-shell{position:relative;display:inline-flex;align-items:flex-start}.menu-shell summary{list-style:none}.menu-shell summary::-webkit-details-marker{display:none}.menu-toggle{display:none!important;border:0;background:rgba(255,255,255,.14);color:#fff!important;border-radius:12px;padding:10px 13px;font-size:22px;line-height:1;cursor:pointer;font-weight:900}.menu-nav{display:flex;flex-wrap:wrap;gap:9px;align-items:center}.menu-nav a{color:#fff!important}.menu-shell[open] .menu-nav{display:flex!important}@media(max-width:700px){.menu-shell{display:block;width:100%}.menu-shell .menu-toggle{display:inline-flex!important;align-items:center;justify-content:center}.menu-shell .menu-nav{display:none!important;flex-direction:column;align-items:stretch;width:100%;padding-top:10px}.menu-shell[open] .menu-nav{display:flex!important}.menu-shell .menu-nav a{width:100%;box-sizing:border-box;text-align:center}.menu-shell .menu-nav{background:rgba(17,24,39,.96);border-radius:16px;padding:10px;margin-top:8px}.cart-card{align-items:flex-start}.cart-actions{width:100%}}
.carrinho-link{position:relative!important;background:rgba(255,255,255,.18)!important;color:#fff!important;font-weight:800!important}.carrinho-badge{display:inline-flex;align-items:center;justify-content:center;min-width:22px;height:22px;padding:0 6px;margin-left:5px;border-radius:999px;background:#fff;color:#111827;font-size:12px;font-weight:900}.cart-page{max-width:900px;margin:0 auto;padding:25px 0 50px}.cart-card{background:rgba(255,255,255,.97);border:1px solid #e5e9ef;border-radius:20px;padding:18px;margin-bottom:14px;box-shadow:0 10px 25px rgba(17,24,39,.08);display:flex;gap:16px;align-items:center}.cart-card img,.cart-sem-imagem{width:90px;height:90px;border-radius:14px;object-fit:contain;background:#f8fafc;flex:0 0 90px}.cart-info{flex:1}.cart-info h3{margin:0 0 7px}.cart-info p{margin:4px 0;color:#697586}.cart-actions{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.qty-control{display:flex;align-items:center;gap:7px}.qty-control a{width:34px;height:34px;border-radius:10px;background:#111827;color:#fff;text-decoration:none;display:inline-flex;align-items:center;justify-content:center;font-weight:900}.qty-control span{min-width:30px;text-align:center;font-weight:800}.cart-total{background:#111827;color:#fff;border-radius:20px;padding:22px;margin-top:20px;display:flex;justify-content:space-between;align-items:center;gap:15px;flex-wrap:wrap}.cart-total strong{font-size:24px}.cart-empty{background:#fff;border:1px solid #e5e9ef;border-radius:20px;padding:35px;text-align:center;box-shadow:0 10px 25px rgba(17,24,39,.07)}.cart-btn{display:inline-flex;align-items:center;justify-content:center;min-height:48px;padding:12px 18px;border-radius:14px;background:#111827;color:#fff!important;text-decoration:none!important;font-weight:800;border:0;cursor:pointer}.cart-btn.secondary{background:#e5e7eb;color:#111827!important}.cart-btn.danger{background:#7f1d1d}.senha-box{max-width:520px;margin:25px auto;background:#fff;border:1px solid #e5e9ef;border-radius:22px;padding:26px;box-shadow:0 12px 30px rgba(17,24,39,.09)}.senha-box input{width:100%;box-sizing:border-box;min-height:50px;border:1px solid #d9dee7;border-radius:13px;padding:12px;margin:5px 0 13px}.senha-box label{font-weight:700;color:#344054}
.menu-toggle{position:relative;z-index:20;user-select:none;-webkit-tap-highlight-color:transparent}.menu-nav{position:relative;z-index:19}.pagamento-box{background:#fff;border:1px solid #e5e9ef;border-radius:20px;padding:22px;margin-top:20px;box-shadow:0 10px 25px rgba(17,24,39,.07)}.checkout-form{display:grid;gap:10px;max-width:560px}.checkout-form input{min-height:50px;padding:12px 14px;border:1px solid #d9dee7;border-radius:13px;box-sizing:border-box;font:inherit}.checkout-note{font-size:13px;color:#697586;line-height:1.5}.pagamento-ok{background:#ecfdf3;color:#166534;border:1px solid #bbf7d0;border-radius:16px;padding:18px}.pagamento-erro{background:#fff0f0;color:#991b1b;border:1px solid #fecaca;border-radius:16px;padding:18px}.tipo-produto-badge{display:inline-flex;align-items:center;gap:6px;padding:6px 10px;border-radius:999px;background:#eef2f7;color:#344054;font-size:12px;font-weight:800;margin:0 0 8px}.cart-affiliate{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}.cart-affiliate a{background:#111827;color:#fff!important}.checkout-own{background:#0f766e!important}.form-ajuda{margin:-3px 0 12px;color:#667085;font-size:13px;line-height:1.45}.tipo-produto-box{margin:8px 0 14px;padding:14px;border:1px solid #e5e9ef;border-radius:15px;background:#f8fafc}.tipo-produto-box strong{display:block;margin-bottom:5px}.estoque-ideia{margin-top:10px;padding:12px;border-radius:13px;background:#fff7ed;border:1px solid #fed7aa;color:#9a3412;font-size:13px;line-height:1.45}
.menu-mobile-wrap{position:relative;width:100%}.menu-check{position:absolute;opacity:0;pointer-events:none}.menu-toggle-real{display:none;border:0;background:rgba(255,255,255,.14);color:#fff;border-radius:13px;padding:10px 14px;font-size:24px;line-height:1;font-weight:900;cursor:pointer;-webkit-tap-highlight-color:transparent;user-select:none}.menu-nav-real{display:flex;flex-wrap:wrap;gap:9px;align-items:center}.menu-nav-real a{color:#fff!important}@media(max-width:700px){.menu-toggle-real{display:inline-flex;align-items:center;justify-content:center}.menu-nav-real{display:none!important;flex-direction:column;align-items:stretch;width:100%;margin-top:9px;padding:10px;background:rgba(17,24,39,.98);border-radius:16px;box-shadow:0 12px 25px rgba(0,0,0,.22)}.menu-check:checked + .menu-toggle-real + .menu-nav-real{display:flex!important}.menu-nav-real a{width:100%;box-sizing:border-box;text-align:center}.menu-mobile-wrap{display:block}}</style>'''


CLIENTE_STYLE = r"""<style id="nossa-loja-cliente-style">
.cliente-box{background:#fff;border:1px solid #e5e9ef;border-radius:22px;padding:22px;margin:20px auto;box-shadow:0 10px 25px rgba(17,24,39,.07);max-width:820px}.cliente-box h1,.cliente-box h2{margin-top:0}.cliente-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.cliente-field{display:flex;flex-direction:column;gap:6px}.cliente-field.full{grid-column:1/-1}.cliente-field label{font-weight:800;color:#344054;font-size:14px}.cliente-field input,.cliente-field select{min-height:50px;padding:12px 14px;border:1px solid #d9dee7;border-radius:13px;box-sizing:border-box;font:inherit;background:#fff;color:#172033}.cliente-field input:focus,.cliente-field select:focus{outline:none;border-color:#7b8798;box-shadow:0 0 0 4px rgba(17,24,39,.07)}.cliente-section{margin-top:22px;padding-top:18px;border-top:1px solid #edf0f4}.consentimento{display:flex;gap:9px;align-items:flex-start;margin:16px 0;color:#475467;font-size:13px;line-height:1.45}.consentimento input{margin-top:3px}.frete-nota{padding:13px 15px;background:#f8fafc;border:1px solid #e5e9ef;border-radius:14px;color:#475467;font-size:13px;line-height:1.5}.pedido-status{display:inline-flex;align-items:center;padding:6px 10px;border-radius:999px;background:#eef2f7;color:#344054;font-size:12px;font-weight:800}.pedido-status.pago{background:#dcfce7;color:#166534}.pedido-status.pendente{background:#fef3c7;color:#92400e}.pedido-status.cancelado{background:#fee2e2;color:#991b1b}.pedido-table{width:100%;border-collapse:collapse}.pedido-table th,.pedido-table td{padding:11px 9px;border-bottom:1px solid #edf0f4;text-align:left;vertical-align:top}.pedido-table th{font-size:12px;text-transform:uppercase;color:#667085}.pedido-form{display:grid;gap:8px}.pedido-form input,.pedido-form select{min-height:42px;padding:9px 11px;border:1px solid #d9dee7;border-radius:10px;box-sizing:border-box;font:inherit}.admin-link-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:20px 0}.admin-link-card{display:block;background:#fff;border:1px solid #e5e9ef;border-radius:18px;padding:18px;text-decoration:none;color:#111827;box-shadow:0 9px 22px rgba(17,24,39,.06)}.admin-link-card strong{display:block;margin-bottom:5px;font-size:18px}.admin-link-card span{color:#667085;font-size:13px}@media(max-width:700px){.cliente-grid{grid-template-columns:1fr}.cliente-field.full{grid-column:auto}.pedido-table{min-width:900px}.pedido-table-wrap{overflow:auto}}
</style>"""


@app.after_request
def aplicar_estilos_e_componentes(response):
    'Aplica o visual e pequenos componentes sem exigir troca dos templates.'
    try:
        if not (response.content_type and "text/html" in response.content_type):
            return response

        html_pagina = response.get_data(as_text=True)
        estilo = PAINEL_STYLE if request.path.startswith("/admin") else LOJA_STYLE

        if "nossa-loja-public-style" not in html_pagina and "nossa-loja-painel-style" not in html_pagina and "</head>" in html_pagina:
            html_pagina = html_pagina.replace("</head>", estilo + "\n</head>", 1)

        if request.path == "/" and "/login" not in html_pagina:
            antigo = '<a href="/produtos">Todos os produtos</a>'
            novo = antigo + '\n\n<a href="/login" class="botao-admin">🔐 Área administrativa</a>'
            if antigo in html_pagina:
                html_pagina = html_pagina.replace(antigo, novo, 1)

        if request.path == "/" and 'id="categorias-modernas"' not in html_pagina:
            categorias_html = getattr(g, "categorias_home_html", "")
            if categorias_html:
                padrao = re.compile(r'<section>\s*<h2>\s*Categorias\s*</h2>\s*<div class="categorias">.*?</div>\s*</section>', re.I | re.S)
                html_pagina = padrao.sub(categorias_html, html_pagina, count=1)

        if request.path == "/produtos" and 'id="filtro-categorias"' not in html_pagina:
            filtros_html = getattr(g, "filtros_categorias_html", "")
            if filtros_html:
                marcador = "<h2>\nTodos os produtos\n</h2>"
                if marcador in html_pagina:
                    html_pagina = html_pagina.replace(marcador, marcador + "\n\n" + filtros_html, 1)

        # Formulário de produto: tipos de venda sem alterar o banco.
        if request.path.startswith("/admin/produto/"):
            script_form = r'''<script>
document.addEventListener('DOMContentLoaded', function(){
  const select=document.querySelector('select[name="plataforma"]');
  const link=document.querySelector('input[name="link_afiliado"]');
  if(!select) return;
  const atual=(select.value||'').trim();
  select.innerHTML='';
  [['Nossa Loja','Produto próprio — pago pelo Mercado Pago'],['Mercado Livre Afiliado','Link de afiliado — pagamento acontece no Mercado Livre'],['Amazon','Link de afiliado — pagamento acontece na Amazon']].forEach(function(item){
    const o=document.createElement('option'); o.value=item[0]; o.textContent=item[0]+' — '+item[1]; if(item[0]===atual || (!atual && item[0]==='Nossa Loja')) o.selected=true; select.appendChild(o);
  });
  const box=document.createElement('div'); box.className='tipo-produto-box'; box.innerHTML='<strong>Como este produto será vendido?</strong><div id="tipo-ajuda" class="form-ajuda"></div>';
  select.parentNode.insertBefore(box, select);
  function atualizar(){
    const tipo=select.value, proprio=tipo==='Nossa Loja';
    if(link){ link.required=!proprio; link.placeholder=proprio?'Opcional para produto próprio':'Cole aqui o link gerado pelo programa de afiliados'; }
    const ajuda=document.getElementById('tipo-ajuda');
    if(ajuda) ajuda.textContent=proprio ? 'Você possui o produto/estoque e recebe o pagamento pelo Mercado Pago.' : (tipo==='Mercado Livre Afiliado' ? 'O cliente será levado ao anúncio do Mercado Livre pelo seu link de afiliado.' : 'O cliente será levado à Amazon pelo seu link de associado.');
  }
  select.addEventListener('change',atualizar); atualizar();
});
</script>'''
            if '</body>' in html_pagina:
                html_pagina = html_pagina.replace('</body>', script_form + '</body>', 1)

        if not request.path.startswith('/admin'):
            carrinho_qtd = sum(int(x.get('quantidade', 0)) for x in obter_carrinho())
            menu_html = f'''<div class="menu-mobile-wrap"><input class="menu-check" type="checkbox" id="menu-check"><label class="menu-toggle-real" for="menu-check" aria-label="Abrir menu">☰</label><div id="menu-principal" class="menu-nav-real"><a href="/">Início</a><a href="/produtos">Produtos</a><a href="/carrinho" class="carrinho-link">🛒 Carrinho <span class="carrinho-badge">{carrinho_qtd}</span></a><a href="/login" class="botao-admin">🔐 Área administrativa</a></div></div>'''
            nav_re = re.compile(r'<nav[^>]*>.*?</nav>', re.I | re.S)
            html_pagina = nav_re.sub('<nav>' + menu_html + '</nav>', html_pagina, count=1)
            if 'nossa-loja-carrinho-style' not in html_pagina and '</head>' in html_pagina:
                html_pagina = html_pagina.replace('</head>', CARRINHO_STYLE + '</head>', 1)
            js = r'''<script>
document.addEventListener('DOMContentLoaded',function(){
  document.querySelectorAll('.produto').forEach(function(card){
    const t=card.querySelector('h3'), b=card.querySelector('.botao');
    if(t&&b){ b.textContent='🛒 Adicionar ao carrinho'; b.href='/carrinho/adicionar?nome='+encodeURIComponent(t.textContent.trim()); b.removeAttribute('target'); b.removeAttribute('rel'); }
  });
});
</script>'''
            if '</body>' in html_pagina:
                html_pagina = html_pagina.replace('</body>', js + '</body>', 1)

        if request.path == '/admin' and '/admin/senha' not in html_pagina and '</nav>' in html_pagina:
            html_pagina = html_pagina.replace('</nav>', '<a href="/admin/senha">🔑 Alterar senha</a><a href="/admin/como-vender">🧭 Como vender</a><a href="/admin/pedidos">🛍 Pedidos</a><a href="/admin/clientes">👥 Clientes</a></nav>', 1)

        response.set_data(html_pagina)
    except Exception:
        pass
    return response


# ==========================================================
# FUNÇÕES AUXILIARES
# ==========================================================

def texto_formulario(nome, padrao=""):
    return request.form.get(nome, padrao).strip()


def converter_preco(valor):
    valor = str(valor or "").strip()

    if not valor:
        return None

    valor = valor.replace("R$", "").strip()

    # Aceita 99,90 e 99.90. Também trata 1.299,90.
    if "," in valor:
        valor = valor.replace(".", "").replace(",", ".")
    else:
        valor = valor.replace(",", "")

    try:
        preco = Decimal(valor)

        if preco < 0:
            raise ValueError("O preço não pode ser negativo.")

        return float(preco)

    except (InvalidOperation, ValueError):
        raise ValueError("Digite um preço válido.")


def converter_categoria(valor):
    valor = str(valor or "").strip()

    if not valor:
        return None

    try:
        return int(valor)
    except ValueError:
        raise ValueError("Categoria inválida.")


def checkbox_ativo(nome):
    return request.form.get(nome) == "on"


def url_valida(url):
    if not url:
        return True

    try:
        resultado = urlparse(url)
        return (
            resultado.scheme in ("http", "https")
            and bool(resultado.netloc)
        )
    except Exception:
        return False


def montar_dados_produto():
    nome = texto_formulario("nome")

    if not nome:
        raise ValueError("O nome do produto é obrigatório.")

    imagem_url = texto_formulario("imagem_url")
    link_afiliado = texto_formulario("link_afiliado")

    if not url_valida(imagem_url):
        raise ValueError(
            "A URL da imagem precisa começar com http:// ou https://."
        )

    if not url_valida(link_afiliado):
        raise ValueError(
            "O link de afiliado precisa ser uma URL válida."
        )

    return {
        "nome": nome,
        "descricao": texto_formulario("descricao"),
        "categoria_id": converter_categoria(
            request.form.get("categoria_id")
        ),
        "preco": converter_preco(
            request.form.get("preco")
        ),
        "imagem_url": imagem_url,
        "link_afiliado": link_afiliado,
        "plataforma": texto_formulario(
            "plataforma",
            "Nossa Loja",
        ),
        "ativo": checkbox_ativo("ativo"),
        "destaque": checkbox_ativo("destaque"),
    }


def buscar_categorias(apenas_ativas=False):
    consulta = supabase.table("categorias").select("*")

    if apenas_ativas:
        consulta = consulta.eq("ativo", True)

    return (
        consulta
        .order("nome")
        .execute()
        .data
        or []
    )


def buscar_produto(produto_id):
    resultado = (
        supabase
        .table("produtos")
        .select("*")
        .eq("id", produto_id)
        .limit(1)
        .execute()
    )

    if not resultado.data:
        return None

    return resultado.data[0]


def buscar_todos_produtos():
    return (
        supabase
        .table("produtos")
        .select("*")
        .order("id", desc=True)
        .execute()
        .data
        or []
    )


def calcular_estatisticas(produtos):
    total = len(produtos)

    ativos = sum(
        1 for produto in produtos
        if produto.get("ativo") is True
    )

    inativos = total - ativos

    destaques = sum(
        1 for produto in produtos
        if produto.get("destaque") is True
    )

    sem_imagem = sum(
        1 for produto in produtos
        if not produto.get("imagem_url")
    )

    sem_link = sum(
        1 for produto in produtos
        if not produto.get("link_afiliado")
    )

    sem_descricao = sum(
        1 for produto in produtos
        if not produto.get("descricao")
    )

    produtos_incompletos = sum(
        1
        for produto in produtos
        if (
            not produto.get("imagem_url")
            or not produto.get("link_afiliado")
            or not produto.get("descricao")
        )
    )

    return {
        "total": total,
        "ativos": ativos,
        "inativos": inativos,
        "destaques": destaques,
        "sem_imagem": sem_imagem,
        "sem_link": sem_link,
        "sem_descricao": sem_descricao,
        "produtos_incompletos": produtos_incompletos,
    }


# ==========================================================
# PROTEÇÃO ADMINISTRATIVA
# ==========================================================

def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logado"):
            flash(
                "Faça login para acessar o painel.",
                "warning",
            )
            return redirect(url_for("login"))

        return func(*args, **kwargs)

    return wrapper


# ==========================================================
# PRODUTO DE TESTE AMAZON — AURAFIT
# ==========================================================

# Este produto é mantido temporariamente no código para testar o
# fluxo Amazon "Adicionar ao carrinho", sem depender do Supabase.
# Quando confirmarmos o funcionamento, podemos gravá-lo normalmente
# na tabela produtos.
AURAFIT_TESTE = {
    "id": "teste-amazon-aurafit",
    "nome": "AURAFIT Bluetooth — Fone Esportivo para Academia",
    "descricao": "Fone de ouvido Bluetooth AURAFIT para uso esportivo, corrida e academia. Produto de teste do fluxo de compra da Amazon.",
    "categoria_id": None,
    "preco": None,
    "imagem_url": "",
    "link_afiliado": "https://www.amazon.com.br/dp/B0HD6XVK2S?tag=pedro0ba1e-20",
    "plataforma": "Amazon",
    "ativo": True,
    "destaque": True,
    "asin": "B0HD6XVK2S",
}


def produto_teste_aurafit():
    # Retorna uma cópia para evitar alterações acidentais no objeto-base.
    return dict(AURAFIT_TESTE)


# ==========================================================
# PÁGINA PRINCIPAL
# ==========================================================

@app.route("/")
def index():
    try:
        produtos_resultado = (
            supabase
            .table("produtos")
            .select("*")
            .eq("ativo", True)
            .order("destaque", desc=True)
            .order("id", desc=True)
            .execute()
        )

        categorias_resultado = (
            supabase
            .table("categorias")
            .select("*")
            .eq("ativo", True)
            .order("nome")
            .execute()
        )

        produtos_publicos = produtos_resultado.data or []

        # Adiciona o AURAFIT de teste à vitrine, mesmo que ele ainda
        # não exista na tabela produtos do Supabase.
        if not any(
            str(p.get("id")) == "teste-amazon-aurafit"
            or "B0HD6XVK2S" in str(p.get("link_afiliado") or "")
            for p in produtos_publicos
        ):
            produtos_publicos.insert(0, produto_teste_aurafit())

        categorias = categorias_resultado.data or []

        botoes = []
        for categoria in categorias:
            cid = categoria.get("id")
            nome = html.escape(str(categoria.get("nome") or "Categoria"))
            if cid is not None:
                botoes.append(
                    f'<a class="categoria-botao" href="/produtos?categoria={cid}">🛒 {nome}</a>'
                )

        if botoes:
            categorias_html = (
                '<section id="categorias-modernas-section">'
                '<h2>Categorias</h2>'
                '<div id="categorias-modernas" class="categorias-modernas">'
                + "".join(botoes)
                + '</div></section>'
            )
        else:
            categorias_html = (
                '<section id="categorias-modernas-section">'
                '<h2>Categorias</h2>'
                '<p>Nenhuma categoria disponível no momento.</p>'
                '</section>'
            )

        g.categorias_home_html = categorias_html

        return render_template(
            "index.html",
            produtos=produtos_publicos,
            categorias=categorias,
        )

    except Exception:
        return render_template(
            "index.html",
            produtos=[],
            categorias=[],
        )


# ==========================================================
# LISTAGEM DE PRODUTOS
# ==========================================================

@app.route("/produtos")
def produtos():
    busca = request.args.get("q", "").strip()
    categoria_id = request.args.get("categoria", "").strip()

    try:
        consulta = (
            supabase
            .table("produtos")
            .select("*")
            .eq("ativo", True)
        )

        if busca:
            consulta = consulta.ilike(
                "nome",
                f"%{busca}%",
            )

        if categoria_id:
            try:
                consulta = consulta.eq(
                    "categoria_id",
                    int(categoria_id),
                )
            except ValueError:
                pass

        resultado = (
            consulta
            .order("destaque", desc=True)
            .order("id", desc=True)
            .execute()
        )

        produtos_publicos = resultado.data or []

        # O AURAFIT aparece na listagem geral para o teste.
        # Se o usuário estiver filtrando uma categoria específica,
        # não forçamos o produto de teste a aparecer nessa categoria.
        if not categoria_id and not busca:
            if not any(
                str(p.get("id")) == "teste-amazon-aurafit"
                or "B0HD6XVK2S" in str(p.get("link_afiliado") or "")
                for p in produtos_publicos
            ):
                produtos_publicos.insert(0, produto_teste_aurafit())

        categorias = buscar_categorias(
            apenas_ativas=True,
        )

        filtros = ['<div id="filtro-categorias" class="filtro-categorias">']
        todos_ativo = "" if categoria_id else " ativo"
        filtros.append(f'<a class="{todos_ativo.strip()}" href="/produtos">Todos</a>')
        for categoria in categorias:
            cid = categoria.get("id")
            nome = html.escape(str(categoria.get("nome") or "Categoria"))
            ativo = " ativo" if str(cid) == str(categoria_id) else ""
            filtros.append(
                f'<a class="{ativo.strip()}" href="/produtos?categoria={cid}">{nome}</a>'
            )
        filtros.append('</div>')
        g.filtros_categorias_html = "".join(filtros)

        return render_template(
            "produtos.html",
            produtos=produtos_publicos,
            categorias=categorias,
            busca=busca,
            categoria_selecionada=categoria_id,
        )

    except Exception:
        return render_template(
            "produtos.html",
            produtos=[],
            categorias=[],
            busca=busca,
            categoria_selecionada=categoria_id,
        )


# ==========================================================
# LOGIN
# ==========================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("admin_logado"):
        return redirect(url_for("admin"))

    erro = None

    if request.method == "POST":
        usuario = texto_formulario("usuario")
        senha = request.form.get("senha", "")

        if (
            usuario == ADMIN_USER
            and senha == senha_atual()
        ):
            session.clear()
            session["admin_logado"] = True

            flash(
                "Login realizado com sucesso.",
                "success",
            )

            return redirect(url_for("admin"))

        erro = "Usuário ou senha incorretos."

    return render_template(
        "login.html",
        erro=erro,
    )



# ==========================================================
# ALTERAR SENHA DO PAINEL
# ==========================================================
def senha_atual():
    try:
        r=supabase.table('configuracoes_admin').select('senha').eq('id',1).limit(1).execute()
        if r.data and r.data[0].get('senha'): return str(r.data[0]['senha'])
    except Exception: pass
    return ADMIN_PASSWORD

def salvar_senha(nova):
    try:
        r=supabase.table('configuracoes_admin').select('id').eq('id',1).limit(1).execute()
        if r.data: supabase.table('configuracoes_admin').update({'senha':nova}).eq('id',1).execute()
        else: supabase.table('configuracoes_admin').insert({'id':1,'senha':nova}).execute()
        return True
    except Exception: return False

@app.route('/admin/senha',methods=['GET','POST'])
@admin_required
def alterar_senha():
    erro=None; sucesso=None
    if request.method=='POST':
        atual=request.form.get('senha_atual',''); nova=request.form.get('nova_senha',''); conf=request.form.get('confirmacao','')
        if atual!=senha_atual(): erro='A senha atual está incorreta.'
        elif len(nova)<6: erro='A nova senha precisa ter pelo menos 6 caracteres.'
        elif nova!=conf: erro='A confirmação da nova senha não confere.'
        elif not salvar_senha(nova): erro='Não consegui salvar. Crie a tabela configuracoes_admin no Supabase e tente novamente.'
        else: sucesso='Senha alterada com sucesso.'
    return f'''<!DOCTYPE html><html lang="pt-br"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Alterar senha — Nossa Loja</title><link rel="stylesheet" href="/static/style.css">{CARRINHO_STYLE}</head><body><main class="container"><div class="senha-box"><h1>🔐 Alterar senha</h1>{f'<div class="sucesso">{html.escape(sucesso)}</div>' if sucesso else ''}{f'<div class="erro">{html.escape(erro)}</div>' if erro else ''}<form method="post"><label>Senha atual</label><input type="password" name="senha_atual" required><label>Nova senha</label><input type="password" name="nova_senha" minlength="6" required><label>Confirmar nova senha</label><input type="password" name="confirmacao" minlength="6" required><button class="cart-btn" type="submit">Salvar nova senha</button></form><p><a href="/admin">← Voltar ao painel</a></p></div></main></body></html>'''

# ==========================================================
# LOGOUT
# ==========================================================

@app.route("/logout")
def logout():
    session.clear()

    flash(
        "Você saiu do painel.",
        "info",
    )

    return redirect(url_for("index"))


# ==========================================================
# PAINEL ADMINISTRATIVO
# ==========================================================

@app.route("/admin")
@admin_required
def admin():
    try:
        produtos_lista = buscar_todos_produtos()
        categorias = buscar_categorias()

        estatisticas = calcular_estatisticas(
            produtos_lista
        )

        busca = request.args.get(
            "q",
            "",
        ).strip()

        categoria_id = request.args.get(
            "categoria",
            "",
        ).strip()

        produtos_filtrados = produtos_lista

        if busca:
            produtos_filtrados = [
                produto
                for produto in produtos_filtrados
                if busca.lower()
                in produto.get(
                    "nome",
                    "",
                ).lower()
            ]

        if categoria_id:
            try:
                categoria_numero = int(
                    categoria_id
                )

                produtos_filtrados = [
                    produto
                    for produto in produtos_filtrados
                    if produto.get(
                        "categoria_id"
                    ) == categoria_numero
                ]
            except ValueError:
                pass

        return render_template(
            "admin.html",
            produtos=produtos_filtrados,
            categorias=categorias,
            estatisticas=estatisticas,
            busca=busca,
            categoria_selecionada=categoria_id,
        )

    except Exception as erro:
        return render_template(
            "admin.html",
            produtos=[],
            categorias=[],
            estatisticas={
                "total": 0,
                "ativos": 0,
                "inativos": 0,
                "destaques": 0,
                "sem_imagem": 0,
                "sem_link": 0,
                "sem_descricao": 0,
                "produtos_incompletos": 0,
            },
            busca="",
            categoria_selecionada="",
        )


# ==========================================================
# NOVO PRODUTO
# ==========================================================

@app.route(
    "/admin/produto/novo",
    methods=["GET", "POST"],
)
@admin_required
def novo_produto():
    categorias = buscar_categorias(
        apenas_ativas=True,
    )

    if request.method == "POST":
        try:
            dados = montar_dados_produto()

            (
                supabase
                .table("produtos")
                .insert(dados)
                .execute()
            )

            flash(
                "Produto cadastrado com sucesso.",
                "success",
            )

            return redirect(url_for("admin"))

        except Exception as erro:
            flash(
                f"Erro ao cadastrar produto: {erro}",
                "danger",
            )

    return render_template(
        "produto_form.html",
        produto=None,
        categorias=categorias,
    )


# ==========================================================
# EDITAR PRODUTO
# ==========================================================

@app.route(
    "/admin/produto/<int:produto_id>/editar",
    methods=["GET", "POST"],
)
@admin_required
def editar_produto(produto_id):
    produto = buscar_produto(produto_id)

    if not produto:
        flash(
            "Produto não encontrado.",
            "danger",
        )
        return redirect(url_for("admin"))

    categorias = buscar_categorias(
        apenas_ativas=True,
    )

    if request.method == "POST":
        try:
            dados = montar_dados_produto()

            (
                supabase
                .table("produtos")
                .update(dados)
                .eq("id", produto_id)
                .execute()
            )

            flash(
                "Produto atualizado com sucesso.",
                "success",
            )

            return redirect(url_for("admin"))

        except Exception as erro:
            flash(
                f"Erro ao atualizar produto: {erro}",
                "danger",
            )

    return render_template(
        "produto_form.html",
        produto=produto,
        categorias=categorias,
    )


# ==========================================================
# DUPLICAR PRODUTO
# ==========================================================

@app.route(
    "/admin/produto/<int:produto_id>/duplicar",
    methods=["POST"],
)
@admin_required
def duplicar_produto(produto_id):
    produto = buscar_produto(produto_id)

    if not produto:
        flash(
            "Produto não encontrado.",
            "danger",
        )
        return redirect(url_for("admin"))

    dados = {
        "nome": f"{produto.get('nome', '')} - Cópia",
        "descricao": produto.get("descricao"),
        "categoria_id": produto.get("categoria_id"),
        "preco": produto.get("preco"),
        "imagem_url": produto.get("imagem_url"),
        "link_afiliado": produto.get("link_afiliado"),
        "plataforma": produto.get(
            "plataforma",
            "Amazon",
        ),
        "ativo": False,
        "destaque": False,
    }

    try:
        (
            supabase
            .table("produtos")
            .insert(dados)
            .execute()
        )

        flash(
            "Produto duplicado. A cópia foi criada desativada.",
            "success",
        )

    except Exception as erro:
        flash(
            f"Erro ao duplicar produto: {erro}",
            "danger",
        )

    return redirect(url_for("admin"))


# ==========================================================
# ATIVAR / DESATIVAR PRODUTO
# ==========================================================

@app.route(
    "/admin/produto/<int:produto_id>/alternar",
    methods=["POST"],
)
@admin_required
def alternar_produto(produto_id):
    produto = buscar_produto(produto_id)

    if not produto:
        flash(
            "Produto não encontrado.",
            "danger",
        )
        return redirect(url_for("admin"))

    novo_status = not bool(
        produto.get("ativo")
    )

    try:
        (
            supabase
            .table("produtos")
            .update({"ativo": novo_status})
            .eq("id", produto_id)
            .execute()
        )

        flash(
            "Produto ativado."
            if novo_status
            else "Produto desativado.",
            "success",
        )

    except Exception as erro:
        flash(
            f"Erro ao alterar produto: {erro}",
            "danger",
        )

    return redirect(url_for("admin"))


# ==========================================================
# DESATIVAR PRODUTO
# Mantida para compatibilidade com o admin.html atual.
# ==========================================================

@app.route(
    "/admin/produto/<int:produto_id>/desativar",
    methods=["POST"],
)
@admin_required
def desativar_produto(produto_id):
    try:
        (
            supabase
            .table("produtos")
            .update({"ativo": False})
            .eq("id", produto_id)
            .execute()
        )

        flash(
            "Produto desativado.",
            "success",
        )

    except Exception as erro:
        flash(
            f"Erro ao desativar produto: {erro}",
            "danger",
        )

    return redirect(url_for("admin"))


# ==========================================================
# ALTERNAR DESTAQUE
# ==========================================================

@app.route(
    "/admin/produto/<int:produto_id>/destaque",
    methods=["POST"],
)
@admin_required
def alternar_destaque(produto_id):
    produto = buscar_produto(produto_id)

    if not produto:
        flash(
            "Produto não encontrado.",
            "danger",
        )
        return redirect(url_for("admin"))

    novo_destaque = not bool(
        produto.get("destaque")
    )

    try:
        (
            supabase
            .table("produtos")
            .update({"destaque": novo_destaque})
            .eq("id", produto_id)
            .execute()
        )

        flash(
            "Destaque do produto atualizado.",
            "success",
        )

    except Exception as erro:
        flash(
            f"Erro ao alterar destaque: {erro}",
            "danger",
        )

    return redirect(url_for("admin"))



# ==========================================================
# CARRINHO LOCAL E TESTE AMAZON
# ==========================================================
def obter_carrinho():
    c=session.get('carrinho',[])
    return c if isinstance(c,list) else []

def salvar_carrinho(c): session['carrinho']=c; session.modified=True

def produto_publico_por_nome(nome):
    if nome==AURAFIT_TESTE['nome']: return produto_teste_aurafit()
    try:
        r=supabase.table('produtos').select('*').eq('nome',nome).eq('ativo',True).limit(1).execute()
        return (r.data or [None])[0]
    except Exception: return None

def item_carrinho(p):
    plataforma = str(p.get('plataforma') or 'Nossa Loja').strip()
    return {'id':str(p.get('id')),'nome':p.get('nome','Produto'),'descricao':p.get('descricao') or '', 'preco':float(p.get('preco') or 0),'imagem_url':p.get('imagem_url') or '', 'link_afiliado':p.get('link_afiliado') or '', 'plataforma':plataforma,'asin':p.get('asin') or '','quantidade':1}

def tipo_produto(i):
    p=str(i.get('plataforma') or '').strip().lower()
    if p == 'nossa loja': return 'proprio'
    if 'mercado livre' in p: return 'mercadolivre'
    if 'amazon' in p: return 'amazon'
    return 'outro'

@app.route('/carrinho')
def carrinho():
    itens=obter_carrinho()
    total_proprio=sum(float(i.get('preco') or 0)*int(i.get('quantidade') or 0) for i in itens if tipo_produto(i)=='proprio')
    total_geral=sum(float(i.get('preco') or 0)*int(i.get('quantidade') or 0) for i in itens)
    partes=[]; itens_amazon=[]
    for i in itens:
        nome=html.escape(str(i.get('nome') or 'Produto')); q=int(i.get('quantidade') or 1); pid=quote(str(i.get('id')),safe=''); img=i.get('imagem_url'); tipo=tipo_produto(i)
        foto=f'<img src="{html.escape(str(img))}" alt="{nome}">' if img else '<div class="cart-sem-imagem">📦</div>'
        badge={'proprio':'🏪 Produto próprio','mercadolivre':'🛒 Mercado Livre Afiliado','amazon':'🟠 Amazon Afiliado'}.get(tipo,'Produto')
        preco=f'R$ {float(i.get("preco") or 0):,.2f}' if i.get('preco') else 'Preço não informado'
        link=str(i.get('link_afiliado') or '')
        acao=''
        if tipo=='mercadolivre' and link:
            acao=f'<div class="cart-affiliate"><a class="cart-btn" href="{html.escape(link)}" target="_blank" rel="nofollow sponsored noopener">🛒 Comprar no Mercado Livre</a></div>'
        elif tipo=='amazon':
            asin=i.get('asin') or ''
            if not asin:
                m=re.search(r'/dp/([A-Z0-9]{10})',link,re.I); asin=m.group(1) if m else ''
            if asin and re.fullmatch(r'[A-Z0-9]{10}',asin): itens_amazon.append((asin,q))
            if link:
                acao=f'<div class="cart-affiliate"><a class="cart-btn" href="{html.escape(link)}" target="_blank" rel="nofollow sponsored noopener">🟠 Comprar na Amazon</a></div>'
        partes.append(f'<article class="cart-card">{foto}<div class="cart-info"><div class="tipo-produto-badge">{badge}</div><h3>{nome}</h3><p>{preco} · Quantidade: {q}</p><div class="cart-actions"><div class="qty-control"><a href="/carrinho/menos?id={pid}">−</a><span>{q}</span><a href="/carrinho/mais?id={pid}">+</a></div><a class="cart-btn danger" href="/carrinho/remover?id={pid}">Remover</a></div>{acao}</div></article>')
    corpo=''.join(partes) if partes else '<div class="cart-empty"><h2>Seu carrinho está vazio</h2><p>Escolha um produto e toque em <b>Adicionar ao carrinho</b>.</p><a class="cart-btn" href="/produtos">Ver produtos</a></div>'
    campos_amazon=''.join(f'<input type="hidden" name="ASIN.{n}" value="{html.escape(a)}"><input type="hidden" name="Quantity.{n}" value="{q}">' for n,(a,q) in enumerate(itens_amazon,1))
    amazon=f'<form method="POST" action="/amazon/adicionar-carrinho" style="display:inline-flex;flex-wrap:wrap;gap:8px"><input type="hidden" name="AssociateTag" value="pedro0ba1e-20">{campos_amazon}<button class="cart-btn" type="submit">🟠 Tentar adicionar Amazon</button></form>' if itens_amazon else ''
    proprio=[i for i in itens if tipo_produto(i)=='proprio']
    checkout_link='<a class="cart-btn checkout-own" href="/checkout">💳 Finalizar compra</a>' if proprio and total_proprio>0 else ''
    aviso=''
    if proprio and total_proprio<=0: aviso='<p class="checkout-note" style="width:100%;margin:0 0 8px">Seu produto próprio precisa ter um preço maior que R$ 0,00 para habilitar o pagamento.</p>'
    if any(tipo_produto(i) in ('amazon','mercadolivre') for i in itens): aviso += '<p class="checkout-note" style="width:100%;margin:0 0 8px">Produtos afiliados são pagos diretamente na plataforma indicada. O Mercado Pago da Nossa Loja cobra somente produtos próprios.</p>'
    total_text=f'R$ {total_geral:,.2f}'; proprio_text=f'R$ {total_proprio:,.2f}'
    pagina=f'''<!doctype html><html lang="pt-br"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Carrinho — Nossa Loja</title><link rel="stylesheet" href="/static/style.css">{CARRINHO_STYLE}</head><body><header><div class="container"><h1>🛒 Nossa Loja</h1><nav></nav></div></header><main class="container"><div class="cart-page"><div class="hero"><h2>Seu carrinho</h2><p>Você pode misturar produtos próprios e recomendações de afiliados. Cada tipo segue seu próprio pagamento.</p></div>{corpo}'''
    if itens:
        pagina+=f'<div class="cart-total"><div><span>Total dos itens</span><br><strong>{total_text}</strong><br><small style="opacity:.82">Pagamento próprio: {proprio_text}</small></div><div style="width:100%;display:flex;flex-wrap:wrap;gap:9px;align-items:center">{aviso}{checkout_link}{amazon}<a class="cart-btn secondary" href="/produtos">+ Continuar comprando</a><a class="cart-btn danger" href="/carrinho/limpar">Limpar carrinho</a></div></div>'
    pagina+='</div></main></body></html>'
    return pagina

@app.route('/carrinho/adicionar')
def carrinho_adicionar():
    nome=unquote(request.args.get('nome','')).strip(); p=produto_publico_por_nome(nome)
    if not p: return redirect(url_for('produtos'))
    c=obter_carrinho(); pid=str(p.get('id'))
    for i in c:
        if str(i.get('id'))==pid: i['quantidade']=int(i.get('quantidade') or 0)+1; salvar_carrinho(c); return redirect(url_for('carrinho'))
    c.append(item_carrinho(p)); salvar_carrinho(c); return redirect(url_for('carrinho'))

@app.route('/carrinho/mais')
def carrinho_mais():
    pid=request.args.get('id',''); c=obter_carrinho()
    for i in c:
        if str(i.get('id'))==pid: i['quantidade']=int(i.get('quantidade') or 0)+1
    salvar_carrinho(c); return redirect(url_for('carrinho'))

@app.route('/carrinho/menos')
def carrinho_menos():
    pid=request.args.get('id',''); novo=[]
    for i in obter_carrinho():
        if str(i.get('id'))==pid:
            q=int(i.get('quantidade') or 1)-1
            if q>0: i['quantidade']=q; novo.append(i)
        else: novo.append(i)
    salvar_carrinho(novo); return redirect(url_for('carrinho'))

@app.route('/carrinho/remover')
def carrinho_remover():
    pid=request.args.get('id',''); salvar_carrinho([i for i in obter_carrinho() if str(i.get('id'))!=pid]); return redirect(url_for('carrinho'))

@app.route('/carrinho/limpar')
def carrinho_limpar(): salvar_carrinho([]); return redirect(url_for('carrinho'))

# ==========================================================
# CLIENTES, PEDIDOS E ENTREGA
# ==========================================================

ESTADOS_BR = ["AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"]

def normalizar_telefone(valor):
    return re.sub(r"[^0-9+() -]", "", str(valor or "").strip())[:30]

def normalizar_cep(valor):
    return re.sub(r"[^0-9]", "", str(valor or ""))[:8]

def cliente_formulario():
    return {
        "nome": texto_formulario("nome_cliente"),
        "email": texto_formulario("email").lower(),
        "telefone": normalizar_telefone(request.form.get("telefone")),
        "cep": normalizar_cep(request.form.get("cep")),
        "endereco": texto_formulario("endereco"),
        "numero": texto_formulario("numero"),
        "complemento": texto_formulario("complemento"),
        "bairro": texto_formulario("bairro"),
        "cidade": texto_formulario("cidade"),
        "estado": texto_formulario("estado").upper(),
        "metodo_envio": texto_formulario("metodo_envio", "Entrega local"),
    }

def validar_cliente_form(dados):
    obrigatorios={"nome":"nome completo","email":"e-mail","telefone":"telefone","cep":"CEP","endereco":"endereço","numero":"número","bairro":"bairro","cidade":"cidade","estado":"estado"}
    for chave,nome in obrigatorios.items():
        if not dados.get(chave): raise ValueError(f"Preencha o campo {nome}.")
    if "@" not in dados["email"] or "." not in dados["email"].split("@")[-1]: raise ValueError("Digite um e-mail válido.")
    if len(dados["cep"]) != 8: raise ValueError("Digite um CEP válido com 8 números.")
    if dados["estado"] not in ESTADOS_BR: raise ValueError("Selecione um estado válido.")
    if dados["metodo_envio"] not in ("Entrega local","Correios/transportadora","Retirada"): dados["metodo_envio"]="Entrega local"

def salvar_cliente(dados):
    registro={"nome":dados["nome"],"email":dados["email"][:180],"telefone":dados["telefone"],"cep":dados["cep"],"endereco":dados["endereco"],"numero":dados["numero"],"complemento":dados["complemento"],"bairro":dados["bairro"],"cidade":dados["cidade"],"estado":dados["estado"]}
    resultado=supabase.table("clientes").upsert(registro,on_conflict="email").execute()
    dados_resultado=resultado.data or []
    if not dados_resultado:
        resultado=supabase.table("clientes").select("*").eq("email",registro["email"]).limit(1).execute()
        dados_resultado=resultado.data or []
    if not dados_resultado: raise RuntimeError("Não consegui salvar o cadastro do cliente no Supabase.")
    return dados_resultado[0]

def criar_pedido_local(cliente,dados_cliente,itens):
    total=sum(Decimal(str(i.get("preco") or 0))*max(1,int(i.get("quantidade") or 1)) for i in itens)
    pedido={"cliente_id":cliente.get("id"),"status_pedido":"Novo","status_pagamento":"Aguardando pagamento","status_envio":"Aguardando","total":f"{total:.2f}","metodo_envio":dados_cliente["metodo_envio"],"frete":"0.00","cep_entrega":dados_cliente["cep"],"endereco_entrega":dados_cliente["endereco"],"numero_entrega":dados_cliente["numero"],"complemento_entrega":dados_cliente["complemento"],"bairro_entrega":dados_cliente["bairro"],"cidade_entrega":dados_cliente["cidade"],"estado_entrega":dados_cliente["estado"],"observacao":""}
    resultado=supabase.table("pedidos").insert(pedido).execute()
    pedido_data=(resultado.data or [None])[0]
    if not pedido_data: raise RuntimeError("Não consegui criar o pedido no Supabase.")
    linhas=[]
    for i in itens:
        try: pid=int(i.get("id"))
        except (TypeError,ValueError): pid=None
        linhas.append({"pedido_id":pedido_data["id"],"produto_id":pid,"nome_produto":str(i.get("nome") or "Produto")[:200],"quantidade":max(1,int(i.get("quantidade") or 1)),"preco_unitario":f"{Decimal(str(i.get('preco') or 0)).quantize(Decimal('0.01')):.2f}","plataforma":str(i.get("plataforma") or "Nossa Loja")[:60]})
    supabase.table("pedido_itens").insert(linhas).execute()
    return pedido_data

def atualizar_pedido_mercadopago(pedido_id,order):
    supabase.table("pedidos").update({"mp_order_id":str(order.get("id") or "")[:200],"external_reference":str(order.get("external_reference") or "")[:200]}).eq("id",pedido_id).execute()

def buscar_pedidos_admin():
    pedidos=supabase.table("pedidos").select("*").order("id",desc=True).execute().data or []
    clientes=supabase.table("clientes").select("id,nome,email,telefone,cidade,estado").execute().data or []
    mapa={str(c.get("id")):c for c in clientes}
    for p in pedidos: p["cliente"]=mapa.get(str(p.get("cliente_id")),{})
    return pedidos

def status_classe(status):
    s=str(status or "").lower()
    if "pago" in s or "enviado" in s or "entregue" in s: return "pago"
    if "aguard" in s or "pendente" in s: return "pendente"
    if "cancel" in s: return "cancelado"
    return ""

# ==========================================================
# CHECKOUT / MERCADO PAGO
# ==========================================================

def itens_permitidos_pagamento():
    # Somente produtos cadastrados como "Nossa Loja" são cobrados pelo nosso Mercado Pago.
    return [i for i in obter_carrinho() if tipo_produto(i) == 'proprio']



def buscar_order_mercadopago(order_id):
    if not MERCADOPAGO_ACCESS_TOKEN or not order_id:
        return None
    req=urllib.request.Request(
        f'https://api.mercadopago.com/v1/orders/{quote(str(order_id), safe="")}',
        method='GET',
        headers={'Accept':'application/json','Authorization':f'Bearer {MERCADOPAGO_ACCESS_TOKEN}'},
    )
    try:
        with urllib.request.urlopen(req,timeout=20) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception:
        return None


def validar_webhook_mp():
    """Valida x-signature quando o segredo do Webhook estiver configurado."""
    if not MERCADOPAGO_WEBHOOK_SECRET:
        return False
    signature=request.headers.get('x-signature','')
    request_id=request.headers.get('x-request-id','')
    data_id=(request.args.get('data.id') or '').lower()
    if not signature or not request_id or not data_id:
        return False
    partes={}
    for item in signature.split(','):
        if '=' in item:
            k,v=item.split('=',1); partes[k.strip()]=v.strip()
    ts=partes.get('ts',''); v1=partes.get('v1','')
    if not ts or not v1: return False
    manifest=f'id:{data_id};request-id:{request_id};ts:{ts};'
    esperado=hmac.new(MERCADOPAGO_WEBHOOK_SECRET.encode('utf-8'),manifest.encode('utf-8'),hashlib.sha256).hexdigest()
    return hmac.compare_digest(esperado,v1)


def atualizar_pedido_por_order_mp(order):
    order_id=str(order.get('id') or '')
    if not order_id: return
    status=str(order.get('status') or '').lower()
    detalhe=str(order.get('status_detail') or '')
    if status=='processed': pagamento='Pago'
    elif status in ('processing','created','action_required'): pagamento='Aguardando pagamento'
    elif status in ('failed','canceled','expired'): pagamento='Recusado' if status=='failed' else 'Cancelado'
    elif status in ('refunded','charged_back'): pagamento='Reembolsado'
    else: pagamento=status or 'Aguardando pagamento'
    dados={'status_pagamento':pagamento}
    if pagamento=='Pago': dados['status_pedido']='Pago — aguardando preparação'
    if detalhe: dados['observacao']=f'Mercado Pago: {detalhe}'[:500]
    supabase.table('pedidos').update(dados).eq('mp_order_id',order_id).execute()

def criar_order_mercadopago(itens, email=''):
    if not MERCADOPAGO_ACCESS_TOKEN:
        raise RuntimeError('Mercado Pago ainda não está configurado no Render. Adicione MERCADOPAGO_ACCESS_TOKEN.')
    total=Decimal('0')
    nomes=[]
    for i in itens:
        qtd=max(1,int(i.get('quantidade') or 1))
        preco=Decimal(str(i.get('preco') or 0)).quantize(Decimal('0.01'))
        if preco<=0: continue
        total += preco*qtd
        nomes.append(f"{str(i.get('nome') or 'Produto')[:60]} x{qtd}")
    if total<=0:
        raise RuntimeError('O carrinho não possui produtos com preço válido para pagamento.')
    # A API atual exige apenas os campos suportados no item. Além disso,
    # algumas contas/fluxos do Checkout Pro aceitam uma única transação por order.
    # Por isso consolidamos o carrinho em um único item cujo preço é o total.
    item_titulo=('Compra Nossa Loja: ' + ', '.join(nomes))[:120]
    itens_mp=[{'title':item_titulo,'unit_price':f'{total:.2f}','quantity':1}]
    base = request.url_root.rstrip('/')
    config={'online':{'success_url':f'{base}/pagamento/sucesso','failure_url':f'{base}/pagamento/erro','pending_url':f'{base}/pagamento/pendente','auto_return':'approved'}}
    if MERCADOPAGO_WEBHOOK_SECRET:
        config['notification_url']=f'{base}/webhooks/mercadopago'
    body={'type':'online','processing_mode':'manual','capture_mode':'automatic_async','total_amount':f'{total:.2f}','external_reference':f'nossa-loja-{uuid.uuid4().hex[:20]}','description':'Compra - Nossa Loja','items':itens_mp,'config':config}
    if email: body['payer']={'email':email[:180]}
    req=urllib.request.Request('https://api.mercadopago.com/v1/orders',data=json.dumps(body).encode('utf-8'),method='POST',headers={'Accept':'application/json','Content-Type':'application/json','Authorization':f'Bearer {MERCADOPAGO_ACCESS_TOKEN}','X-Idempotency-Key':str(uuid.uuid4())})
    try:
        with urllib.request.urlopen(req,timeout=25) as resp: return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        detalhe=e.read().decode('utf-8',errors='replace'); raise RuntimeError(f'Mercado Pago recusou a criação do pagamento ({e.code}). {detalhe[:500]}')
    except urllib.error.URLError as e:
        raise RuntimeError(f'Não consegui conectar ao Mercado Pago: {e.reason}')


@app.route('/checkout', methods=['GET','POST'])
def checkout():
    itens=itens_permitidos_pagamento()
    if not itens:
        return """<!doctype html><html lang="pt-br"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Pagamento - Nossa Loja</title>""" + CARRINHO_STYLE + CLIENTE_STYLE + """</head><body><main class="container"><div class="cliente-box"><h2>💳 Pagamento da Nossa Loja</h2><p>Não há produtos próprios com preço válido no carrinho.</p><p>Produtos Amazon e Mercado Livre são pagos diretamente nas respectivas plataformas.</p><a class="cart-btn" href="/carrinho">← Voltar ao carrinho</a></div></main></body></html>"""
    erro=''
    dados=cliente_formulario() if request.method=='POST' else dict(session.get('cliente_checkout') or {})
    if request.method=='POST':
        try:
            validar_cliente_form(dados)
            if not request.form.get('aceite_dados'): raise ValueError('Marque a autorização para uso dos dados necessários ao pedido e à entrega.')
            cliente=salvar_cliente(dados)
            pedido=criar_pedido_local(cliente,dados,itens)
            order=criar_order_mercadopago(itens,dados['email'])
            checkout_url=order.get('checkout_url') or ''
            if not checkout_url: raise RuntimeError('O Mercado Pago não devolveu a URL do checkout.')
            atualizar_pedido_mercadopago(pedido['id'],order)
            session['cliente_checkout']=dados
            session['ultimo_mp_order']=order.get('id','')
            session['ultimo_pedido_id']=pedido.get('id','')
            session['ultimo_mp_total']=float(pedido.get('total') or 0)
            session.modified=True
            return redirect(checkout_url)
        except Exception as e:
            erro=str(e)
            try:
                if 'pedido' in locals() and pedido and pedido.get('id'):
                    supabase.table('pedidos').update({'status_pagamento':'Erro na criação do pagamento','status_pedido':'Aguardando correção','observacao':str(e)[:500]}).eq('id',pedido['id']).execute()
            except Exception:
                pass
            session['cliente_checkout']=dados
    total=sum(float(i.get('preco') or 0)*int(i.get('quantidade') or 1) for i in itens)
    resumo=''.join(f'<li>{html.escape(str(i.get("nome")))} × {int(i.get("quantidade") or 1)} - R$ {float(i.get("preco") or 0)*int(i.get("quantidade") or 1):,.2f}</li>' for i in itens)
    aviso='' if MERCADOPAGO_ACCESS_TOKEN else '<div class="pagamento-erro"><b>Pagamento ainda não ativado.</b><br>No Render, adicione <code>MERCADOPAGO_ACCESS_TOKEN</code>.</div>'
    erro_html=f'<div class="pagamento-erro">{html.escape(erro)}</div>' if erro else ''
    def val(k): return html.escape(str(dados.get(k,'') or ''))
    estados=''.join(f'<option value="{e}" {"selected" if dados.get("estado")==e else ""}>{e}</option>' for e in ESTADOS_BR)
    metodos=''.join(f'<option value="{m}" {"selected" if dados.get("metodo_envio","Entrega local")==m else ""}>{m}</option>' for m in ("Entrega local","Correios/transportadora","Retirada"))
    return f'''<!doctype html><html lang="pt-br"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Finalizar compra - Nossa Loja</title>{CARRINHO_STYLE}{CLIENTE_STYLE}</head><body><main class="container"><div class="cliente-box"><h1>📦 Finalizar compra</h1><p>Preencha seus dados para o pedido e, quando houver entrega, para o envio.</p>{aviso}{erro_html}<div class="frete-nota">🔒 O pagamento acontece no ambiente seguro do Mercado Pago. A Nossa Loja guarda somente os dados necessários para atendimento, pedido e entrega.</div><form class="checkout-form" method="post"><div class="cliente-section" style="margin-top:8px;border-top:0"><h2>👤 Seus dados</h2><div class="cliente-grid"><div class="cliente-field full"><label>Nome completo *</label><input name="nome_cliente" value="{val('nome')}" required></div><div class="cliente-field"><label>E-mail *</label><input type="email" name="email" value="{val('email')}" required></div><div class="cliente-field"><label>Telefone *</label><input name="telefone" value="{val('telefone')}" placeholder="(48) 99999-9999" required></div></div></div><div class="cliente-section"><h2>🚚 Dados de entrega</h2><div class="cliente-grid"><div class="cliente-field"><label>CEP *</label><input name="cep" inputmode="numeric" maxlength="9" value="{val('cep')}" placeholder="88100-000" required></div><div class="cliente-field"><label>Estado *</label><select name="estado" required><option value="">Selecione</option>{estados}</select></div><div class="cliente-field full"><label>Endereço *</label><input name="endereco" value="{val('endereco')}" required></div><div class="cliente-field"><label>Número *</label><input name="numero" value="{val('numero')}" required></div><div class="cliente-field"><label>Complemento</label><input name="complemento" value="{val('complemento')}" placeholder="Apto, casa, sala..."></div><div class="cliente-field"><label>Bairro *</label><input name="bairro" value="{val('bairro')}" required></div><div class="cliente-field"><label>Cidade *</label><input name="cidade" value="{val('cidade')}" required></div><div class="cliente-field full"><label>Como prefere receber?</label><select name="metodo_envio">{metodos}</select></div></div></div><div class="cliente-section"><h2>🧾 Resumo</h2><ul>{resumo}</ul><h2>Total: R$ {total:,.2f}</h2></div><label class="consentimento"><input type="checkbox" name="aceite_dados" required> <span>Autorizo o uso desses dados para processar minha compra, atendimento e entrega deste pedido.</span></label><button class="cart-btn checkout-own" type="submit">🔒 Continuar para o Mercado Pago</button></form><p class="checkout-note">Depois deste formulário você será levado ao ambiente seguro do Mercado Pago para concluir o pagamento.</p><a class="cart-btn secondary" href="/carrinho">← Voltar ao carrinho</a></div></main></body></html>'''


@app.route('/webhooks/mercadopago', methods=['POST'])
def webhook_mercadopago():
    if not validar_webhook_mp():
        return jsonify({'status':'unauthorized'}), 401
    order_id=request.args.get('data.id') or ((request.get_json(silent=True) or {}).get('data') or {}).get('id')
    order=buscar_order_mercadopago(order_id)
    if order:
        try:
            atualizar_pedido_por_order_mp(order)
        except Exception:
            pass
    return jsonify({'status':'ok'}), 200


@app.route('/pagamento/sucesso')
def pagamento_sucesso():
    return '''<!doctype html><html lang="pt-br"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Pagamento - Nossa Loja</title>''' + CARRINHO_STYLE + '''</head><body><main class="container"><div class="pagamento-ok"><h1>✅ Pagamento concluído</h1><p>Recebemos seu retorno do Mercado Pago.</p><a class="cart-btn" href="/">Voltar para a loja</a></div></main></body></html>'''

@app.route('/pagamento/pendente')
def pagamento_pendente():
    return '''<!doctype html><html lang="pt-br"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Pagamento pendente - Nossa Loja</title>''' + CARRINHO_STYLE + '''</head><body><main class="container"><div class="pagamento-box"><h1>⏳ Pagamento pendente</h1><p>O pagamento ainda está sendo processado.</p><a class="cart-btn" href="/carrinho">Voltar ao carrinho</a></div></main></body></html>'''

@app.route('/pagamento/erro')
def pagamento_erro():
    return '''<!doctype html><html lang="pt-br"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Pagamento - Nossa Loja</title>''' + CARRINHO_STYLE + '''</head><body><main class="container"><div class="pagamento-erro"><h1>❌ Pagamento não concluído</h1><p>Você pode voltar ao carrinho e tentar novamente.</p><a class="cart-btn" href="/carrinho">Voltar ao carrinho</a></div></main></body></html>'''


@app.route('/amazon/adicionar-carrinho', methods=['GET','POST'])
def amazon_adicionar_carrinho():
    tag='pedro0ba1e-20'
    itens=[]
    if request.method=='POST':
        n=1
        while request.form.get(f'ASIN.{n}'):
            asin=str(request.form.get(f'ASIN.{n}','')).upper()
            try: qtd=max(1,int(request.form.get(f'Quantity.{n}',1)))
            except ValueError: qtd=1
            if re.fullmatch(r'[A-Z0-9]{10}',asin): itens.append((asin,qtd))
            n+=1
    if not itens:
        for i in obter_carrinho():
            asin=i.get('asin') or ''
            if not asin:
                m=re.search(r'/dp/([A-Z0-9]{10})',str(i.get('link_afiliado') or ''),re.I)
                asin=m.group(1) if m else ''
            if asin and re.fullmatch(r'[A-Z0-9]{10}',asin): itens.append((asin,int(i.get('quantidade') or 1)))
    if not itens: return redirect(url_for('carrinho'))
    campos=''.join(f'<input type="hidden" name="AssociateTag" value="{html.escape(tag)}"><input type="hidden" name="ASIN.{n}" value="{html.escape(a)}"><input type="hidden" name="Quantity.{n}" value="{q}">' for n,(a,q) in enumerate(itens,1))
    primeiro=itens[0][0]
    fallback=f'https://www.amazon.com.br/dp/{primeiro}?tag={tag}'
    return f'''<!doctype html><html lang="pt-br"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Carrinho Amazon</title></head><body style="font-family:Arial;text-align:center;padding:30px"><h2>🛒 Enviando {len(itens)} produto(s) para o carrinho da Amazon...</h2><p>Se a Amazon aceitar o endpoint de carrinho, os itens serão enviados juntos.</p><form id="f" method="POST" action="https://www.amazon.com.br/gp/aws/cart/add.html">{campos}<button type="submit" style="padding:15px 22px;border:0;border-radius:12px;background:#111827;color:#fff;font-weight:700">Adicionar ao carrinho da Amazon</button></form><p><a href="{fallback}">Abrir produto na Amazon</a></p><script>document.getElementById('f').submit()</script></body></html>'''

@app.route('/amazon/adicionar/<asin>')
def amazon_adicionar(asin):
    asin=str(asin).upper()
    if not re.fullmatch(r'[A-Z0-9]{10}',asin): return redirect(url_for('produtos'))
    return redirect(url_for('amazon_adicionar_carrinho'))


@app.route('/admin/pedidos', methods=['GET','POST'])
@admin_required
def admin_pedidos():
    if request.method=='POST':
        try: pedido_id=int(request.form.get('pedido_id','0'))
        except ValueError: pedido_id=0
        if pedido_id:
            atualizacoes={}
            for campo in ('status_pedido','status_pagamento','status_envio','metodo_envio','transportadora','codigo_rastreio','previsao_entrega','observacao'):
                if campo in request.form: atualizacoes[campo]=texto_formulario(campo)
            if 'frete' in request.form:
                try: atualizacoes['frete']=f"{converter_preco(request.form.get('frete')):.2f}"
                except Exception: pass
            try: supabase.table('pedidos').update(atualizacoes).eq('id',pedido_id).execute(); flash('Pedido atualizado.','success')
            except Exception as erro: flash(f'Erro ao atualizar pedido: {erro}','danger')
        return redirect(url_for('admin_pedidos'))
    try: pedidos=buscar_pedidos_admin()
    except Exception as erro: pedidos=[]; flash(f'Ative as tabelas de clientes/pedidos no Supabase: {erro}','warning')
    linhas=[]
    for p in pedidos:
        c=p.get('cliente') or {}
        linhas.append(f'''<tr><td><b>#{p.get('id')}</b><br><small>{html.escape(str(p.get('created_at') or ''))[:19]}</small></td><td>{html.escape(str(c.get('nome') or ''))}<br><small>{html.escape(str(c.get('email') or ''))}</small><br><small>{html.escape(str(c.get('telefone') or ''))}</small></td><td>R$ {float(p.get('total') or 0):,.2f}</td><td><span class="pedido-status {status_classe(p.get('status_pagamento'))}">{html.escape(str(p.get('status_pagamento') or ''))}</span><br><span class="pedido-status {status_classe(p.get('status_envio'))}">{html.escape(str(p.get('status_envio') or ''))}</span></td><td>{html.escape(str(p.get('metodo_envio') or ''))}<br>{html.escape(str(p.get('endereco_entrega') or ''))}, {html.escape(str(p.get('numero_entrega') or ''))}<br>{html.escape(str(p.get('bairro_entrega') or ''))}<br>{html.escape(str(p.get('cidade_entrega') or ''))}/{html.escape(str(p.get('estado_entrega') or ''))} — {html.escape(str(p.get('cep_entrega') or ''))}<details style="margin-top:8px"><summary>Atualizar envio/pedido</summary><form class="pedido-form" method="post"><input type="hidden" name="pedido_id" value="{p.get('id')}"><select name="status_pedido"><option {'selected' if p.get('status_pedido')=='Novo' else ''}>Novo</option><option {'selected' if p.get('status_pedido')=='Em preparação' else ''}>Em preparação</option><option {'selected' if p.get('status_pedido')=='Enviado' else ''}>Enviado</option><option {'selected' if p.get('status_pedido')=='Entregue' else ''}>Entregue</option><option {'selected' if p.get('status_pedido')=='Cancelado' else ''}>Cancelado</option></select><select name="status_pagamento"><option {'selected' if p.get('status_pagamento')=='Aguardando pagamento' else ''}>Aguardando pagamento</option><option {'selected' if p.get('status_pagamento')=='Pago' else ''}>Pago</option><option {'selected' if p.get('status_pagamento')=='Recusado' else ''}>Recusado</option></select><select name="status_envio"><option {'selected' if p.get('status_envio')=='Aguardando' else ''}>Aguardando</option><option {'selected' if p.get('status_envio')=='Em preparação' else ''}>Em preparação</option><option {'selected' if p.get('status_envio')=='Enviado' else ''}>Enviado</option><option {'selected' if p.get('status_envio')=='Entregue' else ''}>Entregue</option></select><input name="transportadora" placeholder="Transportadora" value="{html.escape(str(p.get('transportadora') or ''))}"><input name="codigo_rastreio" placeholder="Código de rastreio" value="{html.escape(str(p.get('codigo_rastreio') or ''))}"><input name="previsao_entrega" placeholder="Previsão de entrega" value="{html.escape(str(p.get('previsao_entrega') or ''))}"><input name="frete" placeholder="Frete" value="{html.escape(str(p.get('frete') or '0'))}"><input name="observacao" placeholder="Observação" value="{html.escape(str(p.get('observacao') or ''))}"><button class="botao" type="submit">Salvar pedido</button></form></details></td></tr>''')
    tabela=''.join(linhas) or '<tr><td colspan="5">Nenhum pedido cadastrado ainda.</td></tr>'
    return f'''<!doctype html><html lang="pt-br"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Pedidos — Nossa Loja</title>{PAINEL_STYLE}{CLIENTE_STYLE}</head><body><main class="container"><div class="admin-top"><div><h2>🛍 Pedidos</h2><p>Pedidos, clientes e estrutura de envio.</p></div><a class="botao" href="/admin">← Voltar ao painel</a></div><div class="admin-link-grid"><a class="admin-link-card" href="/admin/clientes"><strong>👥 Clientes</strong><span>Consultar cadastros de compradores.</span></a><a class="admin-link-card" href="/admin"><strong>📦 Produtos</strong><span>Voltar ao catálogo.</span></a></div><div class="tabela-container pedido-table-wrap"><table class="pedido-table"><thead><tr><th>Pedido</th><th>Cliente</th><th>Total</th><th>Status</th><th>Entrega / atualização</th></tr></thead><tbody>{tabela}</tbody></table></div></main></body></html>'''

@app.route('/admin/clientes')
@admin_required
def admin_clientes():
    try: clientes=supabase.table('clientes').select('*').order('id',desc=True).execute().data or []
    except Exception as erro: clientes=[]; flash(f'Ative a tabela clientes no Supabase: {erro}','warning')
    linhas=''.join(f'''<tr><td>{html.escape(str(c.get('nome') or ''))}</td><td>{html.escape(str(c.get('email') or ''))}<br>{html.escape(str(c.get('telefone') or ''))}</td><td>{html.escape(str(c.get('endereco') or ''))}, {html.escape(str(c.get('numero') or ''))}<br>{html.escape(str(c.get('bairro') or ''))}<br>{html.escape(str(c.get('cidade') or ''))}/{html.escape(str(c.get('estado') or ''))} — {html.escape(str(c.get('cep') or ''))}</td></tr>''' for c in clientes) or '<tr><td colspan="3">Nenhum cliente cadastrado.</td></tr>'
    return f'''<!doctype html><html lang="pt-br"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Clientes — Nossa Loja</title>{PAINEL_STYLE}{CLIENTE_STYLE}</head><body><main class="container"><div class="admin-top"><div><h2>👥 Clientes</h2><p>Dados usados para atendimento e entrega.</p></div><a class="botao" href="/admin/pedidos">← Voltar aos pedidos</a></div><div class="tabela-container pedido-table-wrap"><table class="pedido-table"><thead><tr><th>Cliente</th><th>Contato</th><th>Endereço</th></tr></thead><tbody>{linhas}</tbody></table></div><p class="checkout-note">Use esses dados somente para finalidades necessárias ao atendimento, pedido e entrega.</p></main></body></html>'''

@app.route('/admin/como-vender')
@admin_required
def como_vender():
    return f'''<!doctype html><html lang="pt-br"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Como cadastrar produtos — Nossa Loja</title>{PAINEL_STYLE}</head><body><main class="container"><div class="admin-top"><div><h2>🧭 Como cadastrar produtos</h2><p>Use o tipo certo para que cada botão leve ao pagamento correto.</p></div><a class="botao" href="/admin">← Voltar ao painel</a></div><div class="senha-box"><h3>🏪 1. Produto próprio</h3><p>Você tem o estoque ou presta o serviço. Cadastre <b>Plataforma = Nossa Loja</b>, informe o preço e deixe o link de afiliado vazio. O botão do carrinho será <b>Finalizar compra</b> e o pagamento será feito no Mercado Pago.</p><h3>🛒 2. Mercado Livre Afiliado</h3><p>Gere o link pelo Portal de Afiliados do Mercado Livre e cole em <b>Link de afiliado</b>. Escolha <b>Mercado Livre Afiliado</b>. O botão abrirá o anúncio do Mercado Livre. O pagamento acontece lá.</p><h3>🟠 3. Amazon</h3><p>Use seu link de associado e escolha <b>Amazon</b>. O pagamento acontece na Amazon.</p><div class="estoque-ideia"><b>Estrutura de entrega já prevista:</b><br>O checkout salva endereço, método de envio, frete, transportadora, código de rastreio e previsão de entrega no pedido.<br><br><b>Webhooks:</b> depois de configurar o Webhook de Order no Mercado Pago, o sistema poderá atualizar automaticamente o status do pagamento.<br><br><b>Ideias simples para começar com estoque:</b><br>kits de automação residencial, tomadas e interruptores inteligentes, sensores, cabos/conectores, fontes 12 V, módulos relé, itens de organização elétrica e pequenos acessórios de instalação. Comece com poucas unidades e produtos que você consegue demonstrar tecnicamente.</div></div></main></body></html>'''


# ==========================================================
# API DE PRODUTOS
# ==========================================================

@app.route("/api/produtos")
def api_produtos():
    try:
        resultado = (
            supabase
            .table("produtos")
            .select("*")
            .eq("ativo", True)
            .order("destaque", desc=True)
            .order("id", desc=True)
            .execute()
        )

        dados = resultado.data or []

        return jsonify({
            "status": "sucesso",
            "total": len(dados),
            "produtos": dados,
        })

    except Exception as erro:
        return jsonify({
            "status": "erro",
            "mensagem": str(erro),
        }), 500


# ==========================================================
# HEALTH CHECK
# ==========================================================

@app.route("/health")
def health():
    try:
        (
            supabase
            .table("produtos")
            .select("id")
            .limit(1)
            .execute()
        )

        return {
            "status": "online",
            "supabase": "conectado",
        }

    except Exception as erro:
        return {
            "status": "erro",
            "erro": str(erro),
        }, 500


# ==========================================================
# START
# ==========================================================

if __name__ == "__main__":
    port = int(
        os.environ.get(
            "PORT",
            5000,
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
    )
