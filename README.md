# villasroyale-ticker

Daten für die Laufbänder auf den VillasRoyale-Carrd-Seiten (VV: Bewertungen, LAU: Monatsraten-Beispiele).
Öffentliche Feeds: `feed-vv.json`, `feed-lau.json`. Betrieb, Regeln und Abläufe der nächtlichen Aufgaben: siehe [RUNBOOK.md](RUNBOOK.md).

    python3 scripts/ticker.py feed vv|lau      # Feed aus data/*.json erzeugen und prüfen
    python3 scripts/ticker.py embeds --base https://raw.githubusercontent.com/jekb159-creator/villasroyale-ticker/main/
