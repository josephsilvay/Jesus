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

BLOG_ID = '962897428202871806'   # butanta.jornalmetro.com.br
BLOG_DOMAIN = 'butanta.jornalmetro.com.br'
SCOPES = ['https://www.googleapis.com/auth/blogger']

# Queries de busca hiperlocais para o Butantã e arredores
BUTANTA_QUERIES = [
    "Butantã São Paulo notícias",
    "Butantã trânsito segurança obras",
    "Pinheiros Vila Madalena Perdizes notícias",
    "USP Butantã eventos",
    "Rio Pinheiros obras São Paulo",
    "Zona Oeste São Paulo notícias hoje",
    "Butantã metro obras São Paulo",
]

# Pautas fixas de alta relevância local
PAUTAS_FALLBACK = [
    "Mobilidade no Butantã: como o metrô e os ônibus atendem os moradores",
    "USP e o bairro do Butantã: a relação entre universidade e comunidade",
    "Obras no Rio Pinheiros: o que muda para quem mora no Butantã",
    "Segurança pública no Butantã: números e iniciativas do bairro",
    "Comércio local do Butantã: conheça os melhores estabelecimentos",
    "Feiras e eventos no Butantã: programação cultural e de lazer",
    "Parques e áreas verdes do Butantã: onde respirar ar puro na Zona Oeste",
    "Escolas e educação no Butantã: opções para famílias do bairro",
    "Trânsito no Butantã: os pontos críticos e como evitá-los",
    "História do bairro do Butantã: da fazenda ao bairro universitário",
    "Saúde pública no Butantã: UBSs, hospitais e serviços disponíveis",
    "Butantã x Pinheiros: comparação entre os bairros vizinhos",
    "Instituto Butantan: pesquisas e visitas abertas ao público",
    "Moradia no Butantã: como está o mercado imobiliário local",
    "Restaurantes e gastronomia do Butantã: dicas para moradores",
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

def get_trending_topic_butanta():
    """Busca notícias recentes sobre o Butantã e Zona Oeste de SP."""
    print("[1] Buscando notícias sobre o Butantã e região...")

    # Tenta Google Trends SP/BR com filtro de palavras locais
    try:
        r = requests.get("https://trends.google.com/trending/rss?geo=BR", timeout=15)
        r.raise_for_status()
        feed = feedparser.parse(r.content)
        local_kw = [
            'butantã', 'pinheiros', 'zona oeste', 'usp', 'são paulo',
            'metrô', 'metro', 'trânsito sp', 'obras sp', 'prefeitura sp',
        ]
        relevant = [e for e in feed.entries[:25]
                    if any(kw in e.title.lower() for kw in local_kw)]
        if relevant:
            item = random.choice(relevant)
            traffic = item.get('ht_approx_traffic', 'alto volume')
            news_url = item.get('ht_news_item_url', '')
            news_source = item.get('ht_news_item_source', '')
            context = (f"Assunto em alta no Brasil com {traffic} buscas. "
                       f"Cobertura: {news_source}.")
            print(f"  -> Trends: {item.title}")
            return item.title, context, news_url
    except Exception as e:
        print(f"  Trends falhou ({e}), tentando Google News...")

    # Busca direta por notícias locais do Butantã no Google News
    try:
        query = random.choice(BUTANTA_QUERIES)
        url = (f"https://news.google.com/rss/search"
               f"?q={urllib.parse.quote(query)}&hl=pt-BR&gl=BR&ceid=BR:pt-419")
        r = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        })
        feed = feedparser.parse(r.content)
        if feed.entries:
            item = random.choice(feed.entries[:10])
            print(f"  -> News: {item.title}")
            context = item.get('summary', '')
            return item.title, context, ''
    except Exception as e:
        print(f"  News falhou ({e})")

    # Fallback seguro: pauta fixa do nicho local
    pauta = random.choice(PAUTAS_FALLBACK)
    print(f"  -> Pauta fixa: {pauta}")
    return pauta, "Assunto de interesse dos moradores do Butantã e Zona Oeste de SP.", ""

def get_gemini_content_butanta(topic, context="", news_url=""):
    print(f"[2] Gerando artigo sobre o Butantã: '{topic}'...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_API_KEY}"

    link_inst = (
        f"Inclua EXATAMENTE este link no texto: "
        f"<a href='{news_url}' target='_blank' rel='noopener'>leia a matéria completa</a>."
        if news_url else
        "Inclua 1 link externo para fonte confiável (G1 SP, UOL, Folha de SP, "
        "Estadão, Agência SP ou Prefeitura de SP)."
    )

    prompt = (
        f"INSTRUÇÃO CRÍTICA: Você é um jornalista local experiente que cobre o bairro do Butantã "
        f"e a Zona Oeste de São Paulo para o 'Jornal do Butantã' (butanta.jornalmetro.com.br). "
        f"Escreva uma matéria jornalística completa e relevante para os moradores locais sobre: '{topic}'.\n"
        f"Contexto: {context}\n\n"
        f"DIRETRIZES:\n"
        f"- TÍTULO jornalístico e chamativo, máx 70 caracteres. "
        f"Sempre contextualizado ao Butantã ou Zona Oeste. "
        f"Exemplos: 'Obras no Butantã: saiba o que muda para os moradores', "
        f"'Segurança no Butantã tem nova iniciativa da prefeitura'\n"
        f"- ÂNGULO LOCAL: conecte SEMPRE o tema ao bairro do Butantã, seus moradores, "
        f"ruas, comércio, serviços ou história. "
        f"Mencione ruas, regiões ou pontos de referência reais do bairro quando possível "
        f"(Av. Corifeu de Azevedo Marques, Rua Figueiredo Magalhães, "
        f"USP, Instituto Butantan, Metrô Butantã, Ceasa, etc.).\n"
        f"- EXTENSÃO: mínimo 900 palavras com informação real e útil ao leitor local.\n"
        f"- LINGUAGEM: jornalismo local, próximo do leitor, claro e objetivo. "
        f"Sem jargões de IA ('é importante notar', 'vale lembrar', 'em resumo').\n"
        f"- SERVIÇO: inclua ao menos 1 bloco de 'informações úteis' "
        f"(telefones, endereços, horários ou links de serviços públicos mencionados).\n"
        f"- SEO: '{topic}' e 'Butantã' no título e primeiro parágrafo. "
        f"Use <h2>, <h3>, listas <ul><li>.\n"
        f"- {link_inst}\n"
        f"- LINKS INTERNOS: 2 links: "
        f"<a href='https://{BLOG_DOMAIN}/search?q={urllib.parse.quote(topic)}'>"
        f"mais notícias sobre {topic}</a>\n"
        f"- FAQ: <h2>Perguntas Frequentes</h2> com 4-5 perguntas "
        f"<h3>Pergunta?</h3><p>Resposta.</p> que moradores buscam no Google.\n\n"
        f"Formato de resposta OBRIGATÓRIO:\n\n"
        f"[TITULO]\n\n"
        f"[KEYWORD_IMAGEM]\n(palavra em inglês para Pexels)\n\n"
        f"[LABELS]\n(até 4 categorias. Ex: Butantã, Zona Oeste, São Paulo, Mobilidade)\n\n"
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
            'title': t.group(1).strip() if t else "Notícias do Butantã",
            'keyword': k.group(1).strip() if k else "sao paulo neighborhood",
            'labels': l.group(1).strip() if l else "Butantã, São Paulo",
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
    topic, context, news_url = get_trending_topic_butanta()
    raw = get_gemini_content_butanta(topic, context, news_url)
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
