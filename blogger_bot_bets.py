import os
import random
import feedparser
import urllib.parse
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv
import requests

load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
PEXELS_API_KEY = os.getenv('PEXELS_API_KEY')

BLOG_ID = '3784349376294815003'  # bets.jornalmetro.com.br
BLOG_DOMAIN = 'bets.jornalmetro.com.br'
SCOPES = ['https://www.googleapis.com/auth/blogger']

# Busca no Google News por termos de alto engajamento em bets
BETS_QUERY = (
    "apostas+esportivas+OR+bet+OR+betano+OR+sportingbet+OR+superbet+"
    "OR+odds+OR+futebol+apostas+OR+brasileirão+apostas+OR+copa+apostas+"
    "OR+tênis+apostas+OR+basquete+NBA+apostas+OR+casa+de+apostas"
)

# Pautas fixas de alto engajamento em bets
PAUTAS_FALLBACK = [
    "Melhores palpites para o Brasileirão hoje",
    "Como funciona o mercado de apostas no futebol brasileiro",
    "Betano vs Sportingbet: qual a melhor casa de apostas em 2026",
    "O que são odds e como calcular seus ganhos em apostas",
    "Apostas ao vivo: estratégias para lucrar durante o jogo",
    "Como fazer gestão de banca nas apostas esportivas",
    "Value bet: como encontrar apostas com valor real",
    "Melhores mercados para apostar no futebol: 1x2, handicap e mais",
    "Como apostar no tênis: guia completo para iniciantes",
    "Bônus de boas-vindas das casas de apostas: como aproveitar",
    "Apostas na NBA: dicas e estratégias para o basquete americano",
    "Double chance: o mercado mais seguro para apostadores iniciantes",
    "Como ler estatísticas de futebol para apostar melhor",
    "Bankroll management: guia definitivo para não perder dinheiro em apostas",
    "Melhores aplicativos de apostas esportivas para celular em 2026",
]

def get_blogger_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('blogger', 'v3', credentials=creds)

def get_trending_topic_bets():
    """Busca notícias e tendências sobre apostas esportivas."""
    print("[1] Buscando pauta de bets no Google News...")

    # Tenta o Google Trends BR primeiro para pegar jogos em alta
    try:
        r = requests.get("https://trends.google.com/trending/rss?geo=BR", timeout=15)
        r.raise_for_status()
        feed = feedparser.parse(r.content)
        bets_kw = ['futebol', 'jogo', 'placar', 'gol', 'campeonato', 'copa',
                   'partida', 'confronto', 'brasileirão', 'libertadores',
                   'champions', 'nba', 'tênis', 'bet', 'aposta']
        relevant = [e for e in feed.entries[:25]
                    if any(kw in e.title.lower() for kw in bets_kw)]
        if relevant:
            item = random.choice(relevant)
            news_url = item.get('ht_news_item_url', '')
            news_source = item.get('ht_news_item_source', '')
            traffic = item.get('ht_approx_traffic', 'alto volume')
            topic = item.title
            context = (f"Tendência em alta no Brasil com {traffic} buscas. "
                       f"Cobertura: {news_source}.")
            print(f"  -> Trends: {topic}")
            return topic, context, news_url
    except Exception as e:
        print(f"  Trends falhou ({e}), tentando Google News...")

    # Fallback: Google News sobre bets
    try:
        url = (f"https://news.google.com/rss/search?q={BETS_QUERY}"
               "&hl=pt-BR&gl=BR&ceid=BR:pt-419")
        r = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        })
        feed = feedparser.parse(r.content)
        if feed.entries:
            item = random.choice(feed.entries[:15])
            print(f"  -> News: {item.title}")
            return item.title, item.get('summary', ''), ''
    except Exception as e:
        print(f"  News falhou ({e})")

    pauta = random.choice(PAUTAS_FALLBACK)
    print(f"  -> Pauta fixa: {pauta}")
    return pauta, "", ""

def get_gemini_content_bets(topic, context="", news_url=""):
    print(f"[2] Gerando artigo de bets sobre '{topic}'...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_API_KEY}"

    link_inst = (
        f"Inclua EXATAMENTE este link externo no texto: "
        f"<a href='{news_url}' target='_blank' rel='noopener'>confira a cobertura completa</a>."
        if news_url else
        "Inclua 1 link externo para uma fonte confiável (ESPN, ge.globo.com, Sofascore, "
        "transfermarkt.com ou odds.com.br)."
    )

    prompt = (
        f"INSTRUÇÃO CRÍTICA: Você é um especialista em apostas esportivas com 10 anos de experiência, "
        f"escrevendo para o blog 'Tudo sobre Bets' (bets.jornalmetro.com.br). "
        f"Escreva um artigo completo e especializado sobre: '{topic}'.\n"
        f"Contexto: {context}\n\n"
        f"DIRETRIZES:\n"
        f"- TÍTULO chamativo e especializado, máx 70 caracteres. "
        f"Exemplos: 'Palpites certeiros para [jogo] hoje', "
        f"'Como lucrar com [tema] usando esta estratégia'\n"
        f"- EXTENSÃO: mínimo 900 palavras com análise real e profunda.\n"
        f"- LINGUAGEM: técnica mas acessível, tom de especialista confiante. "
        f"Sem jargões de IA ('vale lembrar', 'é importante notar', 'em resumo').\n"
        f"- CONTEÚDO: inclua estatísticas, histórico de confrontos quando relevante, "
        f"análise de odds, dicas práticas de gestão de banca.\n"
        f"- AVISO DE RESPONSABILIDADE: inclua 1 parágrafo curto no final alertando "
        f"sobre jogo responsável e maiores de 18 anos.\n"
        f"- SEO: palavra-chave '{topic}' no título e primeiro parágrafo. "
        f"Use <h2>, <h3>, listas <ul><li>.\n"
        f"- {link_inst}\n"
        f"- LINKS INTERNOS: 2 links: "
        f"<a href='https://{BLOG_DOMAIN}/search?q={urllib.parse.quote(topic)}'>"
        f"mais dicas sobre {topic}</a>\n"
        f"- FAQ: ao final, <h2>Perguntas Frequentes</h2> com 4-5 perguntas "
        f"<h3>Pergunta?</h3><p>Resposta.</p>\n\n"
        f"Formato de resposta OBRIGATÓRIO:\n\n"
        f"[TITULO]\n\n"
        f"[KEYWORD_IMAGEM]\n(palavra em inglês para Pexels)\n\n"
        f"[LABELS]\n(até 4 categorias. Ex: Apostas, Futebol, Estratégias, Dicas de Apostas)\n\n"
        f"[CONTEUDO]\n<p>HTML aqui...</p>"
    )

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
    response.raise_for_status()
    data = response.json()
    return data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')

def parse_gemini_output(text):
    import re
    try:
        t = re.search(r'\[TITULO\]\s*(.*?)\s*\[KEYWORD_IMAGEM\]', text, re.DOTALL | re.IGNORECASE)
        k = re.search(r'\[KEYWORD_IMAGEM\]\s*(.*?)\s*\[LABELS\]', text, re.DOTALL | re.IGNORECASE)
        l = re.search(r'\[LABELS\]\s*(.*?)\s*\[CONTEUDO\]', text, re.DOTALL | re.IGNORECASE)
        c = re.search(r'\[CONTEUDO\]\s*(.*)', text, re.DOTALL | re.IGNORECASE)
        return {
            'title': t.group(1).strip() if t else "Dicas de Apostas Esportivas",
            'keyword': k.group(1).strip() if k else "sports betting",
            'labels': l.group(1).strip() if l else "Apostas, Esportes",
            'content': c.group(1).strip() if c else "<p>Erro ao gerar conteúdo.</p>"
        }
    except Exception:
        return None

def get_pexels_image(keyword):
    print(f"[3] Buscando imagem no Pexels para '{keyword}'...")
    try:
        r = requests.get(
            f"https://api.pexels.com/v1/search?query={urllib.parse.quote(keyword)}&per_page=1&orientation=landscape",
            headers={"Authorization": PEXELS_API_KEY}, timeout=10
        )
        if r.status_code == 200:
            photos = r.json().get('photos', [])
            if photos:
                img = photos[0]['src']['original']
                alt = photos[0].get('alt', keyword)
                return (
                    f'<div class="separator" style="clear:both;text-align:center;">'
                    f'<img alt="{alt}" border="0" loading="lazy" decoding="async" src="{img}" '
                    f'style="border-radius:8px;margin-bottom:25px;'
                    f'box-shadow:0 4px 6px rgba(0,0,0,.1);width:100%;max-width:1200px;"/>'
                    f'</div>'
                )
    except Exception as e:
        print(f"  Erro Pexels: {e}")
    return ""

def main():
    service = get_blogger_service()
    topic, context, news_url = get_trending_topic_bets()
    raw = get_gemini_content_bets(topic, context, news_url)
    parsed = parse_gemini_output(raw)

    if not parsed:
        print("Falha ao parsear. Abortando.")
        return

    image_html = get_pexels_image(parsed['keyword'])
    labels = [lb.strip() for lb in parsed['labels'].split(',') if lb.strip()]

    print(f"[4] Publicando em {BLOG_DOMAIN} (ID: {BLOG_ID})...")
    res = service.posts().insert(blogId=BLOG_ID, body={
        "title": parsed['title'],
        "content": image_html + parsed['content'],
        "labels": labels
    }, isDraft=False).execute()

    print("=" * 60)
    print("  SUCESSO! Artigo publicado.")
    print("  LINK:", res.get('url'))
    print("=" * 60)

if __name__ == '__main__':
    main()
