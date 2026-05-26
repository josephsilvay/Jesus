<?php
/**
 * Robô Autônomo do Blogger - f5ul.com
 * Pode ser rodado no Hostinger via Cron Job 24/7.
 */

// Tenta carregar do .env se existir
if (file_exists('.env')) {
    $lines = file('.env', FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    foreach ($lines as $line) {
        if (strpos(trim($line), '#') === 0) continue;
        if (strpos($line, '=') !== false) {
            list($name, $value) = explode('=', $line, 2);
            $_ENV[trim($name)] = trim($value);
            putenv(trim($name) . '=' . trim($value));
        }
    }
}

// ==========================================
// CONFIGURAÇÕES
// ==========================================
define('CLIENT_ID', getenv('BLOGGER_CLIENT_ID'));
define('CLIENT_SECRET', getenv('BLOGGER_CLIENT_SECRET'));
define('REFRESH_TOKEN', getenv('BLOGGER_REFRESH_TOKEN'));
define('BLOG_ID', getenv('BLOGGER_BLOG_ID') ?: '5307582001063172924'); // f5ul.com

define('GEMINI_API_KEY', getenv('GEMINI_API_KEY'));
define('PEXELS_API_KEY', getenv('PEXELS_API_KEY'));

// ==========================================
// FUNÇÕES CEREBRAIS
// ==========================================

function get_blogger_token() {
    $url = 'https://oauth2.googleapis.com/token';
    $data = [
        'client_id' => CLIENT_ID,
        'client_secret' => CLIENT_SECRET,
        'refresh_token' => REFRESH_TOKEN,
        'grant_type' => 'refresh_token'
    ];

    $options = [
        'http' => [
            'header'  => "Content-type: application/x-www-form-urlencoded\r\n",
            'method'  => 'POST',
            'content' => http_build_query($data)
        ]
    ];
    $context  = stream_context_create($options);
    $result = file_get_contents($url, false, $context);
    if ($result === FALSE) die("Erro ao renovar token OAuth do Blogger.");

    $response = json_decode($result, true);
    return $response['access_token'];
}

function get_trending_news() {
    echo "[1] Buscando Trending Topics no Google Trends Brasil...\n";
    $url = "https://trends.google.com/trending/rss?geo=BR";
    
    $options = [
        'http' => [
            'header' => "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36\r\n"
        ]
    ];
    $context = stream_context_create($options);
    $xmlString = @file_get_contents($url, false, $context);
    
    $isTrends = true;
    if(!$xmlString) {
        echo "  ⚠️ Falha ao ler o Google Trends. Usando Google News como fallback...\n";
        $url = "https://news.google.com/rss?hl=pt-BR&gl=BR&ceid=BR:pt-419";
        $xmlString = file_get_contents($url, false, $context);
        $isTrends = false;
    }
    
    if(!$xmlString) die("Erro ao ler feed de notícias.");
    
    $xml = simplexml_load_string($xmlString);
    if(!$xml) die("Erro ao parsear XML.");
    
    $items = [];
    $count = 0;
    
    foreach($xml->channel->item as $itm) {
        if ($isTrends) {
            $ns = $itm->children('ht', true);
            $news_item = $ns->news_item[0] ?? null;
            $news_title = $news_item ? (string)$news_item->news_item_title : '';
            $news_url = $news_item ? (string)$news_item->news_item_url : '';
            $news_source = $news_item ? (string)$news_item->news_item_source : '';
            $approx_traffic = (string)$ns->approx_traffic;
            
            $items[] = [
                'title' => (string)$itm->title,
                'summary' => "Termo de busca em alta no Google Trends Brasil com volume de {$approx_traffic} pesquisas. Notícia de referência: \"{$news_title}\" publicada por {$news_source}.",
                'news_url' => $news_url
            ];
        } else {
            $items[] = [
                'title' => (string)$itm->title,
                'summary' => strip_tags((string)$itm->description),
                'news_url' => ''
            ];
        }
        if(++$count >= 15) break;
    }
    
    if (empty($items)) die("Nenhum item encontrado no feed.");
    
    $randomIndex = array_rand($items);
    $selected = $items[$randomIndex];
    echo "  -> Tópico Sorteado: " . $selected['title'] . "\n";
    return $selected;
}

function call_gemini($topic, $context, $news_url = '') {
    echo "[2] Gerando artigo otimizado (alto CTR) via Gemini sobre '{$topic}'...\n";
    $url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key=" . GEMINI_API_KEY;

    $link_inst = $news_url 
        ? "Use EXATAMENTE a URL '{$news_url}' no atributo href do link para referenciar a fonte oficial da notícia." 
        : "Use um link para um site de autoridade e credibilidade (como gov.br, G1 ou similar).";

    $prompt = "INSTRUÇÃO CRÍTICA: Você é um jornalista digital sênior, especialista em SEO e redação de alto engajamento (estilo R7, G1 e BuzzFeed). " .
        "Produza uma matéria jornalística completa de altíssimo impacto e potencial de cliques (alto CTR) sobre o assunto em alta do Google Trends: '{$topic}'.\n" .
        "Contexto do assunto: {$context}\n\n" .
        "ESTRATÉGIAS DE CLIQUE E SEO (POTENCIAL DE CLIQUES):\n" .
        "- TÍTULO IRRESISTÍVEL: Escreva um título extremamente atraente, com gatilhos de curiosidade, impacto emocional ou revelação (ex: 'O verdadeiro motivo por trás de...', 'Entenda a polêmica...', ou revelações importantes). Evite caixa alta completa ou termos sensacionalistas vazios como 'CHOQUE'. Deve ser jornalístico, porém impossível de não clicar.\n" .
        "- PALAVRA-CHAVE EM DESTAQUE: A palavra-chave/assunto exato '{$topic}' deve aparecer de forma natural no título e no primeiro parágrafo do texto.\n" .
        "- HOOK INICIAL: Comece a notícia com uma frase de impacto direto que prenda o leitor nos primeiros 3 segundos.\n" .
        "- E-E-A-T E FONTES: Insira EXATAMENTE 1 hiperlink externo no corpo do texto (na primeira metade da notícia) apontando para a notícia de referência oficial. {$link_inst} Exemplo de formato: <a href='...' target='_blank'>veja os detalhes na cobertura original</a>.\n" .
        "- LINKS INTERNOS: Insira estrategicamente no meio do texto 1 ou 2 links internos cruzados. Como o blog é f5ul.com, crie âncoras temáticas apontando para a busca do blog no formato: <a href='https://www.f5ul.com/search?q=" . urlencode($topic) . "'>leia mais sobre {$topic}</a>.\n" .
        "- LEITURA DINÂMICA: Use parágrafos curtos, frases diretas, listas de itens, <h2>, <h3> para escaneabilidade rápida.\n" .
        "- SEM CLICHÊS DE IA: Banido o uso de termos genéricos como 'em resumo', 'por fim', 'é importante notar', 'no cenário atual'. Use transições humanas e jornalísticas.\n" .
        "- PERGUNTAS FREQUENTES (FAQ): Ao final da matéria, inclua uma seção com <h2>Perguntas Frequentes</h2> e de 3 a 5 perguntas objetivas com tags <h3> e respostas curtas com <p>, refletindo o que os usuários pesquisariam no Google sobre o tema.\n\n" .
        "Retorne EXCLUSIVAMENTE o formato estrito exigido abaixo.\n\n" .
        "[TITULO]\n(Escreva o título chamativo com no máximo 70 caracteres)\n\n" .
        "[RESUMO]\n(Uma frase de 140 a 160 caracteres que resuma a matéria de forma atraente para aparecer no Google. Sem aspas.)\n\n" .
        "[KEYWORD_IMAGEM]\n(palavra única em inglês para buscar uma foto ilustrativa de alta qualidade no Pexels)\n\n" .
        "[LABELS]\n(Até 3 categorias ou temas separados por vírgula. Ex: Entretenimento, Brasil, Esportes)\n\n" .
        "[CONTEUDO]\n<p>Aqui entra o texto HTML com corpo da noticia</p>";

    $payload = json_encode(["contents" => [["parts" => [["text" => $prompt]]]]]);

    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $payload);
    $result = curl_exec($ch);
    $status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if ($status != 200) die("Erro 200 do Gemini: $result");

    $json = json_decode($result, true);
    return $json['candidates'][0]['content']['parts'][0]['text'] ?? "";
}

function parse_article($text) {
    preg_match('/\[TITULO\]\s*(.*?)\s*\[RESUMO\]/is', $text, $t_match);
    preg_match('/\[RESUMO\]\s*(.*?)\s*\[KEYWORD_IMAGEM\]/is', $text, $r_match);
    preg_match('/\[KEYWORD_IMAGEM\]\s*(.*?)\s*\[LABELS\]/is', $text, $k_match);
    preg_match('/\[LABELS\]\s*(.*?)\s*\[CONTEUDO\]/is', $text, $l_match);
    preg_match('/\[CONTEUDO\]\s*(.*)/is', $text, $c_match);

    return [
        'title' => trim($t_match[1] ?? 'Notícia Urgente'),
        'resumo' => trim($r_match[1] ?? ''),
        'keyword' => trim(explode(',', $k_match[1] ?? 'news')[0]),
        'labels' => array_map('trim', explode(',', $l_match[1] ?? 'Notícias')),
        'content' => trim($c_match[1] ?? '<p>Falha ao formatar conteúdo.</p>')
    ];
}

function get_pexels_image($keyword) {
    echo "[3] Buscando capa no Pexels para '{$keyword}'...\n";
    $url = "https://api.pexels.com/v1/search?query=" . urlencode($keyword) . "&per_page=1&orientation=landscape";
    
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, ["Authorization: " . PEXELS_API_KEY]);
    $result = curl_exec($ch);
    curl_close($ch);

    $data = json_decode($result, true);
    if (!empty($data['photos'][0]['src']['original'])) {
        $img = $data['photos'][0]['src']['original'] . "?auto=compress&cs=tinysrgb&w=1200";
        $alt = htmlspecialchars($data['photos'][0]['alt'] ?? $keyword);
        return "<div class='separator' style='clear: both; text-align: center;'><img alt='{$alt}' border='0' data-original-height='800' data-original-width='1200' loading='lazy' decoding='async' src='{$img}' style='border-radius: 8px; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 100%; max-width: 1200px;'/></div>";
    }
    return "";
}

function publish_to_blogger($access_token, $article) {
    echo "[4] Publicando no f5ul.com...\n";
    $url = "https://www.googleapis.com/blogger/v3/blogs/" . BLOG_ID . "/posts/";
    
    $payload = json_encode([
        "title" => $article['title'],
        "content" => $article['final_html'],
        "labels" => $article['labels']
    ]);

    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        "Authorization: Bearer {$access_token}",
        "Content-Type: application/json"
    ]);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $payload);
    $result = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    if ($http_code == 200 || $http_code == 201) {
        $data = json_decode($result, true);
        echo "=== SUCESSO! LINK: " . $data['url'] . " ===\n";
    } else {
        echo "Erro ao postar: $result\n";
    }
}

// Fluxo principal
echo "[1] Script Iniciado.\n";
$token = get_blogger_token();

$topic_data = get_trending_news();
$raw_text = call_gemini($topic_data['title'], $topic_data['summary'], $topic_data['news_url']);
$article = parse_article($raw_text);

$image_tag = get_pexels_image($article['keyword']);
$article['final_html'] = $image_tag . $article['content'];

publish_to_blogger($token, $article);
echo "Finalizado.\n";
