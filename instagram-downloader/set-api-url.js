const fs = require('fs');
const path = require('path');

const url = process.argv[2];
if (!url) {
  console.error("Erro: Por favor, forneça a URL da API Vercel como argumento.");
  console.log("Exemplo: node set-api-url.js https://instagram-downloader-api.vercel.app");
  process.exit(1);
}

const themePath = path.join(__dirname, 'blogger-theme.xml');
if (!fs.existsSync(themePath)) {
  console.error("Erro: blogger-theme.xml não encontrado no diretório atual.");
  process.exit(1);
}

try {
  let xml = fs.readFileSync(themePath, 'utf8');
  // Substituir a linha apiUrl
  const regex = /apiUrl:\s*['"][^'"]*['"]/;
  if (!regex.test(xml)) {
    console.error("Erro: Não foi possível encontrar a linha CONFIG.apiUrl no XML.");
    process.exit(1);
  }
  xml = xml.replace(regex, `apiUrl: '${url.trim().replace(/\/$/, "")}'`);
  fs.writeFileSync(themePath, xml, 'utf8');
  console.log(`Sucesso! O arquivo blogger-theme.xml foi atualizado com a API URL: ${url}`);
} catch (err) {
  console.error("Erro ao atualizar o arquivo:", err);
}
