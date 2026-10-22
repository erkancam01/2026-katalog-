# Bossy Ürün Kataloğu 2026

Claude Design ile hazırlanan Bossy 2026 ürün kataloğunun yedeği.

- `project/` — her sayfanın kaynak dosyası (`*.dc.html`) ve sayfa düzeni (`canvas.json`)
- `assets/` — sayfalarda kullanılan tüm görseller, orijinal çözünürlükte. Dosya adı, sayfalardaki `/_blob/<id>` referansıyla aynıdır.

Sayfa sırası `project/canvas.json` içindeki `order` alanındadır.
- `pdf/Bossy_Urun_Katalogu_2026.pdf` — tam katalog (123 sayfa: ön kapak, s.01–s.121, arka kapak), vektörel: yazılar, logolar ve teknik çizimler sınırsız büyütülebilir; fotoğraflar orijinal çözünürlükte.

## İngilizce katalog (`en/`)

Türkçe kataloğun birebir kopyası; tasarım, yerleşim ve görseller aynı, sadece metinler teknik İngilizceye çevrildi.

- `en/project/` — İngilizce sayfa kaynakları (`*.dc.html`) ve `canvas.json`. Görseller kök dizindeki `assets/` klasörünü kullanır (aynı `/_blob/<id>` adları).
- `en/pdf/Bossy_Product_Catalog_2026_EN.pdf` — tam İngilizce katalog (123 sayfa: ön kapak, s.01–s.121, arka kapak), A4, vektörel; kontur yazılar vektör yola çevrildi (Type 3 font yok).
- `en/SOZLUK.md` — kullanılan teknik terim karşılıkları.
- `en/ceviri/` — çeviri tabloları (`ordered.tsv` kaynak metinler, `t0*.txt` çeviriler, `numbers.json` sayı biçimi) ve `en_gorsel_degisiklikleri.json` (İngilizceye özel görseller: kapakta mor menteşe).

### Türkçe katalog değişince İngilizceyi güncellemek

```bash
# Çeviri + İngilizceye özel görseller (yeni metin varsa listeler, çevirip tNN.txt'ye ekleyin)
python3 tools/sync_en.py project en/ceviri en/project

# Türkçe kalan metin var mı
python3 tools/catalog_i18n.py check en/project

# PDF (sayfa başına; Playwright + opentype.js gerekir)
node tools/render.js en/project assets cikti --pdf --outline
```
