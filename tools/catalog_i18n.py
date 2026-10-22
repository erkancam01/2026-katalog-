#!/usr/bin/env python3
"""Bossy katalog çeviri aracı.

Sadece görünen metinleri değiştirir; HTML yapısı, stiller, SVG yolları,
görsel referansları ve script blokları bayt bayt korunur.

  extract <src_dir> <out.json>              -> çevrilecek benzersiz metinler
  apply   <src_dir> <dict.json> <out_dir>   -> çevrilmiş kopya
  check   <dir>                             -> Türkçe kalan metinleri listeler
"""
import json
import os
import re
import sys

TAG_RE = re.compile(r"<!--.*?-->|<(?:[^>\"']|\"[^\"]*\"|'[^']*')*>", re.S)
RAW_TAGS = ("script", "style")
ATTRS = ("alt", "title", "aria-label", "placeholder")
ATTR_RE = re.compile(r'(\s(?:%s)=")([^"]*)(")' % "|".join(ATTRS))
LETTER_RE = re.compile(r"[A-Za-zÇĞİÖŞÜçğıöşü]")
HOLE_RE = re.compile(r"\{\{[^}]*\}\}")
TR_CHARS = re.compile(r"[ÇĞİÖŞÜçğıöşü]")


def is_translatable(s):
    core = HOLE_RE.sub("", s)
    return bool(LETTER_RE.search(core))


def segments(html):
    """Yields (kind, text) where kind is 'tag', 'raw', or 'text'."""
    pos = 0
    raw_until = None
    for m in TAG_RE.finditer(html):
        start, end = m.span()
        tag = m.group(0)
        if raw_until:
            if re.match(r"</\s*%s\s*>" % raw_until, tag, re.I):
                yield ("raw", html[pos:start])
                yield ("tag", tag)
                pos = end
                raw_until = None
            continue
        if start > pos:
            yield ("text", html[pos:start])
        yield ("tag", tag)
        pos = end
        tm = re.match(r"<\s*([a-zA-Z0-9-]+)", tag)
        if tm and tm.group(1).lower() in RAW_TAGS and not tag.endswith("/>"):
            raw_until = tm.group(1).lower()
    if pos < len(html):
        yield ("raw" if raw_until else "text", html[pos:])


def split_ws(s):
    m = re.match(r"^(\s*)(.*?)(\s*)$", s, re.S)
    return m.group(1), m.group(2), m.group(3)


def page_strings(html):
    out = []
    for kind, seg in segments(html):
        if kind == "text":
            _, core, _ = split_ws(seg)
            if core and is_translatable(core):
                out.append(core)
        elif kind == "tag" and not seg.startswith("<!--"):
            for m in ATTR_RE.finditer(seg):
                v = m.group(2)
                if v and is_translatable(v):
                    out.append(v)
    return out


def canvas_strings(data):
    out = [data.get("title", "")]
    for b in data.get("boards", {}).values():
        if "title" in b:
            out.append(b["title"])
    for n in data.get("notes", {}).values():
        if "text" in n:
            out.append(n["text"])
    for p in data.get("pages", []):
        out.append(p.get("name", ""))
    return [s for s in out if s and is_translatable(s)]


def extract(src, out_json):
    counts, where = {}, {}
    for name in sorted(os.listdir(src)):
        path = os.path.join(src, name)
        if name.endswith(".dc.html"):
            strs = page_strings(open(path, encoding="utf-8").read())
        elif name == "canvas.json":
            strs = canvas_strings(json.load(open(path, encoding="utf-8")))
        else:
            continue
        for s in strs:
            counts[s] = counts.get(s, 0) + 1
            where.setdefault(s, [])
            if name not in where[s]:
                where[s].append(name)
    items = [{"tr": s, "n": counts[s], "files": where[s][:3]} for s in counts]
    json.dump(items, open(out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(items)} benzersiz metin, toplam {sum(counts.values())} kullanım")


AMP_RE = re.compile(r"&(?!#?\w+;)")


def html_safe(s):
    return AMP_RE.sub("&amp;", s).replace("<", "&lt;")


def plain(s):
    return s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")


def load_dict(spec):
    """Accepts .json dicts or id|text .txt files resolved against ordered.tsv."""
    d = {}
    for path in spec.split(","):
        if path.endswith(".json"):
            d.update(json.load(open(path, encoding="utf-8")))
            continue
        base = os.path.dirname(path) or "."
        ids = {}
        for line in open(os.path.join(base, "ordered.tsv"), encoding="utf-8"):
            i, _, s = line.rstrip("\n").split("\t", 2)
            ids[i] = s
        for line in open(path, encoding="utf-8"):
            line = line.rstrip("\n")
            if not line.strip() or line.startswith("#"):
                continue
            i, t = line.split("|", 1)
            i = i.strip()
            if "@" in i:
                i, f = i.split("@", 1)
                src = ids[i]
                d.setdefault("@" + f + ".dc.html", {})[src] = src if t == "=" else t
                continue
            src = ids[i]
            d[src] = src if t == "=" else t
    return d


def translate_html(html, d, missing):
    parts = []
    for kind, seg in segments(html):
        if kind == "text":
            pre, core, post = split_ws(seg)
            if core and (is_translatable(core) or core in d):
                if core in d:
                    core = html_safe(d[core])
                else:
                    missing.add(core)
            parts.append(pre + core + post)
        elif kind == "tag" and not seg.startswith("<!--"):
            def rep(m):
                v = m.group(2)
                if v and is_translatable(v):
                    if v in d:
                        v = html_safe(d[v]).replace('"', "&quot;")
                    else:
                        missing.add(v)
                return m.group(1) + v + m.group(3)
            seg = ATTR_RE.sub(rep, seg)
            if seg.lower().startswith("<html"):
                seg = seg.replace('lang="tr"', 'lang="en"')
            parts.append(seg)
        else:
            parts.append(seg)
    return "".join(parts)


def apply(src, dict_json, out_dir):
    d = load_dict(dict_json)
    os.makedirs(out_dir, exist_ok=True)
    missing = set()
    for name in sorted(os.listdir(src)):
        path = os.path.join(src, name)
        if name.endswith(".dc.html"):
            html = open(path, encoding="utf-8").read()
            dd = dict(d)
            dd.update(d.get("@" + name, {}))
            new = translate_html(html, dd, missing)
            open(os.path.join(out_dir, name), "w", encoding="utf-8").write(new)
        elif name == "canvas.json":
            data = json.load(open(path, encoding="utf-8"))
            def tr(s):
                if s and is_translatable(s):
                    if s in d:
                        return plain(d[s])
                    missing.add(s)
                return s
            data["title"] = tr(data.get("title", ""))
            for b in data.get("boards", {}).values():
                if "title" in b:
                    b["title"] = tr(b["title"])
            for n in data.get("notes", {}).values():
                if "text" in n:
                    n["text"] = tr(n["text"])
            for p in data.get("pages", []):
                p["name"] = tr(p.get("name", ""))
            json.dump(data, open(os.path.join(out_dir, name), "w", encoding="utf-8"),
                      ensure_ascii=False, indent=2)
    print(f"Çevirisi eksik metin: {len(missing)}")
    for s in sorted(missing)[:50]:
        print("  -", s)


def check(dir_):
    bad = 0
    for name in sorted(os.listdir(dir_)):
        path = os.path.join(dir_, name)
        if name.endswith(".dc.html"):
            strs = page_strings(open(path, encoding="utf-8").read())
        elif name == "canvas.json":
            strs = canvas_strings(json.load(open(path, encoding="utf-8")))
        else:
            continue
        tr = [s for s in strs if TR_CHARS.search(s)]
        if tr:
            bad += len(tr)
            print(name, "->", tr[:5])
    print(f"Türkçe karakter içeren metin: {bad}")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "extract":
        extract(sys.argv[2], sys.argv[3])
    elif cmd == "apply":
        apply(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "check":
        check(sys.argv[2])
