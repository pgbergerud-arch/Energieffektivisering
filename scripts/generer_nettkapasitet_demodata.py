"""
Genererer et syntetisk demo-datasett for nettkapasitet-soner
(data/glitre_nettkapasitet.geojson), som en illustrativ erstatning for ekte
DataArena-data (kart.dataarena.no).

DataArena har ingen dokumentert åpen API. Denne demoen bruker forenklede
sekskant-polygoner rundt tettsteder i Glitre Netts konsesjonsområde
(Agder, Buskerud, deler av Østfold/Akershus, Hadeland, Askøy), med et
syntetisk tall for ledig kapasitet (MW) — IKKE ekte tall.

Bytt ut med ekte data ved å digitalisere/eksportere forsyningsområdene fra
kart.dataarena.no manuelt, eller ved avtale med Glitre Nett om datatilgang.
"""
import json
import math
import random

random.seed(7)

# Tettsteder i (eller nær) Glitre Netts konsesjonsområde, med et grovt
# syntetisk kapasitetstall (MW ledig for store tilknytninger) og kategori.
OMRADER = [
    ("Kristiansand", "Agder", 58.1467, 7.9956, 3.5),
    ("Arendal", "Agder", 58.4610, 8.7723, 6.0),
    ("Grimstad", "Agder", 58.3406, 8.5934, 12.0),
    ("Mandal / Lindesnes", "Agder", 58.0292, 7.4519, 18.5),
    ("Drammen", "Buskerud", 59.7440, 10.2045, 2.0),
    ("Kongsberg", "Buskerud", 59.6689, 9.6503, 9.0),
    ("Hønefoss / Ringerike", "Buskerud", 60.1699, 10.2589, 14.0),
    ("Askøy", "Vestland", 60.4661, 5.1653, 5.0),
]

RADIUS_KM = 9  # grov radius for hver forsyningssone


def kategori_for(mw):
    if mw < 2:
        return "rod"
    if mw < 5:
        return "oransje"
    if mw < 10:
        return "gul"
    return "gronn"


def hexagon(lat, lon, radius_km):
    """Lager en grov sekskant rundt (lat, lon) med gitt radius i km."""
    coords = []
    for i in range(6):
        angle = math.radians(60 * i)
        dlat = (radius_km / 111.0) * math.cos(angle)
        dlon = (radius_km / (111.0 * math.cos(math.radians(lat)))) * math.sin(angle)
        coords.append([round(lon + dlon, 5), round(lat + dlat, 5)])
    coords.append(coords[0])
    return coords


features = []
for i, (navn, fylke, lat, lon, mw) in enumerate(OMRADER, start=1):
    mw_variert = round(mw * random.uniform(0.9, 1.1), 1)
    feature = {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [hexagon(lat, lon, RADIUS_KM)]},
        "properties": {
            "id": i,
            "omrade_navn": navn,
            "fylke": fylke,
            "ledig_kapasitet_mw": mw_variert,
            "kategori": kategori_for(mw_variert),
            "sentrum_lat": lat,
            "sentrum_lon": lon,
            "kilde": "syntetisk_demo",
        },
    }
    features.append(feature)

fc = {"type": "FeatureCollection", "features": features}
with open("data/glitre_nettkapasitet.geojson", "w", encoding="utf-8") as f:
    json.dump(fc, f, ensure_ascii=False, indent=1)

print(f"Skrev {len(features)} nettkapasitet-soner til data/glitre_nettkapasitet.geojson")
