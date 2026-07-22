#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot de Automação de Elite — www.jornalmetro.com.br
Nicho: Finanças Pessoais (Cartões, Empréstimos, Benefícios Sociais, Cupons/Descontos)
Frequência: Máximo 2 postagens por dia
Qualidade: 1.200 a 1.800 palavras, E-E-A-T, SEO Avançado, Schema.org FAQ (JSON-LD)
"""

import os
import re
import json
import time
import random
import urllib.parse
from datetime import datetime, timezone, timedelta
import requests
import feedparser
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

load_dotenv()

# ── Configurações Principais ──────────────────────────────────────────────────
BLOG_ID = "3535680605318989698"  # Blog ID do Jornal Metro (ganhardinheiro.jornalmetro.com.br)
BLOG_DOMAIN = "ganhardinheiro.jornalmetro.com.br"
MAX_DAILY_POSTS = 2
HISTORY_FILE = "published_history.json"
SCOPES = ["https://www.googleapis.com/auth/blogger"]

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

# ── Queries de Alto CPC e Busca Orgânica no Brasil ────────────────────────────
HIGH_CPC_QUERIES = [
    "cartão+de+crédito+sem+anuidade+OR+limite+cartão+OR+Serasa+score",
    "empréstimo+consignado+OR+FGTS+saque+aniversário+OR+crédito+pessoal",
    "Bolsa+Família+calendário+OR+INSS+benefício+OR+Caixa+Tem+auxílio",
    "Desenrola+Brasil+OR+renegociação+dívida+OR+limpar+nome+SPC+Serasa",
    "cupom+de+desconto+OR+promoção+OR+desconto+oferta",
    "PIS+Pasep+abono+salarial+OR+seguro+desemprego+OR+revisão+INSS",
]

PAUTAS_FALLBACK = [
    "Cartão de crédito sem anuidade com aprovação imediata para negativados em 2026",
    "Como antecipar o Saque Aniversário do FGTS pelo Caixa Tem: passo a passo",
    "Calendário e valor do Bolsa Família 2026: saiba como consultar pelo CPF",
    "Como aumentar o Score do Serasa em até 300 pontos de forma rápida e segura",
    "Empréstimo consignado INSS 2026: novas regras e menores taxas de juros",
    "Como consultar valores esquecidos no Banco Central pelo SVR em 2026",
    "Como renegociar dívidas com até 90% de desconto pelo Serasa Limpa Nome",
    "Abono Salarial PIS/Pasep 2026: quem tem direito e tabela de saques",
    "Melhores cartões de crédito com cashback e sem anuidade no Brasil em 2026",
    "Passo a passo para solicitar o BPC/LOAS no INSS sem complicação",
]


# ── Controle de Trava Diária (Máximo 2 Posts/Dia) ─────────────────────────────
def get_today_str():
    brt = timezone(timedelta(hours=-3))
    return datetime.now(brt).strftime("%Y-%m-%d")


def check_and_update_daily_limit(increment=False):
    today = get_today_str()
    data = {}
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"⚠️ Erro ao ler {HISTORY_FILE}: {e}")

    current_count = data.get(today, 0)

    if not increment:
        print(f"📊 Status do dia ({today}): {current_count}/{MAX_DAILY_POSTS} posts efetuados.")
        return current_count < MAX_DAILY_POSTS

    data[today] = current_count + 1
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"✅ Registro atualizado para o dia {today}: {data[today]}/{MAX_DAILY_POSTS} posts.")
    except Exception as e:
        print(f"⚠️ Erro ao salvar {HISTORY_FILE}: {e}")
    return True


# ── Conexão com Blogger ───────────────────────────────────────────────────────
def get_blogger_service():
    creds = None
    if os.path.exists("token.json"):
        try:
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        except Exception as e:
            print(f"⚠️ Erro no token.json: {e}")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open("token.json", "w") as token:
                token.write(creds.to_json())
        else:
            if os.path.exists("client_secret.json"):
                flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
                creds = flow.run_local_server(port=0)
                with open("token.json", "w") as token:
                    token.write(creds.to_json())
            else:
                raise FileNotFoundError("Arquivo client_secret.json não encontrado.")

    return build("blogger", "v3", credentials=creds)


# ── Busca de Pautas de Alto CPC ───────────────────────────────────────────────
def get_trending_finance_topic():
    print("🔎 [1/5] Buscando pautas de alto CPC e busca orgânica...")
    query = random.choice(HIGH_CPC_QUERIES)
    url = f"https://news.google.com/rss/search?q={query}&hl=pt-BR&gl=BR&ceid=BR:pt-419"

    try:
        r = requests.get(
            url,
            timeout=8,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"},
        )
        if r.status_code == 200:
            feed = feedparser.parse(r.content)
            if feed.entries:
                item = random.choice(feed.entries[:10])
                print(f"  -> Pauta selecionada (Google News): {item.title}")
                return item.title, item.get("summary", ""), item.get("link", "")
    except Exception as e:
        print(f"  ⚠️ RSS timeout/falha ({e}), usando fallback curado.")

    pauta = random.choice(PAUTAS_FALLBACK)
    print(f"  -> Pauta selecionada (Fallback Curado): {pauta}")
    return pauta, "", ""


# ── Geração de Conteúdo (Groq Llama-3.3 70B com Fallback Gemini) ───────────────
def generate_article_content(topic, context="", news_url=""):
    print(f"✍️ [2/5] Gerando artigo completo E-E-A-T (1.200-1.800 palavras) sobre '{topic}'...")

    link_instrucao = (
        f"Insira 1 link externo apontando para a fonte oficial usando <a href='{news_url}' target='_blank' rel='noopener'>cobertura oficial de referência</a>."
        if news_url
        else "Insira 1 link externo relevante para um portal oficial (ex: gov.br, caixa.gov.br, bcb.gov.br ou serasa.com.br)."
    )

    prompt = f"""
INSTRUÇÃO CRÍTICA DE REDAÇÃO E-E-A-T (MÁXIMA QUALIDADE E RANKING GOOGLE SERP):
Você é um especialista em finanças pessoais, economia popular e jornalismo de utilidade pública escrevendo para o portal Jornal Metro (jornalmetro.com.br).

Sua missão é criar o artigo mais completo, explicativo e útil da web sobre o tema: "{topic}".
Contexto: {context}

REQUISITOS OBRIGATÓRIOS:
1. EXTENSÃO: Mínimo 1.200 a 1.800 palavras. Textos curtos ou superficiais NÃO são aceitos.
2. TOM DE VOZ: Didático, profissional, acolhedor e altamente esclarecedor. Zero clichês de IA (PROIBIDO usar "no cenário atual", "vale ressaltar", "em resumo", "por fim", "é importante destacar").
3. ESTRUTURA DO ARTIGO (EM HTML):
   - Título chamativo com palavra-chave no início (máximo 65 caracteres)
   - Caixa de Destaque Inicial (div estilizada) com os 3 Principais Pontos do Artigo.
   - <h2>O Que É e Como Funciona</h2>
   - <h2>Quem Tem Direito e Requisitos de Elegibilidade</h2> (use listas <ul><li> com detalhes completos)
   - <h2>Passo a Passo Completo para Solicitar ou Consultar</h2> (use lista ordenada <ol><li> detalhada)
   - <h2>Tabela Prática e Valores</h2> (use <table> estilizada com cabeçalho <thead>)
   - <h2>Cuidados Importantes e Como Evitar Golpes</h2> (dicas de segurança cibernética e financeira)
   - <h2>Fontes Oficiais e Links Recomendados</h2> ({link_instrucao})
   - <h2>Perguntas Frequentes (FAQ)</h2> (Mínimo 4 perguntas em <h3> e respostas detalhadas em <p>)

4. MARCAÇÃO SCHEMA.ORG (JSON-LD):
   Ao final do conteúdo, inclua uma tag <script type="application/ld+json"> contendo o Schema FAQPage oficial do Google correspondente às 4 perguntas do FAQ do artigo.

5. FORMATO DA RESPOSTA:
Retorne EXCLUSIVAMENTE no formato delimitado abaixo:

[TITULO]
Título Chamativo e Otimizado para SEO (max 65 chars)

[KEYWORD_IMAGEM]
English search term for Pexels photo (ex: credit card, money loan, wallet)

[CATEGORIAS]
Finanças Pessoais, Cartões, Benefícios, Empréstimos

[CONTEUDO]
<div class="metro-highlights" style="background:#f0f7ff;border-left:4px solid #0056b3;padding:15px;margin-bottom:20px;border-radius:4px;">
<strong>📌 Destaques Principais:</strong>
<ul>
<li>...</li>
<li>...</li>
<li>...</li>
</ul>
</div>
<p>Início do texto...</p>
... todo o corpo do artigo em HTML ...
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [...]
}}
</script>
"""

    # 1. Tenta Groq (Llama-3.3-70b-versatile)
    if GROQ_API_KEY:
        print("   -> Solicitando geração via Groq (Llama-3.3-70B)...")
        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.6,
                    "max_tokens": 4096,
                },
                timeout=60,
            )
            if r.status_code == 200:
                text = r.json()["choices"][0]["message"]["content"]
                if "[TITULO]" in text and "[CONTEUDO]" in text:
                    print("   ✅ Artigo gerado com sucesso via Groq!")
                    return parse_llm_output(text)
            else:
                print(f"   ⚠️ Groq status {r.status_code}: {r.text[:150]}")
        except Exception as e:
            print(f"   ⚠️ Erro Groq: {e}")

    # 2. Fallback: Gemini API
    if GEMINI_API_KEY:
        print("   -> Fallback: Solicitando geração via Gemini...")
        for model in ["gemini-2.5-flash", "gemini-2.0-flash"]:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
            try:
                r = requests.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    json={"contents": [{"parts": [{"text": prompt}]}]},
                    timeout=60,
                )
                if r.status_code == 200:
                    text = (
                        r.json()
                        .get("candidates", [{}])[0]
                        .get("content", {})
                        .get("parts", [{}])[0]
                        .get("text", "")
                    )
                    if text and "[TITULO]" in text and "[CONTEUDO]" in text:
                        print(f"   ✅ Artigo gerado via Gemini ({model})!")
                        return parse_llm_output(text)
            except Exception as e:
                print(f"   ⚠️ Erro Gemini ({model}): {e}")

    return None


def parse_llm_output(text):
    try:
        t_match = re.search(r"\[TITULO\]\s*(.*?)\s*\[KEYWORD_IMAGEM\]", text, re.DOTALL | re.IGNORECASE)
        k_match = re.search(r"\[KEYWORD_IMAGEM\]\s*(.*?)\s*\[CATEGORIAS\]", text, re.DOTALL | re.IGNORECASE)
        c_match = re.search(r"\[CATEGORIAS\]\s*(.*?)\s*\[CONTEUDO\]", text, re.DOTALL | re.IGNORECASE)
        cont_match = re.search(r"\[CONTEUDO\]\s*(.*)", text, re.DOTALL | re.IGNORECASE)

        return {
            "title": t_match.group(1).strip() if t_match else "Guia Completo de Finanças",
            "keyword": k_match.group(1).strip() if k_match else "finance money",
            "categories": c_match.group(1).strip() if c_match else "Finanças Pessoais",
            "content": cont_match.group(1).strip() if cont_match else "",
        }
    except Exception as e:
        print(f"⚠️ Erro no parseamento: {e}")
        return None


# ── Imagem em Alta Definição via Pexels ───────────────────────────────────────
def get_pexels_image_html(keyword):
    print(f"🖼️ [3/5] Buscando imagem no Pexels para '{keyword}'...")
    if not PEXELS_API_KEY:
        return ""

    try:
        clean_kw = keyword.split(",")[0].strip()
        url = f"https://api.pexels.com/v1/search?query={urllib.parse.quote(clean_kw)}&per_page=1&orientation=landscape"
        r = requests.get(url, headers={"Authorization": PEXELS_API_KEY}, timeout=10)
        if r.status_code == 200:
            photos = r.json().get("photos", [])
            if photos:
                img_url = photos[0]["src"]["original"]
                alt_text = photos[0].get("alt", clean_kw)
                return (
                    f'<div class="post-featured-image" style="text-align:center;margin-bottom:25px;">'
                    f'<img src="{img_url}" alt="{alt_text}" style="max-width:100%;height:auto;border-radius:10px;box-shadow:0 4px 12px rgba(0,0,0,0.15);" loading="lazy" decoding="async"/>'
                    f'<p style="font-size:12px;color:#666;margin-top:6px;">Foto: Pexels / Reprodução</p>'
                    f"</div>\n"
                )
    except Exception as e:
        print(f"⚠️ Erro ao obter imagem do Pexels: {e}")
    return ""


# ── Publicação e Execução Principal ───────────────────────────────────────────
def main():
    print("============================================================")
    print("🚀 INICIANDO AUTOMAÇÃO DE FINANÇAS — JORNAL METRO")
    print("============================================================")

    if not check_and_update_daily_limit(increment=False):
        print("🛑 LIMITE DIÁRIO ATINGIDO (2/2 posts hoje). Encerrando para manter máxima qualidade.")
        return

    topic, context, news_url = get_trending_finance_topic()
    article_data = generate_article_content(topic, context, news_url)

    if not article_data or not article_data.get("content"):
        print("❌ Falha na geração do artigo. Execução abortada.")
        return

    image_html = get_pexels_image_html(article_data["keyword"])

    full_html = image_html + article_data["content"]
    labels = [cat.strip() for cat in article_data["categories"].split(",") if cat.strip()]

    print(f"📤 [4/5] Publicando no Blogger (ID: {BLOG_ID})...")
    try:
        service = get_blogger_service()
        post_body = {
            "title": article_data["title"],
            "content": full_html,
            "labels": labels,
        }
        res = service.posts().insert(blogId=BLOG_ID, body=post_body, isDraft=False).execute()

        post_url = res.get("url", "")
        print("============================================================")
        print("🎉 [5/5] SUCESSO! Artigo de alta qualidade publicado com sucesso!")
        print(f"📌 Título: {article_data['title']}")
        print(f"🔗 Link: {post_url}")
        print("============================================================")

        check_and_update_daily_limit(increment=True)

    except Exception as e:
        print(f"❌ Erro durante a publicação no Blogger: {e}")


if __name__ == "__main__":
    main()
