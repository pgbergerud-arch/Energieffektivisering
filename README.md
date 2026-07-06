# Energipotensial — kart over energieffektiviseringspotensial i norske bygg

Interaktivt kart som visualiserer hvilke bygninger i Norge som har størst
potensial for energieffektivisering, ved å kombinere:

- **Enovas energiattest-register** (energikarakter A–G og oppvarmingskarakter) der bygget er registrert
- **OpenStreetMap** sine bygningsomriss og attributter
- en **modellbasert estimering** (byggeår, bygningstype, areal) for de svært mange byggene som ikke har noen energiattest

Kartet er en statisk nettside (HTML/CSS/JS med Leaflet) og kan driftes gratis på GitHub Pages.

## Kom i gang (med demo-data)

Repoet inneholder et syntetisk demo-datasett (`data/demo_bygninger.geojson`,
~60 bygg i åtte norske byer) slik at kartet fungerer med det samme:

```bash
# fra prosjektmappen
python3 -m http.server 8000
# åpne http://localhost:8000 i nettleseren
```

**Viktig:** Ikke åpne `index.html` eller `nettkapasitet.html` direkte ved å
dobbeltklikke på filen (`file://...` i adressefeltet). Nettlesere blokkerer
da innhenting av de lokale datafilene av sikkerhetsgrunner, og kartet vil
vise en tydelig feilmelding om at kartlaget ikke kunne lastes. Bruk alltid en
lokal server som over (eller "Live Server"-utvidelsen i VS Code, eller
`npx serve`). Når siden er publisert på GitHub Pages fungerer dette
automatisk uten noe ekstra steg, siden den da serveres over `https://`.

Leaflet og MarkerCluster er lagt ved lokalt i `vendor/`-mappen (ikke hentet
fra CDN), slik at kartet ikke er avhengig av tredjeparts-CDN-er og
fungerer likt uansett brannmur/nettverk.

## Slik bytter du ut demo-data med ekte data

Dette miljøet som genererte prosjektet har ikke nettverkstilgang til Enova
eller OpenStreetMap, så datainnhentingen må kjøres **lokalt hos deg**. Tre
steg:

### 1. Hent energiattester fra Enova

Enova publiserer registeret som åpne data via data.norge.no, i tillegg til et
API for tredjepartsaktører (krever avtale):

- Datasett: https://data.norge.no/datasets/6e841199-64b4-36d4-afd2-3d8054e2f96c
- API for tredjepart: https://www.enova.no/energimerking/energimerkestatistikk/

Last ned CSV-distribusjonen og kjør:

```bash
python3 scripts/hent_enova_data.py --inspect ditt_download.csv   # se kolonnenavn
python3 scripts/hent_enova_data.py ditt_download.csv --out data/enova_attester.json
```

Juster `KOLONNEKART` øverst i scriptet hvis kolonnenavnene i filen du laster
ned avviker fra det scriptet forventer.

### 2. Hent bygningsomriss fra OpenStreetMap

Overpass API takler ikke én spørring for hele Norge — kjør kommune for
kommune (eller fylke for fylke):

```bash
python3 scripts/hent_osm_bygninger.py --sted "Grimstad" --out data/osm_grimstad.geojson
python3 scripts/hent_osm_bygninger.py --sted "Oslo" --out data/osm_oslo.geojson
# ... gjenta for aktuelle kommuner, eller skriv en løkke over en kommuneliste
```

Slå sammen filene til én GeoJSON før neste steg, eller kjør steg 3 per kommune
og slå sammen etterpå.

### 3. Koble sammen og beregn potensial-score

```bash
python3 scripts/beregn_potensial.py \
  --enova data/enova_attester.json \
  --osm data/osm_bygninger.geojson \
  --out data/bygninger_norge.geojson
```

Oppdater til slutt `DATA_URL` øverst i `app.js` til den nye filen (eller
erstatt `data/demo_bygninger.geojson` direkte).

**Ytelse ved landsdekkende data:** Norge har mange millioner bygninger — én
enorm GeoJSON-fil vil gjøre nettleseren treg og sprenge GitHub sin
filstørrelsesgrense. For full nasjonal dekning, vurder å:
- dele opp i én GeoJSON-fil per kommune og laste inn kun synlig område, eller
- generere vektorfliser (f.eks. med `tippecanoe`) og bruke et fliselag i stedet for enkeltmarkører.

Klyngevisningen (MarkerCluster) i kartet takler noen titalls tusen punkter
greit, men ikke millioner.

## Metodikk for potensial-score

Score fra 0 (lite å hente) til 100 (stort potensial), beregnet i
`scripts/beregn_potensial.py`:

**Med registrert energiattest:**

| Komponent | Vekt | Grunnlag |
|---|---|---|
| Energikarakter (A–G) | 60 % | A → 0 poeng, G → 100 poeng |
| Oppvarmingskarakter (rød–grønn) | 30 % | grønn → 0 poeng, rød → 100 poeng |
| Byggeår | 10 % | eldre bygg gir høyere poeng |

**Uten registrert energiattest (estimert):**

Score settes ut fra byggeår alene (eller byggeår + liten justering for
bygningstype når byggeår er ukjent), og merkes tydelig som «estimert» i
kartets popup og i datakilde-filteret. Dette er en grov tilnærming — bruk
med forsiktighet, og se det som en peker mot hvor man bør undersøke
nærmere, ikke en fasit.

## Prioritetskart: energipotensial × nettkapasitet

`nettkapasitet.html` er en egen side som kombinerer bygningers
effektiviseringspotensial med nettkapasitet, avgrenset til **Glitre Netts
konsesjonsområde** (Agder, Buskerud, deler av Østfold/Akershus, Hadeland,
Askøy) — siden det er dette området det ekte kapasitetskartet DataArena
(kart.dataarena.no) dekker.

**Viktig forbehold:** DataArena har ingen dokumentert åpen API for
bulk-uttrekk av kapasitetsdata. Nettkapasitet-laget i dette prosjektet er
derfor **syntetiske demo-tall**, ikke ekte tall fra Glitre Nett. Bruk kartet
som et konsept-bevis, ikke som grunnlag for reelle beslutninger, før du har
byttet inn ekte data.

### Slik bytter du til ekte nettkapasitet-data

1. Slå opp kapasitet manuelt per trafoforsyningsområde på kart.dataarena.no
   (eller avtal datatilgang direkte med Glitre Nett).
2. Digitaliser områdene som polygoner (f.eks. i QGIS eller geojson.io) og fyll
   inn `ledig_kapasitet_mw` og `kategori` per polygon, i samme format som
   `data/glitre_nettkapasitet.geojson`.
3. Bruk `scripts/generer_glitre_bygninger.py` som mal, men koble den mot ekte
   Enova/OSM-data for området (se hovedseksjonen i README) i stedet for
   syntetiske bygg.
4. Kjør `scripts/beregn_prioritet.py` på nytt med de ekte filene:

   ```bash
   python3 scripts/beregn_prioritet.py \
     --bygninger data/dine_ekte_bygninger.geojson \
     --nettkapasitet data/dine_ekte_soner.geojson \
     --out data/glitre_prioritet.geojson
   ```

### Metodikk for prioritetsscore

```
prioritet = 0,5 × effektiviseringspotensial + 0,5 × (100 − normalisert ledig kapasitet)
```

Et bygg med høyt potensial for energieffektivisering **og** lite ledig
nettkapasitet i sitt område får høyest prioritet — det er der en oppgradering
gir mest igjen, siden den frigjør nettkapasitet uten å vente på fysisk
nettforsterkning. Normaliseringen av kapasitet bruker `MAKS_KAPASITET_MW`
(standard 20 MW) i `beregn_prioritet.py` — juster denne til et realistisk
maksnivå for området ditt når du bruker ekte tall.

### Nye filer for prioritetskartet

```
nettkapasitet.html                       Prioritetskart-siden
app-nettkapasitet.js                     Kartlogikk for prioritetskartet
data/glitre_bygninger.geojson            Demo-bygninger i Glitre Netts område
data/glitre_nettkapasitet.geojson        Demo nettkapasitet-soner
data/glitre_prioritet.geojson            Sammenkoblet resultat (brukt av kartet)
scripts/generer_nettkapasitet_demodata.py  Genererer demo-soner
scripts/generer_glitre_bygninger.py      Genererer demo-bygninger for området
scripts/beregn_prioritet.py              Kobler bygg↔sone og regner prioritet
```



```bash
git init
git add .
git commit -m "Energipotensial-kart"
git branch -M main
git remote add origin https://github.com/<ditt-brukernavn>/<repo-navn>.git
git push -u origin main
```

Deretter i GitHub: **Settings → Pages → Source: Deploy from a branch → main
/ (root)**. Siden blir tilgjengelig på
`https://<ditt-brukernavn>.github.io/<repo-navn>/` etter noen minutter.

## Prosjektstruktur

```
index.html                    Sidestruktur (Energipotensial-kartet)
nettkapasitet.html             Sidestruktur (Prioritetskartet)
style.css                     Utseende ("fjord → glo"-fargeskala)
app.js                        Kartlogikk for Energipotensial-kartet
app-nettkapasitet.js          Kartlogikk for Prioritetskartet
vendor/                       Lokalt hostet Leaflet + MarkerCluster (ingen CDN-avhengighet)
data/demo_bygninger.geojson   Syntetisk demo-datasett
scripts/
  generer_demodata.py         Genererer demo-datasettet over
  hent_enova_data.py          Konverter Enova-CSV til JSON
  hent_osm_bygninger.py       Hent bygninger fra OSM (Overpass API)
  beregn_potensial.py         Koble sammen data + beregn potensial-score
```

## Lisens / bruk av data

- Enova-data: sjekk gjeldende lisensvilkår på data.norge.no / Enovas sider før publisering av avledede data.
- OpenStreetMap: © OpenStreetMap-bidragsytere, ODbL-lisens — kreditering er allerede lagt inn i kartets attribusjon.
