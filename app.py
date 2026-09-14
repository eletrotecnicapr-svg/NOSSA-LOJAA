import os
from functools import wraps
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse, urlencode
import re
import html

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
    render_template_string,
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
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY,
)

ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin")

# Amazon Associates / carrinho
AMAZON_ASSOCIATE_TAG = os.environ.get("AMAZON_ASSOCIATE_TAG", "pedro0ba1e-20")
AMAZON_CART_BASE = "https://www.amazon.com.br/gp/aws/cart/add.html"


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
:root{
--loja-bg:#f4f6f8;--loja-card:#fff;--loja-dark:#111827;--loja-text:#172033;
--loja-muted:#697586;--loja-border:#e6eaf0;--loja-blue:#2563eb;
--loja-shadow:0 12px 32px rgba(15,23,42,.08);--loja-shadow-hover:0 18px 38px rgba(15,23,42,.14)
}
*{box-sizing:border-box}
body{margin:0!important;background:var(--loja-bg)!important;color:var(--loja-text)!important;
font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif!important}
header{position:relative;background:linear-gradient(135deg,#0f172a,#172554 55%,#1e40af)!important;
padding:0!important;box-shadow:0 8px 28px rgba(15,23,42,.18);overflow:hidden}
header:before{content:"";position:absolute;width:240px;height:240px;right:-90px;top:-110px;border-radius:50%;background:rgba(255,255,255,.08)}
header .container{position:relative;max-width:1180px;padding:20px 22px 22px}
header h1{margin:0!important;font-size:clamp(28px,6vw,44px)!important;font-weight:850!important;
letter-spacing:-1.4px;line-height:1.05}
header p{margin:9px 0 16px!important;color:rgba(255,255,255,.78)!important;font-size:clamp(14px,2.5vw,17px)}
nav{display:flex!important;flex-wrap:wrap;gap:8px;margin:0!important}
nav a{display:inline-flex!important;align-items:center;justify-content:center;padding:10px 15px!important;
border:1px solid rgba(255,255,255,.12);border-radius:999px!important;background:rgba(255,255,255,.09)!important;
color:#fff!important;text-decoration:none!important;font-weight:700;transition:.2s ease}
nav a:hover{background:rgba(255,255,255,.18)!important;transform:translateY(-1px)}
main.container{max-width:1180px;padding:26px 22px 50px!important}
.hero,.loja-hero{position:relative;overflow:hidden;margin-bottom:28px;padding:clamp(28px,6vw,52px);
border-radius:28px;background:radial-gradient(circle at 88% 12%,rgba(37,99,235,.18),transparent 30%),linear-gradient(135deg,#fff,#f8fafc);
border:1px solid var(--loja-border);box-shadow:var(--loja-shadow)}
.hero h2,.loja-hero h2{margin:0 0 10px!important;font-size:clamp(30px,6vw,48px)!important;line-height:1.05;letter-spacing:-1.3px}
.hero p,.loja-hero p{max-width:680px;margin:0;color:var(--loja-muted);font-size:clamp(16px,2.5vw,19px);line-height:1.6}
.loja-hero .etiqueta{display:inline-flex;padding:7px 11px;margin-bottom:12px;border-radius:999px;background:#eaf2ff;color:#1d4ed8;
font-size:12px;font-weight:800;letter-spacing:.4px;text-transform:uppercase}
main.container>section{margin-bottom:30px}
main.container>section>h2{margin:0 0 15px!important;font-size:clamp(23px,4vw,30px);letter-spacing:-.6px}
.categorias-modernas{display:grid!important;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px!important}
.categoria-botao{min-height:66px;display:flex!important;align-items:center;justify-content:center;padding:12px 15px;
border:1px solid var(--loja-border);border-radius:18px!important;background:#fff!important;color:var(--loja-dark)!important;
text-decoration:none!important;font-weight:800;box-shadow:0 6px 16px rgba(15,23,42,.05);transition:.2s ease}
.categoria-botao:hover{border-color:#bfdbfe;background:#eff6ff!important;transform:translateY(-2px)}
.produtos{display:grid!important;grid-template-columns:repeat(auto-fill,minmax(235px,1fr));gap:18px!important}
.produto{position:relative;overflow:hidden;display:flex;flex-direction:column;min-width:0;background:var(--loja-card)!important;
border:1px solid var(--loja-border);border-radius:22px!important;box-shadow:var(--loja-shadow)!important;
transition:transform .2s ease,box-shadow .2s ease}
.produto:hover{transform:translateY(-4px);box-shadow:var(--loja-shadow-hover)!important}
.produto img,.produto .sem-imagem{width:100%;height:220px;object-fit:contain;background:linear-gradient(180deg,#fff,#f8fafc)}
.produto-conteudo{display:flex;flex-direction:column;flex:1;padding:18px!important}
.produto-conteudo h3{margin:0 0 7px!important;font-size:18px;line-height:1.25}
.produto-conteudo p{margin:0;color:var(--loja-muted);line-height:1.5;font-size:14px}
.produto-conteudo strong{display:block;margin:13px 0;font-size:20px;color:#0f172a}
.produto-conteudo .botao,.botao-comprar{margin-top:auto!important;width:100%!important;min-height:50px;display:inline-flex!important;
align-items:center;justify-content:center;gap:8px;border:0!important;border-radius:15px!important;
background:linear-gradient(135deg,#2563eb,#1d4ed8)!important;color:#fff!important;text-decoration:none!important;
font-weight:800;box-shadow:0 8px 18px rgba(37,99,235,.22);transition:.2s ease}
.produto-conteudo .botao:hover,.botao-comprar:hover{transform:translateY(-2px);filter:brightness(1.05);box-shadow:0 13px 25px rgba(37,99,235,.28)}
.filtro-categorias{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 22px}
.filtro-categorias a{display:inline-flex;align-items:center;min-height:40px;padding:8px 13px;border-radius:999px;background:#fff;
border:1px solid var(--loja-border);color:var(--loja-dark);text-decoration:none;font-weight:750}
.filtro-categorias a.ativo,.filtro-categorias a:hover{background:var(--loja-dark);color:#fff}
footer{margin-top:25px;padding:30px 22px!important;background:#0f172a!important;color:rgba(255,255,255,.72)!important}
.loja-search{display:flex;gap:8px;margin:16px auto 0;max-width:760px}
.loja-search input{flex:1;min-width:0;height:50px;padding:0 16px;border:1px solid rgba(255,255,255,.15);
border-radius:15px;background:#fff;color:#172033;font-size:15px;outline:none}
.loja-search button{width:52px;border:0;border-radius:15px;background:#fff;color:#172033;font-size:21px;cursor:pointer}
.carrinho-nav{position:relative}.carrinho-badge{display:inline-flex;min-width:21px;height:21px;align-items:center;justify-content:center;margin-left:4px;padding:0 5px;border-radius:999px;background:#ef4444;color:#fff;font-size:11px}.menu-toggle{display:none;position:absolute;right:22px;top:21px;width:46px;height:46px;border:1px solid rgba(255,255,255,.15);
border-radius:14px;background:rgba(255,255,255,.1);color:#fff;font-size:24px;cursor:pointer}

.carrinho-page{max-width:900px;margin:0 auto}.carrinho-card{background:#fff;border:1px solid var(--loja-border);border-radius:22px;padding:18px;box-shadow:var(--loja-shadow);margin-bottom:12px}.carrinho-item{display:grid;grid-template-columns:90px 1fr auto;gap:16px;align-items:center}.carrinho-item img{width:90px;height:90px;object-fit:contain;border-radius:14px;background:#f8fafc}.carrinho-item h3{margin:0 0 5px;font-size:17px}.carrinho-item p{margin:0;color:var(--loja-muted);font-size:13px}.carrinho-acoes{display:flex;gap:8px;align-items:center;justify-content:flex-end}.carrinho-acoes input{width:65px;height:42px;border:1px solid var(--loja-border);border-radius:11px;padding:0 8px}.carrinho-acoes button,.carrinho-acoes a{min-height:42px;padding:9px 13px;border:0;border-radius:11px;text-decoration:none;font-weight:750;cursor:pointer}.carrinho-atualizar{background:#eef2f7;color:#111827}.carrinho-remover{background:#fff0f0;color:#b42318}.carrinho-final{display:flex;justify-content:space-between;align-items:center;gap:15px;margin-top:18px;padding:20px;border-radius:20px;background:#0f172a;color:#fff}.carrinho-final .total{font-size:22px;font-weight:850}.botao-amazon{display:inline-flex;align-items:center;justify-content:center;min-height:50px;padding:12px 18px;border-radius:14px;background:#ffb000;color:#111827;text-decoration:none;font-weight:850}.carrinho-vazio{padding:45px 25px;text-align:center;background:#fff;border:1px solid var(--loja-border);border-radius:22px}
@media(max-width:700px){.carrinho-item{grid-template-columns:70px 1fr}.carrinho-item img{width:70px;height:70px}.carrinho-acoes{grid-column:1/-1;justify-content:stretch}.carrinho-acoes input{flex:1}.carrinho-acoes button,.carrinho-acoes a{flex:1}.carrinho-final{align-items:stretch;flex-direction:column}.botao-amazon{width:100%}}
@media(max-width:700px){
header .container{padding:18px 18px 19px} header h1{padding-right:58px}
.menu-toggle{display:block} header nav{display:none!important;flex-direction:column;padding-top:10px}
header.menu-aberto nav{display:flex!important} header nav a{width:100%}
main.container{padding:18px 15px 38px!important}.hero,.loja-hero{border-radius:22px;padding:26px 21px}
.produtos{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:12px!important}
.produto img,.produto .sem-imagem{height:175px}.produto-conteudo{padding:14px!important}
.produto-conteudo h3{font-size:16px}.produto-conteudo p{font-size:13px}.produto-conteudo strong{font-size:18px}
.produto-conteudo .botao{font-size:13px;min-height:46px;padding:10px!important}
}
@media(max-width:390px){.produtos{grid-template-columns:1fr!important}.produto img,.produto .sem-imagem{height:205px}}
</style>
"""
# ==========================================================
# AMAZON — CONVERSÃO AUTOMÁTICA DOS LINKS PÚBLICOS
# ==========================================================
def extrair_asin(link):
    if not link:
        return None
    url = str(link).strip()
    for padrao in (
        r"/dp/([A-Z0-9]{10})(?:[/?]|$)",
        r"/gp/product/([A-Z0-9]{10})(?:[/?]|$)",
        r"/gp/aw/d/([A-Z0-9]{10})(?:[/?]|$)",
        r"[?&]asin=([A-Z0-9]{10})(?:[&#]|$)",
    ):
        m = re.search(padrao, url, re.IGNORECASE)
        if m:
            return m.group(1).upper()
    return None


def link_amazon_para_carrinho(link, quantidade=1):
    if not link:
        return None
    url = str(link).strip()
    parsed = urlparse(url)
    dominio = parsed.netloc.lower()
    if "amazon.com.br" not in dominio and "amzn.to" not in dominio and "amazon.com" not in dominio:
        return None
    asin = extrair_asin(url)
    if not asin:
        return None
    params = {
        "AssociateTag": AMAZON_ASSOCIATE_TAG,
        "ASIN.1": asin,
        "Quantity.1": str(max(1, int(quantidade))),
    }
    return f"{AMAZON_CART_BASE}?{urlencode(params)}"


def preparar_produtos_publicos(produtos):
    preparados = []
    for original in produtos or []:
        produto = dict(original)
        original_link = produto.get("link_afiliado")
        carrinho = link_amazon_para_carrinho(original_link)
        produto["link_original"] = original_link
        produto["link_compra"] = carrinho or original_link
        produto["amazon_add_to_cart"] = bool(carrinho)
        preparados.append(produto)
    return preparados


def mapa_links_amazon(produtos):
    return {
        str(p.get("link_afiliado")).strip(): p.get("link_compra")
        for p in produtos or []
        if p.get("link_afiliado") and p.get("link_compra")
        and p.get("link_afiliado") != p.get("link_compra")
    }


def aplicar_melhorias_publicas(html_pagina):
    if '<button class="menu-toggle"' not in html_pagina and "<header>" in html_pagina:
        html_pagina = html_pagina.replace(
            "<header>",
            """<header>
<button class="menu-toggle" type="button" aria-label="Abrir menu"
onclick="document.querySelector('header').classList.toggle('menu-aberto')">☰</button>""",
            1,
        )

    if 'class="loja-search"' not in html_pagina and "</nav>" in html_pagina:
        html_pagina = html_pagina.replace(
            "</nav>",
            """</nav>
<form class="loja-search" action="/produtos" method="GET">
<input name="q" type="search" placeholder="Encontre um produto..." aria-label="Pesquisar produtos">
<button type="submit" aria-label="Pesquisar">⌕</button>
</form>""",
            1,
        )

    if request.path == "/" and 'class="loja-hero"' not in html_pagina:
        html_pagina = re.sub(
            r'<section class="hero">\s*<h2>\s*Produtos selecionados\s*</h2>\s*<p>(.*?)</p>\s*</section>',
            r'<section class="loja-hero"><span class="etiqueta">Nossa seleção</span>'
            r'<h2>Produtos selecionados para facilitar o seu dia.</h2><p>\1</p></section>',
            html_pagina, count=1, flags=re.IGNORECASE|re.DOTALL
        )

    # O template antigo chama o botão apenas de "comprar".
    html_pagina = html_pagina.replace(">comprar</a>", ">🛒 Adicionar à Amazon</a>")
    html_pagina = html_pagina.replace(">Comprar</a>", ">🛒 Adicionar à Amazon</a>")

    # Como os templates atuais ainda usam produto.link_afiliado,
    # troca somente os links Amazon que acabamos de identificar.
    for original, compra in getattr(g, "amazon_href_map", {}).items():
        html_pagina = html_pagina.replace(
            f'href="{html.escape(original)}"',
            f'href="{html.escape(compra)}"',
        )
        html_pagina = html_pagina.replace(
            f"href='{html.escape(original)}'",
            f'href="{html.escape(compra)}"',
        )

    return html_pagina


@app.after_request
def aplicar_estilos_e_componentes(response):
    try:
        if not (response.content_type and "text/html" in response.content_type):
            return response

        html_pagina = response.get_data(as_text=True)
        estilo = PAINEL_STYLE if request.path.startswith("/admin") else LOJA_STYLE

        if (
            "nossa-loja-public-style" not in html_pagina
            and "nossa-loja-painel-style" not in html_pagina
            and "</head>" in html_pagina
        ):
            html_pagina = html_pagina.replace("</head>", estilo + "\n</head>", 1)

        if not request.path.startswith("/admin"):
            html_pagina = aplicar_melhorias_publicas(html_pagina)

            if request.path == "/" and "/login" not in html_pagina:
                antigo = '<a href="/produtos">Todos os produtos</a>'
                novo = antigo + '\n<a href="/login">🔐 Área administrativa</a>'
                if antigo in html_pagina:
                    html_pagina = html_pagina.replace(antigo, novo, 1)

            # Reescreve os links dos cartões para o carrinho interno.
            # Isso evita depender do href antigo gravado no template e faz
            # todos os produtos cadastrados usarem o mesmo fluxo.
            for produto in getattr(g, "produtos_publicos_render", []):
                pid = produto.get("id")
                if isinstance(pid, int):
                    original_href = html.escape(str(produto.get("link_compra") or produto.get("link_afiliado") or ""), quote=True)
                    destino = f"/carrinho/adicionar/{pid}"
                    if original_href:
                        html_pagina = html_pagina.replace(f'href="{original_href}"', f'href="{destino}"')
                        html_pagina = html_pagina.replace(f"href='{original_href}'", f'href="{destino}"')

            # Botão/cabeçalho do carrinho.
            if 'href="/carrinho"' not in html_pagina and "<nav" in html_pagina:
                html_pagina = html_pagina.replace(
                    "</nav>",
                    '<a class="carrinho-nav" href="/carrinho">🛒 Carrinho <span class="carrinho-badge">'
                    + str(sum(obter_carrinho().values())) + '</span></a></nav>', 1
                )

            if request.path == "/" and 'id="categorias-modernas"' not in html_pagina:
                categorias_html = getattr(g, "categorias_home_html", "")
                if categorias_html:
                    padrao = re.compile(
                        r'<section>\s*<h2>\s*Categorias\s*</h2>\s*<div class="categorias">.*?</div>\s*</section>',
                        re.IGNORECASE|re.DOTALL
                    )
                    html_pagina, _ = padrao.subn(categorias_html, html_pagina, count=1)

            if request.path == "/produtos" and 'id="filtro-categorias"' not in html_pagina:
                filtros_html = getattr(g, "filtros_categorias_html", "")
                if filtros_html and "<main" in html_pagina:
                    marcador = "<h2>\nTodos os produtos\n</h2>"
                    if marcador in html_pagina:
                        html_pagina = html_pagina.replace(
                            marcador, marcador + "\n\n" + filtros_html, 1
                        )

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
            "Amazon",
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
    "link_compra": "https://www.amazon.com.br/gp/aws/cart/add.html?AssociateTag=pedro0ba1e-20&ASIN.1=B0HD6XVK2S&Quantity.1=1",
    "amazon_add_to_cart": True,
    "plataforma": "Amazon",
    "ativo": True,
    "destaque": True,
    "asin": "B0HD6XVK2S",
}


def produto_teste_aurafit():
    # Retorna uma cópia para evitar alterações acidentais no objeto-base.
    return dict(AURAFIT_TESTE)


# ==========================================================
# COMPRA — AMAZON ADD TO CART
# ==========================================================
@app.route("/comprar/<int:produto_id>")
def comprar(produto_id):
    # Compatibilidade com links antigos: agora o botão adiciona
    # o produto ao carrinho da Nossa Loja.
    return carrinho_adicionar(produto_id)



# ==========================================================
# CARRINHO DA NOSSA LOJA
# ----------------------------------------------------------
# O carrinho guarda somente IDs/quantidades. O pagamento e o
# checkout continuam na Amazon.
# ==========================================================
def obter_carrinho():
    carrinho = session.get("carrinho", {})
    if not isinstance(carrinho, dict):
        carrinho = {}
    return {str(k): max(1, int(v)) for k, v in carrinho.items()}


def salvar_carrinho(carrinho):
    session["carrinho"] = {str(k): max(1, int(v)) for k, v in carrinho.items()}
    session.modified = True


def montar_carrinho_detalhado():
    carrinho = obter_carrinho()
    itens = []
    total = 0.0
    for pid, quantidade in carrinho.items():
        try:
            produto = buscar_produto(int(pid))
        except (ValueError, TypeError):
            produto = None
        if not produto or not produto.get("ativo"):
            continue
        item = dict(produto)
        item["quantidade"] = quantidade
        try:
            item["subtotal"] = float(produto.get("preco") or 0) * quantidade
        except (TypeError, ValueError):
            item["subtotal"] = 0.0
        item["link_compra"] = link_amazon_para_carrinho(produto.get("link_afiliado"), quantidade)
        item["asin"] = extrair_asin(produto.get("link_afiliado"))
        total += item["subtotal"]
        itens.append(item)
    return itens, total


def gerar_carrinho_amazon(itens):
    params = {"AssociateTag": AMAZON_ASSOCIATE_TAG}
    numero = 1
    for item in itens:
        asin = extrair_asin(item.get("link_afiliado"))
        if not asin:
            continue
        params[f"ASIN.{numero}"] = asin
        params[f"Quantity.{numero}"] = str(max(1, int(item.get("quantidade", 1))))
        numero += 1
    if numero == 1:
        return None
    return f"{AMAZON_CART_BASE}?{urlencode(params)}"


@app.route("/carrinho")
def carrinho():
    itens, total = montar_carrinho_detalhado()
    return render_template_string(r"""<!doctype html><html lang="pt-br"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Carrinho — Nossa Loja</title></head><body><header><div class="container"><h1>🛒 Meu carrinho</h1><p>Revise seus produtos antes de continuar para a Amazon.</p><nav><a href="/">Início</a><a href="/produtos">Produtos</a></nav></div></header><main class="container carrinho-page"><section class="loja-hero"><span class="etiqueta">Seu carrinho</span><h2>Pronto para comprar?</h2><p>Você escolhe aqui. O pagamento e a finalização acontecem na Amazon.</p></section>{% if itens %}{% for item in itens %}<article class="carrinho-card"><div class="carrinho-item">{% if item.imagem_url %}<img src="{{ item.imagem_url }}" alt="{{ item.nome }}">{% else %}<div class="carrinho-item img">📦</div>{% endif %}<div><h3>{{ item.nome }}</h3><p>{% if item.preco %}R$ {{ "%.2f"|format(item.preco) }} por unidade{% else %}Produto selecionado{% endif %}</p></div><form class="carrinho-acoes" method="post" action="/carrinho/atualizar/{{ item.id }}"><input type="number" name="quantidade" min="1" value="{{ item.quantidade }}"><button class="carrinho-atualizar" type="submit">Atualizar</button><button class="carrinho-remover" type="submit" formaction="/carrinho/remover/{{ item.id }}">Remover</button></form></div></article>{% endfor %}<div class="carrinho-final"><div><div>Total informado</div><div class="total">{% if total %}R$ {{ "%.2f"|format(total) }}{% else %}Confira na Amazon{% endif %}</div></div><a class="botao-amazon" href="/carrinho/amazon">🛒 Adicionar tudo à Amazon</a></div><form method="post" action="/carrinho/limpar" style="margin-top:12px;text-align:right"><button class="carrinho-atualizar" type="submit">Limpar carrinho</button></form>{% else %}<div class="carrinho-vazio"><h2>Seu carrinho está vazio</h2><p>Escolha um produto na loja para começar.</p><a class="botao-amazon" href="/produtos">Ver produtos</a></div>{% endif %}</main><footer><p>Nossa Loja</p><p>Links de afiliados — podemos receber comissão pelas compras qualificadas.</p></footer></body></html>""", itens=itens, total=total)


@app.route("/carrinho/adicionar/<int:produto_id>", methods=["GET", "POST"])
def carrinho_adicionar(produto_id):
    produto = buscar_produto(produto_id)
    if not produto or not produto.get("ativo"):
        flash("Produto não encontrado ou indisponível.", "warning")
        return redirect(request.referrer or url_for("produtos"))
    if not produto.get("link_afiliado"):
        flash("Este produto ainda não possui link de compra.", "warning")
        return redirect(request.referrer or url_for("produtos"))

    try:
        quantidade = max(1, int(request.values.get("quantidade", 1)))
    except (TypeError, ValueError):
        quantidade = 1

    carrinho = obter_carrinho()
    chave = str(produto_id)
    carrinho[chave] = carrinho.get(chave, 0) + quantidade
    salvar_carrinho(carrinho)
    flash(f"{produto.get('nome', 'Produto')} foi adicionado ao seu carrinho.", "success")
    return redirect(url_for("carrinho"))


@app.route("/carrinho/atualizar/<int:produto_id>", methods=["POST"])
def carrinho_atualizar(produto_id):
    carrinho = obter_carrinho()
    chave = str(produto_id)
    try:
        quantidade = int(request.form.get("quantidade", 1))
    except (TypeError, ValueError):
        quantidade = 1
    if quantidade <= 0:
        carrinho.pop(chave, None)
    else:
        carrinho[chave] = quantidade
    salvar_carrinho(carrinho)
    return redirect(url_for("carrinho"))


@app.route("/carrinho/remover/<int:produto_id>", methods=["POST"])
def carrinho_remover(produto_id):
    carrinho = obter_carrinho()
    carrinho.pop(str(produto_id), None)
    salvar_carrinho(carrinho)
    return redirect(url_for("carrinho"))


@app.route("/carrinho/limpar", methods=["POST"])
def carrinho_limpar():
    salvar_carrinho({})
    return redirect(url_for("carrinho"))


@app.route("/carrinho/amazon")
def carrinho_amazon():
    itens, _ = montar_carrinho_detalhado()
    link = gerar_carrinho_amazon(itens)
    if not link:
        flash("Seu carrinho está vazio ou há produtos sem ASIN Amazon válido.", "warning")
        return redirect(url_for("carrinho"))
    return redirect(link)

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

        produtos_publicos = preparar_produtos_publicos(produtos_resultado.data or [])
        g.amazon_href_map = mapa_links_amazon(produtos_publicos)
        g.produtos_publicos_render = produtos_publicos

        # Adiciona o AURAFIT de teste à vitrine, mesmo que ele ainda
        # não exista na tabela produtos do Supabase.
        if not any(
            str(p.get("id")) == "teste-amazon-aurafit"
            or "B0HD6XVK2S" in str(p.get("link_afiliado") or "")
            for p in produtos_publicos
        ):
            produtos_publicos.insert(0, produto_teste_aurafit())

        g.produtos_publicos_render = produtos_publicos
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

        produtos_publicos = preparar_produtos_publicos(resultado.data or [])
        g.amazon_href_map = mapa_links_amazon(produtos_publicos)
        g.produtos_publicos_render = produtos_publicos

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

        g.produtos_publicos_render = produtos_publicos
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
            and senha == ADMIN_PASSWORD
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
# DIAGNÓSTICO DOS LINKS AMAZON
# ==========================================================
@app.route("/admin/amazon-links")
@admin_required
def amazon_links():
    produtos = buscar_todos_produtos()
    relatorio = []

    for produto in produtos:
        original = produto.get("link_afiliado")
        carrinho = link_amazon_para_carrinho(original)
        relatorio.append({
            "id": produto.get("id"),
            "nome": produto.get("nome"),
            "plataforma": produto.get("plataforma"),
            "asin": extrair_asin(original),
            "amazon_add_to_cart": bool(carrinho),
            "link_original": original,
            "link_carrinho": carrinho,
        })

    return jsonify({
        "status": "sucesso",
        "total": len(relatorio),
        "convertidos": sum(1 for x in relatorio if x["amazon_add_to_cart"]),
        "nao_convertidos": sum(1 for x in relatorio if not x["amazon_add_to_cart"]),
        "produtos": relatorio,
    })


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
