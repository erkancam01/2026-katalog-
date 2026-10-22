# Bossy Ürün Kataloğu 2026

Claude Design ile hazırlanan Bossy 2026 ürün kataloğunun yedeği.

- `project/` — her sayfanın kaynak dosyası (`*.dc.html`) ve sayfa düzeni (`canvas.json`)
- `assets/` — sayfalarda kullanılan tüm görseller, orijinal çözünürlükte. Dosya adı, sayfalardaki `/_blob/<id>` referansıyla aynıdır.

Sayfa sırası `project/canvas.json` içindeki `order` alanındadır.
- `pdf/Bossy_Urun_Katalogu_2026.pdf` — tam katalog (123 sayfa: ön kapak, s.01–s.121, arka kapak), vektörel: yazılar, logolar ve teknik çizimler sınırsız büyütülebilir; fotoğraflar orijinal çözünürlükte.

## İngilizce katalog (`en/`)

Türkçe kataloğun birebir kopyası; tasarım, yerleşim ve görseller aynı, sadece metinler teknik İngilizceye çevrildi.

- `en/project/` — İngilizce sayfa kaynakları (`*.dc.html`) ve `canvas.json`. Görseller kök dizindeki `assets/` klasörünü kullanır (aynı `/_blob/<id>` adları).
- `en/pdf/Bossy_Product_Catalog_2026_EN.pdf` — tam İngilizce katalog (114 sayfa: ön kapak, s.01–s.112, arka kapak), A4, vektörel; kontur yazılar vektör yola çevrildi (Type 3 font yok).
- `en/SOZLUK.md` — kullanılan teknik terim karşılıkları.
- `en/ceviri/` — çeviri tabloları (`ordered.tsv` kaynak metinler, `t0*.txt` çeviriler, `numbers.json` sayı biçimi).

### Türkçe katalog değişince İngilizceyi güncellemek

```bash
# 1. Çevrilecek metinleri listele (yeni/değişen metinler)
python3 tools/catalog_i18n.py extract project en/ceviri/strings.json

# 2. Çevirileri uygula (eksik metinler listelenir)
python3 tools/catalog_i18n.py apply project en/ceviri/numbers.json,en/ceviri/t01.txt,en/ceviri/t02.txt,en/ceviri/t03.txt,en/ceviri/t04.txt,en/ceviri/t05.txt en/project

# 3. Türkçe kalan metin var mı kontrol et
python3 tools/catalog_i18n.py check en/project

# 4. PDF (sayfa başına; Playwright + opentype.js gerekir)
node tools/render.js en/project assets cikti --pdf --outline
```
