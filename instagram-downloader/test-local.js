const handler = require('./api/api/download.js');

// Mock request and response objects
const req = {
  method: 'GET',
  query: {
    // Test public Instagram post/reel URL
    url: 'https://www.instagram.com/p/DF21Rk8M5z_/'
  }
};

const res = {
  statusCode: 200,
  headers: {},
  setHeader: function(key, val) {
    this.headers[key] = val;
  },
  status: function(code) {
    this.statusCode = code;
    return this;
  },
  json: function(data) {
    console.log("RESPONSE STATUS:", this.statusCode);
    console.log("RESPONSE JSON:", JSON.stringify(data, null, 2));
  },
  end: function() {
    console.log("RESPONSE ENDED");
  }
};

console.log("Iniciando verificação local da API...");
handler(req, res).catch(err => {
  console.error("Erro na execução do handler:", err);
});
