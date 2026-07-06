"""
Henter bygningsomriss (geometri + grunnleggende attributter) fra
OpenStreetMap via Overpass API, kommune for kommune.

Overpass har begrenset kapasitet per spørring, så for å dekke hele Norge bør
du kjøre dette per kommune (eller fylke) i stedet for én kjempespørring.
Bruk gjerne en offentlig kommune-/fylkesinndeling (f.eks. fra Geonorge/SSB)
som inputliste.

Kjør lokalt — dette sandkasse-miljøet har ikke nettverkstilgang til
overpass-api.de.

Eksempel:
    python hent_osm_bygninger.py --sted "Grimstad, Norge" --out data/osm_grimstad.geojson
"""
import argparse
import json
import time
import urllib.request

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

QUERY_TEMPLATE = """
[out:json][timeout:180];
area["name"="{sted}"]["boundary"="administrative"]->.a;
(
  way["building"](area.a);
  relation["building"](area.a);
);
out center tags;
"""


def hent_bygninger(sted, retries=3):
    query = QUERY_TEMPLATE.format(sted=sted)
    req = urllib.request.Request(
        OVERPASS_URL,
        data=("data=" + query).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    for forsok in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=200) as resp:
                return json.load(resp)
        except Exception as e:
            print(f"Forsøk {forsok + 1} feilet: {e}")
            time.sleep(5)
    raise RuntimeError(f"Klarte ikke hente data for {sted} etter {retries} forsøk")


def til_geojson(overpass_resultat):
    features = []
    for el in overpass_resultat.get("elements", []):
        tags = el.get("tags", {})
        if "building" not in tags:
            continue

        if el["type"] == "node":
            lon, lat = el["lon"], el["lat"]
        elif "center" in el:
            lon, lat = el["center"]["lon"], el["center"]["lat"]
        else:
            continue

        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {
                "osm_id": el["id"],
                "osm_type": el["type"],
                "building": tags.get("building"),
                "building_levels": tags.get("building:levels"),
                "start_date": tags.get("start_date"),
                "name": tags.get("name"),
                "addr_street": tags.get("addr:street"),
                "addr_housenumber": tags.get("addr:housenumber"),
                "addr_city": tags.get("addr:city"),
            },
        })
    return {"type": "FeatureCollection", "features": features}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hent bygninger for et sted (kommune/by) fra OpenStreetMap.")
    parser.add_argument("--sted", required=True, help='Navn på administrativt område, f.eks. "Grimstad" eller "Oslo"')
    parser.add_argument("--out", default="data/osm_bygninger.geojson", help="Sti til output GeoJSON")
    args = parser.parse_args()

    resultat = hent_bygninger(args.sted)
    geojson = til_geojson(resultat)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False)

    print(f"Skrev {len(geojson['features'])} bygninger fra OSM til {args.out}")
    print("NB: OSM-bygninger mangler ofte byggeår (start_date) — kombiner gjerne")
    print("med matrikkeldata fra Geonorge/Kartverket for et bedre estimat der")
    print("energiattest mangler.")
