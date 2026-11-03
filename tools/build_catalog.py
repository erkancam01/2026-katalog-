#!/usr/bin/env python3
"""Bossy katalog: vektörel PDF + internetsiz dijital katalog (flipbook) üretimi.

Kullanım (repo kökünden):
    python3 tools/build_catalog.py            # TR + EN: PDF ve dijital katalog
    python3 tools/build_catalog.py tr pdf     # sadece TR PDF
    python3 tools/build_catalog.py en flip    # sadece EN dijital katalog

Gerekenler: Python 3, Playwright (Chromium), Pillow.
Sayfa sırası canvas.json 'order' alanından alınır (sayfa grubu 'katalog', arka kapağa kadar).
Görseller kökteki assets/ klasöründen, yazı tipleri tools/fonts/ klasöründen okunur.
"""
import html as htmlmod, json, os, re, shutil, sys, base64, io
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, 'tools')
FONTS = os.path.join(TOOLS, 'fonts')
ASSETS = os.path.join(ROOT, 'assets')
W, H = 794, 1123

LANGS = {
    'tr': dict(src='project', pdf='pdf/Bossy_Urun_Katalogu_2026.pdf', flip='dijital', html_lang='tr'),
    'en': dict(src='en/project', pdf='en/pdf/Bossy_Product_Catalog_2026_EN.pdf', flip='en/dijital', html_lang='en'),
}

LATIN = 'U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD'
LATIN_EXT = 'U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF'


def font_css(prefix):
    out = []
    faces = [('Anton', 400, 'anton')] + [('Montserrat', w, 'montserrat') for w in (300, 400, 500, 600, 700, 800)]
    for fam, w, stem in faces:
        for sub, rng in (('latin-ext', LATIN_EXT), ('latin', LATIN)):
            fn = f'{stem}-{sub}-{w}-normal.woff2'
            out.append(f"@font-face{{font-family:'{fam}';font-style:normal;font-weight:{w};"
                       f"src:url('{prefix}{fn}') format('woff2');unicode-range:{rng};}}")
    return '\n'.join(out)


ASSET_FILE = {os.path.splitext(a)[0]: a for a in os.listdir(ASSETS)}


def order_of(src):
    c = json.load(open(os.path.join(ROOT, src, 'canvas.json'), encoding='utf-8'))
    b = c['boards']
    o = [f for f in c['order'] if b.get(f, {}).get('page', 'katalog') == 'katalog']
    return o[:o.index('ArkaKapak.dc.html') + 1], b


def parse_page(path):
    """.dc.html -> (title, styles, body) ; {{alan}} varsayılan değerlerle doldurulur (Design çalışma zamanındaki gibi)."""
    h = open(path, encoding='utf-8').read()
    title = re.search(r'<title>(.*?)</title>', h, re.S).group(1)
    m = re.search(r"<script type=\"text/x-dc\"[^>]*data-props='([^']*)'", h)
    props = json.loads(htmlmod.unescape(m.group(1))) if m else {}
    defaults = {k: v['default'] for k, v in props.items() if isinstance(v, dict) and 'default' in v}
    helmet = re.search(r'<helmet>(.*?)</helmet>', h, re.S).group(1)
    body = re.search(r'</helmet>(.*?)</x-dc>', h, re.S).group(1).strip()
    for k, v in defaults.items():
        body = re.sub(r'\{\{\s*' + re.escape(k) + r'\s*\}\}', v, body)
    body = re.sub(r'\{\{\s*[\w.$]+\s*\}\}', '', body)   # tanımsız alan -> boş (çalışma zamanı da böyle)
    styles = ''.join(re.findall(r'<style>.*?</style>', helmet, re.S))
    return title, styles, body


def blobs(s, to):
    def rep(m):
        bid = m.group(1)
        if bid not in ASSET_FILE:
            raise SystemExit('eksik görsel: ' + bid)
        return to(ASSET_FILE[bid])
    return re.sub(r'/_blob/([0-9a-f]{32})', rep, s)


OUTLINE_JS = None


def outline_js():
    """Kontur (text-stroke) Anton yazıları vektör yola çevirir -> PDF'te Type 3 font oluşmaz."""
    global OUTLINE_JS
    if OUTLINE_JS:
        return OUTLINE_JS
    ot = open(os.path.join(TOOLS, 'vendor', 'opentype.min.js'), encoding='utf-8').read()
    f1 = base64.b64encode(open(os.path.join(FONTS, 'anton-latin-400-normal.woff'), 'rb').read()).decode()
    f2 = base64.b64encode(open(os.path.join(FONTS, 'anton-latin-ext-400-normal.woff'), 'rb').read()).decode()
    OUTLINE_JS = ot + r"""
;(function(){
function ab(b){const s=atob(b),u=new Uint8Array(s.length);for(let i=0;i<s.length;i++)u[i]=s.charCodeAt(i);return u.buffer}
const F=[opentype.parse(ab('""" + f1 + """')),opentype.parse(ab('""" + f2 + r"""'))];
const NS='http://www.w3.org/2000/svg';let n=0;
const els=[...document.querySelectorAll('*')].filter(e=>{const c=getComputedStyle(e);return parseFloat(c.webkitTextStrokeWidth)>0 && /Anton/.test(c.fontFamily)});
for(const el of els){
  const cs=getComputedStyle(el),size=parseFloat(cs.fontSize),sw=cs.webkitTextStrokeWidth,sc=cs.webkitTextStrokeColor;
  const glyphs=[];const tw=document.createTreeWalker(el,NodeFilter.SHOW_TEXT);let t;
  while(t=tw.nextNode()){const s=t.data;for(let i=0;i<s.length;i++){const ch=s[i];if(/\s/.test(ch))continue;
    const r=document.createRange();r.setStart(t,i);r.setEnd(t,i+1);const rc=r.getClientRects()[0];if(!rc)continue;glyphs.push([ch,rc]);}}
  if(!glyphs.length)continue;
  if(cs.position==='static')el.style.position='relative';
  const er=el.getClientRects()[0]||el.getBoundingClientRect();
  const bl=parseFloat(cs.borderLeftWidth)||0,bt=parseFloat(cs.borderTopWidth)||0;
  let d='';
  for(const [ch,rc] of glyphs){const f=F.find(f=>f.charToGlyphIndex(ch)>0)||F[0];
    const x=rc.left-er.left-bl,y=rc.top-er.top-bt+f.ascender/f.unitsPerEm*size;
    d+=f.getPath(ch,x,y,size).toPathData(3);}
  const sv=document.createElementNS(NS,'svg');sv.setAttribute('width','1');sv.setAttribute('height','1');
  sv.setAttribute('style','position:absolute;left:0;top:0;overflow:visible;pointer-events:none');
  const p=document.createElementNS(NS,'path');p.setAttribute('d',d);p.setAttribute('fill','none');p.setAttribute('stroke',sc);p.setAttribute('stroke-width',sw);p.setAttribute('stroke-linejoin','miter');
  sv.appendChild(p);el.style.webkitTextStroke='0px transparent';el.style.color='transparent';el.appendChild(sv);n++;
}
window.__outlined=n;})();
"""
    return OUTLINE_JS


def scope_styles(styles, cls):
    css = ''.join(re.findall(r'<style>(.*?)</style>', styles, re.S))
    rules = []
    for sel, decl in re.findall(r'([^{}]+)\{([^{}]*)\}', css):
        sel = sel.strip()
        if sel in ('body', 'html'):
            continue
        rules.append(','.join(f'section.{cls} {s.strip()}' for s in sel.split(',')) + '{' + decl + '}')
    return ''.join(rules)


def build_pdf(lang, pw, tmp):
    cfg = LANGS[lang]
    order, _ = order_of(cfg['src'])
    css, parts = [], []
    for i, f in enumerate(order):
        _, styles, body = parse_page(os.path.join(ROOT, cfg['src'], f))
        css.append(scope_styles(styles, f'p{i}'))
        body = blobs(body, lambda fn: 'file://' + os.path.join(ASSETS, fn))
        parts.append(f'<section class="p{i}" style="width:{W}px;height:{H}px;overflow:hidden;position:relative;'
                     f'page-break-after:always;break-after:page;">{body}</section>')
    doc = ('<!doctype html><html lang="' + cfg['html_lang'] + '"><head><meta charset="utf-8"><style>'
           + font_css('file://' + FONTS + '/')
           + f'@page{{size:{W}px {H}px;margin:0}}html,body{{margin:0;padding:0;background:#fff}}section{{contain:layout paint size}}'
           + ''.join(css) + '</style></head><body>' + '\n'.join(parts) + '</body></html>')
    hp = os.path.join(tmp, f'{lang}_all.html')
    open(hp, 'w', encoding='utf-8').write(doc)
    out = os.path.join(ROOT, cfg['pdf'])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    b = pw.chromium.launch()
    pg = b.new_page(viewport={'width': W, 'height': H})
    pg.goto('file://' + hp, wait_until='load', timeout=300000)
    pg.evaluate('document.fonts.ready')
    pg.wait_for_timeout(1500)
    pg.add_script_tag(content=outline_js())
    print(lang, 'kontur yazı ->', pg.evaluate('window.__outlined'))
    pg.pdf(path=out, width=f'{W}px', height=f'{H}px', print_background=True,
           margin={'top': '0', 'bottom': '0', 'left': '0', 'right': '0'})
    b.close()
    print(lang, 'PDF', out, len(order), 'sayfa', round(os.path.getsize(out) / 1e6, 1), 'MB')
    return len(order)


UI = {
    'tr': {},
    'en': {
        '<h1>BOSSY <b>KATALOG</b> 2027</h1><span>Dijital katalog · vektör sayfalar</span>':
            '<h1>BOSSY <b>CATALOGUE</b> 2027</h1><span>Digital catalogue · vector pages</span>',
        'aria-label="Yakınlaştırma"': 'aria-label="Zoom"',
        'aria-label="Uzaklaştır"': 'aria-label="Zoom out"',
        'aria-label="Yüzde yüz"': 'aria-label="100 percent"',
        'aria-label="Yakınlaştır"': 'aria-label="Zoom in"',
        'id="fs" type="button">Tam ekran<': 'id="fs" type="button">Full screen<',
        'aria-label="Önceki sayfa"': 'aria-label="Previous page"',
        'aria-label="Sonraki sayfa"': 'aria-label="Next page"',
        'id="first" type="button">Kapak<': 'id="first" type="button">Cover<',
        '‹ Geri<': '‹ Back<',
        'id="count">Kapak<': 'id="count">Cover<',
        'İleri ›<': 'Next ›<',
        'id="last" type="button">Son<': 'id="last" type="button">End<',
        'for="goto">SAYFA <': 'for="goto">PAGE <',
        "'Ön kapak'": "'Front cover'",
        "'Arka kapak'": "'Back cover'",
        "'YÜKLENİYOR'": "'LOADING'",
        '>YÜKLENİYOR<': '>LOADING<',
        "'Kapak'": "'Cover'",
        "'Arka'": "'Back'",
        "'Sayfa '": "'Page '",
        "'TAM EKRAN KULLANILAMIYOR'": "'FULL SCREEN UNAVAILABLE'",
        "'Tam ekrandan çık' : 'Tam ekran'": "'Exit full screen' : 'Full screen'",
    },
}
HINT = {
    'tr': None,
    'en': '<div class="hint">← → keys, scroll, or grab a page corner and curl it to turn · click a page to zoom 2× · Ctrl + wheel / pinch to zoom · drag to pan when zoomed · + − 0 keys</div>',
}


def build_flip(lang, pw, tmp):
    cfg = LANGS[lang]
    order, boards = order_of(cfg['src'])
    out = os.path.join(ROOT, cfg['flip'])
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out + '/pages'); os.makedirs(out + '/thumbs')
    depth = cfg['flip'].count('/') + 1                     # dijital -> 1, en/dijital -> 2
    up = '../' * (depth + 1)                               # pages/ altından repo köküne
    fontdir = os.path.join(ROOT, 'dijital', 'fonts')
    if lang == 'tr' or not os.path.isdir(fontdir):
        os.makedirs(fontdir, exist_ok=True)
        for fn in os.listdir(FONTS):
            if fn.endswith('.woff2'):
                shutil.copyfile(os.path.join(FONTS, fn), os.path.join(fontdir, fn))
        open(os.path.join(fontdir, 'fonts.css'), 'w').write(font_css('') + '\n')
    font_href = up + 'dijital/fonts/fonts.css'
    base = f'<style>html,body{{margin:0;padding:0;background:#fff;width:{W}px;height:{H}px;overflow:hidden}}</style>'
    local_pages = []
    for i, f in enumerate(order):
        title, styles, body = parse_page(os.path.join(ROOT, cfg['src'], f))
        head = (f'<!doctype html>\n<html lang="{cfg["html_lang"]}">\n<head>\n<meta charset="utf-8">\n'
                f'<meta name="viewport" content="width={W}">\n<title>{title}</title>\n')
        rel = head + f'<link rel="stylesheet" href="{font_href}">\n' + base + styles + '\n</head>\n<body>\n' + body + '\n</body>\n</html>\n'
        rel = blobs(rel, lambda fn: up + 'assets/' + fn)
        assert '/_blob/' not in rel and 'googleapis' not in rel
        p = os.path.join(out, 'pages', f'p{i:03d}.html')
        open(p, 'w', encoding='utf-8').write(rel)
        local_pages.append(p)
    # küçük resimler (thumbs) -> webp
    from PIL import Image
    b = pw.chromium.launch()
    pg = b.new_page(viewport={'width': W, 'height': H}, device_scale_factor=0.4)
    for i, p in enumerate(local_pages):
        pg.goto('file://' + p, wait_until='load')
        pg.evaluate('document.fonts.ready')
        pg.wait_for_timeout(120)
        png = pg.screenshot(clip={'x': 0, 'y': 0, 'width': W, 'height': H})
        im = Image.open(io.BytesIO(png)).convert('RGB').resize((160, 226), Image.LANCZOS)
        im.save(os.path.join(out, 'thumbs', f'p{i:03d}.webp'), 'WEBP', quality=72)
    b.close()
    # görüntüleyici
    v = open(os.path.join(TOOLS, 'flipbook_template.html'), encoding='utf-8').read()
    N, LAST = len(order), len(order) - 1
    inner = LAST - 1
    yr = '2027'

    def rep(old, new, cnt=1):
        nonlocal v
        assert v.count(old) == cnt, (old[:60], v.count(old))
        v = v.replace(old, new)
    rep('<title>Bossy Katalog 2027</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n', '')
    rep('<link rel="preconnect" href="https://fonts.googleapis.com">\n', '')
    rep('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Anton&family=Montserrat:wght@500;600;700&display=swap">\n',
        f'<link rel="stylesheet" href="{"../" * depth}dijital/fonts/fonts.css">\n')
    rep("""const url = 'pages/p' + pad(i) + '.html';
    (async () => {
      try {
        let s = html.get(i);
        if (!s){ const r = await fetch(url); if (!r.ok) throw new Error(r.status); s = await r.text(); html.set(i, s); }
        if (d._fr === fr) fr.srcdoc = s;
      } catch (_) { if (d._fr === fr) fr.src = url; }
    })();""", "fr.src = 'pages/p' + pad(i) + '.html';   // göreli adres: internetsiz (file://) da çalışır")
    rep("  const html = new Map();        // page -> fetched html string\n", "")
    rep("const N = 124;                 // p000 ön kapak, p001..p122 = s.01..s.122, p123 arka kapak",
        f"const N = {N};                 // p000 ön kapak, p001..p{inner:03d} = s.01..s.{inner}, p{LAST:03d} arka kapak")
    rep("  // spread 0: [null, cover]; 1: [blank, s01]; k: [s(2k-2), s(2k-1)]; 62: [s122, blank]; 63: [back, null]\n",
        "  // spread 0: [null, cover]; 1: [blank, s01]; sonra [s(2k), s(2k+1)] çiftleri; tek kalan son sayfa boş sayfayla; en sonda [arka kapak, null]\n")
    rep("""  for (let k = 2; k <= 61; k++) spreads.push([2*k-2, 2*k-1]);
  spreads.push([122, 'b']); spreads.push([LAST, null]);""",
        """  for (let p = 2; p <= LAST - 1; p += 2) spreads.push(p + 1 <= LAST - 1 ? [p, p + 1] : [p, 'b']);
  spreads.push([LAST, null]);""")
    rep("' <small>/ 122</small>'", "' <small>/ " + str(inner) + "</small>'")
    rep('max="122"', f'max="{inner}"')
    rep('n <= 122', f'n <= {inner}')
    for k, val in UI[lang].items():
        v = v.replace(k, val)
    if HINT[lang]:
        v = re.sub(r'<div class="hint">.*?</div>', HINT[lang], v, count=1, flags=re.S)
    # dil geçişi (TR <-> EN)
    other = '../../dijital/index.html' if lang == 'en' else '../en/dijital/index.html'
    label = 'TÜRKÇE' if lang == 'en' else 'ENGLISH'
    rep('<button class="btn" id="fs" type="button">', f'<a class="btn" href="{other}" style="text-decoration:none">{label}</a>\n    <button class="btn" id="fs" type="button">')
    title = f'Bossy Katalog {yr}' if lang == 'tr' else f'Bossy Catalogue {yr}'
    desc = 'Bossy ürün kataloğu — dijital katalog' if lang == 'tr' else 'Bossy product catalogue — digital catalogue'
    head = (f'<!doctype html>\n<html lang="{cfg["html_lang"]}">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
            f'<title>{title}</title>\n<meta name="description" content="{desc}">\n')
    m = re.match(r'<!doctype html><html><head>.*?(<style>.*?</style>)</head><body>\n', v, re.S)
    if m:
        v = m.group(1) + '\n' + v[m.end():]
    v = re.sub(r'\s*</body></html>\s*$', '', v)
    i = v.index('<header>')
    v = head + v[:i] + '</head>\n<body>\n' + v[i:] + '\n</body>\n</html>\n'
    assert 'claude' not in v.lower() and 'googleapis' not in v and 'fetch(' not in v
    open(os.path.join(out, 'index.html'), 'w', encoding='utf-8').write(v)
    print(lang, 'dijital katalog', out, N, 'sayfa')
    return N


def main():
    args = sys.argv[1:]
    langs = [a for a in args if a in LANGS] or ['tr', 'en']
    what = [a for a in args if a in ('pdf', 'flip')] or ['pdf', 'flip']
    tmp = os.path.join(ROOT, '.build_tmp')
    os.makedirs(tmp, exist_ok=True)
    with sync_playwright() as pw:
        for lang in langs:
            if 'flip' in what:
                build_flip(lang, pw, tmp)
            if 'pdf' in what:
                build_pdf(lang, pw, tmp)
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    main()
