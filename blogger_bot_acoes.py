import os
import random
import feedparser
import urllib.parse
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv
from gemini_retry import call_gemini_with_retry
import requests

load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
PEXELS_API_KEY = os.getenv('PEXELS_API_KEY')

BLOG_ID = '7723830856360056852'   # acoes.jornalmetro.com.br
BLOG_DOMAIN = 'acoes.jornalmetro.com.br'
SCOPES = ['https://www.googleapis.com/auth/blogger']

# Busca no Google News por termos de mercado financeiro/ações
ACOES_QUERY = (
    "B3+OR+Ibovespa+OR+PETR4+OR+VALE3+OR+ITUB4+OR+BBDC4+OR+MGLU3+"
    "OR+ações+bolsa+OR+dividendos+OR+FIIs+OR+fundos+imobiliários+"
    "OR+Selic+OR+Banco+Central+OR+inflação+IPCA+OR+dólar+hoje+"
    "OR+mercado+financeiro+Brasil+OR+B3+hoje"
)

# Pautas fixas de alto engajamento sobre ações
PAUTAS_FALLBACK = [
    "Ibovespa hoje: o que esperar do mercado na abertura",
    "PETR4 ou VALE3: qual ação rende mais em 2026",
    "Como investir na bolsa de valores com pouco dinheiro",
    "Dividendos: as melhores ações para renda passiva em 2026",
    "FIIs: os fundos imobiliários mais rentáveis para comprar agora",
    "Selic a 13,25%: como isso afeta seus investimentos na bolsa",
    "Small caps: as melhores ações baratas da B3 em 2026",
    "Como analisar uma ação antes de comprar: guia para iniciantes",
    "Dólar hoje: impacto das exportadoras na bolsa brasileira",
    "ETFs da B3: a forma mais fácil de diversificar na bolsa",
    "IPCA e inflação: como proteger seus investimentos",
    "Análise técnica vs fundamentalista: qual usar para escolher ações",
    "Tesouro Direto vs ações: qual rende mais em 2026",
    "Como declarar ações no Imposto de Renda 2026",
    "Carteira de ações: como montar do zero com R$ 500",
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

def get_trending_topic_acoes():
    """Busca notícias quentes sobre mercado de ações no Brasil."""
    print("[1] Buscando pauta sobre mercado de ações...")

    # Tenta Google Trends BR primeiro
    try:
        r = requests.get("https://trends.google.com/trending/rss?geo=BR", timeout=15)
        r.raise_for_status()
        feed = feedparser.parse(r.content)
        kw = ['bolsa', 'ação', 'ações', 'b3', 'ibovespa', 'petr', 'vale',
              'dividendo', 'fii', 'investimento', 'selic', 'mercado', 'dólar',
              'ipca', 'inflação', 'banco', 'petrobras', 'magazine', 'nubank']
        relevant = [e for e in feed.entries[:25]
                    if any(k in e.title.lower() for k in kw)]
        if relevant:
            item = random.choice(relevant)
            traffic = item.get('ht_approx_traffic', 'alto volume')
            news_url = item.get('ht_news_item_url', '')
            news_source = item.get('ht_news_item_source', '')
            context = (f"Tendência em alta no Brasil com {traffic} buscas. "
                       f"Cobertura: {news_source}.")
            print(f"  -> Trends: {item.title}")
            return item.title, context, news_url
        else:
            pauta = random.choice(PAUTAS_FALLBACK)
            print(f"  -> Sem trending relevante. Pauta fixa: {pauta}")
            return pauta, "", ""
    except Exception as e:
        print(f"  Trends falhou ({e}), tentando Google News...")

    # Fallback: Google News sobre ações
    try:
        url = (f"https://news.google.com/rss/search?q={ACOES_QUERY}"
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

    # Último fallback: pauta fixa do nicho de ações
    pauta = random.choice(PAUTAS_FALLBACK)
    print(f"  -> Pauta fixa: {pauta}")
    return pauta, "", ""

def get_gemini_content_acoes(topic, context="", news_url=""):
    print(f"[2] Gerando artigo sobre mercado de ações: '{topic}'...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_API_KEY}"

    link_inst = (
        f"Inclua EXATAMENTE este link externo no texto: "
        f"<a href='{news_url}' target='_blank' rel='noopener'>leia a cobertura completa</a>."
        if news_url else
        "Inclua 1 link externo para fonte confiável (InfoMoney, Valor Econômico, "
        "B3.com.br, Banco Central, Status Invest ou Fundamentus)."
    )

    prompt = (
        f"INSTRUÇÃO CRÍTICA: Você é um analista de mercado financeiro sênior com CGA/CFP, "
        f"especialista em ações brasileiras e B3, escrevendo para o portal 'Ações Hoje' "
        f"(acoes.jornalmetro.com.br). Produza uma matéria jornalística completa sobre: '{topic}'.\n"
        f"Contexto: {context}\n\n"
        f"DIRETRIZES:\n"
        f"- TÍTULO impactante e específico, máx 70 caracteres. "
        f"Exemplos: 'PETR4 sobe 3% após resultado: compra ou venda?', "
        f"'Ibovespa abre em alta com dados do Fed: o que esperar hoje'\n"
        f"- EXTENSÃO: mínimo 900 palavras com análise real e dados concretos.\n"
        f"- LINGUAGEM: técnica mas acessível, tom de analista experiente. "
        f"Nada de jargões de IA ('vale lembrar', 'é importante destacar', 'em resumo').\n"
        f"- DADOS: mencione preços, variações percentuais, volumes quando possível. "
        f"Se não tiver dados exatos, use dados ilustrativos e cite que são estimativas.\n"
        f"- ANÁLISE: inclua análise técnica básica (suporte/resistência), "
        f"fundamentos (P/L, DY) e perspectivas de curto/médio prazo.\n"
        f"- CONTEXTO MACRO: conecte o tema com Selic, dólar, inflação quando relevante.\n"
        f"- SEO: '{topic}' no título e primeiro parágrafo. Use <h2>, <h3>, <ul><li>.\n"
        f"- {link_inst}\n"
        f"- LINKS INTERNOS: 2 links: "
        f"<a href='https://{BLOG_DOMAIN}/search?q={urllib.parse.quote(topic)}'>"
        f"mais análises sobre {topic}</a>\n"
        f"- DISCLAIMER: 1 parágrafo ao final: "
        f"'Este conteúdo é informativo e não constitui recomendação de investimento. "
        f"Consulte um profissional certificado antes de investir.'\n"
        f"- FAQ: <h2>Perguntas Frequentes</h2> com 4-5 perguntas "
        f"<h3>Pergunta?</h3><p>Resposta.</p> que investidores buscam no Google.\n\n"
        f"Formato de resposta OBRIGATÓRIO:\n\n"
        f"[TITULO]\n\n"
        f"[KEYWORD_IMAGEM]\n(palavra em inglês para Pexels)\n\n"
        f"[LABELS]\n(até 4 categorias. Ex: Ações, B3, Dividendos, Ibovespa)\n\n"
        f"[CONTEUDO]\n<p>HTML aqui...</p>"
    )

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    return call_gemini_with_retry(url, payload)

def parse_gemini_output(text):
    import re
    try:
        t = re.search(r'\[TITULO\]\s*(.*?)\s*\[KEYWORD_IMAGEM\]', text, re.DOTALL | re.IGNORECASE)
        k = re.search(r'\[KEYWORD_IMAGEM\]\s*(.*?)\s*\[LABELS\]', text, re.DOTALL | re.IGNORECASE)
        l = re.search(r'\[LABELS\]\s*(.*?)\s*\[CONTEUDO\]', text, re.DOTALL | re.IGNORECASE)
        c = re.search(r'\[CONTEUDO\]\s*(.*)', text, re.DOTALL | re.IGNORECASE)
        return {
            'title': t.group(1).strip() if t else "Mercado de Ações Hoje",
            'keyword': k.group(1).strip() if k else "stock market",
            'labels': l.group(1).strip() if l else "Ações, B3",
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
    topic, context, news_url = get_trending_topic_acoes()
    raw = get_gemini_content_acoes(topic, context, news_url)
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
