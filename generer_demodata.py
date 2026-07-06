"""
Genererer et syntetisk demo-datasett (data/demo_bygninger.geojson) slik at kartet
fungerer ut av boksen. Dette er IKKE ekte data - se README.md for hvordan du
bytter dette ut med ekte data fra Enova og OpenStreetMap.
"""
import json
import random

random.seed(42)

byer = [
    ("Oslo", "Oslo", 59.9139, 10.7522),
    ("Bergen", "Vestland", 60.3913, 5.3221),
    ("Trondheim", "Trøndelag", 63.4305, 10.3951),
    ("Stavanger", "Rogaland", 58.9700, 5.7331),
    ("Tromsø", "Troms", 69.6492, 18.9553),
    ("Kristiansand", "Agder", 58.1467, 7.9956),
    ("Bodø", "Nordland", 67.2804, 14.4049),
    ("Lillehammer", "Innlandet", 61.1153, 10.4662),
]

bygningstyper = ["Enebolig", "Rekkehus", "Boligblokk", "Kontorbygg", "Skolebygg", "Fritidsbolig"]
energikarakterer = ["A", "B", "C", "D", "E", "F", "G"]
oppvarmingskarakterer = ["gronn", "lysegronn", "gul", "oransje", "rod"]

LETTER_SCORE = {"A": 0, "B": 15, "C": 30, "D": 50, "E": 65, "F": 80, "G": 100}
HEAT_SCORE = {"gronn": 0, "lysegronn": 25, "gul": 50, "oransje": 75, "rod": 100}


def byggeaar_score(aar):
    if aar < 1950:
        return 90
    if aar < 1980:
        return 75
    if aar < 2000:
        return 55
    if aar < 2010:
        return 40
    return 20


features = []
fid = 1
for by, fylke, lat, lon in byer:
    n = random.randint(6, 9)
    for _ in range(n):
        dlat = random.uniform(-0.06, 0.06)
        dlon = random.uniform(-0.1, 0.1)
        btype = random.choice(bygningstyper)
        byggeaar = random.randint(1900, 2023)
        areal = random.randint(60, 4000) if btype not in ("Enebolig", "Fritidsbolig") else random.randint(60, 220)
        har_attest = random.random() < 0.45

        if har_attest:
            ek = random.choice(energikarakterer)
            ok = random.choice(oppvarmingskarakterer)
            score = round(0.6 * LETTER_SCORE[ek] + 0.3 * HEAT_SCORE[ok] + 0.1 * byggeaar_score(byggeaar))
            kilde = "registrert"
        else:
            ek = None
            ok = None
            score = round(byggeaar_score(byggeaar) * random.uniform(0.85, 1.1))
            score = max(0, min(100, score))
            kilde = "estimert"

        feat = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(lon + dlon, 5), round(lat + dlat, 5)]},
            "properties": {
                "id": fid,
                "navn": f"{btype} {fid}",
                "kommune": by,
                "fylke": fylke,
                "bygningstype": btype,
                "byggeaar": byggeaar,
                "areal_m2": areal,
                "energikarakter": ek,
                "oppvarmingskarakter": ok,
                "kilde": kilde,
                "potensial_score": score,
            },
        }
        features.append(feat)
        fid += 1

fc = {"type": "FeatureCollection", "features": features}
with open("data/demo_bygninger.geojson", "w", encoding="utf-8") as f:
    json.dump(fc, f, ensure_ascii=False, indent=1)

print(f"Skrev {len(features)} bygninger til data/demo_bygninger.geojson")
