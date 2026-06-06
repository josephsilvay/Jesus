"""Helper com retry automático para chamadas à API do Gemini (erro 429)."""
import time
import requests

def call_gemini_with_retry(url, payload, max_retries=4, wait_seconds=60):
    """Chama a API do Gemini com retry automático em caso de 429."""
    headers = {"Content-Type": "application/json"}
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            if response.status_code == 429:
                wait = wait_seconds * attempt  # espera progressiva: 60s, 120s, 180s...
                print(f"  [Gemini] 429 Too Many Requests. Aguardando {wait}s antes de tentar novamente (tentativa {attempt}/{max_retries})...")
                time.sleep(wait)
                continue
            response.raise_for_status()
            data = response.json()
            text = (data.get('candidates', [{}])[0]
                       .get('content', {})
                       .get('parts', [{}])[0]
                       .get('text', ''))
            if text:
                return text
            print(f"  [Gemini] Resposta vazia na tentativa {attempt}. Tentando novamente...")
            time.sleep(30)
        except requests.exceptions.HTTPError as e:
            if attempt == max_retries:
                raise
            print(f"  [Gemini] Erro HTTP {e}. Tentativa {attempt}/{max_retries}. Aguardando 60s...")
            time.sleep(60)
        except Exception as e:
            if attempt == max_retries:
                raise
            print(f"  [Gemini] Erro inesperado: {e}. Tentativa {attempt}/{max_retries}...")
            time.sleep(30)
    raise Exception("Gemini falhou após todas as tentativas.")
