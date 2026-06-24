#!/usr/bin/env python3
import os
import json
import feedparser
import hashlib
from datetime import datetime
from anthropic import Anthropic
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import unicodedata

FEEDS = [
    {"url": "https://news.google.com/rss/search?q=retail+moda+Argentina&hl=es-419&gl=AR&ceid=AR:es-419", "section": "Moda y calzado", "emoji": "👗", "source_label": "Google News", "country": "AR"},
    {"url": "https://news.google.com/rss/search?q=retail+calzado+Argentina&hl=es-419&gl=AR&ceid=AR:es-419", "section": "Moda y calzado", "emoji": "👗", "source_label": "Google News", "country": "AR"},
    {"url": "https://news.google.com/rss/search?q=supermercados+Argentina&hl=es-419&gl=AR&ceid=AR:es-419", "section": "Grocery", "emoji": "🛒", "source_label": "Google News", "country": "AR"},
    {"url": "https://news.google.com/rss/search?q=eventos+retail+OR+conferencia+retail+Argentina&hl=es-419&gl=AR&ceid=AR:es-419", "section": "Agenda", "emoji": "📅", "source_label": "Google News", "country": "AR"},
    {"url": "https://news.google.com/rss/search?q=retail+moda+Mexico&hl=es-419&gl=MX&ceid=MX:es-419", "section": "Moda y calzado", "emoji": "👗", "source_label": "Google News", "country": "MX"},
    {"url": "https://news.google.com/rss/search?q=supermercados+Mexico&hl=es-419&gl=MX&ceid=MX:es-419", "section": "Grocery", "emoji": "🛒", "source_label": "Google News", "country": "MX"},
    {"url": "https://news.google.com/rss/search?q=eventos+retail+OR+conferencia+retail+Mexico&hl=es-419&gl=MX&ceid=MX:es-419", "section": "Agenda", "emoji": "📅", "source_label": "Google News", "country": "MX"},
]

EXCLUDE_TERMS = ["robo", "robar", "detienen", "detenido", "asalto", "hurto"]
EXCLUDE_COUNTRIES = ["España", "Madrid", "Barcelona", "Europa", "italiano", "portugués", "francés", "EE.UU", "USA", "California", "Texas"]

SECTION_EMOJIS = {
    "Moda y calzado": "👗",
    "Grocery": "🛒",
    "Retail físico": "🏪",
    "Retail tech": "💡",
    "Agenda": "📅"
}

def normalize(text):
    return unicodedata.normalize('NFKD', text.lower()).encode('ASCII', 'ignore').decode('ASCII')

def get_hash(title):
    return hashlib.md5(normalize(title).encode()).hexdigest()

def load_seen():
    if os.path.exists("seen.json"):
        with open("seen.json") as f:
            return json.load(f)
    return {}

def save_seen(seen):
    with open("seen.json", "w") as f:
        json.dump(seen, f)

def get_summary(title, snippet):
    try:
        client = Anthropic()
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=100,
            messages=[{"role": "user", "content": f"Resume en UNA oración: {title}. {snippet}"}]
        )
        return message.content[0].text
    except:
        return snippet[:150]

def has_excluded_country(text):
    text_lower = text.lower()
    return any(country.lower() in text_lower for country in EXCLUDE_COUNTRIES)

def build_html(items_by_section):
    html = '''<html>
<head>
<style>
body { font-family: Georgia, serif; max-width: 700px; margin: 0 auto; padding: 20px; background: #fafafa; }
.header { text-align: center; padding: 30px 0; border-bottom: 3px solid #1a1a2e; margin-bottom: 25px; }
.logo { font-size: 14px; letter-spacing: 2px; text-transform: uppercase; color: #9a3b2e; margin-bottom: 10px; }
.title { font-size: 48px; color: #1a1a2e; margin: 5px 0; }
.title span { font-size: 68px; color: #9a3b2e; }
.tagline { font-size: 13px; font-style: italic; color: #666; margin-top: 10px; }
.toc { background: #1a1a2e; color: white; padding: 20px; border-radius: 8px; margin-bottom: 25px; }
.toc-title { font-size: 12px; letter-spacing: 2px; text-transform: uppercase; color: #9a3b2e; margin-bottom: 12px; }
.toc-item { display: flex; align-items: center; margin: 8px 0; font-size: 14px; }
.toc-emoji { margin-right: 12px; font-size: 18px; }
.toc-count { margin-left: auto; color: #9a3b2e; font-weight: bold; }
.section { margin-top: 30px; }
.section-header { display: flex; align-items: center; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid #9a3b2e; }
.section-emoji { font-size: 22px; margin-right: 10px; }
.section-title { font-size: 18px; color: #1a1a2e; font-weight: bold; }
.item { margin: 15px 0; padding: 12px; border-left: 4px solid #ddd; background: white; }
.item-title { margin: 0 0 5px 0; font-weight: bold; }
.item-title a { color: #1a1a2e; text-decoration: none; }
.item-title a:hover { text-decoration: underline; }
.item-meta { margin: 0 0 5px 0; font-size: 12px; color: #888; }
.item-summary { margin: 0; font-size: 13px; color: #444; }
.footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 11px; color: #999; text-align: center; }
.link-filters { margin-top: 15px; }
.link-filters a { color: #9a3b2e; font-size: 12px; text-decoration: none; font-weight: bold; }
.link-filters a:hover { text-decoration: underline; }
</style>
</head>
<body>

<div class="header">
  <div class="logo">Despacho semanal de retail</div>
  <div class="title">RE<span>T</span>AIL</div>
  <div class="tagline">by Fernando Turn</div>
  <div class="tagline">Cinco minutos de retail LatAm para empezar el día.</div>
</div>
'''
    
    # Tabla de contenidos
    html += '<div class="toc">'
    html += '<div class="toc-title">En esta edición</div>'
    for section, items in items_by_section.items():
        emoji = SECTION_EMOJIS.get(section, "📌")
        html += f'<div class="toc-item"><div class="toc-emoji">{emoji}</div><div>{section}</div><div class="toc-count">{len(items)}</div></div>'
    html += '</div>'
    
    # Contenido
    for section, items in items_by_section.items():
        emoji = SECTION_EMOJIS.get(section, "📌")
        html += f'<div class="section"><div class="section-header"><div class="section-emoji">{emoji}</div><div class="section-title">{section}</div></div>'
        for item in items:
            html += f'''<div class="item">
<p class="item-title"><a href="{item["link"]}">{item["title"]}</a></p>
<p class="item-meta">{item["source"]} · {item["date"]}</p>
<p class="item-summary">{item["summary"]}</p>
</div>'''
        html += '</div>'
    
    html += '''<div class="footer">
<p>Titulares enlazados a la fuente original. Resúmenes generados automáticamente.</p>
<div class="link-filters">
  <a href="https://turn.github.io/retail-latam-digest/" target="_blank">Ver directorio filtrable →</a>
</div>
</div>

</body>
</html>'''
    return html

def main():
    seen = load_seen()
    all_items = []
    
    for feed in FEEDS:
        try:
            parsed = feedparser.parse(feed["url"])
            for entry in parsed.entries[:10]:
                title = entry.get("title", "")
                link = entry.get("link", "")
                snippet = entry.get("summary", "")[:200]
                
                if any(term in title.lower() for term in EXCLUDE_TERMS):
                    continue
                
                if has_excluded_country(title) or has_excluded_country(snippet):
                    continue
                
                h = get_hash(title)
                if h in seen:
                    continue
                
                seen[h] = True
                summary = get_summary(title, snippet)
                all_items.append({
                    "title": title,
                    "link": link,
                    "source": feed["source_label"],
                    "section": feed["section"],
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "summary": summary
                })
        except Exception as e:
            print(f"Error en {feed['url']}: {e}")
    
    if not all_items:
        print("0 notas nuevas")
        return
    
    items_by_section = {}
    for item in all_items:
        section = item["section"]
        if section not in items_by_section:
            items_by_section[section] = []
        items_by_section[section].append(item)
    
    html = build_html(items_by_section)
    
    try:
        smtp = smtplib.SMTP("smtp.gmail.com", 587)
        smtp.starttls()
        smtp.login(os.getenv("GMAIL_USER"), os.getenv("GMAIL_APP_PASSWORD"))
        
        msg = MIMEMultipart()
        msg["From"] = os.getenv("GMAIL_USER")
        msg["To"] = "turn.fernando@gmail.com"
        msg["Subject"] = f"RETAIL · Despacho diario · {datetime.now().strftime('%Y-%m-%d')}"
        msg.attach(MIMEText(html, "html"))
        
        smtp.send_message(msg)
        smtp.quit()
        print(f"Mail enviado: {len(all_items)} notas")
    except Exception as e:
        print(f"Error mail: {e}")
    
    save_seen(seen)

if __name__ == "__main__":
    main()
