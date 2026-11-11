#!/usr/bin/env python3
"""Enrich game data with Perplexity (web-grounded) so answer checks are instant and accurate.
  python3 scripts/enrich.py abcs    -> A-Z word lists merged into every ABCs category
  python3 scripts/enrich.py books   -> modern-book quotes checked/corrected
Needs PERPLEXITY_API_KEY in the environment (or in Claude's config on this Mac)."""
import json, os, re, sys, time, urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def key():
    if os.environ.get("PERPLEXITY_API_KEY"): return os.environ["PERPLEXITY_API_KEY"]
    p = Path.home() / "Library/Application Support/Claude/claude_desktop_config.json"
    return json.loads(p.read_text())["mcpServers"]["perplexity"]["env"]["PERPLEXITY_API_KEY"]

def ask(prompt, preset="fast-search", tries=4):
    body = json.dumps({"preset": preset, "input": prompt}).encode()
    for i in range(tries):
        try:
            r = urllib.request.Request("https://api.perplexity.ai/v1/responses", data=body,
                headers={"Authorization": "Bearer " + key(), "Content-Type": "application/json", "User-Agent": "curl/8.4.0"})
            d = json.load(urllib.request.urlopen(r, timeout=180))
            return "\n".join(c.get("text", "") for o in d.get("output", []) if o.get("type") == "message" for c in o.get("content", []))
        except Exception as e:
            if i == tries - 1: raise
            time.sleep(10 * (i + 1))

def az(text):
    """Parse 'A: x, y' lines into a clean list; drops citations, junk and runs of near-identical made-up names."""
    out = []
    for line in text.splitlines():
        m = re.match(r"^\s*\**([A-Za-z])\**\s*[:\-]\s*(.+)$", line)
        if not m: continue
        items = [re.sub(r"\[\d+\]|\(.*?\)|\*", "", w).strip(" .") for w in m.group(2).split(",")]
        items = [w for w in items if 1 < len(w) <= 45 and "?" not in w and w[0].isalnum()]
        firsts = Counter(w.lower().split()[0] for w in items)
        out += [w for w in items if firsts[w.lower().split()[0]] < 5 or len(w.split()) == 1]   # e.g. 20 "xingu ..." birds = invented
    return list(dict.fromkeys(out))

norm = lambda s: re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s.lower())).strip()
first = lambda s: (re.sub(r"^(the|a|an) ", "", s.lower().strip()) or "?")[0].upper()

def describe(noun):
    if "movie" in noun: return f"movies released in {noun.split()[0]} (wide-release, streaming and international films people would know), exact titles"
    if noun.startswith("famous") or "composer" in noun or "god" in noun: return f"{noun}s (full names as commonly known)"
    if "team" in noun: return f"{noun}s, past and present (team names as commonly used, e.g. 'Boston Celtics')"
    return f"{noun}s (common English names people use)"

def abcs():
    idx = json.loads((ROOT / "abcs/index.json").read_text())
    for x in idx:
        f = ROOT / "abcs/cats" / f"{x['key']}.json"; d = json.loads(f.read_text())
        q = (f"List as many real {describe(x['noun'])} as possible, grouped by first letter A to Z. "
             "One line per letter exactly like 'A: name, name, name'. Up to 30 per letter. Only items you are confident are real and correct; "
             "skip letters with none. No descriptions, no numbering, no citations.")
        try: words = az(ask(q))
        except Exception as e: print("  skip", x["key"], e, flush=True); continue
        have = {norm(n) for a in d["a"] for n in a.split("#")[0].split("|")}
        add = [w for w in words if norm(w) not in have]
        d["a"] += [w.replace("|", " ").replace("#", " ") + f"#q{i}" for i, w in enumerate(add)]
        f.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")))
        n = Counter(first(a.split("#")[0].split("|")[0]) for a in d["a"]); x["n"] = {k: v for k, v in n.items() if len(k) == 1 and "A" <= k <= "Z"}
        print(f"  {x['key']:14s} +{len(add)}", flush=True)
        (ROOT / "abcs/index.json").write_text(json.dumps(idx, separators=(",", ":")))

def books():
    f = ROOT / "bythebook/books.json"; B = json.loads(f.read_text())
    import importlib.util; sp = importlib.util.spec_from_file_location("popular", ROOT / "scripts/popular.py"); pm = importlib.util.module_from_spec(sp); sp.loader.exec_module(pm)
    modern = {t for t, *_ in pm.P}
    for b in B:
        if b["title"] not in modern: continue   # classics were already checked word-for-word against Project Gutenberg
        q = (f"For the book '{b['title']}' by {b['author']}, here are 5 short quotes. For each, give the exact wording as it appears in the book "
             "(fix any misquote). If a line is not actually in the book (e.g. it is only from a film), replace it with a different short, real, well-known line from the book. "
             "Keep them ordered from least to most recognizable and under 30 words each. Never include the book's title words. "
             "Answer as a JSON array of 5 strings only.\n" + json.dumps(b["quotes"], ensure_ascii=False))
        try:
            t = ask(q); m = re.search(r"\[.*\]", t, re.S); qs = json.loads(m.group(0)) if m else None
        except Exception as e: print("  skip", b["title"], e, flush=True); continue
        if isinstance(qs, list) and len(qs) == 5 and all(isinstance(s, str) and 3 < len(s) < 260 for s in qs):
            changed = sum(1 for a, c in zip(b["quotes"], qs) if norm(a) != norm(c)); b["quotes"] = [re.sub(r"\[\d+\]", "", s).strip() for s in qs]
            print(f"  {b['title'][:40]:40s} {changed} fixed", flush=True)
        f.write_text(json.dumps(B, ensure_ascii=False, indent=0))

if __name__ == "__main__":
    {"abcs": abcs, "books": books}[sys.argv[1]]()
