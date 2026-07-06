"""
Henter energiattest-data (energikarakter, oppvarmingskarakter, byggeår, areal
m.m.) for norske bygg.

Enova publiserer datasettet "Energimerking av boliger og yrkesbygg" som åpne
data via data.norge.no, i tillegg til et API for tredjepartsaktører:

    Datasett (CSV-nedlasting):
      https://data.norge.no/datasets/6e841199-64b4-36d4-afd2-3d8054e2f96c

    API for tredjepartsaktører (krever søknad/avtale med Enova):
      https://www.enova.no/energimerking/energimerkestatistikk/

Fremgangsmåte:
  1. Sjekk data.norge.no-siden over for gjeldende nedlastingslenke til CSV-
     distribusjonen (lenken endres av og til, så den er ikke hardkodet her).
  2. Hvis du trenger sanntidsdata eller søk per matrikkelnummer/adresse,
     søk om API-tilgang hos Enova (lenke over).
  3. Kjør dette scriptet med enten en lokal CSV-fil eller en API-nøkkel.

Dette scriptet kjøres IKKE i sandkassen som genererte prosjektet (nettverket
der har ikke tilgang til data.norge.no/enova.no) — kjør det lokalt hos deg,
der du har vanlig internettilgang.
"""
import argparse
import csv
import json
import sys


# Enova sin karakterskala A (best) -> G (dårligst)
ENERGI_TIL_TALL = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7}

# Antatte kolonnenavn i Enovas CSV-eksport. Enovas faktiske feltnavn kan
# avvike noe — juster KOLONNEKART til det som faktisk står i filen du laster
# ned (kjør scriptet med --inspect for å se kolonnene).
KOLONNEKART = {
    "matrikkel": "Bygningsnummer",
    "adresse": "Adresse",
    "kommune": "Kommunenavn",
    "postnummer": "Postnummer",
    "bygningstype": "Bygningskategori",
    "byggeaar": "Byggeår",
    "areal_m2": "Oppvarmet_BRA",
    "energikarakter": "Energikarakter",
    "oppvarmingskarakter": "Oppvarmingskarakter",
    "utstedelsesdato": "Attestdato",
}


def inspect(path):
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.reader(f, delimiter=";")
        header = next(reader)
        print("Fant følgende kolonner i CSV-filen:")
        for h in header:
            print(" -", h)


def normaliser_oppvarmingskarakter(verdi):
    """Enova bruker en 5-delt fargeskala rødt->grønt for oppvarming."""
    if not verdi:
        return None
    v = verdi.strip().lower()
    mapping = {
        "rød": "rod", "rod": "rod",
        "oransje": "oransje",
        "gul": "gul",
        "lysegrønn": "lysegronn", "lysegronn": "lysegronn",
        "grønn": "gronn", "gronn": "gronn",
    }
    return mapping.get(v, None)


def konverter(input_path, output_path):
    rader = []
    with open(input_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for rad in reader:
            try:
                out = {
                    "matrikkel": rad.get(KOLONNEKART["matrikkel"], "").strip(),
                    "adresse": rad.get(KOLONNEKART["adresse"], "").strip(),
                    "kommune": rad.get(KOLONNEKART["kommune"], "").strip(),
                    "bygningstype": rad.get(KOLONNEKART["bygningstype"], "").strip(),
                    "byggeaar": int(rad[KOLONNEKART["byggeaar"]]) if rad.get(KOLONNEKART["byggeaar"], "").strip().isdigit() else None,
                    "areal_m2": float(rad[KOLONNEKART["areal_m2"]].replace(",", ".")) if rad.get(KOLONNEKART["areal_m2"], "").strip() else None,
                    "energikarakter": (rad.get(KOLONNEKART["energikarakter"], "") or "").strip().upper() or None,
                    "oppvarmingskarakter": normaliser_oppvarmingskarakter(rad.get(KOLONNEKART["oppvarmingskarakter"], "")),
                }
                rader.append(out)
            except Exception as e:
                print(f"Hopper over rad pga. feil: {e}", file=sys.stderr)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(rader, f, ensure_ascii=False)

    print(f"Skrev {len(rader)} energiattester til {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Konverter Enova energiattest-CSV til JSON for videre bruk.")
    parser.add_argument("input_csv", help="Sti til CSV-fil lastet ned fra data.norge.no")
    parser.add_argument("--out", default="data/enova_attester.json", help="Sti til output JSON")
    parser.add_argument("--inspect", action="store_true", help="Bare vis kolonnenavnene i filen og avslutt")
    args = parser.parse_args()

    if args.inspect:
        inspect(args.input_csv)
    else:
        konverter(args.input_csv, args.out)
