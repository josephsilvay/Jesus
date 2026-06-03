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

BLOG_ID = '7077322472767831610'
SCOPES = ['https://www.googleapis.com/auth/blogger']

TRENDING_COUNTRIES = ['MX', 'AR', 'CO', 'ES', 'CL', 'PE', 'VE']
COUNTRY_NAMES = {
    'MX': 'México', 'AR': 'Argentina', 'CO': 'Colombia',
    'ES': 'España', 'CL': 'Chile', 'PE': 'Perú', 'VE': 'Venezuela'
}

TEMAS_CASEIROS = [
    "trucos para limpiar el baño sin esfuerzo",
    "remedios caseros para el dolor de cabeza",
    "cómo eliminar manchas de ropa con ingredientes de cocina",
    "plantas que alejan mosquitos de tu hogar",
    "trucos de limpieza que tu abuela conocía",
    "cómo hacer un desengrasante casero poderoso",
    "remedios naturales para la gripe y el resfriado",
    "cómo organizar la cocina para ahorrar tiempo",
    "bicarbonato de sodio usos caseros sorprendentes",
    "vinagre blanco para limpiar el hogar",
    "cómo hacer jabón líquido en casa",
    "plantas medicinales que debes tener en casa",
    "cómo eliminar el moho de las paredes naturalmente",
    "trucos para mantener los alimentos frescos por más tiempo",
    "remedios caseros para el insomnio",
    "cómo limpiar el microondas con limón",
    "cómo ahorrar agua y electricidad en casa",
    "recetas de limpiadores multiusos caseros",
    "tips para eliminar olores del hogar",
    "cómo hacer compost en casa fácilmente",
]

def get_blogger_service():
    creds = None
    token_file = 'token.json'
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
    return build('blogger', 'v3', credentials=creds)

def get_trending_topic_es():
    geo = random.choice(TRENDING_COUNTRIES)
    print(f"[1] Buscando tendencias en {COUNTRY_NAMES.get(geo, geo)} (Google Trends)...")

    dicas_keywords = [
        'limpiar', 'cocina', 'hogar', 'casa', 'remedio', 'salud',
        'receta', 'plantas', 'natural', 'ahorro', 'organizar',
        'trucos', 'consejos', 'jardín', 'limpieza', 'alimentos'
    ]

    url = f"https://trends.google.com/trending/rss?geo={geo}"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        feed = feedparser.parse(r.content)
        if feed.entries:
            relevant = [e for e in feed.entries[:20] if any(kw in e.title.lower() for kw in dicas_keywords)]
            item = random.choice(relevant) if relevant else random.choice(feed.entries[:15])

            approx_traffic = item.get('ht_approx_traffic', 'alto volumen')
            news_title = item.get('ht_news_item_title', '')
            news_url = item.get('ht_news_item_url', '')
            news_source = item.get('ht_news_item_source', '')
            context = (
                f"Tendencia en Google Trends {COUNTRY_NAMES.get(geo, geo)} con {approx_traffic} búsquedas. "
                f"Referencia: '{news_title}' — {news_source}."
            )
            print(f"  -> Tendencia: {item.title}")
            return item.title, context, news_url, geo
    except Exception as e:
        print(f"  Fallback (error: {e})")

    tema = random.choice(TEMAS_CASEIROS)
    print(f"  -> Tema fijo: {tema}")
    return tema, "Consejo casero muy popular en países hispanohablantes.", "", geo

def get_gemini_content_es(topic, context="", news_url="", geo="MX"):
    print(f"[2] Generando artículo en español sobre '{topic}'...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_API_KEY}"

    link_inst = (
        f"Incluye EXACTAMENTE este enlace externo en el texto: <a href='{news_url}' target='_blank' rel='noopener'>más información aquí</a>."
        if news_url else
        "Incluye 1 enlace a una fuente confiable (Wikipedia en español, healthline.com/es, consumer.es o similar)."
    )

    prompt = (
        f"INSTRUCCIÓN: Eres una abuela sabia y experta en trucos caseros, remedios naturales y consejos del hogar. "
        f"Escribe un artículo en ESPAÑOL PERFECTO sobre: '{topic}'.\n"
        f"Contexto: {context}\n\n"
        f"REGLAS:\n"
        f"- TÍTULO con gancho emocional, máx 70 caracteres. Estilo: '7 trucos que tu abuela conocía...'\n"
        f"- VOZ CÁLIDA: escribe como abuela afectuosa, usa 'tú', 'mija/mijo'. Sin lenguaje de IA.\n"
        f"- HOOK: primera frase que enganche en 3 segundos.\n"
        f"- Usa <h2>, <h3>, listas <ul><li>, párrafos cortos.\n"
        f"- '{topic}' en título y primer párrafo.\n"
        f"- {link_inst}\n"
        f"- 2 enlaces internos: <a href='https://dicasdevovo.blogspot.com/search?q={urllib.parse.quote(topic)}'>más trucos sobre {topic}</a>\n"
        f"- Mínimo 800 palabras con consejos prácticos reales.\n"
        f"- PREGUNTAS FRECUENTES al final: <h2>Preguntas Frecuentes</h2> con 3-4 <h3>¿...?</h3><p>respuesta</p>\n"
        f"- 100% español. Sin frases de IA como 'en conclusión', 'es importante destacar'.\n\n"
        f"Formato de respuesta OBLIGATORIO:\n\n"
        f"[TITULO]\n\n"
        f"[KEYWORD_IMAGEN]\n(una palabra en inglés para Pexels)\n\n"
        f"[LABELS]\n(hasta 3 categorías en español)\n\n"
        f"[CONTENIDO]\n<p>HTML aquí...</p>"
    )

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
    response.raise_for_status()
    data = response.json()
    return data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')

def parse_gemini_output_es(text):
    import re
    try:
        t = re.search(r'\[TITULO\]\s*(.*?)\s*\[KEYWORD_IMAGEN\]', text, re.DOTALL | re.IGNORECASE)
        k = re.search(r'\[KEYWORD_IMAGEN\]\s*(.*?)\s*\[LABELS\]', text, re.DOTALL | re.IGNORECASE)
        l = re.search(r'\[LABELS\]\s*(.*?)\s*\[CONTENIDO\]', text, re.DOTALL | re.IGNORECASE)
        c = re.search(r'\[CONTENIDO\]\s*(.*)', text, re.DOTALL | re.IGNORECASE)
        return {
            'title': t.group(1).strip() if t else "Trucos caseros de la abuela",
            'keyword': k.group(1).strip() if k else "home cleaning",
            'labels': l.group(1).strip() if l else "Trucos, Hogar",
            'content': c.group(1).strip() if c else "<p>Error al generar contenido.</p>"
        }
    except Exception:
        return None

def get_pexels_image(keyword):
    print(f"[3] Buscando imagen en Pexels para '{keyword}'...")
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
                    f'<img alt="{alt}" border="0" loading="lazy" src="{img}" '
                    f'style="border-radius:10px;margin-bottom:20px;'
                    f'box-shadow:0 4px 15px rgba(0,0,0,.15);width:100%;max-width:800px;"/>'
                    f'</div>'
                )
    except Exception as e:
        print(f"  Error Pexels: {e}")
    return ""

def main():
    service = get_blogger_service()
    topic, context, news_url, geo = get_trending_topic_es()
    raw = get_gemini_content_es(topic, context, news_url, geo)
    parsed = parse_gemini_output_es(raw)
    if not parsed:
        print("Falha ao parsear. Abortando.")
        return
    image_html = get_pexels_image(parsed['keyword'])
    labels = [lb.strip() for lb in parsed['labels'].split(',') if lb.strip()]
    print(f"[4] Publicando no Blogger ES (ID: {BLOG_ID})...")
    res = service.posts().insert(blogId=BLOG_ID, body={
        "title": parsed['title'],
        "content": image_html + parsed['content'],
        "labels": labels
    }, isDraft=False).execute()
    print("=" * 60)
    print("  ¡ÉXITO! Artículo publicado.")
    print("  LINK:", res.get('url'))
    print("=" * 60)

if __name__ == '__main__':
    main()
