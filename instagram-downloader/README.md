# Guia de Instalação: Downloader de Reels do Instagram

Este projeto é composto por dois elementos principais:
1. **Frontend**: Um tema XML totalmente customizado para o **Blogger** (design responsivo, moderno, escuro e com otimização de SEO e AdSense).
2. **Backend**: Uma API Serverless Node.js pronta para implantação rápida na **Vercel** (gratuita) que realiza a extração do vídeo a partir da URL do Instagram.

---

## 🚀 Passo 1: Publicar a API na Vercel (Gratuito)

A API backend é necessária para consultar o Instagram e extrair os links diretos do arquivo MP4.

1. **Criar uma conta na Vercel:**
   - Acesse [vercel.com](https://vercel.com) e crie uma conta gratuita (você pode fazer login usando seu e-mail ou conta do GitHub).

2. **Fazer o deploy da pasta `/api`:**
   - **Método CLI (Mais Rápido):**
     1. Abra o terminal na pasta `instagram-downloader/api` no seu computador.
     2. Instale o Vercel CLI (se não tiver instalado): `npm install -g vercel`.
     3. Execute o comando `vercel` e siga as instruções na tela para fazer login e iniciar o deploy.
     4. Ao finalizar o deploy de desenvolvimento, execute `vercel --prod` para gerar o link final de produção.
   - **Método GitHub (Mais Recomendado para atualizações automáticas):**
     1. Crie um repositório privado no seu GitHub (ex: `instagram-downloader-api`).
     2. Envie os arquivos contidos dentro da pasta `instagram-downloader/api/` para esse repositório.
     3. Acesse o painel da Vercel, clique em **Add New -> Project** e selecione o repositório que você acabou de criar.
     4. Clique em **Deploy**.
   
3. **Guardar o link da API:**
   - Ao concluir, a Vercel gerará um domínio gratuito para a sua API, como por exemplo: `https://instagram-downloader-api.vercel.app`. Guarde esta URL!

---

## 🌐 Passo 2: Configurar o Subdomínio no Blogger

Você usará um subdomínio (ex: `baixar-reels.jornalmetro.com.br`) apontado diretamente para a hospedagem gratuita do Blogger.

1. **Criar um novo Blog:**
   - Acesse [blogger.com](https://www.blogger.com) com sua conta Google.
   - Crie um novo blog com qualquer título (ex: *InstaBaixar*) e escolha um endereço temporário `.blogspot.com`.

2. **Apontar seu subdomínio no seu Gerenciador de DNS (Cloudflare, GoDaddy, Hostgator, etc.):**
   - Vá nas configurações de DNS do seu domínio `jornalmetro.com.br`.
   - Adicione um novo registro do tipo **CNAME**:
     - **Nome/Host:** `baixar-reels` (ou a palavra-chave desejada, ex: `baixarvideoinstagram`)
     - **Destino/Target:** `ghs.google.com`
     - **TTL:** Automático ou 3600.
     - *(Se estiver usando a Cloudflare, marque a nuvem como "Apenas DNS / DNS Only" provisoriamente para validação).*

3. **Configurar o Domínio Personalizado no Blogger:**
   - No painel do Blogger, vá em **Configurações (Settings) -> Publicação (Publishing) -> Domínio personalizado**.
   - Digite o subdomínio completo, incluindo a palavra-chave, por exemplo: `baixar-reels.jornalmetro.com.br` e salve.
   - *Nota: O Blogger pode pedir para criar um segundo registro CNAME de segurança no seu DNS para provar que você é dono do domínio. Se pedir, adicione o registro CNAME apontado no seu painel DNS e aguarde alguns minutos para salvar novamente.*
   - Ative a opção **Redirecionar domínio** e garanta que a opção **Disponibilidade de HTTPS** esteja marcada como **Sim**.

---

## 🎨 Passo 3: Instalar o Tema Personalizado no Blogger

1. **Dica Rápida:** Em vez de editar a URL da API manualmente, você pode rodar no terminal:
   ```bash
   node set-api-url.js <SUA_URL_DA_VERCEL>
   ```
   Isso atualizará o arquivo `blogger-theme.xml` automaticamente!

2. Abra o arquivo [blogger-theme.xml](blogger-theme.xml) localizado nesta pasta em um editor de texto de sua preferência (Notepad, VS Code, etc.) e copie todo o conteúdo (Ctrl+A, Ctrl+C).
2. Acesse o painel do Blogger, clique na seção **Tema (Theme)** no menu lateral.
3. Clique no botão de seta para baixo ao lado do botão laranja "Personalizar" (Customize) e escolha **Editar HTML (Edit HTML)**.
4. Delete todo o código XML existente no editor do Blogger.
5. Cole o código XML completo que você copiou (Ctrl+V).
6. **⚠️ ANTES DE SALVAR, faça as seguintes alterações nas configurações de JavaScript (Role até a linha ~880 do código ou pesquise por `const CONFIG = {`):**

```javascript
    const CONFIG = {
      // 1. Substitua pela URL da sua API gerada no Passo 1 na Vercel:
      apiUrl: 'https://instagram-downloader-api.vercel.app', 
      
      // 2. Configure seus dados do Google AdSense para ativar a monetização:
      adsense: {
        publisherId: 'ca-pub-XXXXXXXXXXXXXXX', // Cole seu ID de editor AdSense (ex: ca-pub-123456789)
        slots: {
          top: 'XXXXXXXXXX',     // ID do bloco de anúncio Superior
          result: 'XXXXXXXXXX',  // ID do bloco de anúncio de Resultado (Dentro do downloader)
          middle: 'XXXXXXXXXX',  // ID do bloco de anúncio Central
          sidebar: 'XXXXXXXXXX', // ID do bloco de anúncio Lateral (Exibido nas páginas de artigos)
          bottom: 'XXXXXXXXXX'   // ID do bloco de anúncio do Rodapé
        }
      }
    };
```

7. Substitua as strings `XXXXXXXXXX` e `ca-pub-XXXXXXXXXXXXXXX` pelos dados reais obtidos na sua conta do Google AdSense.
   - *Nota: Enquanto você mantiver o ID padrão `ca-pub-XXXXXXXXXXXXXXX`, o site exibirá placeholders visuais elegantes demarcando os locais onde os anúncios serão mostrados, ajudando você a visualizar o layout.*
8. Clique no ícone de disquete no canto superior direito para **Salvar**.

---

## ✍️ Passo 4: Otimização de SEO (Publicando Artigos)

Para que o site consiga visitantes orgânicos do Google, é essencial criar postagens úteis.

1. No painel do Blogger, clique em **Postagens (Posts) -> Nova postagem**.
2. Crie artigos explicativos com tópicos focados na palavra-chave. Exemplos de títulos:
   - *Como baixar Reels do Instagram no celular Android e iPhone de graça*
   - *Melhores formas de salvar vídeos do Instagram em HD em 2026*
3. O tema está programado para esconder a ferramenta de download principal na página de artigos, exibindo em vez disso um layout de leitura limpo com uma barra lateral contendo um **Mini-downloader**. Isso estimula a conversão e mantém o usuário engajado no site!

---

## 🛠️ Manutenção e Troubleshooting

- **CORS Error:** Se ao clicar em download a ferramenta exibir erro de conexão, verifique se a URL da sua API em `CONFIG.apiUrl` está correta e se possui o prefixo `https://` sem barra `/` no final.
- **O download abre o vídeo no navegador em vez de baixar direto:** Devido às restrições de segurança do navegador em links diretos do CDN do Facebook/Instagram (`*.fbcdn.net`), o navegador às vezes reproduz o vídeo na tela. O site já possui um aviso instruindo o usuário a clicar nos 3 pontinhos do player de vídeo e selecionar **"Fazer o download"** (ou clicar com o botão direito e "Salvar link como").
- **Vídeos Privados:** O downloader suporta apenas links públicos do Instagram. Mídias de perfis privados não são acessíveis pela API devido a restrições de autenticação.
