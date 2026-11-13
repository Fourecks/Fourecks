#!/usr/bin/env python3
"""Render the public GitHub contribution calendar; never request private activity."""
import argparse, datetime as dt, html, json, re, sys, urllib.request
from html.parser import HTMLParser
from pathlib import Path

class Calendar(HTMLParser):
    def __init__(self):
        super().__init__(); self.days = []; self.tips = {}; self.tip = None
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "td" and a.get("data-date") and a.get("data-level"):
            self.days.append({"date": a["data-date"], "level": int(a["data-level"]), "id": a["id"]})
        if tag == "tool-tip" and a.get("for"):
            self.tip = a["for"]; self.tips[self.tip] = ""
    def handle_data(self, data):
        if self.tip is not None: self.tips[self.tip] += data
    def handle_endtag(self, tag):
        if tag == "tool-tip": self.tip = None

def build(username):
    if not re.fullmatch(r"[A-Za-z0-9-]+", username): raise ValueError("Invalid GitHub username")
    url = "https://github.com/users/" + username + "/contributions"
    req = urllib.request.Request(url, headers={"User-Agent": "public-profile-calendar", "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=30) as response: source = response.read().decode("utf-8")
    cal = Calendar(); cal.feed(source)
    if not 350 <= len(cal.days) <= 380: raise ValueError("Unexpected calendar; keep the last valid SVG")
    days = sorted(cal.days, key=lambda day: day["date"])
    for day in days:
        tip = cal.tips.get(day["id"], "").strip()
        if not tip: raise ValueError("Missing contribution tooltip")
        count = re.match(r"([0-9]+) contributions?", tip)
        day["count"] = int(count.group(1)) if count else 0
        if not count and not tip.lower().startswith("no contributions"): raise ValueError("Unknown tooltip format")
    start = dt.date.fromisoformat(days[0]["date"])
    start -= dt.timedelta(days=(start.weekday() + 1) % 7)
    total = sum(day["count"] for day in days)
    colors = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="280" viewBox="0 0 1200 280" role="img" aria-label="Calendario real de contribuciones públicas de ' + html.escape(username) + '">']
    parts += ['<rect x="1" y="1" width="1198" height="278" rx="10" fill="#0d1117" stroke="#303b47"/>',
              '<g font-family="Arial,sans-serif"><text x="30" y="40" fill="#e6edf3" font-size="25" font-weight="600">Contribuciones</text>',
              '<text x="1170" y="40" text-anchor="end" fill="#96d5b2" font-size="22">' + str(total) + ' contribuciones públicas</text>',
              '<text x="30" y="65" fill="#8b9baa" font-size="14">' + days[0]["date"] + ' — ' + days[-1]["date"] + '</text>']
    for row, label in [(1,"Lun"),(3,"Mié"),(5,"Vie")]:
        parts.append('<text x="30" y="' + str(116+row*19) + '" fill="#92a2b1" font-size="12">' + label + '</text>')
    months = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
    seen = set()
    for day in days:
        date = dt.date.fromisoformat(day["date"]); offset = (date-start).days
        col, row = divmod(offset, 7); x, y = 76+col*19, 103+row*19
        key = (date.year,date.month)
        if key not in seen:
            seen.add(key); parts.append('<text x="'+str(x)+'" y="90" fill="#92a2b1" font-size="12">'+months[date.month-1]+'</text>')
        parts.append('<rect x="'+str(x)+'" y="'+str(y)+'" width="15" height="15" rx="2" fill="'+colors[day["level"]]+'"><title>'+day["date"]+': '+str(day["count"])+' contribuciones</title></rect>')
    parts.append('<text x="30" y="258" fill="#8b9baa" font-size="12">Datos públicos de GitHub · Actualizado '+dt.datetime.now(dt.timezone.utc).date().isoformat()+'</text>')
    parts.append('<text x="994" y="258" fill="#8b9baa" font-size="12">Menos</text>')
    for i,color in enumerate(colors): parts.append('<rect x="'+str(1038+i*19)+'" y="246" width="15" height="15" rx="2" fill="'+color+'"/>')
    parts.append('<text x="1140" y="258" fill="#8b9baa" font-size="12">Más</text></g></svg>')
    return "".join(parts), total

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", default="Fourecks")
    parser.add_argument("--output", default="assets/contributions.svg")
    parser.add_argument("--stdout-json", action="store_true")
    args = parser.parse_args()
    svg,total = build(args.username)
    if args.stdout_json: print(json.dumps({"svg":svg,"total":total}))
    else:
        path=Path(args.output); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(svg,encoding="utf-8")
        print("Rendered public calendar:", total, "contributions")
