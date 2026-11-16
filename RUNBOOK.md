# VillasRoyale Laufbänder – Betrieb (täglich ca. 23:00)

Zwei Laufbänder (fixe Leiste am unteren Rand der Carrd-Seiten, nicht klickbar):

| Band | Seite | Inhalt | Feed | Daten | Aufgabe (nachts) |
|---|---|---|---|---|---|
| M5a | VV (Touristen) | Bewertungen Booking.com (Skala 10) und Airbnb (Skala 5), nie vermischt | `feed-vv.json` | `data/vv.json` | **Laufband VV** – braucht den Rechner (Browser) |
| M5b | LAU | Monatsraten-Beispiele 2027, „not an offer“ | `feed-lau.json` | `data/lau.json` | **Laufband LAU** – läuft in der Cloud (PriceLabs) |

Die Carrd-Seiten laden beim Aufruf den Feed (`https://raw.githubusercontent.com/jekb159-creator/villasroyale-ticker/main/feed-*.json`). Carrd muss für neue Werte **nicht** neu veröffentlicht werden.
Schutz auf der Seite: Feed älter als 72 h (LAU) bzw. 14 Tage (VV) → Leiste wird ausgeblendet; Feed nicht erreichbar → statischer Fallback höchstens 7 (LAU) bzw. 21 Tage (VV) nach Einbau, danach ausgeblendet. Es werden nie veraltete Zahlen angezeigt.

## Grundregeln für beide Aufgaben
- Zuerst `git pull --rebase`. Nur die eigene Datei ändern (`data/vv.json` bzw. `data/lau.json`), dann `python3 scripts/ticker.py feed vv|lau`.
- Exit 0 → `git add data feed-*.json && git commit -m "<vv|lau> YYYY-MM-DD" && git pull --rebase && git push`.
- Exit 1 (Prüfung schlägt an: Sprung, unplausibler Wert, zu wenige Einträge) → **nichts pushen**, Meldung im Lauf-Ergebnis nennen. Niemals unbeaufsichtigt `--accept-changes` verwenden; das macht nur Joaquín nach Rückfrage.
- Nichts veröffentlichen außer dem Push in dieses Repo. Carrd wird von den Aufgaben nicht angefasst.
- Ergebnis am Ende in 3–5 Zeilen: was neu, was ausgelassen und warum, ob gepusht.

## Aufgabe „Laufband LAU“ (Cloud, PriceLabs-Konnektor)
Regel (Parameterliste M5b/M6): Monatsrate = Summe der PriceLabs-Tagespreise (`price`, inkl. Customizations) aller Tage des Kalendermonats `config.year` × `discount_factor` (0.75 = 25 % Langzeitrabatt ab 29 Nächten), gerundet auf `round_to` (10 €). Nur Beispiele, keine Angebote.
1. `data/lau.json` lesen. `config.lau_candidates` ist die Prioritätenliste (Monat, Villa); `config.listing_ids` die Guesty-IDs (`pms_name` = `guesty`).
2. Für jeden Kandidaten in Reihenfolge, bis `max_rate_items` Raten vorliegen: `get_listing_prices(listing_id, "guesty", 1. des Monats, letzter des Monats)`.
   - Ist **irgendein Tag** nicht frei (`user_price == -1`, also gebucht oder blockiert) → Kandidat überspringen (kein Monatsbeispiel für einen belegten Monat).
   - Villa mit `config.closed_from` (Rex ab 2027-01-12): Monate ab diesem Datum nicht verwenden.
   - Summe der `price` aller Tage berechnen (Python/Bash, Anzahl Tage gegenprüfen), × 0.75, auf 10 runden.
3. `rates` in `data/lau.json` neu schreiben (`{"month","villa","eur","read":"YYYY-MM-DD"}`, in Prioritätenreihenfolge). Weniger als `min_rate_items` verfügbar → nichts ändern, melden.
4. Feed bauen, prüfen, pushen (Grundregeln).

## Aufgabe „Laufband VV“ (Rechner/Built-in-Browser)
Regel (M5a): Werte exakt wie auf der öffentlichen Seite angezeigt (Booking.com „Scored x“ von 10, Airbnb Sterne x von 5). Airbnb-Villa ohne angezeigte Bewertung → nicht aufnehmen.
1. `data/vv.json` lesen. Seiten: Airbnb `https://www.airbnb.com/rooms/<config.airbnb_room_ids[Villa]>`; Booking über `config.booking_urls[Villa]`, falls leer: Booking-Suche nach „VillasRoyale <Villa>“, Treffer mit passender Property-ID (`config.booking_property_ids`) prüfen und die gefundene URL in `config.booking_urls` eintragen.
2. Bewertung je Eintrag lesen und in `ratings` ändern (`value` als Text wie angezeigt, `read` = heute). Nicht lesbare Seite → alter Wert und altes `read` bleiben, melden.
3. Eine Villa mit `closed_from` ≤ heute wird vom Skript automatisch ausgelassen (Rex ab 12.01.2027).
4. Feed bauen, prüfen, pushen (Grundregeln). Ist der Rechner/Browser nicht erreichbar → nichts tun und das melden (der Feed bleibt bis zu 14 Tage gültig).

## Carrd-Embeds neu erzeugen (nur bei Änderung von Design/Text)
`python3 scripts/ticker.py embeds --base https://raw.githubusercontent.com/jekb159-creator/villasroyale-ticker/main/` → `carrd/embed-vv.html` (VV-Seite) und `carrd/embed-lau.html` (LAU-Seite). Inhalt in das jeweilige Embed („Ticker …“, versteckt, Body-Ende) einsetzen und im Carrd-Entwurf speichern.

## Datenschutz-Hinweis
Der Aufruf des Feeds sendet die IP-Adresse der Besucher an GitHub (USA). Die Seiten haben aktuell kein Consent-Banner. Vor Livegang prüfen (Datenschutzerklärung) oder die Datei später auf eine eigene Domain legen.
