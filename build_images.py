#!/usr/bin/env python3
"""
Descarga fotos reales de Wikimedia Commons (licencias libres), las redimensiona
con Pillow para que pesen poco, y las guarda en docs/img/.

Tambien escribe docs/img/credits.json con la atribucion de cada foto
(autor, licencia, enlace a la pagina de Commons) que el pie de pagina del
sitio usa para mostrar los creditos.

Pensado para correr en el runner de GitHub Actions (que si tiene acceso a
Wikimedia). Tambien se puede correr localmente:  python build_images.py

Requisitos: Pillow  (pip install Pillow)
"""
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from PIL import Image

API = "https://commons.wikimedia.org/w/api.php"
OUT_DIR = os.path.join(os.path.dirname(__file__), "romania", "img")
# Wikimedia pide un User-Agent descriptivo con contacto; los genericos desde
# IPs de cloud (runners) se rate-limitean al toque.
USER_AGENT = ("RomaniaTripSite/1.0 "
              "(https://github.com/FernandoTurn/retail-latam-digest-; "
              "turn.fernando@gmail.com)")

MAX_RETRIES = 6          # reintentos por request ante 429 / errores transitorios
REQUEST_PAUSE = 1.5      # pausa base entre requests (cortesia con Wikimedia)

MAX_WIDTH = 1100          # ancho maximo del JPG final
JPEG_QUALITY = 80         # calidad de compresion
REQUEST_WIDTH = 1500      # ancho que pedimos a Commons antes de recomprimir

# Para cada slot: lista de busquedas en orden de preferencia. Se usa la primera
# que devuelva una imagen con licencia libre.  Asi el sitio no depende de un
# nombre de archivo exacto que podria cambiar.
SLOTS = {
    "bucharest":      ["Romanian Athenaeum Bucharest", "Palace of Parliament Bucharest"],
    "bran_castle":    ["Bran Castle", "Castelul Bran"],
    "bucegi":         ["Sphinx Bucegi", "Babele Bucegi", "Bucegi Mountains"],
    "peles":          ["Peles Castle", "Castelul Peles Sinaia"],
    "bucharest_old":  ["Lipscani Bucharest", "Stavropoleos Church Bucharest", "Bucharest old town"],
    "therme":         ["Therme Bucuresti", "Therme Bucharest", "Aqua park indoor palms"],
    "airplane":       ["El Al Boeing 737", "El Al aircraft", "Boeing 737 takeoff"],
    "car":            ["Volkswagen T-Roc", "VW T-Roc"],
    # --- atracciones individuales ---
    "dino_parc":      ["Dino Parc Rasnov", "Dinosaur park Rasnov Romania"],
    "rasnov_fortress":["Râșnov Citadel", "Cetatea Rasnov", "Rasnov fortress"],
    "alpine_coaster": ["Cheile Gradistei Fundata", "Alpine coaster Romania"],
    "dambovicioara":  ["Cheile Dambovicioarei", "Dambovicioara gorge", "Pestera Dambovicioara"],
    "ialomita_cave":  ["Ialomita Monastery", "Pestera Ialomitei", "Ialomita Cave"],
    "sinaia_cablecar":["Telecabina Sinaia", "Sinaia gondola cable car", "Sinaia Cota 1400"],
    "busteni_cablecar":["Babele Bucegi", "Telecabina Busteni"],
    "afi_cotroceni":  ["AFI Palace Cotroceni", "AFI Cotroceni"],
    "gymboland":      ["Gymboland Bucharest"],
    "museum_senses":  ["Museum of Senses Bucharest"],
    "transfagarasan": ["Transfagarasan", "Transfagarasan road"],
    "vidraru":        ["Vidraru dam", "Lake Vidraru", "Barajul Vidraru"],
    "poenari":        ["Poenari Castle", "Cetatea Poenari"],
}

FREE_HINTS = ("cc", "public domain", "pd", "no restrictions", "free")


def http_get(url):
    """GET con reintentos y backoff que respeta Retry-After ante HTTP 429."""
    last_err = None
    for attempt in range(MAX_RETRIES):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            time.sleep(REQUEST_PAUSE)        # cortesia entre requests exitosos
            return data
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code == 429 or 500 <= e.code < 600:
                # respeta Retry-After si viene; sino backoff exponencial
                ra = e.headers.get("Retry-After") if e.headers else None
                try:
                    wait = int(ra) if ra else 0
                except ValueError:
                    wait = 0
                wait = max(wait, 2 ** (attempt + 1))   # 2,4,8,16,32,64
                wait = min(wait, 60)
                print(f"  . {e.code} en {url[:60]}…; espero {wait}s "
                      f"(intento {attempt+1}/{MAX_RETRIES})", file=sys.stderr)
                time.sleep(wait)
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            last_err = e
            wait = min(2 ** (attempt + 1), 60)
            print(f"  . error de red en {url[:60]}…; espero {wait}s "
                  f"(intento {attempt+1}/{MAX_RETRIES})", file=sys.stderr)
            time.sleep(wait)
    raise last_err if last_err else RuntimeError("http_get agoto reintentos")


def strip_html(s):
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def is_free(license_short):
    low = (license_short or "").lower()
    return any(h in low for h in FREE_HINTS)


def search_image(query):
    """Devuelve (thumburl, credit_dict) para la mejor imagen libre, o None."""
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": "6",          # File:
        "gsrlimit": "12",
        "prop": "imageinfo",
        "iiprop": "url|extmetadata|mime|size",
        "iiurlwidth": str(REQUEST_WIDTH),
    }
    data = json.loads(http_get(API + "?" + urllib.parse.urlencode(params)))
    pages = (data.get("query") or {}).get("pages") or {}
    # ordenar por "index" de busqueda para respetar la relevancia
    items = sorted(pages.values(), key=lambda p: p.get("index", 999))
    for page in items:
        info = (page.get("imageinfo") or [None])[0]
        if not info:
            continue
        mime = info.get("mime", "")
        if mime not in ("image/jpeg", "image/png"):
            continue
        if (info.get("width") or 0) < 800:
            continue
        meta = info.get("extmetadata") or {}
        lic = strip_html((meta.get("LicenseShortName") or {}).get("value"))
        if not is_free(lic):
            continue
        thumburl = info.get("thumburl") or info.get("url")
        if not thumburl:
            continue
        credit = {
            "title": page.get("title", "").replace("File:", ""),
            "artist": strip_html((meta.get("Artist") or {}).get("value")) or "Wikimedia Commons",
            "license": lic,
            "licenseUrl": strip_html((meta.get("LicenseUrl") or {}).get("value")),
            "source": info.get("descriptionurl", ""),
        }
        return thumburl, credit
    return None


def save_resized(raw, path):
    img = Image.open(io.BytesIO(raw))
    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")
    if img.width > MAX_WIDTH:
        h = round(img.height * MAX_WIDTH / img.width)
        img = img.resize((MAX_WIDTH, h), Image.LANCZOS)
    img.save(path, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
    return os.path.getsize(path)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    credits = {}
    failures = []
    for key, queries in SLOTS.items():
        got = None
        for q in queries:
            try:
                res = search_image(q)
            except Exception as e:  # red intermitente / rate limit
                print(f"  ! error buscando '{q}': {e}", file=sys.stderr)
                time.sleep(2)
                res = None
            if res:
                got = res
                used_query = q
                break
            time.sleep(1)
        if not got:
            print(f"[X] {key}: sin imagen libre encontrada", file=sys.stderr)
            failures.append(key)
            continue
        thumburl, credit = got
        try:
            raw = http_get(thumburl)
            size = save_resized(raw, os.path.join(OUT_DIR, key + ".jpg"))
        except Exception as e:
            print(f"[X] {key}: error al descargar/guardar: {e}", file=sys.stderr)
            failures.append(key)
            continue
        credit["query"] = used_query
        credits[key] = credit
        print(f"[OK] {key}: {size//1024} KB  <- {credit['title']} ({credit['license']})")
        time.sleep(1)

    with open(os.path.join(OUT_DIR, "credits.json"), "w", encoding="utf-8") as f:
        json.dump(credits, f, ensure_ascii=False, indent=2)
    print(f"\nListo: {len(credits)} imagenes, {len(failures)} fallidas -> {OUT_DIR}")
    if failures:
        print("Fallidas:", ", ".join(failures), file=sys.stderr)
    # No fallar el build por una sola imagen faltante; el sitio degrada con placeholder.


if __name__ == "__main__":
    main()
