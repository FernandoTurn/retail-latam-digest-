#!/usr/bin/env python3
"""
Genera la geometria REAL de la ruta (siguiendo las carreteras) con el servicio
de routing publico OSRM y la guarda como romania/data/route.geojson.

Pensado para correr en el runner de GitHub Actions (que si tiene salida a
internet). El sitio carga ese GeoJSON con Leaflet y dibuja la polyline real +
los marcadores numerados, sin depender de ninguna API en runtime.

Si OSRM falla, igual escribe un GeoJSON con los marcadores y una linea recta
entre ellos como respaldo (el mapa sigue funcionando, degradado).
"""
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request

OUT_DIR = os.path.join(os.path.dirname(__file__), "romania", "data")
OSRM = "https://router.project-osrm.org/route/v1/driving/"
USER_AGENT = ("RomaniaTripSite/1.0 "
              "(https://github.com/FernandoTurn/retail-latam-digest-; "
              "turn.fernando@gmail.com)")
MAX_RETRIES = 6

# Paradas numeradas (marcadores). lng, lat.
STOPS = [
    {"lng": 26.1010, "lat": 44.5722, "en": "Otopeni Airport", "he": "נמל התעופה אוטופני",
     "date_en": "Aug 2 · start", "date_he": "2.8 · התחלה", "maps": "Henri Coanda International Airport Otopeni"},
    {"lng": 25.3671, "lat": 45.5149, "en": "Bran (Kapa Chalet)", "he": "בראן (Kapa Chalet)",
     "date_en": "Aug 3–6", "date_he": "3–6.8", "maps": "Kapa Chalet Sohodol Bran"},
    {"lng": 25.4570, "lat": 45.4000, "en": "Bucegi — Hotel Peștera", "he": "בוצֶ'גי — Hotel Peștera",
     "date_en": "Aug 7–8", "date_he": "7–8.8", "maps": "Hotel Pestera Wellness Spa Bucegi"},
    {"lng": 25.5510, "lat": 45.3500, "en": "Sinaia", "he": "סינאיה",
     "date_en": "Aug 9", "date_he": "9.8", "maps": "Sinaia"},
    {"lng": 24.1520, "lat": 45.7983, "en": "Sibiu", "he": "סיביו",
     "date_en": "Aug 10", "date_he": "10.8", "maps": "Sibiu"},
    {"lng": 24.6333, "lat": 45.3600, "en": "Vidraru (Transfăgărășan)", "he": "ווידרארו (טרנספגרשאן)",
     "date_en": "Aug 11", "date_he": "11.8", "maps": "Posada Vidraru"},
    {"lng": 26.1025, "lat": 44.4268, "en": "Bucharest", "he": "בוקרשט",
     "date_en": "Aug 12–13", "date_he": "12–13.8", "maps": "Bucharest"},
]

# Coordenadas de routing = paradas + un via-point en el lago Bâlea para forzar
# el paso por la Transfăgărășan entre Sibiu y Vidraru (si no, OSRM podria rodear).
BALEA = {"lng": 24.6172, "lat": 45.6042}
ROUTE_COORDS = ([ (STOPS[i]["lng"], STOPS[i]["lat"]) for i in range(5) ]  # OTP..Sibiu
                + [ (BALEA["lng"], BALEA["lat"]) ]                        # Bâlea (via)
                + [ (STOPS[5]["lng"], STOPS[5]["lat"]),                   # Vidraru
                    (STOPS[6]["lng"], STOPS[6]["lat"]) ])                 # Bucharest


def rdp(points, eps):
    """Ramer-Douglas-Peucker iterativo: reduce la polyline conservando su forma.
    points = [[lng,lat], ...] · eps en grados (~0.0006 ≈ 65 m)."""
    n = len(points)
    if n < 3:
        return points[:]
    keep = [False] * n
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        s, e = stack.pop()
        ax, ay = points[s]; bx, by = points[e]
        dx = bx - ax; dy = by - ay
        seg2 = dx * dx + dy * dy
        dmax = 0.0; idx = -1
        for i in range(s + 1, e):
            px, py = points[i]
            if seg2 == 0:
                d = math.hypot(px - ax, py - ay)
            else:
                t = ((px - ax) * dx + (py - ay) * dy) / seg2
                t = 0.0 if t < 0 else 1.0 if t > 1 else t
                d = math.hypot(px - (ax + t * dx), py - (ay + t * dy))
            if d > dmax:
                dmax = d; idx = i
        if idx != -1 and dmax > eps:
            keep[idx] = True
            stack.append((s, idx)); stack.append((idx, e))
    return [points[i] for i in range(n) if keep[i]]


def http_get(url):
    last = None
    for attempt in range(MAX_RETRIES):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 429 or 500 <= e.code < 600:
                wait = min(2 ** (attempt + 1), 60)
                print(f"  . {e.code}; espero {wait}s ({attempt+1}/{MAX_RETRIES})", file=sys.stderr)
                time.sleep(wait); continue
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
            wait = min(2 ** (attempt + 1), 60)
            print(f"  . red; espero {wait}s ({attempt+1}/{MAX_RETRIES})", file=sys.stderr)
            time.sleep(wait)
    raise last if last else RuntimeError("http_get agoto reintentos")


def fetch_route():
    coords = ";".join(f"{lng},{lat}" for lng, lat in ROUTE_COORDS)
    url = OSRM + coords + "?overview=full&geometries=geojson"
    data = json.loads(http_get(url))
    if data.get("code") != "Ok":
        raise RuntimeError("OSRM code=" + str(data.get("code")))
    route = data["routes"][0]
    return route["geometry"]["coordinates"], route.get("distance", 0), route.get("duration", 0)


def features(line_coords, dist, dur, source):
    feats = [{
        "type": "Feature",
        "properties": {"kind": "route", "source": source,
                       "distance_km": round(dist / 1000), "duration_h": round(dur / 3600, 1)},
        "geometry": {"type": "LineString", "coordinates": line_coords},
    }]
    for i, s in enumerate(STOPS, 1):
        feats.append({
            "type": "Feature",
            "properties": {"kind": "stop", "order": i, "en": s["en"], "he": s["he"],
                           "date_en": s["date_en"], "date_he": s["date_he"], "maps": s["maps"]},
            "geometry": {"type": "Point", "coordinates": [s["lng"], s["lat"]]},
        })
    return {"type": "FeatureCollection", "features": feats}


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    try:
        line, dist, dur = fetch_route()
        raw = len(line)
        line = rdp(line, 0.00008)                        # ~9 m: conserva las curvas de montaña
        line = [[round(x, 5), round(y, 5)] for x, y in line]   # ~1 m de precision
        fc = features(line, dist, dur, "OSRM")
        print(f"[OK] ruta OSRM: {raw} -> {len(line)} puntos, {round(dist/1000)} km, {round(dur/3600,1)} h")
    except Exception as e:
        print(f"[X] OSRM fallo ({e}); uso linea recta de respaldo", file=sys.stderr)
        straight = [[s["lng"], s["lat"]] for s in STOPS]
        fc = features(straight, 0, 0, "fallback-straight")
    with open(os.path.join(OUT_DIR, "route.geojson"), "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False)
    print("Listo ->", os.path.join(OUT_DIR, "route.geojson"))


if __name__ == "__main__":
    main()
