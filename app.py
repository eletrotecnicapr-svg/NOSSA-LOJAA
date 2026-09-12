import os
from functools import wraps
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
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


@app.after_request
def aplicar_estilo_painel(response):
    """
    Injeta o visual moderno nas páginas administrativas sem
    precisar alterar os arquivos HTML existentes.
    """
    try:
        if (
            response.content_type
            and "text/html" in response.content_type
            and request.path.startswith("/admin")
        ):
            html = response.get_data(as_text=True)

            if "nossa-loja-painel-style" not in html and "</head>" in html:
                html = html.replace(
                    "</head>",
                    PAINEL_STYLE + "\n</head>",
                    1,
                )
                response.set_data(html)
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

        return render_template(
            "index.html",
            produtos=produtos_resultado.data or [],
            categorias=categorias_resultado.data or [],
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

        categorias = buscar_categorias(
            apenas_ativas=True,
        )

        return render_template(
            "produtos.html",
            produtos=resultado.data or [],
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
