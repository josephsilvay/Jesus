import requests

def gerar_token_definitivo():
    print("=" * 60)
    print(" GERADOR DE TOKEN PERMANENTE DO FACEBOOK ".center(60, "="))
    print("=" * 60)
    print("\nPara isso funcionar, você precisa do seu APP_ID, APP_SECRET, o ID da Página")
    print("e de um Short-Lived User Token recém-gerado no Graph API Explorer.")
    
    app_id = input("\n[1] Digite o seu APP_ID: ").strip()
    app_secret = input("[2] Digite o seu APP_SECRET: ").strip()
    page_id = input("[3] Digite o ID da sua Página (Page ID): ").strip()
    short_user_token = input("[4] Cole o Short-Lived User Token (o que você gera no Graph API Explorer): ").strip()
    
    if not all([app_id, app_secret, page_id, short_user_token]):
        print("❌ Todos os campos são obrigatórios. Saindo.")
        return

    print("\n🔄 [PASSO 1] Convertendo Short-Lived User Token para Long-Lived User Token (Válido por 60 dias)...")
    url_ll_user = "https://graph.facebook.com/v19.0/oauth/access_token"
    params_ll_user = {
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": short_user_token
    }
    
    try:
        r1 = requests.get(url_ll_user, params=params_ll_user)
        r1.raise_for_status()
        long_user_token = r1.json().get("access_token")
        print("✅ Long-Lived User Token gerado com sucesso!")
    except Exception as e:
        print(f"❌ Erro no Passo 1: {e}")
        if hasattr(e, 'response') and e.response:
            print(e.response.text)
        return

    print("🔄 [PASSO 2] Convertendo Long-Lived User Token em um Permanent Page Access Token (Nunca expira)...")
    url_page = f"https://graph.facebook.com/v19.0/{page_id}"
    params_page = {
        "fields": "access_token",
        "access_token": long_user_token
    }
    
    try:
        r2 = requests.get(url_page, params=params_page)
        r2.raise_for_status()
        page_token = r2.json().get("access_token")
        
        print("\n" + "=" * 60)
        print(" 🎉 SUCESSO! SEU TOKEN PERMANENTE FOI GERADO 🎉")
        print("=" * 60)
        print("\nEste token nunca irá expirar. Copie o texto exato abaixo e adicione")
        print("no GitHub Secrets como um novo secret chamado FB_PAGE_TOKEN:")
        print("\n" + page_token)
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"❌ Erro no Passo 2: {e}")
        if hasattr(e, 'response') and e.response:
            print(e.response.text)

if __name__ == "__main__":
    gerar_token_definitivo()
