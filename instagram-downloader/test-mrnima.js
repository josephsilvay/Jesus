const { instagramDownload } = require('./api/node_modules/@mrnima/instagram-downloader');

const url = 'https://www.instagram.com/reel/C3_a7yEMx9Z/';

console.log("Iniciando teste com @mrnima/instagram-downloader...");
instagramDownload(url)
  .then(res => {
    console.log("SUCESSO:", JSON.stringify(res, null, 2));
  })
  .catch(err => {
    console.error("ERRO:", err);
  });
