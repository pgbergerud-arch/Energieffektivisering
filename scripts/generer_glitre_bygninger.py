"""
Genererer et syntetisk demo-datasett med bygninger avgrenset til Glitre Netts
konsesjonsområde (data/glitre_bygninger.geojson) — samme metode som
generer_demodata.py, men begrenset til de samme tettstedene som brukes i
nettkapasitet-demoen, slik at de to lagene kan kobles sammen geografisk.
"""
import json
import random

random.seed(11)

OMRADER = [
    ("Kristiansand", "Agder", 58.1467, 7.9956),
    ("Arendal", "Agder", 58.4610, 8.7723),
    ("Grimstad", "Agder", 58.3406, 8.5934),
    ("Mandal / Lindesnes", "Agder", 58.0292, 7.4519),
    ("Drammen", "Buskerud", 59.7440, 10.2045),
    ("Kongsberg", "Buskerud", 59.6689, 9.6503),
    ("Hønefoss / Ringerike", "Buskerud", 60.1699, 10.2589),
    ("Askøy", "Vestland", 60.4661, 5.1653),
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
# Hold bygningene godt innenfor sekskant-radiusen (9 km) til tilhørende
# nettkapasitet-sone, slik at punkt-i-polygon-koblingen faktisk gir treff.
for by, fylke, lat, lon in OMRADER:
    n = random.randint(9, 13)
    for _ in range(n):
        dlat = random.uniform(-0.045, 0.045)
        dlon = random.uniform(-0.07, 0.07)
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
with open("data/glitre_bygninger.geojson", "w", encoding="utf-8") as f:
    json.dump(fc, f, ensure_ascii=False, indent=1)

print(f"Skrev {len(features)} bygninger til data/glitre_bygninger.geojson")
