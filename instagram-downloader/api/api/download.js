module.exports = async function handler(req, res) {
  // Configuração manual de CORS (como fail-safe, além do vercel.json)
  res.setHeader("Access-Control-Allow-Credentials", "true");
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET,OPTIONS,PATCH,DELETE,POST,PUT");
  res.setHeader(
    "Access-Control-Allow-Headers",
    "X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version"
  );

  // Responder a requisições OPTIONS (CORS preflight) imediatamente
  if (req.method === "OPTIONS") {
    res.status(200).end();
    return;
  }

  // Obter a URL do Instagram a partir de query params ou body
  let url = req.query.url || (req.body && req.body.url);

  if (!url) {
    return res.status(400).json({
      success: false,
      error: "Por favor, forneça uma URL do Instagram."
    });
  }

  url = url.trim();

  // Validação simples da URL
  if (!url.includes("instagram.com")) {
    return res.status(400).json({
      success: false,
      error: "A URL informada não parece ser um link válido do Instagram."
    });
  }

  console.log(`[API] Processando URL: ${url}`);

  let success = false;
  let mediaUrl = "";
  let mediaType = "video";
  let title = "Instagram Media";
  let errors = [];

  // Método 1: Scraper SaveIG.app (Muito estável, retorna HTML limpo em JSON)
  try {
    console.log("[API] Tentando Método 1 (SaveIG API)...");
    const params = new URLSearchParams();
    params.append('q', url);
    params.append('t', 'media');
    params.append('lang', 'en');

    const saveigResponse = await fetch('https://saveig.app/api/ajaxSearch', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: params.toString()
    });

    if (saveigResponse.ok) {
      const data = await saveigResponse.json();
      if (data && data.status === 'ok' && data.data) {
        const html = data.data;
        
        // Extrair o link direto do vídeo/imagem do HTML usando Regex
        // Os links do CDN da Meta Geralmente contêm "fbcdn.net" ou "instagram.com" e estão no atributo href
        const hrefRegex = /href="([^"]+)"/g;
        let match;
        const links = [];
        
        while ((match = hrefRegex.exec(html)) !== null) {
          let link = match[1].replace(/&amp;/g, '&');
          // Evitar links de redirecionamento ou vazios
          if (link.includes("fbcdn.net") || link.includes("instagram.com") || link.includes("download")) {
            links.push(link);
          }
        }

        if (links.length > 0) {
          mediaUrl = links[0];
          // Detectar se é imagem
          if (html.includes("download-image") || mediaUrl.includes(".jpg") || mediaUrl.includes(".png") || mediaUrl.includes(".webp")) {
            mediaType = "image";
          } else {
            mediaType = "video";
          }
          success = true;
          console.log("[API] Sucesso com SaveIG API!");
        } else {
          errors.push("SaveIG: Nenhum link de download válido encontrado no HTML.");
        }
      } else {
        errors.push("SaveIG: Resposta com status inválido.");
      }
    } else {
      errors.push(`SaveIG: HTTP ${saveigResponse.status}`);
    }
  } catch (error) {
    console.error("[API] Erro na SaveIG API:", error.message);
    errors.push("SaveIG: " + error.message);
  }

  // Método 2: snapsave-media-downloader (Fallback)
  if (!success) {
    try {
      console.log("[API] Tentando Método 2 (snapsave-media-downloader)...");
      const { snapsave } = await import("snapsave-media-downloader");
      const response = await snapsave(url);

      if (response && response.success && response.data && response.data.media && response.data.media.length > 0) {
        const bestMedia = response.data.media[0];
        mediaUrl = bestMedia.url;
        mediaType = bestMedia.type || "video";
        title = response.data.description || "Instagram Media";
        success = true;
        console.log("[API] Sucesso com snapsave-media-downloader!");
      } else {
        errors.push("SnapSave: " + ((response && response.message) || "Sem mídia retornada"));
      }
    } catch (error) {
      console.error("[API] Erro no snapsave-media-downloader:", error.message);
      errors.push("SnapSave: " + error.message);
    }
  }

  // Método 3: API pública alternativa (Vyturex)
  if (!success) {
    try {
      console.log("[API] Tentando Método 3 (API Pública Vyturex)...");
      const vyturexResponse = await fetch(`https://api.vyturex.com/instagram?url=${encodeURIComponent(url)}`);
      if (vyturexResponse.ok) {
        const data = await vyturexResponse.json();
        if (data && data.url) {
          mediaUrl = data.url;
          mediaType = "video";
          success = true;
          console.log("[API] Sucesso com API Vyturex!");
        } else {
          errors.push("Vyturex: Sem URL no JSON");
        }
      } else {
        errors.push(`Vyturex: HTTP ${vyturexResponse.status}`);
      }
    } catch (error) {
      console.error("[API] Erro na API Vyturex:", error.message);
      errors.push("Vyturex: " + error.message);
    }
  }

  // Retornar resultado se algum método funcionou
  if (success && mediaUrl) {
    return res.status(200).json({
      success: true,
      type: mediaType,
      url: mediaUrl,
      title: title
    });
  }

  // Falha total de todos os métodos
  console.error("[API] Todos os métodos falharam:", errors);
  return res.status(422).json({
    success: false,
    error: "Não foi possível extrair o vídeo. Verifique se o post é de uma conta pública e tente novamente.",
    details: errors
  });
};
