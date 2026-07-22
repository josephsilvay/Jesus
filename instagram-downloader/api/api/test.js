module.exports = async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET");

  const url = req.query.url || "https://www.instagram.com/reel/C3_a7yEMx9Z/";
  let cleanUrl = url.split('?')[0];
  if (!cleanUrl.endsWith('/')) {
    cleanUrl += '/';
  }
  const jsonUrl = `${cleanUrl}?__a=1&__d=dis`;

  try {
    const response = await fetch(jsonUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin'
      }
    });

    const status = response.status;
    const contentType = response.headers.get('content-type') || '';
    
    let bodyText = '';
    try {
      bodyText = await response.text();
    } catch (e) {
      bodyText = 'Error reading body: ' + e.message;
    }

    res.status(200).json({
      jsonUrl,
      status,
      contentType,
      bodySnippet: bodyText.substring(0, 1000),
      isJson: contentType.includes('application/json')
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};
