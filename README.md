# Bossy Ürün Kataloğu 2026

Claude Design ile hazırlanan Bossy ürün kataloğunun (kapakta 2027) yedeği. Son güncelleme: **3 Kasım 2026**.

Katalog **126 sayfa**: ön kapak, s.01–s.124, arka kapak (A4, 794 × 1123 px). Sayfa sırası `canvas.json` içindeki `order` alanındadır (sayfa grubu `katalog`, arka kapağa kadar); diğer gruplar (`kapak`, `bolum04`, `arsiv`) seçenek/arşiv sayfalarıdır.

## Türkçe katalog

- `project/` — her sayfanın kaynak dosyası (`*.dc.html`) ve sayfa düzeni (`canvas.json`)
- `assets/` — sayfalarda kullanılan tüm görseller, orijinal çözünürlükte. Dosya adı, sayfalardaki `/_blob/<id>` referansıyla aynıdır (TR ve EN görselleri aynı klasörde).
- `pdf/Bossy_Urun_Katalogu_2026.pdf` — tam katalog (126 sayfa), vektörel: yazılar, logolar ve teknik çizimler sınırsız büyütülebilir; fotoğraflar orijinal çözünürlükte; kontur yazılar vektör yola çevrildi.
- `dijital/index.html` — **dijital katalog** (sayfa çevirmeli flipbook). İnternet gerektirmez: klasörü indirip `index.html` dosyasını tarayıcıda açmanız yeterli. Sayfalar vektördür (HTML/SVG), yazı tipleri `dijital/fonts/` altındadır.

## İngilizce katalog (`en/`)

Türkçe kataloğun İngilizce sürümü; tasarım, yerleşim ve görseller aynı, metinler teknik İngilizce.

- `en/project/` — İngilizce sayfa kaynakları (`*.dc.html`) ve `canvas.json`. İngilizce katalog kendi görsel kimliklerini (`/_blob/<id>`) kullanır; dosyalar yine kökteki `assets/` klasöründedir.
- `en/pdf/Bossy_Product_Catalog_2026_EN.pdf` — tam İngilizce katalog (126 sayfa), A4, vektörel.
- `en/dijital/index.html` — İngilizce dijital katalog (internetsiz çalışır). Sağ üstteki düğmeyle TR ⇄ EN geçilir.
- `en/SOZLUK.md`, `en/ceviri/` — terim sözlüğü ve eski çeviri tabloları.

## Yeniden üretmek

```bash
# PDF (TR+EN) ve dijital kataloglar; Python 3 + Playwright (Chromium) + Pillow gerekir
python3 tools/build_catalog.py

# yalnızca bir dil / bir çıktı
python3 tools/build_catalog.py tr pdf
python3 tools/build_catalog.py en flip
```

- `tools/build_catalog.py` — sayfaları `canvas.json` sırasıyla birleştirir, görselleri `assets/`, yazı tiplerini `tools/fonts/` klasöründen yerel olarak bağlar; PDF'i Chromium ile vektörel basar, dijital kataloğu `tools/flipbook_template.html` görüntüleyicisiyle oluşturur.
- `tools/render.js` — tek tek sayfaları PNG/PDF olarak çizmek için (Node + Playwright + opentype.js).
- `tools/sync_en.py`, `tools/catalog_i18n.py` — eski çeviri araçları.
