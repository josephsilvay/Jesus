import os
import random
import time
import feedparser
import urllib.parse
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv
import requests

# Carrega chaves (Gemini/Pexels) do arquivo .env original
load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
PEXELS_API_KEY = os.getenv('PEXELS_API_KEY')

# Escopo necessário para postar no Blogger
SCOPES = ['https://www.googleapis.com/auth/blogger']

def get_blogger_service():
    """Autentica o usuario e retorna o serviço da API do Blogger apontado pelo OAuth."""
    creds = None
    if os.path.exists('token.json'):
        try:
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        except Exception as e:
            print(f"❌ Erro ao ler token.json: {e}")
            print("Verifique se o segredo TOKEN_JSON no GitHub Actions contém um JSON válido.")
            raise
    else:
        print("⚠️ token.json não encontrado.")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 O token expirou. Tentando renovar com o refresh_token...")
            try:
                creds.refresh(Request())
                print("✅ Token renovado com sucesso!")
                with open('token.json', 'w') as token:
                    token.write(creds.to_json())
            except Exception as e:
                print(f"❌ Erro ao renovar o token: {e}")
                print("Isso geralmente acontece porque o refresh token expirou ou foi revogado.")
                print("Se você configurou seu consentimento OAuth como 'Em Teste' (Testing) no Google Console, o refresh token expira em 7 dias.")
                print("Solução: Rode o script localmente para gerar um novo token.json e atualize o segredo TOKEN_JSON no GitHub.")
                raise
        else:
            print("⚠️ Token inexistente/inválido e sem refresh_token válido.")
            if not os.path.exists('client_secret.json'):
                print("❌ Erro: client_secret.json não encontrado.")
                print("Verifique se o segredo CLIENT_SECRET_JSON no GitHub está configurado.")
                raise FileNotFoundError("client_secret.json não encontrado")
            try:
                flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
            except Exception as e:
                print(f"❌ Erro ao carregar client_secret.json: {e}")
                print("Verifique se o segredo CLIENT_SECRET_JSON no GitHub é um JSON válido.")
                raise
            
            if os.getenv('GITHUB_ACTIONS') == 'true':
                print("❌ Erro: É necessária autenticação interativa, mas o script está rodando em ambiente headless (GitHub Actions).")
                print("Não é possível abrir o navegador para login.")
                print("Solução: Execute o bot localmente (onde abrirá o navegador para login), "
                      "e depois copie o conteúdo do arquivo 'token.json' gerado para o segredo TOKEN_JSON do GitHub.")
                raise PermissionError("Autenticação interativa necessária no GitHub Actions.")
                
            print("🔑 Abrindo navegador para autenticação...")
            creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
                
    return build('blogger', 'v3', credentials=creds)

def get_blog_id(service):
    """Procura automaticamente o Blog ID correto na sua conta Google."""
    request = service.blogs().listByUser(userId='self')
    response = request.execute()
    if 'items' in response:
        for blog in response['items']:
            # Garante que o alvo é o blog principal f5ul.com
            if 'f5ul.com' in blog['url'] or '5307582001063172924' == blog['id']:
                return blog['id']
        # Fallback: retorna o primeiro da conta
        return response['items'][0]['id']
    raise Exception("Nenhum blog encontrado na sua conta!")

def get_trending_topic():
    """Busca tópicos em alta no Google Trends Brasil."""
    print("[1] Buscando Trending Topics no Google Trends Brasil...")
    url = "https://trends.google.com/trending/rss?geo=BR"
    is_trends = True
    
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        xml_content = r.content
    except Exception as e:
        print(f"  ⚠️ Erro ao acessar Google Trends ({e}). Usando Google News como fallback...")
        url = "https://news.google.com/rss?hl=pt-BR&gl=BR&ceid=BR:pt-419"
        r = requests.get(url, timeout=15)
        xml_content = r.content
        is_trends = False

    feed = feedparser.parse(xml_content)
    
    if not feed.entries:
        raise Exception("Nenhum tópico retornado pelo feed. Verifique a conexão.")
    
    # Sorteia um dos 15 primeiros
    item = random.choice(feed.entries[:15])
    topic_title = item.title
    
    if is_trends:
        approx_traffic = item.get('ht_approx_traffic', 'alto volume')
        news_title = item.get('ht_news_item_title', '')
        news_url = item.get('ht_news_item_url', '')
        news_source = item.get('ht_news_item_source', '')
        
        context = f"Termo em alta no Google Trends com mais de {approx_traffic} buscas. Notícia de referência: '{news_title}' publicada por {news_source}."
    else:
        context = item.get('summary', '')
        news_url = ''
        
    print(f"  -> Tópico Sorteado: {topic_title}")
    return topic_title, context, news_url

def get_gemini_content(topic, context="", news_url=""):
    """Comunica com o Gemini para escrever a notícia jornalística."""
    print(f"[2] Gerando artigo otimizado (alto CTR) via Gemini sobre '{topic}'...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_API_KEY}"
    
    link_inst = f"Use EXATAMENTE a URL '{news_url}' no atributo href do link para referenciar a fonte oficial da notícia." if news_url else "Use um link para um site de autoridade e credibilidade (como gov.br, G1 ou similar)."
    
    prompt = (
        f"INSTRUÇÃO CRÍTICA: Você é um jornalista digital sênior, especialista em SEO e redação de alto engajamento (estilo R7, G1 e BuzzFeed). "
        f"Escreva uma Notícia completa de altíssimo impacto e potencial de cliques (alto CTR) sobre o tópico em alta do Google Trends: '{topic}'.\n"
        f"Contexto do assunto: {context}\n\n"
        f"ESTRATÉGIAS DE CLIQUE E SEO (POTENCIAL DE CLIQUES):\n"
        f"- TÍTULO IRRESISTÍVEL: Escreva um título extremamente atraente, com gatilhos de curiosidade, impacto emocional ou revelação (ex: 'O verdadeiro motivo por trás de...', 'Entenda a polêmica...', ou revelações importantes). Evite caixa alta completa ou termos sensacionalistas vazios como 'CHOQUE'. Deve ser jornalístico, porém impossível de não clicar.\n"
        f"- PALAVRA-CHAVE EM DESTAQUE: A palavra-chave/assunto exato '{topic}' deve aparecer de forma natural no título e no primeiro parágrafo do texto.\n"
        f"- HOOK INICIAL: Comece a notícia com uma frase de impacto direto que prenda o leitor nos primeiros 3 segundos.\n"
        f"- E-E-A-T E FONTES: Insira EXATAMENTE 1 hiperlink externo no corpo do texto (na primeira metade da notícia) apontando para a notícia de referência oficial. {link_inst} Exemplo de formato: <a href='...' target='_blank'>veja os detalhes na cobertura original</a>.\n"
        f"- LINKS INTERNOS: Insira estrategicamente no meio do texto 1 ou 2 links internos cruzados. Como o blog é f5ul.com, crie âncoras temáticas apontando para a busca do blog no formato: <a href='https://www.f5ul.com/search?q={urllib.parse.quote(topic)}'>leia mais sobre {topic}</a>.\n"
        f"- LEITURA DINÂMICA: Use parágrafos curtos, frases diretas, listas de itens, <h2>, <h3> para escaneabilidade rápida.\n"
        f"- SEM CLICHÊS DE IA: Banido o uso de termos genéricos como 'em resumo', 'por fim', 'é importante notar', 'no cenário atual'. Use transições humanas e jornalísticas.\n"
        f"- PERGUNTAS FREQUENTES (FAQ): Ao final da matéria, inclua uma seção com <h2>Perguntas Frequentes</h2> e de 3 a 5 perguntas objetivas com tags <h3> e respostas curtas com <p>, refletindo o que os usuários pesquisariam no Google sobre o tema.\n\n"
        f"REGRAS DE FORMATO:\n"
        f"- Retorne EXCLUSIVAMENTE no formato abaixo.\n"
        f"- Não adicione formatação markdown na resposta geral fora do [CONTEUDO].\n\n"
        f"[TITULO]\n(Escreva o título chamativo com no máximo 70 caracteres)\n\n"
        f"[KEYWORD_IMAGEM]\n(palavra única em inglês para buscar uma foto ilustrativa de alta qualidade no Pexels)\n\n"
        f"[LABELS]\n(Até 3 categorias ou temas separados por vírgula. Ex: Entretenimento, Brasil, Esportes)\n\n"
        f"[CONTEUDO]\n<p>Aqui entra o texto HTML com corpo da noticia</p>"
    )
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {"Content-Type": "application/json"}
    
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    data = response.json()
    
    candidate = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
    if not candidate:
         raise Exception("O Gemini não retornou um formato valido.")
    return candidate

def parse_gemini_output(text):
    """Separa as peças Title, Keyword, Labels e Content."""
    import re
    try:
        t_match = re.search(r'\[TITULO\]\s*(.*?)\s*\[KEYWORD_IMAGEM\]', text, re.DOTALL | re.IGNORECASE)
        k_match = re.search(r'\[KEYWORD_IMAGEM\]\s*(.*?)\s*\[LABELS\]', text, re.DOTALL | re.IGNORECASE)
        l_match = re.search(r'\[LABELS\]\s*(.*?)\s*\[CONTEUDO\]', text, re.DOTALL | re.IGNORECASE)
        c_match = re.search(r'\[CONTEUDO\]\s*(.*)', text, re.DOTALL | re.IGNORECASE)
        
        return {
            'title': t_match.group(1).strip() if t_match else "Giro de Notícias Importante",
            'keyword': k_match.group(1).strip() if k_match else "news",
            'labels': l_match.group(1).strip() if l_match else "Notícias",
            'content': c_match.group(1).strip() if c_match else "<p>Erro ao ler o robô</p>"
        }
    except Exception as e:
        print("Erro no parseamento. Extração manual falhou.")
        return None

def get_pexels_image(keyword):
    """Busca imagem no Pexels"""
    print(f"[3] Procurando imagem no banco Pexels para '{keyword}'...")
    url = f"https://api.pexels.com/v1/search?query={urllib.parse.quote(keyword.split(',')[0])}&per_page=1&orientation=landscape"
    headers = {"Authorization": PEXELS_API_KEY}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if data.get('photos'):
            url_img = data['photos'][0]['src']['original']
            alt_text = data['photos'][0].get('alt', keyword)
            return f'<div class="separator" style="clear: both; text-align: center;"><img alt="{alt_text}" border="0" data-original-height="1000" data-original-width="1500" src="{url_img}" style="border-radius: 8px; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 100%; max-width: 800px;"/></div>'
    return ""

def main():
    if not GEMINI_API_KEY:
        print("❌ Erro: GEMINI_API_KEY não está configurada no ambiente ou no arquivo .env!")
        print("Verifique se o segredo ENV_FILE no GitHub contém GEMINI_API_KEY.")
        raise ValueError("GEMINI_API_KEY não encontrada")
    if not PEXELS_API_KEY:
        print("❌ Erro: PEXELS_API_KEY não está configurada no ambiente ou no arquivo .env!")
        print("Verifique se o segredo ENV_FILE no GitHub contém PEXELS_API_KEY.")
        raise ValueError("PEXELS_API_KEY não encontrada")

    service = get_blogger_service()
    blog_id = get_blog_id(service)
    
    topic, context, news_url = get_trending_topic()
    raw_text = get_gemini_content(topic, context, news_url)
    parsed = parse_gemini_output(raw_text)
    
    if not parsed:
        print("Falha ao gerar os dados. Abortando turno.")
        return
        
    image_html = get_pexels_image(parsed['keyword'])
    
    # Prepara HTML para o Blogger (Blogger prefere imagens injetadas direto no post)
    final_html = image_html + parsed['content']
    
    # Etiquetas (Labels) transformadas em Lista
    labels_list = [lb.strip() for lb in parsed['labels'].split(',') if lb.strip()]
    
    post_data = {
        "title": parsed['title'],
        "content": final_html,
        "labels": labels_list
    }
    
    print(f"[4] Publicando no Blogger f5ul.com (BlogID: {blog_id})...")
    request = service.posts().insert(blogId=blog_id, body=post_data, isDraft=False)
    response = request.execute()
    
    print("=" * 60)
    print(" SUCESSO! Artigo publicado.")
    print(" LINK:", response.get('url'))
    print("=" * 60)

if __name__ == '__main__':
    main()
