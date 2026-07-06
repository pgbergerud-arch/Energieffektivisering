"""
Kombinerer Enova-energiattester (fra hent_enova_data.py) med OSM-bygninger
(fra hent_osm_bygninger.py) og beregner en potensial-score 0-100 for hver
bygning.

Kobling gjøres på adresse (gate + husnummer + kommune), som er en enkel og
robust tilnærming når man ikke har direkte tilgang til matrikkelnummer i
begge datasett. For høyere treffsikkerhet: bruk Kartverkets adresse-API
eller matrikkelnummer der det finnes i begge kilder.

Bruk:
    python beregn_potensial.py \
        --enova data/enova_attester.json \
        --osm data/osm_bygninger.geojson \
        --out data/bygninger_norge.geojson
"""
import argparse
import json
import re

ENERGI_SCORE = {"A": 0, "B": 15, "C": 30, "D": 50, "E": 65, "F": 80, "G": 100}
OPPVARMING_SCORE = {"gronn": 0, "lysegronn": 25, "gul": 50, "oransje": 75, "rod": 100}

# Vekting når registrert energiattest finnes
VEKT_ENERGIKARAKTER = 0.6
VEKT_OPPVARMING = 0.3
VEKT_BYGGEAAR = 0.1


def byggeaar_score(aar):
    """Grov tilnærming: eldre bygg -> antatt høyere potensial for oppgradering."""
    if aar is None:
        return 60  # nøytral default når byggeår er ukjent
    if aar < 1950:
        return 90
    if aar < 1980:
        return 75
    if aar < 2000:
        return 55
    if aar < 2010:
        return 40
    return 20


def bygningstype_justering(building_tag):
    """Liten justering basert på bygningstype (OSM building=*)."""
    if not building_tag:
        return 0
    tunge_typer = {"house", "detached", "terrace", "farm", "cabin"}
    lette_typer = {"apartments", "commercial", "office", "retail"}
    if building_tag in tunge_typer:
        return 5
    if building_tag in lette_typer:
        return -5
    return 0


def normaliser_adresse(gate, husnr, kommune):
    if not gate or not kommune:
        return None
    gate = re.sub(r"\s+", " ", gate.strip().lower())
    husnr = (husnr or "").strip().lower()
    kommune = kommune.strip().lower()
    return f"{gate}|{husnr}|{kommune}"


def bygg_enova_indeks(enova_rader):
    indeks = {}
    for rad in enova_rader:
        adr_deler = (rad.get("adresse") or "").rsplit(" ", 1)
        gate = adr_deler[0] if adr_deler else rad.get("adresse")
        husnr = adr_deler[1] if len(adr_deler) > 1 else ""
        nokkel = normaliser_adresse(gate, husnr, rad.get("kommune", ""))
        if nokkel:
            indeks[nokkel] = rad
    return indeks


def beregn_score(enova_rad, osm_props):
    byggeaar = None
    if enova_rad and enova_rad.get("byggeaar"):
        byggeaar = enova_rad["byggeaar"]
    elif osm_props.get("start_date") and str(osm_props["start_date"])[:4].isdigit():
        byggeaar = int(str(osm_props["start_date"])[:4])

    if enova_rad and enova_rad.get("energikarakter") in ENERGI_SCORE:
        ek_score = ENERGI_SCORE[enova_rad["energikarakter"]]
        ok_score = OPPVARMING_SCORE.get(enova_rad.get("oppvarmingskarakter"), 50)
        score = (
            VEKT_ENERGIKARAKTER * ek_score
            + VEKT_OPPVARMING * ok_score
            + VEKT_BYGGEAAR * byggeaar_score(byggeaar)
        )
        kilde = "registrert"
    else:
        base = byggeaar_score(byggeaar)
        justering = bygningstype_justering(osm_props.get("building"))
        score = base + justering
        kilde = "estimert"

    score = max(0, min(100, round(score)))
    return score, kilde, byggeaar


def slaa_sammen(enova_path, osm_path, out_path):
    with open(enova_path, encoding="utf-8") as f:
        enova_rader = json.load(f)
    with open(osm_path, encoding="utf-8") as f:
        osm = json.load(f)

    enova_indeks = bygg_enova_indeks(enova_rader)
    treff = 0
    features = []

    for feat in osm["features"]:
        p = feat["properties"]
        nokkel = normaliser_adresse(p.get("addr_street"), p.get("addr_housenumber"), p.get("addr_city") or "")
        enova_rad = enova_indeks.get(nokkel) if nokkel else None
        if enova_rad:
            treff += 1

        score, kilde, byggeaar = beregn_score(enova_rad, p)

        features.append({
            "type": "Feature",
            "geometry": feat["geometry"],
            "properties": {
                "id": p["osm_id"],
                "navn": p.get("name") or f"{p.get('building', 'Bygning').capitalize()}",
                "kommune": (enova_rad or {}).get("kommune") or p.get("addr_city") or "Ukjent",
                "fylke": (enova_rad or {}).get("fylke") or "",
                "bygningstype": p.get("building") or (enova_rad or {}).get("bygningstype") or "Ukjent",
                "byggeaar": byggeaar,
                "areal_m2": (enova_rad or {}).get("areal_m2"),
                "energikarakter": (enova_rad or {}).get("energikarakter"),
                "oppvarmingskarakter": (enova_rad or {}).get("oppvarmingskarakter"),
                "kilde": kilde,
                "potensial_score": score,
            },
        })

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f, ensure_ascii=False)

    print(f"Skrev {len(features)} bygninger til {out_path}")
    print(f"Koblet mot registrert energiattest for {treff} av {len(features)} bygninger "
          f"({100 * treff / max(1, len(features)):.1f} %)")
    print("Resten fikk en estimert score basert på byggeår og bygningstype.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kombiner Enova- og OSM-data og beregn potensial-score per bygning.")
    parser.add_argument("--enova", required=True, help="JSON-fil fra hent_enova_data.py")
    parser.add_argument("--osm", required=True, help="GeoJSON-fil fra hent_osm_bygninger.py")
    parser.add_argument("--out", default="data/bygninger_norge.geojson", help="Sti til ferdig GeoJSON for kartet")
    args = parser.parse_args()

    slaa_sammen(args.enova, args.osm, args.out)
