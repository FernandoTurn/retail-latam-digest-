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
<meta charset="UTF-8">
<style>
body { font-family: Georgia, serif; max-width: 700px; margin: 0; padding: 20px; background: white; }
table { width: 100%; border-collapse: collapse; }
.header { text-align: center; padding: 30px 0; border-bottom: 3px solid #1a1a2e; margin-bottom: 25px; }
.logo { font-size: 12px; letter-spacing: 2px; text-transform: uppercase; color: #9a3b2e; margin-bottom: 8px; }
.title { font-size: 48px; color: #1a1a2e; margin: 5px 0; line-height: 1; }
.title-span { font-size: 68px; color: #9a3b2e; }
.tagline { font-size: 12px; font-style: italic; color: #666; margin-top: 8px; }
.toc { background: #1a1a2e; color: white; padding: 20px; border-radius: 8px; margin-bottom: 25px; }
.toc-title { font-size: 11px; letter-spacing: 2px; text-transform: uppercase; color: #9a3b2e; margin-bottom: 12px; }
.toc-row { font-size: 14px; padding: 6px 0; }
.toc-count { color: #9a3b2e; font-weight: bold; }
.section-header { background: #1a1a2e; color: white; padding: 12px 15px; margin-top: 25px; border-radius: 4px; }
.section-title { font-size: 16px; font-weight: bold; }
.item { margin: 15px 0; padding: 12px; border-left: 4px solid #ddd; background: #fafafa; }
.item-title { margin: 0 0 5px 0; font-weight: bold; }
.item-title a { color: #1a1a2e; text-decoration: none; }
.item-meta { margin: 0 0 5px 0; font-size: 11px; color: #999; }
.item-summary { margin: 0; font-size: 12px; color: #333; }
.footer { margin-top: 40px; padding-top: 15px; border-top: 1px solid #ddd; font-size: 10px; color: #999; text-align: center; }
</style>
</head>
<body>

<div class="header">
  <div class="logo">Despacho semanal de retail</div>
  <div class="title">RE<span class="title-span">T</span>AIL</div>
  <div class="tagline">por Fernando Turn M.S.C.</div>
  <div class="tagline">Cinco minutos de retail LatAm para empezar el día.</div>
</div>

<div class="toc">
  <div class="toc-title">En esta edición</div>
'''
    
    # Tabla de contenidos
    for section, items in items_by_section.items():
        emoji = SECTION_EMOJIS.get(section, "📌")
        html += f'<div class="toc-row">{emoji} {section} <span class="toc-count">{len(items)}</span></div>'
    
    html += '</div>'
    
    # Contenido
    for section, items in items_by_section.items():
        emoji = SECTION_EMOJIS.get(section, "📌")
        html += f'<div class="section-header"><span class="section-title">{emoji} {section}</span></div>'
        for item in items:
            html += f'''<div class="item">
<div class="item-title"><a href="{item["link"]}">{item["title"]}</a></div>
<div class="item-meta">{item["source"]} · {item["date"]}</div>
<div class="item-summary">{item["summary"]}</div>
</div>'''
    
    html += '''<div class="footer">
<p>Los titulares enlazan a sus fuentes originales, propiedad de los respectivos medios. Los resúmenes son generados automáticamente con IA y pueden contener errores u omisiones — verificá siempre en la fuente antes de citar o tomar decisiones. RETAIL no se responsabiliza por la exactitud del contenido de terceros.</p>
<p><a href="https://turn.github.io/retail-latam-digest/" style="color: #9a3b2e; text-decoration: none;">Ver directorio filtrable →</a></p>
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
