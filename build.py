cat > build.py << 'EOF'
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

# Feeds
FEEDS = [
    {"url": "https://news.google.com/rss/search?q=retail+moda+Argentina&hl=es-419&gl=AR&ceid=AR:es-419", "section": "Moda y calzado", "source_label": "Google News"},
    {"url": "https://news.google.com/rss/search?q=supermercados+Argentina&hl=es-419&gl=AR&ceid=AR:es-419", "section": "Grocery", "source_label": "Google News"},
]

EXCLUDE_TERMS = ["robo", "robar", "detienen"]

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

def build_html(items_by_section):
    html = '<html><body style="font-family: Georgia, serif; max-width: 700px; margin: 0 auto; padding: 20px;">'
    html += '<div style="text-align: center; padding: 20px 0; border-bottom: 3px solid #1a1a2e;">'
    html += '<div style="font-size: 11px; letter-spacing: 3px; color: #9a3b2e;">Despacho semanal de retail</div>'
    html += '<h1 style="font-size: 48px; color: #1a1a2e; margin: 5px 0;">RE<span style="font-size: 68px; color: #9a3b2e;">T</span>AIL</h1>'
    html += '<p style="font-size: 12px; color: #666; margin: 5px 0;">by Fernando Turn</p>'
    html += '<p style="font-size: 12px; font-style: italic; color: #888;">Cinco minutos de retail LatAm para empezar el día.</p>'
    html += '</div>'
    
    for section, items in items_by_section.items():
        html += f'<div style="margin-top: 25px;"><h2 style="color: #9a3b2e; font-size: 16px; border-left: 3px solid #9a3b2e; padding-left: 10px;">{section}</h2>'
        for item in items:
            html += f'<div style="margin: 15px 0; padding: 12px; border-left: 3px solid #ddd;">'
            html += f'<p style="margin: 0 0 5px 0;"><a href="{item["link"]}" style="color: #1a1a2e; font-weight: bold; text-decoration: none;">{item["title"]}</a></p>'
            html += f'<p style="margin: 0 0 5px 0; font-size: 12px; color: #666;">{item["source"]} · {item["date"]}</p>'
            html += f'<p style="margin: 0; font-size: 13px; color: #333;">{item["summary"]}</p>'
            html += '</div>'
        html += '</div>'
    
    html += '<div style="margin-top: 30px; padding-top: 15px; border-top: 1px solid #ddd; font-size: 11px; color: #999; text-align: center;">'
    html += '<p>Titulares enlazados a la fuente original. Resúmenes generados automáticamente.</p>'
    html += '</div></body></html>'
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
EOF
