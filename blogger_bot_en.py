import os
import random
import feedparser
import urllib.parse
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv
from gemini_retry import call_gemini_with_retry
import requests

load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
PEXELS_API_KEY = os.getenv('PEXELS_API_KEY')

BLOG_ID = '9219139459874116229'   # grandmastips2026.blogspot.com
BLOG_DOMAIN = 'grandmastips2026.blogspot.com'
SCOPES = ['https://www.googleapis.com/auth/blogger']

# English-speaking countries for Google Trends rotation
TRENDING_COUNTRIES = ['US', 'GB', 'CA', 'AU', 'IE']
COUNTRY_NAMES = {
    'US': 'United States', 'GB': 'United Kingdom',
    'CA': 'Canada', 'AU': 'Australia', 'IE': 'Ireland'
}

# High-engagement home tips topics as fallback
TIPS_FALLBACK = [
    "how to clean grout without scrubbing",
    "natural remedies for a cold and flu",
    "how to remove stains from white clothes",
    "plants that repel mosquitoes naturally",
    "baking soda cleaning hacks grandma swore by",
    "how to make a powerful all-purpose cleaner at home",
    "natural remedies for headaches without medication",
    "how to keep food fresh longer in the fridge",
    "vinegar cleaning hacks that actually work",
    "how to get rid of ants naturally at home",
    "DIY fabric softener with ingredients from your pantry",
    "home remedies for better sleep without pills",
    "how to remove bad smells from the house naturally",
    "easy ways to unclog a drain without chemicals",
    "how to clean the oven without harsh chemicals",
    "surprising uses of lemon around the house",
    "how to save money on groceries every week",
    "natural remedies for joint pain and arthritis",
    "how to remove mold from bathroom walls naturally",
    "grandma's secret recipes for household cleaning",
]

def get_blogger_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('blogger', 'v3', credentials=creds)

def _en_topic_is_relevant(title: str) -> bool:
    """Returns True only if the trending topic is genuinely about home/health/cooking."""
    t = title.lower()

    positive_kw = [
        'clean', 'cleaning', 'home', 'house', 'kitchen', 'remedy', 'remedies',
        'health', 'recipe', 'recipes', 'plant', 'natural', 'saving', 'savings',
        'tip', 'tips', 'garden', 'gardening', 'laundry', 'stain', 'stains',
        'hack', 'hacks', 'diy', 'organiz', 'food', 'cooking', 'baking',
        'pest', 'vinegar', 'baking soda', 'lemon', 'ingredient', 'smell',
        'odor', 'mold', 'drain', 'grout', 'declutter', 'storage',
    ]

    negative_kw = [
        'nba', 'nfl', 'mlb', 'nhl', 'fifa', 'champions', 'league',
        'playoff', 'finals', 'semifinal', 'tournament', 'match',
        'football', 'basketball', 'baseball', 'soccer', 'tennis',
        'boxing', 'ufc', 'wrestling', 'formula 1', 'nascar',
        'president', 'congress', 'senate', 'election', 'political', 'government',
        'killed', 'injured', 'accident', 'shooting', 'disaster', 'earthquake',
        'hurricane', 'flood', 'fire', 'crime', 'murder', 'arrest',
        'stock', 'bitcoin', 'crypto', 'market', 'economy', 'inflation',
        'movie', 'actor', 'singer', 'concert', 'album', 'awards', 'oscars',
        ' vs ', 'score', 'standings', 'draft', 'trade', 'contract',
    ]

    has_positive = any(kw in t for kw in positive_kw)
    has_negative = any(kw in t for kw in negative_kw)
    return has_positive and not has_negative

def get_trending_topic_en():
    """Fetches trending topics — only home/health/cooking niche topics."""
    geo = random.choice(TRENDING_COUNTRIES)
    print(f"[1] Fetching trending topics in {COUNTRY_NAMES[geo]} (Google Trends)...")

    try:
        r = requests.get(f"https://trends.google.com/trending/rss?geo={geo}", timeout=15)
        r.raise_for_status()
        feed = feedparser.parse(r.content)
        if feed.entries:
            relevant = [e for e in feed.entries[:25] if _en_topic_is_relevant(e.title)]

            if relevant:
                item = random.choice(relevant)
                traffic = item.get('ht_approx_traffic', 'high volume')
                news_url = item.get('ht_news_item_url', '')
                news_source = item.get('ht_news_item_source', '')
                context = (f"Trending in {COUNTRY_NAMES[geo]} with {traffic} searches. "
                           f"Coverage: {news_source}.")
                print(f"  -> Trending: {item.title}")
                return item.title, context, news_url, geo
            else:
                print(f"  -> No relevant trending topic. Using fixed topic.")
    except Exception as e:
        print(f"  -> Error: {e}. Using fixed topic.")

    tip = random.choice(TIPS_FALLBACK)
    print(f"  -> Fixed topic: {tip}")
    return tip, "Popular home tip highly searched in English-speaking countries.", "", geo

def get_gemini_content_en(topic, context="", news_url="", geo="US"):
    print(f"[2] Generating English article about '{topic}'...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_API_KEY}"

    link_inst = (
        f"Include EXACTLY this external link in the text: "
        f"<a href='{news_url}' target='_blank' rel='noopener'>read more here</a>."
        if news_url else
        "Include 1 external link to a trusted source (WikiHow, Healthline, The Spruce, Good Housekeeping, or BBC Good Food)."
    )

    prompt = (
        f"CRITICAL INSTRUCTION: You are a warm, wise grandmother with decades of experience in home tips, "
        f"natural remedies, and household hacks. You write for the blog 'Grandma's Tips' "
        f"(grandmastips2026.blogspot.com), beloved by millions across English-speaking countries.\n"
        f"Write a complete article in PERFECT, NATURAL ENGLISH about: '{topic}'.\n"
        f"Context: {context}\n\n"
        f"RULES:\n"
        f"- IRRESISTIBLE TITLE: Emotional hook, max 70 characters. Style: "
        f"'7 Grandma Tricks That Will Change Your Life', "
        f"'The Secret Ingredient That Cleans Everything', "
        f"'Stop Buying It – Make It at Home Instead'\n"
        f"- WARM VOICE: Write as a loving grandmother talking directly to the reader. "
        f"Use 'dear', 'honey', 'sweetheart' occasionally. Friendly, personal, not corporate.\n"
        f"- HOOK: First sentence must grab attention in 3 seconds.\n"
        f"- STRUCTURE: Use <h2> and <h3> headings, <ul><li> lists, short paragraphs.\n"
        f"- KEYWORD: Include '{topic}' naturally in the title and first paragraph.\n"
        f"- {link_inst}\n"
        f"- INTERNAL LINKS: 2 internal links: "
        f"<a href='https://{BLOG_DOMAIN}/search?q={urllib.parse.quote(topic)}'>more tips on {topic}</a>\n"
        f"- LENGTH: Minimum 900 words with real, practical advice.\n"
        f"- INGREDIENTS/MATERIALS: If applicable, list ingredients or supplies in a tidy table or list.\n"
        f"- FAQ: End with <h2>Frequently Asked Questions</h2> with 4-5 "
        f"<h3>Question?</h3><p>Answer.</p> that people actually Google.\n"
        f"- LANGUAGE: 100% natural English. NO AI phrases like 'it's worth noting', "
        f"'in conclusion', 'it is important to', 'in summary'. Write like a real person.\n\n"
        f"MANDATORY RESPONSE FORMAT:\n\n"
        f"[TITLE]\n\n"
        f"[IMAGE_KEYWORD]\n(one word in English for Pexels image search)\n\n"
        f"[LABELS]\n(up to 3 categories. E.g.: Cleaning, Natural Remedies, Kitchen)\n\n"
        f"[CONTENT]\n<p>HTML article here...</p>"
    )

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    return call_gemini_with_retry(url, payload)

def parse_gemini_output_en(text):
    import re
    try:
        t = re.search(r'\[TITLE\]\s*(.*?)\s*\[IMAGE_KEYWORD\]', text, re.DOTALL | re.IGNORECASE)
        k = re.search(r'\[IMAGE_KEYWORD\]\s*(.*?)\s*\[LABELS\]', text, re.DOTALL | re.IGNORECASE)
        l = re.search(r'\[LABELS\]\s*(.*?)\s*\[CONTENT\]', text, re.DOTALL | re.IGNORECASE)
        c = re.search(r'\[CONTENT\]\s*(.*)', text, re.DOTALL | re.IGNORECASE)
        return {
            'title': t.group(1).strip() if t else "Grandma's Home Tips",
            'keyword': k.group(1).strip() if k else "home",
            'labels': l.group(1).strip() if l else "Tips, Home",
            'content': c.group(1).strip() if c else "<p>Error generating content.</p>"
        }
    except Exception:
        return None

def get_pexels_image(keyword):
    print(f"[3] Fetching Pexels image for '{keyword}'...")
    try:
        r = requests.get(
            f"https://api.pexels.com/v1/search?query={urllib.parse.quote(keyword)}&per_page=1&orientation=landscape",
            headers={"Authorization": PEXELS_API_KEY}, timeout=10
        )
        if r.status_code == 200:
            photos = r.json().get('photos', [])
            if photos:
                img = photos[0]['src']['original']
                alt = photos[0].get('alt', keyword)
                return (
                    f'<div class="separator" style="clear:both;text-align:center;">'
                    f'<img alt="{alt}" border="0" loading="lazy" decoding="async" src="{img}" '
                    f'style="border-radius:10px;margin-bottom:25px;'
                    f'box-shadow:0 4px 15px rgba(0,0,0,.15);width:100%;max-width:800px;"/>'
                    f'</div>'
                )
    except Exception as e:
        print(f"  Pexels error: {e}")
    return ""

def main():
    service = get_blogger_service()
    topic, context, news_url, geo = get_trending_topic_en()
    raw = get_gemini_content_en(topic, context, news_url, geo)
    parsed = parse_gemini_output_en(raw)

    if not parsed:
        print("Failed to parse content. Aborting.")
        return

    image_html = get_pexels_image(parsed['keyword'])
    labels = [lb.strip() for lb in parsed['labels'].split(',') if lb.strip()]

    print(f"[4] Publishing to {BLOG_DOMAIN} (ID: {BLOG_ID})...")
    res = service.posts().insert(blogId=BLOG_ID, body={
        "title": parsed['title'],
        "content": image_html + parsed['content'],
        "labels": labels
    }, isDraft=False).execute()

    print("=" * 60)
    print("  SUCCESS! Article published.")
    print("  LINK:", res.get('url'))
    print("=" * 60)

if __name__ == '__main__':
    main()
