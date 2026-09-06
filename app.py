

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
    jsonify
)

from supabase import create_client


# ==========================================================
# CONFIGURAÇÃO
# ==========================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "chave-temporaria-trocar-em-producao"
)

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

ADMIN_USER = os.environ.get(
    "ADMIN_USER",
    "admin"
)

ADMIN_PASSWORD = os.environ.get(
    "ADMIN_PASSWORD",
    "admin"
)


# ==========================================================
# FUNÇÕES AUXILIARES
# ==========================================================

def texto_formulario(nome, padrao=""):
    """
    Obtém um campo do formulário sem retornar None.
    """
    return request.form.get(nome, padrao).strip()


def converter_preco(valor):
    """
    Converte preços como:
    99
    99.90
    99,90

    Retorna None quando o campo estiver vazio.
    """

    valor = str(valor or "").strip()

    if not valor:
        return None

    valor = valor.replace("R$", "")
    valor = valor.replace(".", "")
    valor = valor.replace(",", ".")

    try:
        preco = Decimal(valor)

        if preco < 0:
            raise ValueError("O preço não pode ser negativo.")

        return float(preco)

    except (InvalidOperation, ValueError):
        raise ValueError("Digite um preço válido.")


def converter_categoria(valor):
    """
    Converte o ID da categoria para inteiro.
    """
    valor = str(valor or "").strip()

    if not valor:
        return None

    try:
        return int(valor)

    except ValueError:
        raise ValueError("Categoria inválida.")


def checkbox_ativo(nome):
    """
    Retorna True quando o checkbox estiver marcado.
    """
    return request.form.get(nome) == "on"


def url_valida(url):
    """
    Valida URLs de imagem e links de afiliado.
    """
    if not url:
        return True

    try:
        resultado = urlparse(url)

        return resultado.scheme in (
            "http",
            "https"
        ) and bool(resultado.netloc)

    except Exception:
        return False


def montar_dados_produto():
    """
    Monta os dados enviados para o Supabase.
    """

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

    dados = {
        "nome": nome,

        "descricao": texto_formulario(
            "descricao"
        ),

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
            "Amazon"
        ),

        "ativo": checkbox_ativo(
            "ativo"
        ),

        "destaque": checkbox_ativo(
            "destaque"
        )
    }

    return dados


def buscar_categorias(apenas_ativas=False):
    """
    Busca as categorias cadastradas.
    """

    consulta = (
        supabase
        .table("categorias")
        .select("*")
    )

    if apenas_ativas:
        consulta = consulta.eq(
            "ativo",
            True
        )

    return (
        consulta
        .order("nome")
        .execute()
        .data or []
    )


def buscar_produto(produto_id):
    """
    Busca um produto pelo ID.
    """

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
    """
    Busca todos os produtos.
    """

    return (
        supabase
        .table("produtos")
        .select("*")
        .order("id", desc=True)
        .execute()
        .data or []
    )


def calcular_estatisticas(produtos):
    """
    Calcula estatísticas para o painel administrativo.
    """

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
        "produtos_incompletos": produtos_incompletos
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
                "warning"
            )

            return redirect(
                url_for("login")
            )

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
            categorias=categorias_resultado.data or []
        )

    except Exception:
        flash(
            "Não foi possível carregar os produtos.",
            "danger"
        )

        return render_template(
            "index.html",
            produtos=[],
            categorias=[]
        )


# ==========================================================
# LISTAGEM DE PRODUTOS
# ==========================================================

@app.route("/produtos")
def produtos():

    busca = request.args.get(
        "q",
        ""
    ).strip()

    categoria_id = request.args.get(
        "categoria",
        ""
    ).strip()

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
                f"%{busca}%"
            )

        if categoria_id:
            try:
                consulta = consulta.eq(
                    "categoria_id",
                    int(categoria_id)
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
            apenas_ativas=True
        )

        return render_template(
            "produtos.html",
            produtos=resultado.data or [],
            categorias=categorias,
            busca=busca,
            categoria_selecionada=categoria_id
        )

    except Exception:
        flash(
            "Erro ao buscar produtos.",
            "danger"
        )

        return render_template(
            "produtos.html",
            produtos=[],
            categorias=[],
            busca=busca,
            categoria_selecionada=categoria_id
        )


# ==========================================================
# LOGIN
# ==========================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if session.get("admin_logado"):
        return redirect(
            url_for("admin")
        )

    erro = None

    if request.method == "POST":

        usuario = texto_formulario(
            "usuario"
        )

        senha = request.form.get(
            "senha",
            ""
        )

        if (
            usuario == ADMIN_USER
            and senha == ADMIN_PASSWORD
        ):

            session.clear()

            session["admin_logado"] = True

            flash(
                "Login realizado com sucesso.",
                "success"
            )

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

    flash(
        "Você saiu do painel.",
        "info"
    )

    return redirect(
        url_for("index")
    )


# ==========================================================
# PAINEL ADMINISTRATIVO
# ==========================================================

@app.route("/admin")
@admin_required
def admin():

    try:
        produtos = buscar_todos_produtos()

        categorias = buscar_categorias()

        estatisticas = calcular_estatisticas(
            produtos
        )

        busca = request.args.get(
            "q",
            ""
        ).strip()

        categoria_id = request.args.get(
            "categoria",
            ""
        ).strip()

        produtos_filtrados = produtos

        if busca:
            produtos_filtrados = [
                produto
                for produto in produtos_filtrados
                if busca.lower()
                in produto.get(
                    "nome",
                    ""
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
            categoria_selecionada=categoria_id
        )

    except Exception:
        flash(
            "Erro ao carregar o painel.",
            "danger"
        )

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
                "produtos_incompletos": 0
            },
            busca="",
            categoria_selecionada=""
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

    categorias = buscar_categorias(
        apenas_ativas=True
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
                "success"
            )

            return redirect(
                url_for("admin")
            )

        except Exception as erro:
            flash(
                f"Erro ao cadastrar produto: {erro}",
                "danger"
            )

    return render_template(
        "produto_form.html",
        produto=None,
        categorias=categorias
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

    produto = buscar_produto(
        produto_id
    )

    if not produto:
        flash(
            "Produto não encontrado.",
            "danger"
        )

        return redirect(
            url_for("admin")
        )

    categorias = buscar_categorias(
        apenas_ativas=True
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
                "success"
            )

            return redirect(
                url_for("admin")
            )

        except Exception as erro:
            flash(
                f"Erro ao atualizar produto: {erro}",
                "danger"
            )

    return render_template(
        "produto_form.html",
        produto=produto,
        categorias=categorias
    )


# ==========================================================
# DUPLICAR PRODUTO
# ==========================================================

@app.route(
    "/admin/produto/<int:produto_id>/duplicar",
    methods=["POST"]
)
@admin_required
def duplicar_produto(produto_id):

    produto = buscar_produto(
        produto_id
    )

    if not produto:
        flash(
            "Produto não encontrado.",
            "danger"
        )

        return redirect(
            url_for("admin")
        )

    dados = {
        "nome": f"{produto.get('nome', '')} - Cópia",

        "descricao": produto.get(
            "descricao"
        ),

        "categoria_id": produto.get(
            "categoria_id"
        ),

        "preco": produto.get(
            "preco"
        ),

        "imagem_url": produto.get(
            "imagem_url"
        ),

        "link_afiliado": produto.get(
            "link_afiliado"
        ),

        "plataforma": produto.get(
            "plataforma",
            "Amazon"
        ),

        "ativo": False,

        "destaque": False
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
            "success"
        )

    except Exception as erro:
        flash(
            f"Erro ao duplicar produto: {erro}",
            "danger"
        )

    return redirect(
        url_for("admin")
    )


# ==========================================================
# ATIVAR OU DESATIVAR PRODUTO
# ==========================================================

@app.route(
    "/admin/produto/<int:produto_id>/alternar",
    methods=["POST"]
)
@admin_required
def alternar_produto(produto_id):

    produto = buscar_produto(
        produto_id
    )

    if not produto:
        flash(
            "Produto não encontrado.",
            "danger"
        )

        return redirect(
            url_for("admin")
        )

    novo_status = not bool(
        produto.get("ativo")
    )

    try:
        (
            supabase
            .table("produtos")
            .update({
                "ativo": novo_status
            })
            .eq("id", produto_id)
            .execute()
        )

        if novo_status:
            mensagem = "Produto ativado."
        else:
            mensagem = "Produto desativado."

        flash(
            mensagem,
            "success"
        )

    except Exception as erro:
        flash(
            f"Erro ao alterar produto: {erro}",
            "danger"
        )

    return redirect(
        url_for("admin")
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

    try:
        (
            supabase
            .table("produtos")
            .update({
                "ativo": False
            })
            .eq("id", produto_id)
            .execute()
        )

        flash(
            "Produto desativado.",
            "success"
        )

    except Exception as erro:
        flash(
            f"Erro ao desativar produto: {erro}",
            "danger"
        )

    return redirect(
        url_for("admin")
    )


# ==========================================================
# ALTERNAR DESTAQUE
# ==========================================================

@app.route(
    "/admin/produto/<int:produto_id>/destaque",
    methods=["POST"]
)
@admin_required
def alternar_destaque(produto_id):

    produto = buscar_produto(
        produto_id
    )

    if not produto:
        flash(
            "Produto não encontrado.",
            "danger"
        )

        return redirect(
            url_for("admin")
        )

    novo_destaque = not bool(
        produto.get("destaque")
    )

    try:
        (
            supabase
            .table("produtos")
            .update({
                "destaque": novo_destaque
            })
            .eq("id", produto_id)
            .execute()
        )

        flash(
            "Destaque do produto atualizado.",
            "success"
        )

    except Exception as erro:
        flash(
            f"Erro ao alterar destaque: {erro}",
            "danger"
        )

    return redirect(
        url_for("admin")
    )


# ==========================================================
# API DE PRODUTOS
# ==========================================================

@app.route("/api/produtos")
def api_produtos():

    try:
        produtos = (
            supabase
            .table("produtos")
            .select("*")
            .eq("ativo", True)
            .order("destaque", desc=True)
            .order("id", desc=True)
            .execute()
        )

        return jsonify({
            "status": "sucesso",
            "total": len(produtos.data or []),
            "produtos": produtos.data or []
        })

    except Exception as erro:

        return jsonify({
            "status": "erro",
            "mensagem": str
