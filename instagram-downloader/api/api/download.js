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

  // Método 1: snapsave-media-downloader (Scraper do SnapSave.app)
  try {
    console.log("[API] Tentando Método 1 (snapsave-media-downloader)...");
    const { snapsave } = await import("snapsave-media-downloader");
    const response = await snapsave(url);
    console.log("[API] Resposta snapsave:", JSON.stringify(response));

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

  // Método 2: Fallback para @bochilteam/scraper (Instagram Downloader)
  if (!success) {
    try {
      console.log("[API] Tentando Método 2 (@bochilteam/scraper)...");
      const { instagram } = await import("@bochilteam/scraper");
      const bochilRes = await instagram(url);
      console.log("[API] Resposta bochilteam:", JSON.stringify(bochilRes));

      if (bochilRes && bochilRes.length > 0) {
        // Bochilteam retorna array de strings ou objetos
        const bestMedia = bochilRes[0];
        mediaUrl = typeof bestMedia === "string" ? bestMedia : bestMedia.url;
        mediaType = "video"; // Geralmente reels/vídeos
        success = true;
        console.log("[API] Sucesso com @bochilteam/scraper!");
      } else {
        errors.push("Bochilteam: Sem mídia retornada");
      }
    } catch (error) {
      console.error("[API] Erro no @bochilteam/scraper:", error.message);
      errors.push("Bochilteam: " + error.message);
    }
  }

  // Método 3: Fallback para API pública alternativa
  if (!success) {
    try {
      console.log("[API] Tentando Método 3 (API Pública Vyturex)...");
      const fetchResponse = await fetch(`https://api.vyturex.com/instagram?url=${encodeURIComponent(url)}`);
      if (fetchResponse.ok) {
        const data = await fetchResponse.json();
        console.log("[API] Resposta Vyturex:", JSON.stringify(data));
        if (data && data.url) {
          mediaUrl = data.url;
          mediaType = "video";
          success = true;
          console.log("[API] Sucesso com API Vyturex!");
        } else {
          errors.push("Vyturex: Sem URL no JSON");
        }
      } else {
        errors.push(`Vyturex HTTP ${fetchResponse.status}`);
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
    error: "Não foi possível extrair o vídeo. Verifique se o post é público e tente novamente.",
    details: errors
  });
};
