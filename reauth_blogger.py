#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Reautenticação para o Jornal Metro
Gera token.json e token_finance_elite.json com a conta Google dona do blog.
"""
import os
import json
import sys
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/blogger"]
TARGET_BLOG = "5307582001063172924"

print("=" * 60)
print("🔐 INICIANDO REAUTENTICAÇÃO GOOGLE BLOGGER")
print("   Blog alvo: Jornal Metro (5307582001063172924)")
print("   Conta requerida: joseph.silvay@gmail.com (ou dona do blog)")
print("=" * 60)

if not os.path.exists("client_secret.json"):
    print("❌ client_secret.json não encontrado!")
    sys.exit(1)

flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)

# Executa servidor local na porta 8080 (ou automática)
print("\n👉 Abrindo navegador para autorização...")
creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")

with open("token.json", "w") as f:
    f.write(creds.to_json())
with open("token_finance_elite.json", "w") as f:
    f.write(creds.to_json())

print("✅ Credenciais salvas com sucesso em token.json e token_finance_elite.json!")

service = build("blogger", "v3", credentials=creds)
user = service.users().get(userId="self").execute()
print(f"👤 Usuário conectado: {user.get('displayName')} ({user.get('id')})")

try:
    blog_info = service.blogUserInfos().get(userId="self", blogId=TARGET_BLOG).execute()
    has_admin = blog_info.get("blog_user_info", {}).get("hasAdminAccess", False)
    print(f"📋 Permissão no Jornal Metro ({TARGET_BLOG}): Admin={has_admin}")
    print(f"🌐 Blog: {blog_info.get('blog', {}).get('name')} - {blog_info.get('blog', {}).get('url')}")
except Exception as e:
    print(f"⚠️ Erro ao verificar blogUserInfos: {e}")
