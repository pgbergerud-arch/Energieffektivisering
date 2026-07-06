"""
Kobler hver bygning til den nettkapasitet-sonen (trafoforsyningsområde) den
ligger i, og beregner en kombinert prioritetsscore:

    prioritet = 0.5 * effektiviseringspotensial + 0.5 * (lav nettkapasitet)

Altså: bygg med både høyt potensial for energieffektivisering OG et strammet
nett rundt seg får høyest prioritet — det er her man får mest igjen for
innsatsen, siden effektivisering frigjør nettkapasitet uten å vente på
nettforsterkning.

Bruk:
    python beregn_prioritet.py \
        --bygninger data/glitre_bygninger.geojson \
        --nettkapasitet data/glitre_nettkapasitet.geojson \
        --out data/glitre_prioritet.geojson
"""
import argparse
import json

VEKT_POTENSIAL = 0.5
VEKT_KAPASITET = 0.5

# Brukes til å normalisere ledig_kapasitet_mw til en 0-100 skala. Juster
# MAKS_KAPASITET_MW hvis du bruker ekte data med et annet naturlig makstall.
MAKS_KAPASITET_MW = 20.0


def punkt_i_polygon(punkt, polygon_coords):
    """Enkel ray-casting-algoritme for punkt-i-polygon (ingen avhengigheter)."""
    x, y = punkt
    inside = False
    n = len(polygon_coords)
    j = n - 1
    for i in range(n):
        xi, yi = polygon_coords[i]
        xj, yj = polygon_coords[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-15) + xi):
            inside = not inside
        j = i
    return inside


def finn_sone(punkt, soner):
    for sone in soner:
        ring = sone["geometry"]["coordinates"][0]
        if punkt_i_polygon(punkt, ring):
            return sone
    return None


def kapasitet_score(mw):
    """Lav ledig kapasitet -> høy score (høyere prioritet)."""
    andel = max(0.0, min(1.0, mw / MAKS_KAPASITET_MW))
    return round(100 * (1 - andel))


def prosesser(bygninger_path, nettkapasitet_path, out_path):
    with open(bygninger_path, encoding="utf-8") as f:
        bygninger = json.load(f)
    with open(nettkapasitet_path, encoding="utf-8") as f:
        soner = json.load(f)["features"]

    treff = 0
    ut_features = []

    for feat in bygninger["features"]:
        p = dict(feat["properties"])
        punkt = feat["geometry"]["coordinates"]
        sone = finn_sone(punkt, soner)

        if sone:
            treff += 1
            mw = sone["properties"]["ledig_kapasitet_mw"]
            kap_score = kapasitet_score(mw)
            p["nettomrade"] = sone["properties"]["omrade_navn"]
            p["ledig_kapasitet_mw"] = mw
            p["kapasitet_kategori"] = sone["properties"]["kategori"]
        else:
            kap_score = 50  # nøytral default hvis bygget ikke faller i noen sone
            p["nettomrade"] = None
            p["ledig_kapasitet_mw"] = None
            p["kapasitet_kategori"] = None

        prioritet = round(VEKT_POTENSIAL * p["potensial_score"] + VEKT_KAPASITET * kap_score)
        p["kapasitet_score"] = kap_score
        p["prioritet_score"] = max(0, min(100, prioritet))

        ut_features.append({"type": "Feature", "geometry": feat["geometry"], "properties": p})

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": ut_features}, f, ensure_ascii=False)

    print(f"Skrev {len(ut_features)} bygninger med prioritetsscore til {out_path}")
    print(f"{treff} av {len(ut_features)} bygninger ble koblet til en nettkapasitet-sone "
          f"({100 * treff / max(1, len(ut_features)):.1f} %)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Koble bygninger til nettkapasitet-soner og beregn prioritetsscore.")
    parser.add_argument("--bygninger", required=True)
    parser.add_argument("--nettkapasitet", required=True)
    parser.add_argument("--out", default="data/glitre_prioritet.geojson")
    args = parser.parse_args()

    prosesser(args.bygninger, args.nettkapasitet, args.out)
