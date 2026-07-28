#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║   FINANCE ELITE BOT — Blog ID 5307582001063172924                   ║
║   Automação Jornalística de Elite — Estilo InfoMoney / Investing.com ║
║   Frequência: 6 posts/dia | 2.000–3.500 palavras por artigo         ║
║   Qualidade: EEAT, SEO Técnico, GEO, Schema.org, YouTube Embeds     ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os
import re
import json
import time
import random
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests
import feedparser
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

load_dotenv()

GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY    = os.getenv("GROQ_API_KEY")
PEXELS_API_KEY  = os.getenv("PEXELS_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

BLOG_ID         = "5307582001063172924"
BLOG_DOMAIN     = "f5ul.com"
MAX_DAILY_POSTS = 6
HISTORY_FILE    = "finance_elite_history.json"
SCOPES          = ["https://www.googleapis.com/auth/blogger"]
BRT             = timezone(timedelta(hours=-3))

HIGH_CPC_QUERIES = [
    "cartão de crédito sem anuidade 2025 aprovação imediata",
    "melhor cartão de crédito cashback 2025",
    "cartão de crédito para negativado sem consulta SPC",
    "melhor investimento 2025 renda fixa CDB LCI LCA",
    "Tesouro Direto como investir passo a passo 2025",
    "fundos imobiliários FIIs dividendos mensais 2025",
    "ações baratas para comprar agora bolsa brasileira",
    "empréstimo consignado INSS 2025 menor taxa",
    "empréstimo FGTS saque aniversário passo a passo",
    "empréstimo pessoal online aprovação imediata negativado",
    "como sair das dívidas rápido 2025 dicas práticas",
    "Serasa limpa nome renegociação dívida desconto",
    "como aumentar score Serasa rapidamente",
    "Bolsa Família calendário 2025 valor consulta CPF",
    "INSS revisão benefício quem tem direito",
    "abono salarial PIS Pasep 2025 como sacar",
    "FGTS consulta saldo como sacar 2025",
    "Selic taxa de juros 2025 impacto investimentos",
    "inflação IPCA 2025 previsão economia brasileira",
    "mercado financeiro resumo semana tendências",
]

PAUTAS_EVERGREEN = [
    "Como investir com R$ 100 reais por mês e construir patrimônio em 2025",
    "Cartão de crédito sem anuidade com cashback: os 7 melhores do Brasil em 2025",
    "Tesouro Direto para iniciantes: guia completo de como começar a investir",
    "Como aumentar o score do Serasa em 30 dias: dicas comprovadas",
    "Empréstimo consignado INSS 2025: simulação, taxas e como contratar",
    "Como sair das dívidas em 12 meses com salário mínimo: plano definitivo",
    "FIIs: os melhores fundos imobiliários para quem quer renda mensal",
    "CDB, LCI e LCA: qual o melhor investimento de renda fixa agora?",
    "Como declarar imposto de renda 2025 sem erros e restituir mais",
    "Saque FGTS aniversário 2025: quem pode, valores e como antecipar",
    "Bolsa Família 2025: calendário, valor extra e como consultar pelo CPF",
    "Como funciona o score de crédito: tudo o que você precisa saber",
    "Melhores ações da bolsa para iniciantes comprarem em 2025",
    "Como fazer renda extra de R$ 1.000 por mês trabalhando online",
    "Empréstimo com garantia de imóvel: vantagens, riscos e melhores bancos",
    "Nubank, Inter ou C6: qual banco digital é melhor para você em 2025?",
    "Como negociar dívidas com desconto de até 90% no Serasa Limpa Nome",
    "Poupança ou Tesouro Selic: qual rende mais em 2025?",
    "Cartão de crédito para negativado: 5 opções sem consulta ao SPC/Serasa",
    "Como funciona o Desenrola Brasil 2025 e como renegociar sua dívida",
    "PIX parcelado: como funciona e quais bancos oferecem essa opção",
    "Como montar uma reserva de emergência do zero: passo a passo completo",
    "Ações ou fundos imobiliários: onde investir R$ 500 por mês?",
    "Previdência privada PGBL ou VGBL: qual escolher para sua aposentadoria?",
    "Golpes financeiros mais comuns em 2025: como se proteger",
    "Como pagar menos juros no cartão de crédito: estratégias eficazes",
    "Imposto de renda sobre investimentos: o que é isento e o que é tributado",
    "Cartão de crédito com limite alto: como conseguir aprovação mais fácil",
    "Seguros de vida e saúde em 2025: quando vale a pena contratar?",
    "Como usar o Caixa Tem para receber benefícios e fazer pagamentos",
]

EXPERT_SOURCES_RSS = [
    {"name": "InfoMoney",    "url": "https://www.infomoney.com.br/feed/",          "type": "portal financeiro"},
    {"name": "Exame",        "url": "https://exame.com/feed/",                     "type": "revista de negócios"},
    {"name": "CNN Brasil",   "url": "https://www.cnnbrasil.com.br/economia/feed/", "type": "canal de notícias"},
    {"name": "UOL Economia", "url": "https://rss.uol.com.br/feed/economia.xml",    "type": "portal de notícias"},
]

SPECIALISTS_DB = [
    {"name": "Roberto Indech",    "title": "estrategista-chefe de investimentos",  "org": "Rico Investimentos"},
    {"name": "Mirela Malvestiti", "title": "economista-chefe",                     "org": "SPC Brasil"},
    {"name": "Simone Pasianotto", "title": "economista-chefe",                     "org": "Reag Investimentos"},
    {"name": "Ana Luiza Assad",   "title": "especialista em finanças pessoais",    "org": "Serasa"},
    {"name": "Guilherme Neves",   "title": "analista de crédito sênior",           "org": "Banco Central do Brasil"},
    {"name": "Cláudio Damasceno", "title": "doutor em economia",                   "org": "FGV IBRE"},
    {"name": "Sandra Blanco",     "title": "consultora de investimentos",           "org": "Órama Investimentos"},
    {"name": "Alberto Ajzental",  "title": "economista e professor",                "org": "FGV"},
    {"name": "Daniela Casabona", "title": "analista de crédito",                  "org": "Serasa Experian"},
    {"name": "Paulo Bittencourt", "title": "diretor executivo",                    "org": "Apogeo Investimentos"},
    {"name": "Vanessa Pereira",   "title": "especialista em educação financeira",  "org": "ANBIMA"},
]


# ── Controle de limite diário ──────────────────────────────────────────────────

def get_today_str():
    return datetime.now(BRT).strftime("%Y-%m-%d")

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Erro ao ler histórico: {e}")
    return {}

def save_history(data):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ Erro ao salvar histórico: {e}")

def check_daily_limit():
    today = get_today_str()
    data  = load_history()
    count = len(data.get(today, []))
    print(f"📊 Posts hoje ({today}): {count}/{MAX_DAILY_POSTS}")
    return count < MAX_DAILY_POSTS

def register_post(title, url):
    today = get_today_str()
    data  = load_history()
    if today not in data:
        data[today] = []
    data[today].append({"title": title, "url": url, "ts": datetime.now(BRT).isoformat()})
    save_history(data)

def get_published_titles():
    data   = load_history()
    titles = []
    for day_posts in data.values():
        for post in day_posts:
            titles.append(post.get("title", "").lower())
    return titles


# ── Autenticação Blogger API v3 ────────────────────────────────────────────────

def get_blogger_service():
    creds = None
    if os.path.exists("token.json"):
        try:
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        except Exception as e:
            print(f"⚠️ Erro ao ler token.json: {e}")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Renovando token OAuth expirado...")
            creds.refresh(Request())
            with open("token.json", "w") as f:
                f.write(creds.to_json())
            print("✅ Token renovado!")
        else:
            if not os.path.exists("client_secret.json"):
                raise FileNotFoundError("client_secret.json não encontrado.")
            if os.getenv("GITHUB_ACTIONS") == "true":
                raise PermissionError("Autenticação interativa necessária. Execute localmente para gerar token.json.")
            flow  = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
            creds = flow.run_local_server(port=0)
            with open("token.json", "w") as f:
                f.write(creds.to_json())

    return build("blogger", "v3", credentials=creds)


# ── Busca de pautas ────────────────────────────────────────────────────────────

def get_finance_pauta():
    print("🔎 [1/6] Buscando pauta financeira de alto impacto...")
    published = get_published_titles()
    query     = random.choice(HIGH_CPC_QUERIES)
    encoded   = urllib.parse.quote(query)
    rss_url   = f"https://news.google.com/rss/search?q={encoded}&hl=pt-BR&gl=BR&ceid=BR:pt-419"

    try:
        r = requests.get(rss_url, timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (compatible; FinanceEliteBot/1.0)"})
        if r.status_code == 200:
            feed       = feedparser.parse(r.content)
            candidates = [e for e in feed.entries[:15] if e.title.lower() not in published]
            if candidates:
                entry = random.choice(candidates[:8])
                print(f"   ✅ Pauta (Google News): {entry.title}")
                return entry.title, entry.get("summary", ""), entry.get("link", "")
    except Exception as e:
        print(f"   ⚠️ Erro no RSS ({e}), usando pauta evergreen curada.")

    available = [p for p in PAUTAS_EVERGREEN if p.lower() not in published]
    if not available:
        available = PAUTAS_EVERGREEN
    pauta = random.choice(available)
    print(f"   ✅ Pauta (Evergreen): {pauta}")
    return pauta, "", ""


# ── Vídeo YouTube ──────────────────────────────────────────────────────────────

def find_youtube_video(topic):
    print(f"🎬 [2/6] Buscando vídeo YouTube para '{topic[:55]}...'")

    if YOUTUBE_API_KEY:
        try:
            q       = urllib.parse.quote(f"{topic} explicação finanças")
            api_url = (f"https://www.googleapis.com/youtube/v3/search"
                       f"?part=snippet&q={q}&type=video&videoDuration=medium"
                       f"&videoEmbeddable=true&relevanceLanguage=pt&regionCode=BR"
                       f"&maxResults=5&key={YOUTUBE_API_KEY}")
            r = requests.get(api_url, timeout=10)
            if r.status_code == 200:
                items = r.json().get("items", [])
                if items:
                    preferred = ["infomoney","primo rico","xp investimentos",
                                 "nath finanças","me poupe","gustavo cerbasi"]
                    best = next((i for i in items
                                 if any(p in i["snippet"]["channelTitle"].lower()
                                        for p in preferred)), items[0])
                    vid_id  = best["id"]["videoId"]
                    vtitle  = best["snippet"]["title"]
                    channel = best["snippet"]["channelTitle"]
                    print(f"   ✅ Vídeo via API: {vtitle}")
                    return _build_youtube_embed(vid_id, vtitle, channel)
        except Exception as e:
            print(f"   ⚠️ YouTube API: {e}")

    fallback = {
        "investimento":   ("6iGfYH7-M8I", "Como Começar a Investir do Zero",              "Me Poupe!"),
        "tesouro direto": ("TmA-wMzPVbQ", "Tesouro Direto Explicado Passo a Passo",       "Primo Rico"),
        "cartão":         ("sVY5b3_o-jU", "Melhores Cartões de Crédito 2025",             "Nath Finanças"),
        "empréstimo":     ("CkKN0GWI0Ag", "Empréstimo Consignado: Tudo Que Você Precisa", "Me Poupe!"),
        "fgts":           ("GtJ0E45Dq3M", "FGTS Saque Aniversário: Vale a Pena?",         "Primo Rico"),
        "bolsa":          ("y9I2hcHLVuQ", "Como Investir na Bolsa de Valores",            "XP Investimentos"),
        "dívida":         ("vl7SB6LvXAk", "Como Sair das Dívidas em 2025",               "Me Poupe!"),
        "score":          ("U6c9GH2D3Sk", "Como Aumentar o Score do Serasa",             "Nath Finanças"),
        "poupança":       ("8CWk-aeVAEk", "Poupança vs Tesouro: Qual Rende Mais?",        "Primo Invest"),
        "renda extra":    ("aCqHSC14Xvk", "Como Fazer Renda Extra em 2025",              "Me Poupe!"),
        "selic":          ("Lz3UWTGx2tA", "Selic Alta: Proteja e Renda Mais",            "InfoMoney"),
        "inflação":       ("4k7G3SoHB0I", "Como a Inflação Afeta Seu Bolso",             "InfoMoney"),
        "previdência":    ("sU8FeIHyZBA", "PGBL ou VGBL: Qual Previdência Escolher?",    "XP Investimentos"),
        "fii":            ("J3lkB2gZX4A", "FIIs: Ganhe Renda Mensal com Fundos Imob.",   "Clube FII"),
    }
    t_lower = topic.lower()
    for key, (vid_id, vtitle, channel) in fallback.items():
        if key in t_lower:
            print(f"   ✅ Vídeo (fallback temático): {vtitle}")
            return _build_youtube_embed(vid_id, vtitle, channel)

    return _build_youtube_embed("6iGfYH7-M8I",
                                "Como Organizar Suas Finanças e Investir Melhor", "Me Poupe!")


def _build_youtube_embed(video_id, title, channel):
    return f"""
<div class="video-wrapper" style="margin:32px 0;border-radius:14px;overflow:hidden;box-shadow:0 8px 28px rgba(0,0,0,0.18);">
  <div style="position:relative;padding-bottom:56.25%;height:0;overflow:hidden;background:#000;">
    <iframe
      src="https://www.youtube.com/embed/{video_id}?rel=0&modestbranding=1&color=white"
      title="{title}"
      frameborder="0"
      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
      allowfullscreen loading="lazy"
      style="position:absolute;top:0;left:0;width:100%;height:100%;">
    </iframe>
  </div>
  <div style="background:#1a1a2e;padding:10px 16px;">
    <p style="color:#ddd;font-size:13px;margin:0;">
      📹 <strong style="color:#fff;">{title}</strong>
      <span style="color:#aaa;"> — Canal: {channel} (YouTube)</span>
    </p>
  </div>
</div>
"""


# ── Referências de especialistas ───────────────────────────────────────────────

def get_expert_references(topic):
    print("💬 [3/6] Buscando referências de especialistas...")
    references = []

    for source in EXPERT_SOURCES_RSS:
        if len(references) >= 2:
            break
        try:
            r = requests.get(source["url"], timeout=8,
                headers={"User-Agent": "Mozilla/5.0 (compatible; FinanceEliteBot/1.0)"})
            if r.status_code != 200:
                continue
            feed        = feedparser.parse(r.content)
            topic_words = set(w for w in topic.lower().split() if len(w) > 4)
            for entry in feed.entries[:20]:
                entry_text = (entry.title + " " + entry.get("summary", "")).lower()
                if any(w in entry_text for w in topic_words):
                    references.append({
                        "source_name":   source["name"],
                        "source_type":   source["type"],
                        "article_title": entry.title,
                        "article_url":   entry.get("link", ""),
                        "summary":       re.sub(r"<[^>]+>", "", entry.get("summary", ""))[:280],
                    })
                    break
        except Exception:
            continue

    specialists = random.sample(SPECIALISTS_DB, min(2, len(SPECIALISTS_DB)))
    for spec in specialists:
        references.append({
            "specialist_name":  spec["name"],
            "specialist_title": spec["title"],
            "specialist_org":   spec["org"],
        })

    print(f"   ✅ {len(references)} referências preparadas.")
    return references


# ── Imagem Pexels ──────────────────────────────────────────────────────────────

def get_pexels_image(keyword):
    print(f"🖼️ [4/6] Buscando imagem Pexels para '{keyword[:40]}'...")
    if not PEXELS_API_KEY:
        print("   ⚠️ PEXELS_API_KEY ausente.")
        return ""
    try:
        clean_kw = keyword.split(",")[0].strip()
        url = (f"https://api.pexels.com/v1/search"
               f"?query={urllib.parse.quote(clean_kw)}&per_page=3&orientation=landscape")
        r = requests.get(url, headers={"Authorization": PEXELS_API_KEY}, timeout=10)
        if r.status_code == 200:
            photos = r.json().get("photos", [])
            if photos:
                photo        = random.choice(photos)
                img_url      = photo["src"]["large2x"]
                alt_text     = photo.get("alt", clean_kw)
                photographer = photo.get("photographer", "Pexels")
                pexels_url   = photo.get("url", "https://www.pexels.com")
                return (
                    f'<div class="featured-image" style="text-align:center;margin:0 0 30px 0;">'
                    f'<img src="{img_url}" alt="{alt_text}" '
                    f'style="width:100%;max-width:900px;height:auto;border-radius:12px;'
                    f'box-shadow:0 6px 20px rgba(0,0,0,0.15);" loading="eager" decoding="async"/>'
                    f'<p style="font-size:11px;color:#999;margin-top:6px;font-style:italic;">'
                    f'📷 Foto: <a href="{pexels_url}" target="_blank" rel="noopener" style="color:#999;">'
                    f'{photographer}</a> / Pexels (uso editorial livre)</p>'
                    f'</div>\n'
                )
    except Exception as e:
        print(f"   ⚠️ Erro Pexels: {e}")
    return ""


# ── Geração do artigo ──────────────────────────────────────────────────────────

def _build_prompt(topic, context, news_url, references):
    article_refs    = [r for r in references if "source_name" in r]
    specialist_refs = [r for r in references if "specialist_name" in r]

    ref_block = ""
    if article_refs:
        ref_block += "\n📰 ARTIGOS DE REFERÊNCIA (cite com créditos):\n"
        for ref in article_refs:
            ref_block += (f"  • [{ref['source_name']}] \"{ref['article_title']}\"\n"
                          f"    URL: {ref['article_url']}\n"
                          f"    Resumo: {ref['summary']}\n\n")

    if specialist_refs:
        ref_block += "\n👤 ESPECIALISTAS PARA CITAÇÕES JORNALÍSTICAS (inclua os dois):\n"
        for spec in specialist_refs:
            ref_block += f"  • {spec['specialist_name']}, {spec['specialist_title']} da {spec['specialist_org']}\n"
        ref_block += (
            "\n  Formato obrigatório — PADRÃO JORNALÍSTICO BRASILEIRO:\n"
            "  Opção A: Segundo [Nome], [cargo] da [org], \"[citação com min. 20 palavras].\"\n"
            "  Opção B: \"[Citação]\", afirmou [Nome], [cargo] da [org].\n"
        )

    link_inst = (
        f'Inclua este link: <a href="{news_url}" target="_blank" rel="noopener">leia a cobertura completa</a>.'
        if news_url
        else "Inclua 1 link externo oficial (bcb.gov.br, serasa.com.br, caixa.gov.br ou infomoney.com.br)."
    )

    today_fmt   = datetime.now(BRT).strftime("%d de %B de %Y")
    today_iso   = datetime.now(BRT).strftime("%Y-%m-%dT%H:%M:%S-03:00")

    return f"""INSTRUÇÃO MÁXIMA — REDAÇÃO JORNALÍSTICA DE ELITE (PADRÃO INFOMONEY / INVESTING.COM BRASIL):

Você é um jornalista sênior especializado em economia, finanças pessoais e investimentos com 15 anos de experiência em grandes veículos brasileiros. Crie o artigo mais completo e útil da internet sobre o tema abaixo, publicado em {today_fmt}.

━━━ TEMA: {topic}
━━━ CONTEXTO: {context if context else "Artigo evergreen de alta relevância para o público brasileiro."}

{ref_block}

━━━ REQUISITOS OBRIGATÓRIOS (E-E-A-T MÁXIMO):

1. EXTENSÃO: Mínimo 2.000 palavras reais. Artigos curtos são REJEITADOS.
2. TOM: Jornalístico, didático, acolhedor. Parágrafos curtos (máx 3 linhas). Voz ativa.
   PROIBIDO: "no cenário atual", "vale ressaltar", "em resumo", "por fim",
   "é importante destacar", "cabe salientar", "neste contexto", "de forma geral"
3. CITAÇÕES DOS 2 ESPECIALISTAS: obrigatórias no padrão jornalístico brasileiro acima.
4. ESTRUTURA HTML COMPLETA (nesta ordem):

[A] Caixa de Destaques (3 pontos-chave):
<div style="background:#EBF5FB;border-left:5px solid #1A5276;padding:18px 22px;margin:0 0 28px;border-radius:8px;">
<strong>📌 O que você vai aprender neste artigo:</strong>
<ul style="margin:10px 0 0;padding-left:18px;"><li>...</li><li>...</li><li>...</li></ul>
</div>

[B] <h2>O Que É e Por Que Você Precisa Saber</h2> (300-400 palavras de contexto e relevância)
[C] <h2>Como Funciona na Prática</h2> (400-500 palavras explicando mecanismos detalhados)
[D] <h2>Quem Tem Direito: Requisitos Completos</h2> (listas <ul><li> detalhadas)
[E] <h2>Passo a Passo Completo: Como Fazer</h2> (lista <ol><li> cada passo com 2-3 linhas)
[F] <h2>Valores, Taxas e Comparativo</h2> (tabela HTML estilizada obrigatória):
<table style="width:100%;border-collapse:collapse;margin:20px 0;font-size:14px;">
<thead style="background:#1A5276;color:#fff;"><tr><th style="padding:10px;text-align:left;">...</th>...</tr></thead>
<tbody><tr style="background:#f9f9f9;"><td style="padding:10px;border-bottom:1px solid #eee;">...</td>...</tr></tbody>
</table>
[G] <h2>O Que Dizem os Especialistas</h2>:
<div style="background:#F4F6F7;border:1px solid #BFC9CA;padding:18px 22px;margin:18px 0;border-radius:8px;font-style:italic;">
<p>"[Citação do especialista 1]"</p>
<p style="font-style:normal;font-size:13px;color:#555;margin-top:8px;">— <strong>[Nome]</strong>, [cargo] da [org]</p>
</div>
(repita o bloco para o especialista 2)
[H] <h2>Cuidados e Como Evitar Golpes</h2>:
<div style="background:#FDEDEC;border-left:5px solid #C0392B;padding:18px 22px;margin:20px 0;border-radius:8px;">
⚠️ <strong>ATENÇÃO — Golpes e fraudes mais comuns:</strong>
<ul>...</ul>
</div>
[I] Dica de Ouro:
<div style="background:#EAFAF1;border-left:5px solid #1E8449;padding:18px 22px;margin:20px 0;border-radius:8px;">
💡 <strong>Dica de Ouro:</strong> [melhor conselho prático e acionável]
</div>
[J] <h2>Fontes e Referências Oficiais</h2>: {link_inst} + 1-2 links de autoridade adicionais
[K] <h2>Perguntas Frequentes sobre [TEMA]</h2>: mínimo 5 perguntas em <h3> + respostas em <p> (2-4 linhas)

[L] SCHEMA.ORG JSON-LD ao final (obrigatório):
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@graph": [
    {{
      "@type": "NewsArticle",
      "headline": "[titulo]",
      "datePublished": "{today_iso}",
      "dateModified": "{today_iso}",
      "author": {{"@type": "Organization", "name": "Redação Finance Elite"}},
      "publisher": {{"@type": "Organization", "name": "Finance Elite Blog", "url": "https://www.{BLOG_DOMAIN}"}},
      "description": "[meta description]",
      "inLanguage": "pt-BR"
    }},
    {{
      "@type": "FAQPage",
      "mainEntity": [
        {{"@type": "Question", "name": "Pergunta?", "acceptedAnswer": {{"@type": "Answer", "text": "Resposta."}}}}
      ]
    }}
  ]
}}
</script>

━━━ FORMATO EXATO DE RESPOSTA (não adicione texto fora dos delimitadores):

[TITULO]
Título chamativo com keyword no início (máx 65 caracteres)

[META_DESCRIPTION]
Meta description SEO com CTA (máx 155 caracteres)

[KEYWORD_IMAGEM]
english keyword for pexels photo (ex: credit card money, bank loan, investment chart)

[LABELS]
Label1, Label2, Label3, Label4 (máx 5 labels em português)

[CONTEUDO]
<div class="finance-elite-post">
[TODO O HTML DO ARTIGO — MÍNIMO 2.000 PALAVRAS]
</div>
"""


def _call_groq(prompt):
    """Chama Groq Llama-3.3-70B. Faz fallback para prompt compacto se 413."""
    if not GROQ_API_KEY:
        return None

    def _do_groq_request(p, label=""):
        print(f"   → Gerando via Groq (Llama-3.3-70B){label}...")
        return requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={"model": "llama-3.3-70b-versatile",
                  "messages": [{"role": "user", "content": p}],
                  "temperature": 0.65, "max_tokens": 7000},
            timeout=120)

    try:
        r = _do_groq_request(prompt)
        if r.status_code == 200:
            text = r.json()["choices"][0]["message"]["content"]
            if "[TITULO]" in text and "[CONTEUDO]" in text:
                print("   ✅ Artigo gerado via Groq!")
                return text
            print("   ⚠️ Groq: resposta sem delimitadores esperados.")
        elif r.status_code in (413, 400):
            # Prompt grande demais: tenta versão compacta
            print(f"   ⚠️ Groq status {r.status_code} (payload grande). Tentando prompt compacto...")
            compact = prompt[:6000] + "\n\n[Responda em HTML completo com os delimitadores [TITULO], [META_DESCRIPTION], [KEYWORD_IMAGEM], [LABELS], [CONTEUDO]]"
            r2 = _do_groq_request(compact, " — compacto")
            if r2.status_code == 200:
                text = r2.json()["choices"][0]["message"]["content"]
                if "[TITULO]" in text and "[CONTEUDO]" in text:
                    print("   ✅ Artigo gerado via Groq (compacto)!")
                    return text
            print(f"   ⚠️ Groq compacto status {r2.status_code}: {r2.text[:200]}")
        elif r.status_code == 429:
            print("   ⚠️ Groq rate limit. Aguardando 30s...")
            time.sleep(30)
        else:
            print(f"   ⚠️ Groq status {r.status_code}: {r.text[:300]}")
    except requests.exceptions.Timeout:
        print("   ⚠️ Timeout Groq (120s)")
    except Exception as e:
        print(f"   ⚠️ Erro Groq: {e}")
    return None


def _call_gemini(prompt):
    """Chama Gemini com retry para 429/503/529 (erros transientes). Remove gemini-1.5 (deprecated)."""
    if not GEMINI_API_KEY:
        return None
    for model in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite"]:
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{model}:generateContent?key={GEMINI_API_KEY}")
        payload = {"contents": [{"parts": [{"text": prompt}]}],
                   "generationConfig": {"temperature": 0.65, "maxOutputTokens": 8192}}
        for attempt in range(3):
            try:
                r = requests.post(url, json=payload, timeout=150)
                if r.status_code == 200:
                    text = (r.json().get("candidates",[{}])[0]
                                    .get("content",{}).get("parts",[{}])[0].get("text",""))
                    if text and "[TITULO]" in text and "[CONTEUDO]" in text:
                        print(f"   ✅ Artigo gerado via Gemini ({model})!")
                        return text
                    print(f"   ⚠️ Gemini {model}: resposta sem delimitadores.")
                    break
                elif r.status_code in (429, 503, 529):
                    # Rate limit E sobrecarga do servidor — ambos são transientes
                    wait = 30 * (attempt + 1)
                    print(f"   ⏳ Gemini {model} status {r.status_code}. Aguardando {wait}s (tentativa {attempt+1}/3)...")
                    time.sleep(wait)
                elif r.status_code == 404:
                    print(f"   ⚠️ Gemini {model}: modelo não encontrado (404). Próximo modelo.")
                    break
                else:
                    print(f"   ⚠️ Gemini {model}: status {r.status_code} — {r.text[:150]}")
                    break
            except requests.exceptions.Timeout:
                print(f"   ⚠️ Timeout Gemini ({model}), tentativa {attempt+1}/3")
                time.sleep(15)
            except Exception as e:
                print(f"   ⚠️ Erro Gemini ({model}): {e}")
                time.sleep(10)
    return None


def generate_elite_article(topic, context, news_url, references):
    print("✍️ [5/6] Gerando artigo de elite (mín. 2.000 palavras)...")
    prompt = _build_prompt(topic, context, news_url, references)
    raw    = _call_groq(prompt) or _call_gemini(prompt)
    if not raw:
        print("❌ Todas as APIs falharam.")
        return None
    return _parse_llm_output(raw)


def _parse_llm_output(text):
    try:
        t   = re.search(r"\[TITULO\]\s*(.*?)\s*\[META_DESCRIPTION\]", text, re.DOTALL|re.IGNORECASE)
        md  = re.search(r"\[META_DESCRIPTION\]\s*(.*?)\s*\[KEYWORD_IMAGEM\]", text, re.DOTALL|re.IGNORECASE)
        ki  = re.search(r"\[KEYWORD_IMAGEM\]\s*(.*?)\s*\[LABELS\]", text, re.DOTALL|re.IGNORECASE)
        lb  = re.search(r"\[LABELS\]\s*(.*?)\s*\[CONTEUDO\]", text, re.DOTALL|re.IGNORECASE)
        ct  = re.search(r"\[CONTEUDO\]\s*(.*)", text, re.DOTALL|re.IGNORECASE)
        if not (t and ct):
            print("⚠️ Parseamento falhou: campos obrigatórios ausentes.")
            return None
        return {
            "title":            t.group(1).strip(),
            "meta_description": md.group(1).strip() if md else "",
            "keyword":          ki.group(1).strip() if ki else "finance money brazil",
            "labels":           lb.group(1).strip() if lb else "Finanças, Economia, Investimentos",
            "content":          ct.group(1).strip(),
        }
    except Exception as e:
        print(f"⚠️ Erro no parseamento: {e}")
        return None


# ── Montagem do post final ─────────────────────────────────────────────────────

def assemble_post(article, image_html, youtube_html):
    content = article["content"]

    # Injeta YouTube após 1º </h2> (pós 1º parágrafo seguinte)
    if youtube_html:
        first_h2 = content.find("</h2>")
        if first_h2 != -1:
            insert_at = first_h2 + len("</h2>")
            next_p    = content.find("</p>", insert_at)
            if next_p != -1 and (next_p - insert_at) < 600:
                insert_at = next_p + len("</p>")
            content = content[:insert_at] + "\n" + youtube_html + "\n" + content[insert_at:]
        else:
            safe = min(600, len(content) // 4)
            content = content[:safe] + "\n" + youtube_html + "\n" + content[safe:]

    pub_date = datetime.now(BRT).strftime("%d/%m/%Y às %H:%M")
    header = (
        f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:22px;'
        f'padding-bottom:14px;border-bottom:2px solid #EBF5FB;font-size:12px;color:#777;">'
        f'<span>📅 {pub_date} (Brasília)</span>'
        f'<span style="color:#ddd;">|</span>'
        f'<span>📂 Economia &amp; Finanças</span>'
        f'<span style="color:#ddd;">|</span>'
        f'<span>⏱️ Leitura: ~8 min</span>'
        f'</div>\n'
    )

    topic_q = urllib.parse.quote(article["title"].split(":")[0][:30])
    footer = f"""
<div style="background:#F0F3F4;border-radius:12px;padding:22px 26px;margin-top:40px;">
  <p style="font-size:15px;font-weight:700;margin:0 0 12px;color:#1A5276;">📚 Leia também:</p>
  <ul style="margin:0;padding-left:22px;font-size:14px;color:#333;line-height:1.9;">
    <li><a href="https://www.{BLOG_DOMAIN}/search?q=investimentos" style="color:#1A5276;text-decoration:none;">Como investir melhor o seu dinheiro em 2025</a></li>
    <li><a href="https://www.{BLOG_DOMAIN}/search?q=cartao+de+credito" style="color:#1A5276;text-decoration:none;">Os melhores cartões de crédito sem anuidade do Brasil</a></li>
    <li><a href="https://www.{BLOG_DOMAIN}/search?q=emprestimo+consignado" style="color:#1A5276;text-decoration:none;">Empréstimo consignado: guia completo para 2025</a></li>
    <li><a href="https://www.{BLOG_DOMAIN}/search?q=score+serasa" style="color:#1A5276;text-decoration:none;">Como aumentar seu score e conseguir mais crédito</a></li>
    <li><a href="https://www.{BLOG_DOMAIN}/search?q={topic_q}" style="color:#1A5276;text-decoration:none;">Mais artigos sobre este tema</a></li>
  </ul>
</div>
<div style="background:linear-gradient(135deg,#1A5276,#2980B9);color:#fff;border-radius:12px;padding:20px 24px;margin-top:16px;text-align:center;">
  <p style="margin:0 0 8px;font-size:16px;font-weight:700;">💡 Este conteúdo foi útil para você?</p>
  <p style="margin:0;font-size:13px;opacity:.9;">Compartilhe com amigos e familiares que precisam desta informação. Juntos construímos uma educação financeira mais acessível para todos os brasileiros.</p>
</div>
<p style="font-size:11px;color:#aaa;text-align:center;margin-top:16px;">
  ⚠️ <em>As informações deste artigo têm caráter educativo e informativo. Consulte sempre um especialista certificado antes de tomar decisões financeiras.</em>
</p>
"""
    return header + image_html + content + footer


# ── Publicação Blogger ─────────────────────────────────────────────────────────

def publish_to_blogger(service, article, full_html):
    print(f"📤 [6/6] Publicando no Blogger (Blog ID: {BLOG_ID})...")
    labels = [lb.strip() for lb in article["labels"].split(",") if lb.strip()]
    for essential in ["Finanças", "Economia"]:
        if not any(l.lower() == essential.lower() for l in labels):
            labels.append(essential)

    try:
        res = service.posts().insert(
            blogId=BLOG_ID,
            body={"title": article["title"], "content": full_html, "labels": labels[:10]},
            isDraft=False
        ).execute()
        post_url = res.get("url", "")
        print("=" * 65)
        print("🎉 PUBLICAÇÃO BEM-SUCEDIDA!")
        print(f"   📌 Título : {article['title']}")
        print(f"   🔗 URL    : {post_url}")
        print(f"   🏷️  Labels : {', '.join(labels[:10])}")
        print("=" * 65)
        return post_url
    except Exception as e:
        print(f"❌ Erro ao publicar no Blogger: {e}")
        return None


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    now_brt = datetime.now(BRT)
    print("=" * 65)
    print("🚀  FINANCE ELITE BOT — Automação Jornalística Premium")
    print(f"    Blog: {BLOG_DOMAIN}  |  Blog ID: {BLOG_ID}")
    print(f"    Horário BRT: {now_brt.strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 65)

    if not GEMINI_API_KEY and not GROQ_API_KEY:
        print("❌ ERRO CRÍTICO: Configure GEMINI_API_KEY ou GROQ_API_KEY no .env")
        raise SystemExit(1)
    if not PEXELS_API_KEY:
        print("⚠️ PEXELS_API_KEY ausente — posts sem imagem destacada.")

    if not check_daily_limit():
        print(f"🛑 Limite de {MAX_DAILY_POSTS} posts/dia atingido. Encerrando.")
        return

    topic, context, news_url = get_finance_pauta()
    youtube_html             = find_youtube_video(topic)
    references               = get_expert_references(topic)
    temp_image               = get_pexels_image(topic[:35])
    article                  = generate_elite_article(topic, context, news_url, references)

    if not article:
        print("❌ Geração falhou. Execução encerrada sem publicação.")
        return

    image_html = get_pexels_image(article.get("keyword", topic[:35])) or temp_image
    full_html  = assemble_post(article, image_html, youtube_html)
    service    = get_blogger_service()
    post_url   = publish_to_blogger(service, article, full_html)

    if post_url:
        register_post(article["title"], post_url)
        today_posts = load_history().get(get_today_str(), [])
        print(f"\n📊 Histórico: {len(today_posts)}/{MAX_DAILY_POSTS} posts publicados hoje.")
    else:
        print("⚠️ Publicação falhou. Histórico não atualizado.")


if __name__ == "__main__":
    main()
