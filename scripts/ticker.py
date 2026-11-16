#!/usr/bin/env python3
"""VillasRoyale Laufbaender: data/data.json -> ticker.json (+ Carrd-Embeds).

  python3 scripts/ticker.py feed vv|lau [--accept-changes]   erzeugt feed-vv.json bzw. feed-lau.json und prueft sie (Exit 1 = nicht uebernehmen)
  python3 scripts/ticker.py embeds --base <RAW-BASIS-URL/>   erzeugt carrd/embed-vv.html und carrd/embed-lau.html

Nur Standardbibliothek. Item-Format in den Feeds: "*fett*|Teil|^Akzent^" ('|' = Trenner  ·  ).
"""
import datetime as dt, html, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = {"vv": ROOT / "data" / "vv.json", "lau": ROOT / "data" / "lau.json"}
FEED = {"vv": ROOT / "feed-vv.json", "lau": ROOT / "feed-lau.json"}
NAME = {"Leon": "Léon"}            # Anzeigename
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
SCALE = {"Booking.com": 10, "Airbnb": 5}
MAX_RATING_DELTA, MAX_RATE_DELTA = 0.4, 0.30
MAX_AGE_H, FALLBACK_DAYS = 720, 30   # Ausblenden: Feed aelter als 30 Tage (720 h) bzw. statischer Fallback aelter als 30 Tage
BUILT_DATE = None  # wird beim Erzeugen der Embeds gesetzt

def nm(v): return NAME.get(v, v)
def now(): return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)

# ---------------------------------------------------------------- Feed
def rating_items(d, today):
    closed = d["config"].get("closed_from", {})
    out = []
    for r in d["ratings"]:
        if r["villa"] in closed and today >= dt.date.fromisoformat(closed[r["villa"]]):
            continue                      # Villa geschlossen -> nicht mehr anzeigen
        out.append("*%s*|%s|^%s/%d^" % (r["platform"], nm(r["villa"]), r["value"], SCALE[r["platform"]]))
    return out

def rate_items(d):
    n = d["config"]["max_rate_items"]
    return ["*%s*|%s|Monthly rate ^€ %s^" % (r["month"], nm(r["villa"]), format(r["eur"], ",")) for r in d["rates"][:n]]

LAU_HEAD = ["*Arrive whenever you can. Stay as long as you like.*", "Seasonal rental|from 29 nights|up to 6 months"]
def lau_tail(d): return ["Examples for %d|not an offer" % d["config"]["year"]]

def build_feed(key, d, today=None):
    today = today or now().date()
    items = rating_items(d, today) if key == "vv" else LAU_HEAD + rate_items(d) + lau_tail(d)
    return {"schema": 1, "updated": now().isoformat().replace("+00:00", "Z"), "items": items}

R_RATING = re.compile(r"^\*(Booking\.com|Airbnb)\*\|([^|*^]+)\|\^(\d{1,2}(?:\.\d{1,2})?)/(10|5)\^$")
R_RATE = re.compile(r"^\*(%s)\*\|([^|*^]+)\|Monthly rate \^€ (\d{1,3}(?:,\d{3})*)\^$" % "|".join(MONTHS))

def parse_rating(s):
    m = R_RATING.match(s)
    if not m: return None
    return (m[1], m[2]), float(m[3]), int(m[4])

def parse_rate(s):
    m = R_RATE.match(s)
    return None if not m else ((m[1], m[2]), int(m[3].replace(",", "")))

def validate(key, feed, old, d, accept=False):
    err, cfg, items = [], d["config"], feed["items"]
    try:
        age = (now() - dt.datetime.fromisoformat(feed["updated"].replace("Z", "+00:00"))).total_seconds() / 3600
        if not -1 < age < 2: err.append("updated nicht aktuell")
    except Exception: err.append("updated ungueltig")
    if len(items) > 20: err.append("zu viele Items")
    if key == "vv":
        pr = [parse_rating(s) for s in items]
        if any(p is None for p in pr): err.append("VV: Item mit ungueltigem Format")
        pr = [p for p in pr if p]
        if len(pr) < cfg["min_rating_items"]: err.append("VV: zu wenige Bewertungen (%d)" % len(pr))
        for k, v, sc in pr:
            if not 0 < v <= sc: err.append("VV: Bewertung ausserhalb Skala %s" % (k,))
            if sc == 10 and v < 5 or sc == 5 and v < 3: err.append("VV: unplausibel niedrig %s=%s" % (k, v))
        if old and not accept:
            o = {k: v for k, v, _ in filter(None, (parse_rating(s) for s in old["items"]))}
            for k, v, _ in pr:
                if k in o and abs(v - o[k]) > MAX_RATING_DELTA: err.append("VV: Sprung %s %s -> %s (--accept-changes)" % (k, o[k], v))
    else:
        rates = [parse_rate(s) for s in items if s.startswith("*") and "Monthly rate" in s]
        if any(r is None for r in rates): err.append("LAU: Rate-Item mit ungueltigem Format")
        rates = [r for r in rates if r]
        if len(rates) < cfg["min_rate_items"]: err.append("LAU: zu wenige Monatsraten (%d)" % len(rates))
        for k, eur in rates:
            if not 1000 <= eur <= 40000: err.append("LAU: Rate ausserhalb 1.000-40.000 EUR %s=%d" % (k, eur))
        if old and not accept:
            o = dict(filter(None, (parse_rate(s) for s in old["items"])))
            for k, eur in rates:
                if k in o and abs(eur - o[k]) / o[k] > MAX_RATE_DELTA: err.append("LAU: Sprung %s %d -> %d (--accept-changes)" % (k, o[k], eur))
    return err

def cmd_feed(key, accept):
    d = json.loads(DATA[key].read_text(encoding="utf-8"))
    feed = build_feed(key, d)
    old = json.loads(FEED[key].read_text(encoding="utf-8")) if FEED[key].exists() else None
    err = validate(key, feed, old, d, accept)
    if err:
        print("FEHLER - %s NICHT geschrieben:\n  " % FEED[key].name + "\n  ".join(err)); return 1
    FEED[key].write_text(json.dumps(feed, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("%s geschrieben: %d Items" % (FEED[key].name, len(feed["items"]))); return 0

# ---------------------------------------------------------------- Embeds
CSS = """<style>
#vr-ticker{position:fixed;left:0;right:0;bottom:0;height:40px;z-index:9990;display:flex;align-items:center;background:#2C3220;color:#F4EFE6;border-top:1px solid rgba(255,255,255,.10);font-family:Inter,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;pointer-events:none;-webkit-user-select:none;user-select:none}
#vr-ticker .vr-brand{flex:none;height:100%;display:flex;align-items:center;padding:0 18px 0 20px;font-family:"Playfair Display",Georgia,serif;font-size:16px;font-weight:600;letter-spacing:.01em;color:#fff;white-space:nowrap;position:relative;z-index:2;background:#2C3220}
#vr-ticker .vr-claim{flex:none;height:100%;display:flex;align-items:center;padding:0 20px 0 0;font-size:12px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:#E8B48A;white-space:nowrap;position:relative;z-index:2;background:#2C3220}
#vr-ticker .vr-view{flex:1 1 auto;min-width:0;height:100%;overflow:hidden;-webkit-mask-image:linear-gradient(90deg,transparent 0,#000 28px,#000 calc(100% - 28px),transparent 100%);mask-image:linear-gradient(90deg,transparent 0,#000 28px,#000 calc(100% - 28px),transparent 100%)}
#vr-ticker .vr-track{display:flex;width:max-content;height:100%;align-items:center;animation:vr-run 80s linear infinite;will-change:transform}
#vr-ticker .vr-set{display:flex;flex:none;align-items:center}
#vr-ticker .vr-i{flex:none;display:inline-flex;align-items:center;padding-left:26px;white-space:nowrap;font-size:13px;font-weight:500;letter-spacing:.09em;text-transform:uppercase;color:#F4EFE6}
#vr-ticker .vr-i::after{content:"";flex:none;width:4px;height:4px;margin-left:26px;border-radius:50%;background:#B6622A}
#vr-ticker .vr-i b{font-weight:600;color:#fff}
#vr-ticker .vr-i em{font-style:normal;font-weight:700;color:#E8B48A}
@keyframes vr-run{from{transform:translate3d(0,0,0)}to{transform:translate3d(-50%,0,0)}}
@media (prefers-reduced-motion:reduce){#vr-ticker .vr-track{animation-play-state:paused}}
body{padding-bottom:40px}
@media (max-width:736px){#vr-ticker{height:36px}#vr-ticker .vr-brand{padding:0 12px 0 14px;font-size:14px}#vr-ticker .vr-claim{display:none}#vr-ticker .vr-i{padding-left:18px;font-size:12px}#vr-ticker .vr-i::after{margin-left:18px}body{padding-bottom:36px}}
</style>"""

# Laedt ticker.json (nur textContent, nie innerHTML). Veraltete/fehlende Daten -> Leiste wird ausgeblendet, nie alte Werte.
JS = """<script>
(function(){
var U="__URL__",BUILT="__BUILT__",MAXH=__MAXH__,FB=__FB__;
var el=document.getElementById("vr-ticker"),tr=el&&el.querySelector(".vr-track");if(!tr)return;
function hide(){el.style.display="none";document.body.style.paddingBottom="0"}
function node(s){var sp=document.createElement("span");sp.className="vr-i";
String(s).split("|").forEach(function(p,i){if(i)sp.appendChild(document.createTextNode("\\u00a0\\u00b7\\u00a0"));
p.split(/(\\*[^*]+\\*|\\^[^^]+\\^)/).forEach(function(t){if(!t)return;var c=t.charAt(0),n;
if(c==="*"&&t.length>2){n=document.createElement("b");n.textContent=t.slice(1,-1)}
else if(c==="^"&&t.length>2){n=document.createElement("em");n.textContent=t.slice(1,-1).replace(/ /g,"\\u00a0")}
else n=document.createTextNode(t);sp.appendChild(n)})});return sp}
function render(items){tr.textContent="";
for(var k=0;k<2;k++){var set=document.createElement("div");set.className="vr-set";if(k)set.setAttribute("aria-hidden","true");
items.forEach(function(s){set.appendChild(node(s))});tr.appendChild(set)}
var w=tr.firstChild.offsetWidth;if(w>0)tr.style.animationDuration=Math.max(30,w/55)+"s"}
function fb(){if((Date.now()-Date.parse(BUILT))/864e5>FB)hide()}
try{fetch(U,{cache:"no-store"}).then(function(r){if(!r.ok)throw 0;return r.json()}).then(function(d){
var h=(Date.now()-Date.parse(d.updated))/36e5,it=d.items;
if(!(h>-2)||!Array.isArray(it))throw 0;
if(h>MAXH){hide();return}
it=it.slice(0,40).map(String).filter(function(s){return s.length>0&&s.length<=160});
if(!it.length)throw 0;render(it)}).catch(fb)}catch(e){fb()}
})();
</script>"""

def to_html(s):
    out = []
    for i, part in enumerate(s.split("|")):
        if i: out.append("&nbsp;&middot;&nbsp;")
        for t in re.split(r"(\*[^*]+\*|\^[^^]+\^)", part):
            if not t: continue
            if t[0] == "*" and len(t) > 2: out.append("<b>%s</b>" % html.escape(t[1:-1]))
            elif t[0] == "^" and len(t) > 2: out.append("<em>%s</em>" % html.escape(t[1:-1]).replace(" ", "&nbsp;"))
            else: out.append(html.escape(t))
    return ('<span class="vr-i">%s</span>' % "".join(out)).encode("ascii", "xmlcharrefreplace").decode()

def embed(key, feed, url, claim, aria, comment, maxh, fb):
    sets = "".join(to_html(s) for s in feed["items"])
    built = feed["updated"][:10]
    return (comment + "\n" + CSS + "\n"
        + '<div id="vr-ticker" role="region" aria-label="%s">\n<div class="vr-brand">VillasRoyale&reg;</div>\n' % aria
        + (('<div class="vr-claim">%s</div>\n' % claim) if claim else "")
        + '<div class="vr-view"><div class="vr-track">\n<div class="vr-set">' + sets + '</div>\n<div class="vr-set" aria-hidden="true">' + sets + '</div>\n</div></div>\n</div>\n'
        + JS.replace("__URL__", url).replace("__BUILT__", built).replace("__MAXH__", str(maxh)).replace("__FB__", str(fb)))

def cmd_embeds(base):
    (ROOT / "carrd").mkdir(exist_ok=True)
    c = "<!-- VillasRoyale %s. Daten: %s (taeglich ca. 23:00 aktualisiert). Statischer Inhalt = Fallback; Feed aelter als %s h oder Fallback aelter als %d Tage blendet die Leiste aus. -->"
    feed = json.loads(FEED["vv"].read_text(encoding="utf-8")); url = base + "feed-vv.json"
    (ROOT / "carrd" / "embed-vv.html").write_text(embed("vv", feed, url, "Enjoy the Best!", "Guest ratings on Booking.com (scale 10) and Airbnb (scale 5)", c % ("M5a Laufband VV", url, MAX_AGE_H, FALLBACK_DAYS), MAX_AGE_H, FALLBACK_DAYS), encoding="utf-8")
    feed = json.loads(FEED["lau"].read_text(encoding="utf-8")); url = base + "feed-lau.json"
    (ROOT / "carrd" / "embed-lau.html").write_text(embed("lau", feed, url, None, "Seasonal rental: monthly rate examples", c % ("M5b Laufband LAU", url, MAX_AGE_H, FALLBACK_DAYS), MAX_AGE_H, FALLBACK_DAYS), encoding="utf-8")
    print("embeds geschrieben fuer", base)

if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["feed"] and a[1:2] in (["vv"], ["lau"]): sys.exit(cmd_feed(a[1], "--accept-changes" in a))
    if a[:1] == ["embeds"] and "--base" in a: cmd_embeds(a[a.index("--base") + 1]); sys.exit(0)
    print(__doc__); sys.exit(2)
