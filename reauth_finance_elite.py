#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Reautenticação — Finance Elite Bot
============================================
Execute este script UMA VEZ para gerar o token.json
com a conta Google dona do blog 5307582001063172924.

Uso: python reauth_finance_elite.py
"""

import os, json, sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES       = ["https://www.googleapis.com/auth/blogger"]
TARGET_BLOG  = "5307582001063172924"
TOKEN_FILE   = "token_finance_elite.json"   # arquivo separado, não sobrescreve o atual
SECRET_FILE  = "client_secret.json"

print("=" * 60)
print("🔐 REAUTENTICAÇÃO — Finance Elite Bot")
print(f"   Blog alvo: {TARGET_BLOG}")
print("=" * 60)
print()
print("⚠️  IMPORTANTE: Quando o navegador abrir, faça login com a")
print("   conta Google que é DONA do blog:")
print("   https://www.blogger.com/blog/posts/5307582001063172924")
print()
input("   Pressione ENTER para abrir o navegador...")

if not os.path.exists(SECRET_FILE):
    print(f"\n❌ Arquivo {SECRET_FILE} não encontrado!")
    print("   Baixe-o do Google Cloud Console > Credenciais > OAuth 2.0")
    sys.exit(1)

flow  = InstalledAppFlow.from_client_secrets_file(SECRET_FILE, SCOPES)
creds = flow.run_local_server(port=0)

# Salva token temporário para verificar
with open(TOKEN_FILE, "w") as f:
    f.write(creds.to_json())
print(f"\n✅ Autenticação concluída! Token salvo em: {TOKEN_FILE}")

# Verifica se o blog-alvo está acessível
print("\n🔍 Verificando acesso ao blog-alvo...")
service  = build("blogger", "v3", credentials=creds)
response = service.blogs().listByUser(userId="self").execute()
blogs    = response.get("items", [])

print("\n📋 Blogs acessíveis com esta conta:")
found = False
for b in blogs:
    mark = "  ← ✅ BLOG CORRETO!" if b["id"] == TARGET_BLOG else ""
    print(f"   • {b['name']} | ID: {b['id']} | {b['url']}{mark}")
    if b["id"] == TARGET_BLOG:
        found = True

print()
if found:
    # Substitui o token principal
    import shutil
    shutil.copy(TOKEN_FILE, "token.json")
    os.remove(TOKEN_FILE)
    print("🎉 SUCESSO! token.json atualizado com as permissões corretas.")
    print("   Agora execute: python finance_elite_bot.py")
    print()
    print("   Para o GitHub Actions, atualize o secret TOKEN_JSON com")
    print(f"   o conteúdo do arquivo token.json gerado.")
else:
    print(f"❌ O blog {TARGET_BLOG} não está acessível com esta conta.")
    print("   Certifique-se de fazer login com a conta correta.")
    print(f"   O arquivo {TOKEN_FILE} foi salvo para inspeção.")
    sys.exit(1)
