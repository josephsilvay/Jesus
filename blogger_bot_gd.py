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

BLOG_ID = '3535680605318989698'  # ganhardinheiro.jornalmetro.com.br
BLOG_DOMAIN = 'ganhardinheiro.jornalmetro.com.br'
SCOPES = ['https://www.googleapis.com/auth/blogger']

# Palavras-chave de alto CPC para busca no Google News
HIGH_CPC_QUERY = (
    "cartão+de+crédito+OR+Serasa+OR+INSS+OR+Bolsa+Família+"
    "OR+empréstimo+OR+Caixa+Tem+OR+FGTS+OR+score+OR+renda+extra+"
    "OR+auxílio+OR+benefício+OR+financiamento+OR+negativado"
)

# Pautas fixas de fallback (alto CPC garantido)
PAUTAS_FALLBACK = [
    "Como aumentar o score do Serasa rapidamente em 2026",
    "Cartão de crédito sem anuidade para negativados em 2026",
    "Como solicitar empréstimo pelo FGTS pelo celular",
    "Bolsa Família 2026: quem tem direito e como se cadastrar",
    "INSS 2026: como consultar benefícios pelo aplicativo",
    "Caixa Tem: novidades e como usar o saldo do auxílio",
    "Como limpar o nome e sair do SPC e Serasa de graça",
    "Renda extra em casa: melhores formas de ganhar dinheiro em 2026",
    "Financiamento de carro: como conseguir com o nome sujo",
    "Empréstimo consignado para aposentados e pensionistas do INSS",
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

def get_trending_topic_gd():
    """Busca notícias de alto CPC sobre finanças no Brasil."""
    print("[1] Buscando pauta de alto CPC no Google News...")
    url = (
        f"https://news.google.com/rss/search?q={HIGH_CPC_QUERY}"
        "&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    )
    try:
        r = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        })
        r.raise_for_status()
        feed = feedparser.parse(r.content)
        if feed.entries:
            item = random.choice(feed.entries[:15])
            print(f"  -> Pauta: {item.title}")
            return item.title, item.get('summary', '')
    except Exception as e:
        print(f"  Fallback (erro: {e})")

    pauta = random.choice(PAUTAS_FALLBACK)
    print(f"  -> Pauta fixa: {pauta}")
    return pauta, ""

def get_gemini_content_gd(topic, context=""):
    print(f"[2] Gerando artigo de alto CPC sobre '{topic}'...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_API_KEY}"

    prompt = (
        f"INSTRUÇÃO CRÍTICA: Você é um repórter financeiro sênior estilo E-E-A-T "
        f"escrevendo para o portal 'Ganhar Dinheiro'. "
        f"Produza uma matéria completa sobre: '{topic}'.\n"
        f"Contexto: {context}\n\n"
        f"DIRETRIZES:\n"
        f"- TÍTULO chamativo e jornalístico, máx 70 caracteres. Exemplos de estilo: "
        f"'Saiba como consultar seu benefício INSS sem sair de casa', "
        f"'Score acima de 700: o que fazer diferente em 2026'\n"
        f"- EXTENSÃO: mínimo 900 palavras. Artigos curtos serão descartados.\n"
        f"- LINGUAGEM: natural, direta, voltada para as dores financeiras do leitor. "
        f"Proibido jargões de IA ('no cenário atual', 'em resumo', 'por fim', 'vale lembrar').\n"
        f"- SEO: palavra-chave no título e primeiro parágrafo. "
        f"Use <h2>, <h3> e listas <ul><li> para escaneabilidade.\n"
        f"- LINK EXTERNO: 1 hiperlink para fonte oficial (gov.br, Banco Central, Serasa, "
        f"Caixa, INSS, G1) que valide os fatos. "
        f"Formato: <a href='URL' target='_blank'>texto ancora</a>\n"
        f"- LINKS INTERNOS: 2 links internos no formato: "
        f"<a href='https://{BLOG_DOMAIN}/search?q={urllib.parse.quote(topic)}'>"
        f"leia mais sobre {topic}</a>\n"
        f"- CITAÇÃO: 1 citação real de autoridade (ministro, diretor de banco, especialista). "
        f"Cite a fonte claramente. Não invente.\n"
        f"- FAQ: ao final, <h2>Perguntas Frequentes</h2> com 4-5 perguntas "
        f"<h3>Pergunta?</h3><p>Resposta.</p> que o leitor pesquisaria no Google.\n\n"
        f"Formato de resposta OBRIGATÓRIO:\n\n"
        f"[TITULO]\n\n"
        f"[KEYWORD_IMAGEM]\n(palavra em inglês para Pexels)\n\n"
        f"[LABELS]\n(até 3 categorias. Ex: Cartão, Empréstimo, Benefício)\n\n"
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
            'title': t.group(1).strip() if t else "Novidades Financeiras",
            'keyword': k.group(1).strip() if k else "finance",
            'labels': l.group(1).strip() if l else "Dinheiro, Finanças",
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
    topic, context = get_trending_topic_gd()
    raw = get_gemini_content_gd(topic, context)
    parsed = parse_gemini_output(raw)

    if not parsed:
        print("Falha ao parsear conteúdo. Abortando.")
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
