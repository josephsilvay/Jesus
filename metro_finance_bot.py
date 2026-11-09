#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot Jornal Metro v3 - www.jornalmetro.com.br
Qualidade: 2.000+ palavras, pautas equilibradas (evergreen+atual), anti-IA, titulo PT-BR, videos verificados
"""

import os
import re
import json
import random
import unicodedata
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

BLOG_ID      = "5307582001063172924"
BLOG_DOMAIN  = "www.jornalmetro.com.br"
MAX_DAILY    = 2
HISTORY_FILE = "published_history.json"
SCOPES       = ["https://www.googleapis.com/auth/blogger"]

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

BRT = timezone(timedelta(hours=-3))

# ── Palavras que nunca devem ser minusculizadas (proprios, siglas) ──────────
PROPER_TOKENS = {
    "Brasil", "INSS", "FGTS", "CPF", "CEF", "Caixa", "Serasa", "SPC",
    "Nubank", "Itau", "Bradesco", "Santander", "BTG", "XP", "PIS", "Pasep",
    "BPC", "LOAS", "Pix", "PIX", "SVR", "BCB", "STF", "Procon", "Febraban",
    "Bolsa", "Familia", "Desenrola", "CNPJ", "RG", "CET", "IOF", "CDI",
    "Selic", "IBGE", "IPCA", "FGV", "Boa Vista", "Open Finance",
}

# ── Queries RSS – equilibradas entre evergreen e atual ─────────────────────
HIGH_CPC_QUERIES = [
    "cartao+de+credito+aprovacao+OR+limite+OR+cashback+OR+score+Serasa",
    "emprestimo+consignado+INSS+OR+FGTS+antecipacao+OR+credito+pessoal+juros",
    "Bolsa+Familia+valor+OR+INSS+beneficio+revisao+OR+BPC+LOAS",
    "Desenrola+Brasil+renegociacao+OR+limpar+nome+OR+negativado+divida",
    "PIS+Pasep+abono+OR+seguro+desemprego+OR+FGTS+saldo",
    "cartao+de+credito+negado+OR+score+baixo+OR+como+conseguir+credito",
    "emprestimo+pessoal+online+OR+fintech+credito+OR+banco+digital+conta",
    "INSS+aposentadoria+OR+revisao+beneficio+OR+consignado+taxa",
]

# ── Fallback com pautas equilibradas: frias mas com angulo especifico ──────
PAUTAS_FALLBACK = [
    "Bancos cortaram limite de cartao de credito: o que fazer se o seu foi reduzido",
    "Consignado INSS: como comparar taxas entre bancos e achar a menor antes de assinar",
    "Score Serasa caiu sem motivo? Veja as causas mais comuns e como reverter rapido",
    "FGTS: quem tem direito ao saque aniversario e quanto perde quem migra agora",
    "Cartao de credito negado mesmo com nome limpo: os 5 motivos que os bancos nao revelam",
    "Bolsa Familia bloqueado: as razoes mais comuns e o passo a passo para desbloquear",
    "Emprestimo pessoal vs consignado: quando vale a pena cada um, com simulacao",
    "BPC LOAS 2026: novas regras de revisao e quem pode perder o beneficio",
    "Como aumentar o limite do cartao de credito sem pedir: estrategias que funcionam",
    "Negativado com cartao de credito: as opcoes reais de credito para quem esta no SPC",
    "Saque aniversario FGTS: bancos oferecem antecipacao, mas o custo real assusta",
    "Revisao da aposentadoria pelo INSS: quem tem direito e quanto pode receber a mais",
    "Open Finance: como usar seus dados bancarios para conseguir credito mais barato",
    "Cartao sem anuidade com cashback: os que realmente valem a pena em 2026",
    "Abono salarial PIS/Pasep: trabalhadores perdem beneficio por erro cadastral",
]

# Palavras-chave de qualidade para filtrar manchetes do RSS
RSS_QUALITY_SIGNALS = [
    r'\d+%', r'\d+ pontos', r'veja como', r'entenda', r'saiba', r'caiu',
    r'subiu', r'bloqueado', r'negado', r'aprovado', r'mudou', r'nova regra',
    r'passo a passo', r'compare', r'simulacao', r'quanto', r'quando',
    r'qual', r'como conseguir', r'como fazer', r'como evitar', r'cuidado',
]

# ── Utilidades ──────────────────────────────────────────────────────────────

def get_today_str():
    return datetime.now(BRT).strftime("%Y-%m-%d")


def normalize_title_pt(title: str) -> str:
    """
    Normaliza titulo para ortografia portuguesa:
    - Apenas a primeira palavra e substantivos proprios em maiuscula
    - Siglas, nomes de marcas e institucoes permanecem intactos
    """
    words = title.split()
    result = []
    for i, w in enumerate(words):
        # Mantem a primeira palavra como esta (mas com apenas 1a letra maiscula)
        clean = w.strip(".,;:!?\"'")
        if i == 0:
            result.append(w[0].upper() + w[1:].lower() if w else w)
            continue
        # Mantem tokens proprios/siglas
        if clean in PROPER_TOKENS or clean.isupper() and len(clean) >= 2:
            result.append(w)
            continue
        # Lowercase geral
        result.append(w.lower())
    return " ".join(result)


def check_and_update_daily_limit(increment=False):
    today = get_today_str()
    data = {}
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
    count = data.get(today, 0)
    if not increment:
        print(f"Posts hoje: {count}/{MAX_DAILY}")
        return count < MAX_DAILY
    data[today] = count + 1
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Registro: {data[today]}/{MAX_DAILY} posts.")
    return True


def get_blogger_service():
    creds = None
    if os.path.exists("token.json"):
        try:
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        except Exception:
            pass
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open("token.json", "w") as f:
                f.write(creds.to_json())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
            creds = flow.run_local_server(port=0)
            with open("token.json", "w") as f:
                f.write(creds.to_json())
    return build("blogger", "v3", credentials=creds)


def score_headline(title: str) -> int:
    """Pontua manchete: prefere titulos com angulo especifico, dados, conflito."""
    t = title.lower()
    score = 0
    for pattern in RSS_QUALITY_SIGNALS:
        if re.search(pattern, t):
            score += 1
    # Penaliza titulos muito genericos (rankings simples)
    if re.search(r'^(os|as) \d+ (melhores|piores)', t):
        score -= 2
    # Bonus para manchetes com tensao/conflito
    for w in ['mas', 'apesar', 'embora', 'porém', 'risco', 'perigo', 'alerta', 'cuidado', 'fraude']:
        if w in t:
            score += 1
    return score


def get_trending_finance_topic():
    print("[1/5] Buscando pauta...")
    best_title, best_summary, best_url, best_score = None, "", "", -99

    for query in random.sample(HIGH_CPC_QUERIES, k=3):
        url = f"https://news.google.com/rss/search?q={query}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
        try:
            r = requests.get(url, timeout=8,
                headers={"User-Agent": "Mozilla/5.0 Chrome/120.0.0.0"})
            if r.status_code != 200:
                continue
            feed = feedparser.parse(r.content)
            for item in feed.entries[:8]:
                s = score_headline(item.title)
                if s > best_score:
                    best_score = s
                    best_title = item.title
                    best_summary = item.get("summary", "")
                    best_url = item.get("link", "")
        except Exception:
            continue

    if best_title and best_score >= 0:
        print(f"  -> Pauta RSS (score={best_score}): {best_title}")
        return best_title, best_summary, best_url

    pauta = random.choice(PAUTAS_FALLBACK)
    print(f"  -> Pauta Fallback: {pauta}")
    return pauta, "", ""


def verify_youtube_video(video_id):
    try:
        url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            d = r.json()
            return d.get("title", ""), d.get("thumbnail_url", "")
    except Exception:
        pass
    return None, None


def get_youtube_embed_html(query):
    print(f"  [VIDEO] Buscando: {query}")
    for q in [query, " ".join(query.split()[:4])]:
        try:
            r = requests.get(
                f"https://www.youtube.com/results?search_query={urllib.parse.quote(q)}&sp=CAI%3D",
                timeout=10, headers={"User-Agent": "Mozilla/5.0 Chrome/120.0.0.0"})
            if r.status_code != 200:
                continue
            ids = list(dict.fromkeys(re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', r.text)))
            for vid_id in ids[:6]:
                title, _ = verify_youtube_video(vid_id)
                if title:
                    print(f"  [VIDEO] OK: '{title}' ({vid_id})")
                    embed_url = f"https://www.youtube.com/embed/{vid_id}?rel=0&modestbranding=1"
                    return (
                        f'<div style="margin:36px 0;border-radius:14px;overflow:hidden;box-shadow:0 8px 28px rgba(0,0,0,0.15);">'
                        f'<div class="vid-wrapper">'
                        f'<iframe src="{embed_url}" title="{title}" frameborder="0" '
                        f'allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" '
                        f'allowfullscreen></iframe>'
                        f'</div>'
                        f'<div style="background:#1a1a2e;padding:10px 16px;">'
                        f'<p style="color:#ddd;font-size:13px;margin:0;">&#128249; <strong style="color:#fff;">{title}</strong></p>'
                        f'</div></div>\n'
                    )
        except Exception as e:
            print(f"  [VIDEO] Erro: {e}")
    print("  [VIDEO] Nenhum video verificado encontrado.")
    return ""


def get_pexels_images(keyword, count=1):
    if not PEXELS_API_KEY:
        return []
    try:
        kw = keyword.split(",")[0].strip()
        r = requests.get(
            f"https://api.pexels.com/v1/search?query={urllib.parse.quote(kw)}&per_page={count+2}&orientation=landscape",
            headers={"Authorization": PEXELS_API_KEY}, timeout=10)
        if r.status_code == 200:
            return [
                {"url": p["src"]["large2x"], "alt": p.get("alt", kw),
                 "photographer": p.get("photographer", "Pexels"),
                 "photo_url": p.get("url", "https://www.pexels.com")}
                for p in r.json().get("photos", [])[:count]
            ]
    except Exception as e:
        print(f"  Pexels erro: {e}")
    return []


def make_image_html(img, caption=""):
    return (
        f'<figure style="margin:36px 0;text-align:center;">'
        f'<img src="{img["url"]}" alt="{img["alt"]}" loading="lazy" decoding="async" '
        f'style="width:100%;height:auto;border-radius:12px;box-shadow:0 4px 16px rgba(0,0,0,0.12);"/>'
        f'<figcaption style="font-size:12px;color:#999;margin-top:8px;font-style:italic;">'
        f'{caption or img["alt"]} &mdash; Foto: '
        f'<a href="{img["photo_url"]}" rel="noopener" target="_blank" style="color:#999;">{img["photographer"]}</a> / Pexels'
        f'</figcaption></figure>\n'
    )


def sanitize_content(html):
    html = re.sub(r"\[?(CAIXA_DESTAQUE|CAIXA_LEIA_TAMBEM|INTRO)\]?", "", html, flags=re.IGNORECASE)
    html = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"<p[^>]*>\\s*</p>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"<div[^>]*>\\s*</div>", "", html, flags=re.IGNORECASE)
    
    # Quebrar paragrafos muito longos
    def split_p(m):
        text = m.group(1)
        # Se for muito longo (ex: > 350 chars), tenta quebrar no ponto final
        if len(text) > 200 and ". " in text:
            parts = text.split(". ")
            mid = len(parts) // 2
            p1 = ". ".join(parts[:mid]) + "."
            p2 = ". ".join(parts[mid:])
            return f"<p>{p1}</p>\n<p>{p2}</p>"
        return m.group(0)
    html = re.sub(r"<p>(.*?)</p>", split_p, html, flags=re.IGNORECASE|re.DOTALL)
    
    return html.strip()


def generate_article_content(topic, context="", news_url=""):
    hoje = datetime.now(BRT).strftime("%d/%m/%Y")
    print(f"[2/5] Gerando artigo sobre '{topic}'...")

    link_instrucao = (
        f'<a href="{news_url}" target="_blank" rel="noopener">leia a cobertura completa aqui</a>.'
        if news_url else
        "Inclua links para portais oficiais: gov.br, caixa.gov.br, bcb.gov.br ou serasa.com.br."
    )

    prompt = f"""Voce e Joseph Silva (joseph.silvay@gmail.com), especialista e jornalista de financas pessoais com 15 anos de experiencia, escrevendo para o Jornal Metro (jornalmetro.com.br). Data de hoje: {hoje}.

TEMA: "{topic}"
CONTEXTO: {context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REGRAS DE ESCRITA (inegociaveis):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TITULO:
- Apenas a PRIMEIRA PALAVRA e SUBSTANTIVOS PROPRIOS (nomes de bancos, orgaos, programas) com letra maiuscula. O resto das palavras deve ser minusculo.
- Exemplo ERRADO: "Como Aumentar Seu Score de Credito em 2026"
- Exemplo CERTO: "Como aumentar seu score de credito em 2026"
- Deve ter entre 6 e 12 palavras, com angulo especifico (dado, conflito ou promessa pratica), para nao ficar muito curto.

PARAGRAFOS:
- Cada <p> tem NO MAXIMO 3 frases curtas e diretas.
- Varie o comprimento das frases (misture curtas e medias).
- Comece paragrafos de formas diferentes: nunca dois seguidos com "O ", "A ", "Em ".
- PROIBIDO comecar frase com "Vale ressaltar", "E importante", "Em resumo", "Por fim", "Nesse sentido", "Sendo assim", "Dessa forma".

TOM E VOZ:
- Escreva como um jornalista humano que conhece o assunto de verdade.
- Use exemplos concretos com valores em reais, prazos reais, nomes de bancos reais.
- Mostre o lado humano: mencione situacoes reais que brasileiros enfrentam.
- Use dados especificos (porcentagens, valores, prazos) — invente se necessario, mas sejam verossimeis.
- Inclua um ponto de vista critico ou uma advertencia genuina.

PROIBICOES:
- PROIBIDO <iframe>, <video>, <embed> (inseridos automaticamente pelo sistema)
- PROIBIDO style com width, max-width, min-width ou margin:auto
- PROIBIDO qualquer marcador de lista comecando com ** (negrito de markdown)
- PROIBIDO listas de itens genéricos sem explicacao — cada <li> deve ter pelo menos 2 frases

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ESTRUTURA DO ARTIGO (2.000+ palavras):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[INTRO] — 3 paragrafos de abertura que prendem o leitor, sem revelar tudo de cara.

[CAIXA_DESTAQUE] — div com background:#EBF5FB e border-left:5px solid #1A5276. Obrigatorio colocar um titulo <strong>Resumo da matéria</strong> dentro da caixa, seguido de uma lista <ul><li> com os 3 pontos mais importantes.

[PLACEHOLDER_VIDEO_1] — escreva exatamente este texto no ponto onde o primeiro video deve aparecer.

<h2>O que e isso e por que importa agora</h2>
— 4 paragrafos detalhados com contexto, dados e exemplo pratico real.
— 1 caixa de estatistica: <div style="background:#f8f9fa;border-left:4px solid #2563eb;padding:16px;border-radius:6px;margin:24px 0;"> com numero impactante em <strong style="font-size:22px;color:#2563eb;">NUMERO</strong>

<h2>Como funciona na pratica</h2>
— 4 paragrafos explicativos, didaticos, com exemplo de cenario real.
— 1 caixa de dica: <div style="background:#EAFAF1;border-left:4px solid #27AE60;padding:16px;border-radius:6px;margin:24px 0;">

[PLACEHOLDER_IMAGEM_EXTRA] — escreva exatamente este texto para a segunda imagem.

<h2>Quem tem direito e o que exigem</h2>
— Lista <ul> com pelo menos 6 <li> bem explicados (2 frases cada).

<h2>Passo a passo completo</h2>
— Lista <ol> com pelo menos 8 passos detalhados.

<h2>Numeros, taxas e comparativo</h2>
— Tabela <table> com <thead> e <tbody>, pelo menos 4 linhas, sem style inline nas celulas.

<h2>A visao de especialistas (Mercado e Entidades)</h2>
— Cite 2 falas de especialistas (economistas, advogados, etc.) usando <blockquote>.
— É OBRIGATÓRIO DAR OS CRÉDITOS DO VEÍCULO ORIGINAL (ex: "Segundo o economista Fulano de Tal, em entrevista ao Valor Econômico..." ou "...afirmou ao InfoMoney").
— Use seu conhecimento da base de dados para trazer citações clássicas ou conhecidas sobre o tema ou use o contexto fornecido.
— 3 paragrafos de analise critica sobre o impacto na vida financeira do brasileiro.

[PLACEHOLDER_VIDEO_2] — segundo video (opcional, so escreva se fizer sentido no artigo).

<h2>Armadilhas e como nao cair nelas</h2>
— Caixa vermelha: <div style="background:#FDEDEC;border-left:5px solid #C0392B;padding:16px;border-radius:6px;margin:24px 0;">
— Lista com pelo menos 5 armadilhas/golpes reais, cada uma com explicacao.

<h2>Fontes e onde buscar ajuda</h2>
— {link_instrucao}
— Lista com links reais para orgaos oficiais.

<h2>Perguntas frequentes</h2>
— MINIMO 5 perguntas em <h3> com respostas completas em <p> (2-3 frases reais, sem enrolacao).

[CAIXA_LEIA_TAMBEM] — <div style="background:#F0F3F4;border-radius:12px;padding:22px 26px;margin-top:40px;"> com 4 links de artigos relacionados.

Schema FAQPage completo em <script type="application/ld+json"> com as 5+ perguntas.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMATO EXATO DA RESPOSTA:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

###TITULO###
titulo aqui (primeira palavra maiuscula, resto minusculo exceto proprios)

###KEYWORD###
keyword ingles para foto 1 (ex: credit card, family allowance)

###KEYWORD2###
keyword ingles para foto 2 (diferente da primeira)

###KEYWORD_VIDEO###
termo em portugues para busca de video no YouTube (ex: cartao de credito aprovacao, consignado INSS 2026)

###CATEGORIAS###
Categoria1, Categoria2

###CONTEUDO###
<p>Frase de abertura impactante. Segunda frase. Terceira frase.</p>
<p>Segundo paragrafo. Segunda frase. Terceira frase.</p>
... artigo completo ...
"""

    for attempt in range(2):
        if GROQ_API_KEY:
            for groq_model in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]:
                print(f"   -> Tentativa {attempt+1}: Groq ({groq_model})...")
                try:
                    r = requests.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                        json={"model": groq_model,
                              "messages": [{"role": "user", "content": prompt}],
                              "temperature": 0.7, "max_tokens": 8192},
                        timeout=120,
                    )
                    if r.status_code == 200:
                        text = r.json()["choices"][0]["message"]["content"]
                        if "###TITULO###" in text and "###CONTEUDO###" in text:
                            print(f"   Gerado via Groq ({groq_model})!")
                            return parse_llm_output(text)
                        print(f"   Groq sem delimitadores (tentativa {attempt+1}).")
                    else:
                        print(f"   Groq status {r.status_code}")
                except Exception as e:
                    print(f"   Erro Groq: {e}")

        if GEMINI_API_KEY:
            for model in ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-flash-latest"]:
                print(f"   -> Gemini ({model})...")
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
                try:
                    r = requests.post(url,
                        headers={"Content-Type": "application/json"},
                        json={"contents": [{"parts": [{"text": prompt}]}]},
                        timeout=120)
                    if r.status_code == 200:
                        text = (r.json().get("candidates", [{}])[0]
                                .get("content", {}).get("parts", [{}])[0].get("text", ""))
                        if text and "###TITULO###" in text and "###CONTEUDO###" in text:
                            print(f"   Gerado via Gemini ({model})!")
                            return parse_llm_output(text)
                except Exception as e:
                    print(f"   Erro Gemini: {e}")
    return None


def parse_llm_output(text):
    try:
        t   = re.search(r"###TITULO###\s*(.*?)\s*###KEYWORD###",         text, re.DOTALL|re.IGNORECASE)
        k   = re.search(r"###KEYWORD###\s*(.*?)\s*###KEYWORD2###",       text, re.DOTALL|re.IGNORECASE)
        k2  = re.search(r"###KEYWORD2###\s*(.*?)\s*###KEYWORD_VIDEO###", text, re.DOTALL|re.IGNORECASE)
        kv  = re.search(r"###KEYWORD_VIDEO###\s*(.*?)\s*###CATEGORIAS###", text, re.DOTALL|re.IGNORECASE)
        c   = re.search(r"###CATEGORIAS###\s*(.*?)\s*###CONTEUDO###",    text, re.DOTALL|re.IGNORECASE)
        cnt = re.search(r"###CONTEUDO###\s*(.*)",                        text, re.DOTALL|re.IGNORECASE)

        raw_title = t.group(1).strip() if t else "Guia de financas pessoais"
        return {
            "title":         normalize_title_pt(raw_title),
            "keyword":       k.group(1).strip()  if k  else "finance brazil",
            "keyword2":      k2.group(1).strip() if k2 else "money savings",
            "keyword_video": kv.group(1).strip() if kv else "financas pessoais",
            "categories":    c.group(1).strip()  if c  else "Financas Pessoais",
            "content":       cnt.group(1).strip() if cnt else "",
        }
    except Exception as e:
        print(f"Erro no parse: {e}")
        return None


def main():
    print("=" * 60)
    print("JORNAL METRO - AUTOMACAO v3")
    print("=" * 60)

    if not check_and_update_daily_limit(increment=False):
        print("Limite diario atingido.")
        return

    topic, context, news_url = get_trending_finance_topic()
    data = generate_article_content(topic, context, news_url)

    if not data or not data.get("content"):
        print("Falha na geracao. Abortando.")
        return

    # Imagens
    imgs1 = get_pexels_images(data["keyword"],  count=1)
    imgs2 = get_pexels_images(data["keyword2"], count=1)
    hero_html = make_image_html(imgs1[0]) if imgs1 else ""
    img2_html = make_image_html(imgs2[0]) if imgs2 else ""

    # Videos verificados
    print("[VIDEO] Buscando videos...")
    vid1 = get_youtube_embed_html(data["keyword_video"])
    vid2 = get_youtube_embed_html(data["keyword_video"] + " passo a passo")

    # Montar HTML final
    content = data["content"]
    content = re.sub(r'\[?PLACEHOLDER_VIDEO_1\]?', vid1 or "", content, flags=re.IGNORECASE)
    content = re.sub(r'\[?PLACEHOLDER_VIDEO_2\]?', vid2 or "", content, flags=re.IGNORECASE)
    content = re.sub(r'\[?PLACEHOLDER_IMAGEM_EXTRA\]?', img2_html or "", content, flags=re.IGNORECASE)
    content = sanitize_content(content)
    full_html = hero_html + content

    labels = [x.strip() for x in data["categories"].split(",") if x.strip()]

    print(f"[4/5] Publicando: '{data['title']}'")
    try:
        svc = get_blogger_service()
        res = svc.posts().insert(
            blogId=BLOG_ID,
            body={"title": data["title"], "content": full_html, "labels": labels},
            isDraft=False,
        ).execute()
        print("=" * 60)
        print(f"PUBLICADO: {res.get('url', '')}")
        print("=" * 60)
        check_and_update_daily_limit(increment=True)
    except Exception as e:
        print(f"Erro ao publicar: {e}")


if __name__ == "__main__":
    main()
