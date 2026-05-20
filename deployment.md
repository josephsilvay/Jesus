# Guia de Publicação / Implantação (Deployment Guide)

Este documento descreve como publicar e hospedar o aplicativo **Aconselhamento Celestial** na nuvem de forma gratuita ou de baixo custo.

---

## Opção 1: Render.com (Recomendado — Gratuito e Rápido)

O **Render** é uma plataforma PaaS (Platform as a Service) excelente para hospedar aplicações Python.

### Passo a Passo:
1. **Crie um Repositório Git**:
   * Inicialize um repositório Git local e envie para o GitHub/GitLab:
     ```bash
     git init
     git add .
     git commit -m "Initial commit"
     ```
2. **Crie uma Conta no Render**:
   * Acesse [dashboard.render.com](https://dashboard.render.com) e crie sua conta (pode conectar com o GitHub).
3. **Crie um Novo "Web Service"**:
   * Clique em **New** > **Web Service**.
   * Conecte o repositório do GitHub que você acabou de criar.
4. **Configure os Detalhes do Web Service**:
   * **Language**: `Python`
   * **Build Command**: `pip install -r requirements.txt`
   * **Start Command**: `python server.py`
5. **Adicione as Variáveis de Ambiente**:
   * Vá em **Environment** e adicione:
     * `GROQ_API_KEY`: A sua chave da Groq.
     * `GEMINI_API_KEY`: A sua chave do Gemini (backup).
6. **Deploy**:
   * O Render compilará os pacotes e inicializará o servidor. Ele fornecerá uma URL pública gratuita (ex: `seu-app.onrender.com`).

---

## Opção 2: Servidor VPS (DigitalOcean, AWS, Google Cloud, Linode)

Se você tem ou deseja alugar um servidor virtual (VPS), pode rodar o serviço facilmente.

### Passo a Passo:
1. **Prepare o Servidor**:
   * Instale o Python 3 e o pip (no Ubuntu):
     ```bash
     sudo apt update
     sudo apt install python3 python3-pip python3-venv -y
     ```
2. **Clone seu Código e crie o arquivo `.env`**:
   * Configure o arquivo `.env` no servidor com as chaves API necessárias.
3. **Crie o Ambiente Virtual e Instale Dependências**:
   * Rode os comandos:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     pip install -r requirements.txt
     ```
4. **Gerencie o Processo do Servidor**:
   * Para rodar em segundo plano e garantir que o processo não feche ao desconectar:
     ```bash
     nohup python3 -u server.py > server.log 2>&1 &
     ```
   * **Como parar o servidor**:
     * Procure o processo: `ps aux | grep server.py`
     * Encerre o processo: `kill <PID>`
5. **Configurar Nginx (Opcional - Recomendado para HTTPS)**:
   * Recomenda-se usar o **Nginx** como Proxy Reverso encaminhando a porta `80/443` para a porta `8000` do app Python.

---

## Opção 3: PythonAnywhere

O **PythonAnywhere** é especializado em hospedagem Python simples.
1. Crie uma conta gratuita em [pythonanywhere.com](https://www.pythonanywhere.com).
2. Faça o upload dos arquivos ou clone o repositório via Bash no painel.
3. Crie um ambiente virtual e instale `requirements.txt`.
4. Configure um Web App apontando para o seu script.
