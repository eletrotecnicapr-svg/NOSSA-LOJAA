import os
from functools import wraps

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)

from supabase import create_client


app = Flask(__name__)

app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "chave-temporaria-trocar-em-producao"
)


# ==========================================================
# SUPABASE
# ==========================================================

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


# ==========================================================
# ADMIN
# ==========================================================

ADMIN_USER = os.environ.get(
    "ADMIN_USER",
    "admin"
)

ADMIN_PASSWORD = os.environ.get(
    "ADMIN_PASSWORD",
    "admin"
)


def admin_required(func):

    @wraps(func)
    def wrapper(*args, **kwargs):

        if not session.get("admin_logado"):

            return redirect(
                url_for("login")
            )

        return func(*args, **kwargs)

    return wrapper


# ==========================================================
# LOJA
# ==========================================================

@app.route("/")
def index():

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
        categorias=categorias_resultado.data or []
    )


@app.route("/produtos")
def produtos():

    resultado = (
        supabase
        .table("produtos")
        .select("*")
        .eq("ativo", True)
        .order("id", desc=True)
        .execute()
    )

    return render_template(
        "produtos.html",
        produtos=resultado.data or []
    )


# ==========================================================
# LOGIN
# ==========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    erro = None

    if request.method == "POST":

        usuario = request.form.get(
            "usuario",
            ""
        )

        senha = request.form.get(
            "senha",
            ""
        )

        if (
            usuario == ADMIN_USER
            and senha == ADMIN_PASSWORD
        ):

            session["admin_logado"] = True

            return redirect(
                url_for("admin")
            )

        erro = "Usuário ou senha incorretos."

    return render_template(
        "login.html",
        erro=erro
    )


# ==========================================================
# LOGOUT
# ==========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("index")
    )


# ==========================================================
# PAINEL ADMINISTRATIVO
# ==========================================================

@app.route("/admin")
@admin_required
def admin():

    produtos = (
        supabase
        .table("produtos")
        .select("*")
        .order("id", desc=True)
        .execute()
    )

    categorias = (
        supabase
        .table("categorias")
        .select("*")
        .order("id")
        .execute()
    )

    return render_template(
        "admin.html",
        produtos=produtos.data or [],
        categorias=categorias.data or []
    )


# ==========================================================
# NOVO PRODUTO
# ==========================================================

@app.route(
    "/admin/produto/novo",
    methods=["GET", "POST"]
)
@admin_required
def novo_produto():

    categorias = (
        supabase
        .table("categorias")
        .select("*")
        .eq("ativo", True)
        .order("nome")
        .execute()
    )

    if request.method == "POST":

        dados = {

            "nome": request.form.get(
                "nome"
            ),

            "descricao": request.form.get(
                "descricao"
            ),

            "categoria_id": (
                int(request.form["categoria_id"])
                if request.form.get("categoria_id")
                else None
            ),

            "preco": (
                float(request.form["preco"])
                if request.form.get("preco")
                else None
            ),

            "imagem_url": request.form.get(
                "imagem_url"
            ),

            "link_afiliado": request.form.get(
                "link_afiliado"
            ),

            "plataforma": request.form.get(
                "plataforma",
                "Amazon"
            ),

            "ativo": (
                request.form.get("ativo")
                == "on"
            ),

            "destaque": (
                request.form.get("destaque")
                == "on"
            )
        }

        supabase.table(
            "produtos"
        ).insert(
            dados
        ).execute()

        return redirect(
            url_for("admin")
        )

    return render_template(
        "produto_form.html",
        produto=None,
        categorias=categorias.data or []
    )


# ==========================================================
# EDITAR PRODUTO
# ==========================================================

@app.route(
    "/admin/produto/<int:produto_id>/editar",
    methods=["GET", "POST"]
)
@admin_required
def editar_produto(produto_id):

    produto_resultado = (
        supabase
        .table("produtos")
        .select("*")
        .eq("id", produto_id)
        .limit(1)
        .execute()
    )

    if not produto_resultado.data:

        return "Produto não encontrado", 404

    produto = produto_resultado.data[0]

    categorias = (
        supabase
        .table("categorias")
        .select("*")
        .eq("ativo", True)
        .order("nome")
        .execute()
    )

    if request.method == "POST":

        dados = {

            "nome": request.form.get(
                "nome"
            ),

            "descricao": request.form.get(
                "descricao"
            ),

            "categoria_id": (
                int(request.form["categoria_id"])
                if request.form.get("categoria_id")
                else None
            ),

            "preco": (
                float(request.form["preco"])
                if request.form.get("preco")
                else None
            ),

            "imagem_url": request.form.get(
                "imagem_url"
            ),

            "link_afiliado": request.form.get(
                "link_afiliado"
            ),

            "plataforma": request.form.get(
                "plataforma",
                "Amazon"
            ),

            "ativo": (
                request.form.get("ativo")
                == "on"
            ),

            "destaque": (
                request.form.get("destaque")
                == "on"
            )
        }

        (
            supabase
            .table("produtos")
            .update(dados)
            .eq("id", produto_id)
            .execute()
        )

        return redirect(
            url_for("admin")
        )

    return render_template(
        "produto_form.html",
        produto=produto,
        categorias=categorias.data or []
    )


# ==========================================================
# DESATIVAR PRODUTO
# ==========================================================

@app.route(
    "/admin/produto/<int:produto_id>/desativar",
    methods=["POST"]
)
@admin_required
def desativar_produto(produto_id):

    (
        supabase
        .table("produtos")
        .update({
            "ativo": False
        })
        .eq("id", produto_id)
        .execute()
    )

    return redirect(
        url_for("admin")
    )


# ==========================================================
# HEALTH CHECK
# ==========================================================

@app.route("/health")
def health():

    try:

        resultado = (
            supabase
            .table("produtos")
            .select("id")
            .limit(1)
            .execute()
        )

        return {
            "status": "online",
            "supabase": "conectado"
        }

    except Exception as erro:

        return {
            "status": "erro",
            "erro": str(erro)
        }, 500


# ==========================================================
# START
# ==========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )