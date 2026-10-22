#!/usr/bin/env python3
"""Türkçe katalogdaki değişiklikleri İngilizce kataloğa yansıtır.

  python3 tools/sync_en.py <tr_project_dir> <ceviri_dir> <en_out_dir>

1. Türkçe sayfalardaki metinlerden çevirisi olmayanları bulur, ceviri/ordered.tsv
   dosyasına yeni id'lerle ekler ve listeler (çevrilip yeni bir tNN.txt'ye yazılmalı).
2. Tüm çeviri tablolarını (numbers.json + t*.txt, sırayla) uygular.
3. en_gorsel_degisiklikleri.json'daki İngilizceye özel görsel değişikliklerini uygular
   (ör. kapakta mor menteşe).
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from catalog_i18n import apply, canvas_strings, load_dict, page_strings  # noqa: E402


def main(tr_dir, ceviri, out_dir):
    tables = [os.path.join(ceviri, "numbers.json")] + sorted(glob.glob(os.path.join(ceviri, "t[0-9]*.txt")))
    spec = ",".join(tables)
    d = load_dict(spec)

    canvas = json.load(open(os.path.join(tr_dir, "canvas.json"), encoding="utf-8"))
    seen, rows = set(), []
    for s in canvas_strings(canvas):
        if s not in d and s not in seen:
            seen.add(s); rows.append(("canvas", s))
    for name in canvas["order"]:
        for s in page_strings(open(os.path.join(tr_dir, name), encoding="utf-8").read()):
            if s not in d and s not in seen:
                seen.add(s); rows.append((name.replace(".dc.html", ""), s))
    if rows:
        tsv = os.path.join(ceviri, "ordered.tsv")
        last = max(int(l.split("\t")[0]) for l in open(tsv, encoding="utf-8"))
        with open(tsv, "a", encoding="utf-8") as f:
            for k, (p, s) in enumerate(rows):
                f.write(f"{last + 1 + k}\t{p}\t{s}\n")
        print(f"Çevrilecek {len(rows)} yeni metin (id {last + 1}–{last + len(rows)}):")
        for k, (p, s) in enumerate(rows):
            print(f"{last + 1 + k}\t{p}\t{s}")
        print("Bunları yeni bir tNN.txt dosyasına 'id|çeviri' olarak yazıp tekrar çalıştırın.")
        return 1

    apply(tr_dir, spec, out_dir)
    ov_path = os.path.join(ceviri, "en_gorsel_degisiklikleri.json")
    if os.path.exists(ov_path):
        ov = json.load(open(ov_path, encoding="utf-8"))
        for f in os.listdir(out_dir):
            if not f.endswith(".dc.html"):
                continue
            p = os.path.join(out_dir, f)
            s = open(p, encoding="utf-8").read()
            s2 = s
            for a, b in ov.items():
                s2 = s2.replace("/_blob/" + a, "/_blob/" + b)
            if s2 != s:
                open(p, "w", encoding="utf-8").write(s2)
                print("İngilizceye özel görsel uygulandı:", f)
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
