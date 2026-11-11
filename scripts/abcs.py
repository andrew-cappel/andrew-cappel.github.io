#!/usr/bin/env python3
"""Builds the ABCs answer bank from Wikidata (CC0): abcs/index.json + abcs/cats/<key>.json.
Each category lists its answers (label, aliases, id); the game picks a category per letter each day.
Run: python3 scripts/abcs.py   (re-run any time to refresh)"""
import json, re, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "abcs"
API, UA = "https://query.wikidata.org/sparql", "GauntletABCs/1.0 (daily alphabet game)"
SP = lambda c: f"?c wdt:P279* wd:{c}. ?x wdt:P31|wdt:P279 ?c."            # anything that is (a kind of) c
TAX = lambda t, rank="Q7432": f"?x wdt:P171+ wd:{t}; wdt:P105 wd:{rank}."  # taxa under t
HUM = lambda occ: f"?x wdt:P106 wd:{occ}; wdt:P31 wd:Q5."
# key: (family, noun used in the prompt, body using ?x, min sitelinks)
C = {
 "countries": ("places", "country", "?x wdt:P31 wd:Q3624078.", 0),
 "capitals": ("places", "capital city", "?c wdt:P31 wd:Q3624078; wdt:P36 ?x.", 0),
 "states": ("places", "U.S. state", "?x wdt:P31 wd:Q35657.", 0),
 "bigcities": ("places", "city with over a million people", "?x wdt:P31/wdt:P279* wd:Q515; wdt:P1082 ?p. FILTER(?p > 1000000)", 0),
 "rivers": ("nature", "river", "?x wdt:P31 wd:Q4022.", 80),
 "mountains": ("nature", "mountain", "?x wdt:P31 wd:Q8502.", 70),
 "islands": ("nature", "island", "?x wdt:P31 wd:Q23442.", 90),
 "dogs": ("animals", "dog breed", "?x wdt:P31 wd:Q39367.", 5),
 "cats": ("animals", "cat breed", "?x wdt:P31 wd:Q43577.", 3),
 "mammals": ("animals", "mammal", TAX("Q7377"), 45),
 "birds": ("animals", "bird", TAX("Q5113"), 45),
 "fish": ("animals", "fish", TAX("Q127282"), 35),
 "dinosaurs": ("animals", "dinosaur", "?x wdt:P31 wd:Q23038290; wdt:P105 wd:Q34740; wdt:P171+ wd:Q430.", 20),
 "videogames": ("games", "video game", "?x wdt:P31 wd:Q7889.", 35),
 "boardgames": ("games", "board game", "?x wdt:P31/wdt:P279* wd:Q131436.", 20),
 "elements": ("science", "chemical element", "?x wdt:P31 wd:Q11344.", 0),
 "constellations": ("science", "constellation", "?x wdt:P31 wd:Q8928.", 0),
 "proglangs": ("science", "programming language", "?x wdt:P31 wd:Q9143.", 30),
 "fruit": ("food", "fruit", SP("Q1364"), 40),
 "vegetables": ("food", "vegetable", SP("Q11004"), 30),
 "desserts": ("food", "dessert", SP("Q182940"), 20),
 "cheeses": ("food", "cheese", SP("Q10943"), 15),
 "cocktails": ("food", "cocktail", "?x wdt:P31 wd:Q134768.", 3),
 "spices": ("food", "spice or herb", SP("Q42527"), 10),
 "instruments": ("music", "musical instrument", SP("Q34379"), 25),
 "genres": ("music", "music genre", "?x wdt:P31 wd:Q188451.", 40),
 "singers": ("people", "famous singer", HUM("Q177220"), 80),
 "actors": ("people", "famous actor or actress", HUM("Q33999"), 90),
 "painters": ("people", "famous painter", HUM("Q1028181"), 60),
 "composers": ("people", "classical composer", HUM("Q36834"), 60),
 "novelists": ("people", "famous novelist", HUM("Q6625963"), 80),
 "greekgods": ("people", "Greek god or goddess", "?x wdt:P31 wd:Q22989102.", 3),
 "superheroes": ("tv", "superhero", "{ ?x wdt:P31/wdt:P279* wd:Q188784 } UNION { ?x wdt:P106 wd:Q188784 } UNION { ?x wdt:P31/wdt:P279* wd:Q1114461 . ?x wdt:P1080 ?u }", 25),
 "tvseries": ("tv", "TV series", "?x wdt:P31/wdt:P279* wd:Q5398426.", 60),
 "carbrands": ("things", "car brand", "?x wdt:P31/wdt:P279* wd:Q786820.", 15),
 "gems": ("things", "gemstone", SP("Q83437"), 10),
 "sports": ("things", "sport", "?x wdt:P31/wdt:P279* wd:Q349.", 40),
 "dances": ("things", "dance", SP("Q11639"), 20),
 "nba": ("sport", "NBA team", "?x wdt:P118 wd:Q155223; wdt:P31/wdt:P279* wd:Q12973014.", 0),
 "nfl": ("sport", "NFL team", "?x wdt:P118 wd:Q1215884; wdt:P31/wdt:P279* wd:Q12973014.", 0),
}
for y in range(2018, 2027):  # movies by year, e.g. "Name a 2026 movie"
    C[f"films{y}"] = ("films", f"{y} movie", f"?x wdt:P31 wd:Q11424; wdt:P577 ?d. FILTER(YEAR(?d) = {y})", 12)

Q = """SELECT ?x ?label ?sl (GROUP_CONCAT(DISTINCT ?alt; separator="\\t") AS ?alts) WHERE {{
  {body}
  ?x wikibase:sitelinks ?sl. FILTER(?sl >= {minsl})
  ?x rdfs:label ?label. FILTER(LANG(?label)="en")
  OPTIONAL {{ ?x skos:altLabel ?alt. FILTER(LANG(?alt)="en") }}
}} GROUP BY ?x ?label ?sl ORDER BY DESC(?sl) LIMIT 2500"""

def run(q):
    for i in range(6):
        try:
            req = urllib.request.Request(API + "?" + urllib.parse.urlencode({"query": q, "format": "json"}), headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=70) as r: return json.load(r)["results"]["bindings"]
        except urllib.error.HTTPError as e:
            if e.code != 429 or i == 5: raise
            time.sleep(int(e.headers.get("Retry-After") or 0) or 20 * (i + 1))

clean = lambda s: re.sub(r"\s+", " ", re.sub(r"[|#\t]", " ", re.sub(r"\s*\(.*?\)\s*", " ", s))).strip()
first = lambda s: (re.sub(r"^(the|a|an) ", "", s.lower().strip()) or "?")[0].upper()
fwd = lambda b: re.sub(r'(wdt:P\d+[*+]\s+(?:wd:Q\d+|\?\w+))\s*([.}])', r'\1 . hint:Prior hint:gearing "forward" \2', b)

def main():
    import sys
    only = set(sys.argv[1:])   # rebuild just these categories and keep the rest
    (OUT / "cats").mkdir(parents=True, exist_ok=True)
    index = [x for x in json.loads((OUT / "index.json").read_text()) if x["key"] in C and x["key"] not in only] if only and (OUT / "index.json").exists() else []
    for key, (fam, noun, body, minsl) in C.items():
        if only and key not in only: continue
        try: rows = run(Q.format(body=body, minsl=minsl))
        except Exception as e: print("  skip", key, e, flush=True); continue
        seen, ans, counts = set(), [], {}
        for r in rows:
            lab = clean(r["label"]["value"])
            if not lab or re.match(r"^Q\d+$", lab) or lab.lower() in seen: continue
            seen.add(lab.lower())
            al = [clean(a) for a in r.get("alts", {}).get("value", "").split("\t") if a and len(a) <= 40][:5]
            ans.append("|".join([lab] + [a for a in al if a]) + "#" + r["x"]["value"].rsplit("/", 1)[1])
            for k in {first(lab)}:   # count by the main name only
                if k.isalpha() and len(k) == 1 and "A" <= k <= "Z": counts[k] = counts.get(k, 0) + 1
        check = fwd(body.split(" FILTER NOT")[0].split(" FILTER(?p")[0] + (" FILTER(?p > 1000000)" if "FILTER(?p" in body else "") if "YEAR" not in body else body)
        (OUT / "cats" / f"{key}.json").write_text(json.dumps({"key": key, "noun": noun, "body": check, "a": ans}, ensure_ascii=False, separators=(",", ":")))
        index.append({"key": key, "fam": fam, "noun": noun, "n": counts})
        print(f"  {len(ans):5d}  {key}", flush=True); time.sleep(2)
    (OUT / "index.json").write_text(json.dumps(index, separators=(",", ":")))
    print("wrote", len(index), "categories")

if __name__ == "__main__":
    main()
