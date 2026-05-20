import os
import json
import urllib.request
import urllib.error
import ssl
import asyncio
import base64
import tempfile
import time
import edge_tts
from http.server import SimpleHTTPRequestHandler, HTTPServer

PORT = 8000

try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass

# ─── Carrega variáveis do .env ───────────────────────────────────
def load_env():
    env = {}
    if os.path.exists('.env'):
        with open('.env', 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    k, v = line.split('=', 1)
                    env[k.strip()] = v.strip()
    return env

# ─── TTS com edge-tts ────────────────────────────────────────────
def tts_to_base64(text):
    import re
    # Remove asteriscos e marcações de negrito do markdown
    cleaned = text.replace('*', '')

    # Dicionario de abreviações bíblicas comuns
    abbrevs = {
        'Gn': 'Gênesis', 'Ex': 'Êxodo', 'Êx': 'Êxodo', 'Lv': 'Levítico', 'Nm': 'Números',
        'Dt': 'Deuteronômio', 'Js': 'Josué', 'Jz': 'Juízes', 'Rt': 'Rute', '1Sm': '1 Samuel',
        '2Sm': '2 Samuel', '1Re': '1 Reis', '2Re': '2 Reis', '1Cr': '1 Crônicas', '2Cr': '2 Crônicas',
        'Ne': 'Neemias', 'Et': 'Ester', 'Sl': 'Salmos', 'Pv': 'Provérbios', 'Ec': 'Eclesiastes',
        'Ct': 'Cantares', 'Is': 'Isaías', 'Jr': 'Jeremias', 'Lm': 'Lamentações', 'Ez': 'Ezequiel',
        'Dn': 'Daniel', 'Os': 'Oseias', 'Jl': 'Joel', 'Am': 'Amós', 'Ob': 'Obadias',
        'Mq': 'Miqueias', 'Na': 'Naum', 'Hc': 'Habacuque', 'Sf': 'Sofonias', 'Ag': 'Ageu',
        'Zc': 'Zacarias', 'Ml': 'Malaquias', 'Mt': 'Mateus', 'Mc': 'Marcos', 'Lc': 'Lucas',
        'Jo': 'João', 'At': 'Atos', 'Rm': 'Romanos', '1Co': '1 Coríntios', '2Co': '2 Coríntios',
        '1Cor': '1 Coríntios', '2Cor': '2 Coríntios', 'Gl': 'Gálatas', 'Ef': 'Efésios',
        'Fp': 'Filipenses', 'Fil': 'Filipenses', 'Cl': 'Colossenses', '1Ts': '1 Tessalonicenses',
        '2Ts': '2 Tessalonicenses', '1Tm': '1 Timóteo', '2Tm': '2 Timóteo', 'Tt': 'Tito',
        'Fm': 'Filemon', 'Hb': 'Hebreus', 'Tg': 'Tiago', '1Pe': '1 Pedro', '2Pe': '2 Pedro',
        '1Jo': '1 João', '2Jo': '2 João', '3Jo': '3 João', 'Ap': 'Apocalipse'
    }

    # Tratamentos para algarismos romanos antes de livros (ex: II Co -> 2 Coríntios)
    cleaned = re.sub(r'\bIII\s+([A-Za-zÀ-ÿ]+)', r'3 \1', cleaned)
    cleaned = re.sub(r'\bII\s+([A-Za-zÀ-ÿ]+)', r'2 \1', cleaned)
    cleaned = re.sub(r'\bI\s+([A-Za-zÀ-ÿ]+)', r'1 \1', cleaned)

    # Substitui abreviações comuns de livros separadas
    book_abbrevs = {
        'Co': 'Coríntios', 'Cor': 'Coríntios', 'Pe': 'Pedro', 'Ped': 'Pedro', 'Jo': 'João',
        'Ts': 'Tessalonicenses', 'Tm': 'Timóteo', 'Cr': 'Crônicas', 'Sm': 'Samuel', 'Re': 'Reis'
    }
    for ab, full in book_abbrevs.items():
        cleaned = re.sub(r'\b' + ab + r'\b', full, cleaned)

    # Substitui a tabela geral de abreviações
    for ab, full in abbrevs.items():
        cleaned = re.sub(r'\b' + ab + r'\b', full, cleaned)

    # Converte os números de livros para a fala ordinal correta (ex: 2 Coríntios -> Segunda Coríntios)
    ordinals = {
        r'\b1\s+Coríntios\b': 'Primeira Coríntios',
        r'\b2\s+Coríntios\b': 'Segunda Coríntios',
        r'\b1\s+Pedro\b': 'Primeira Pedro',
        r'\b2\s+Pedro\b': 'Segunda Pedro',
        r'\b1\s+João\b': 'Primeira João',
        r'\b2\s+João\b': 'Segunda João',
        r'\b3\s+João\b': 'Terceira João',
        r'\b1\s+Tessalonicenses\b': 'Primeira Tessalonicenses',
        r'\b2\s+Tessalonicenses\b': 'Segunda Tessalonicenses',
        r'\b1\s+Timóteo\b': 'Primeiro Timóteo',
        r'\b2\s+Timóteo\b': 'Segundo Timóteo',
        r'\b1\s+Crônicas\b': 'Primeiro Crônicas',
        r'\b2\s+Crônicas\b': 'Segundo Crônicas',
        r'\b1\s+Reis\b': 'Primeiro Reis',
        r'\b2\s+Reis\b': 'Segundo Reis',
        r'\b1\s+Samuel\b': 'Primeiro Samuel',
        r'\b2\s+Samuel\b': 'Segundo Samuel',
    }
    for pat, rep in ordinals.items():
        cleaned = re.sub(pat, rep, cleaned)

    # Converte notações de capitulo:versiculo (ex: Mateus 6:34 -> Mateus, capítulo 6, versículo 34)
    cleaned = re.sub(r'(\b[A-Za-zÁÉÍÓÚÂÊÔÃÕÀáéíóúâêôãõ]+)\s+(\d+):(\d+)', r'\1, capítulo \2, versículo \3', cleaned)

    async def _gen():
        # Voz madura pt-BR-AntonioNeural com pitch e rate otimizados para sabedoria
        communicate = edge_tts.Communicate(cleaned, 'pt-BR-AntonioNeural', rate='-20%', pitch='-12Hz')
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
            path = tmp.name
        try:
            await communicate.save(path)
            with open(path, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
        finally:
            if os.path.exists(path):
                os.remove(path)

    try:
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(_gen())
    finally:
        loop.close()

# ─── Chamada à API Groq (OpenAI-compatible) ──────────────────────
def call_groq(api_key, user_message, system_prompt):
    """
    Tenta os modelos Groq em ordem de qualidade/limite.
    - llama-3.3-70b-versatile:  1.000 req/dia (melhor qualidade)
    - llama-3.1-8b-instant:    14.400 req/dia (backup rápido)
    """
    groq_models = [
        'llama-3.3-70b-versatile',
        'llama-3.1-8b-instant',
        'mixtral-8x7b-32768',
    ]

    payload = json.dumps({
        'model': '',        # será substituído
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user',   'content': user_message},
        ],
        'temperature': 0.75,
        'max_tokens': 900,
    }).encode('utf-8')

    for model in groq_models:
        pl = json.loads(payload)
        pl['model'] = model
        req = urllib.request.Request(
            'https://api.groq.com/openai/v1/chat/completions',
            data=json.dumps(pl).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}',
                'User-Agent': 'curl/7.88.1',
                'Accept': '*/*',
            },
            method='POST'
        )
        try:
            print(f'[Groq] Tentando {model}...')
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                text = data['choices'][0]['message']['content'].strip()
                text = text.replace('*', '')
                print(f'[Groq] Sucesso com {model}.')
                return text
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8')
            print(f'[Groq] Erro HTTP {e.code} em {model}: {body[:200]}')
            if e.code == 429:
                time.sleep(0.5)
                continue  # tenta próximo modelo
        except Exception as ex:
            print(f'[Groq] Erro geral em {model}: {ex}')

    return None  # todos os modelos falharam

# ─── Chamada à API Gemini (backup) ───────────────────────────────
def call_gemini(api_key, user_message, system_prompt):
    gemini_models = [
        'gemini-2.5-flash',
        'gemini-flash-latest',
        'gemini-2.0-flash',
        'gemini-1.5-flash',
    ]

    payload = {
        'contents': [{'parts': [{'text': user_message}]}],
        'systemInstruction': {'parts': [{'text': system_prompt}]},
        'safetySettings': [
            {'category': 'HARM_CATEGORY_HARASSMENT',       'threshold': 'BLOCK_MEDIUM_AND_ABOVE'},
            {'category': 'HARM_CATEGORY_HATE_SPEECH',      'threshold': 'BLOCK_MEDIUM_AND_ABOVE'},
            {'category': 'HARM_CATEGORY_SEXUALLY_EXPLICIT','threshold': 'BLOCK_MEDIUM_AND_ABOVE'},
            {'category': 'HARM_CATEGORY_DANGEROUS_CONTENT','threshold': 'BLOCK_MEDIUM_AND_ABOVE'},
        ]
    }

    for model in gemini_models:
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}'
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        try:
            print(f'[Gemini] Tentando {model}...')
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                text = data['candidates'][0]['content']['parts'][0]['text'].strip()
                text = text.replace('*', '')
                print(f'[Gemini] Sucesso com {model}.')
                return text
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8')
            print(f'[Gemini] Erro HTTP {e.code} em {model}: {body[:200]}')
            if e.code in [429, 503]:
                time.sleep(0.8)
                continue
        except Exception as ex:
            print(f'[Gemini] Erro geral em {model}: {ex}')

    return None

# ─── HTTP Handler ─────────────────────────────────────────────────
class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        if self.path == '/api/counsel':
            self.handle_counsel()
        else:
            self.send_error(404)

    def handle_counsel(self):
        length = int(self.headers.get('Content-Length', 0))
        try:
            body = json.loads(self.rfile.read(length).decode('utf-8'))
            user_msg = body.get('message', '').strip()
        except Exception:
            self.send_response(400); self.end_headers(); return

        if not user_msg:
            self.send_response(400); self.end_headers(); return

        env = load_env()
        groq_key   = env.get('GROQ_API_KEY', os.environ.get('GROQ_API_KEY', ''))
        gemini_key = env.get('GEMINI_API_KEY', os.environ.get('GEMINI_API_KEY', ''))

        system_prompt = (
            "Você é o personagem Jesus, falando diretamente com uma pessoa que busca aconselhamento bíblico. "
            "Responda sempre em português, com profunda compaixão, amor, sabedoria e calma. "
            "Fale diretamente à pessoa em primeira pessoa (usando 'eu', 'meu filho(a)', etc.). "
            "NUNCA use o caractere asterisco (*) em nenhum lugar do texto. Não use markdown. "
            "Não use nenhum símbolo especial de formatação como **negrito** ou _itálico_. "
            "Escreva tudo como texto puro, em parágrafos simples.\n\n"
            "Você DEVE obrigatoriamente citar pelo menos DOIS versículos bíblicos altamente específicos "
            "e assertivos para a situação exata descrita. Evite versículos genéricos. "
            "Analise a aflição e selecione os dois textos mais cirúrgicos e apropriados.\n\n"
            "Estrutura obrigatória em parágrafos separados:\n"
            "Parágrafo 1: Acolhida carinhosa e calma, demonstrando que compreende especificamente a dor relatada.\n"
            "Parágrafo 2: Cite e explique os dois versículos bíblicos específicos, conectando cada um à situação da pessoa.\n"
            "Parágrafo 3: Conselho prático e espiritual de esperança, terminando com uma frase serena de amor e presença."
        )

        # ── Prioridade: Groq (grátis, generoso) → Gemini (backup)
        answer = None

        if groq_key:
            answer = call_groq(groq_key, user_msg, system_prompt)

        if answer is None and gemini_key:
            answer = call_gemini(gemini_key, user_msg, system_prompt)

        if answer is None:
            if not groq_key:
                error_msg = (
                    "GROQ_API_KEY não configurada. "
                    "Crie uma chave gratuita em console.groq.com e adicione ao arquivo .env como: GROQ_API_KEY=sua_chave"
                )
            else:
                error_msg = "Todos os modelos estão indisponíveis no momento. Tente novamente em instantes."

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': error_msg}).encode('utf-8'))
            return

        # ── Gera áudio
        try:
            audio_b64 = tts_to_base64(answer)
        except Exception as e:
            print(f'TTS falhou: {e}')
            audio_b64 = ''

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'counsel': answer, 'audio': audio_b64}).encode('utf-8'))

    def log_message(self, fmt, *args):
        print(f'[HTTP] {self.address_string()} - {fmt % args}')

# ─── Main ─────────────────────────────────────────────────────────
if __name__ == '__main__':
    httpd = HTTPServer(('', PORT), Handler)
    print(f'Servidor rodando em http://localhost:{PORT}')
    print()

    env = load_env()
    groq_key   = env.get('GROQ_API_KEY', '')
    gemini_key = env.get('GEMINI_API_KEY', '')

    if groq_key:
        print('  [OK] GROQ_API_KEY encontrada — usando Groq como modelo principal (grátis)')
    else:
        print('  [AVISO] GROQ_API_KEY NAO encontrada.')
        print('          Adicione ao .env:  GROQ_API_KEY=sua_chave')
        print('          Chave gratuita em: https://console.groq.com')

    if gemini_key:
        print('  [OK] GEMINI_API_KEY encontrada — Gemini disponível como backup')
    print()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\nServidor encerrado.')
        httpd.server_close()
