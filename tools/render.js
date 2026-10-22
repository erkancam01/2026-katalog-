// Bossy katalog yerel render: .dc.html -> bağımsız HTML -> PNG / PDF
// node render.js <projectDir> <assetsDir> <outDir> [--pdf] [--png] [--measure] [files...]
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const [, , projectDir, assetsDir, outDir, ...rest] = process.argv;
const flags = new Set(rest.filter(a => a.startsWith('--')));
let files = rest.filter(a => !a.startsWith('--'));
fs.mkdirSync(outDir, { recursive: true });

const FONT_DIR = process.env.FONT_DIR || path.join(__dirname, 'fonts');
const fontCss = [
  ['Anton', 400, 'anton-latin-ext-400-normal.woff2'],
  ['Anton', 400, 'anton-latin-400-normal.woff2'],
  ...[300, 400, 500, 600, 700, 800].flatMap(w => [
    ['Montserrat', w, `montserrat-latin-ext-${w}-normal.woff2`],
    ['Montserrat', w, `montserrat-latin-${w}-normal.woff2`],
  ]),
].map(([f, w, p]) => `@font-face{font-family:'${f}';font-weight:${w};font-style:normal;src:url('file://${path.join(FONT_DIR, p)}') format('woff2');}`).join('\n');

const assetExt = {};
for (const a of fs.readdirSync(assetsDir)) assetExt[a.replace(/\.[^.]+$/, '')] = a;

function standalone(src) {
  const xdc = src.match(/<x-dc>([\s\S]*)<\/x-dc>/)[1];
  const helmet = (xdc.match(/<helmet>([\s\S]*?)<\/helmet>/) || [, ''])[1];
  const body = xdc.replace(/<helmet>[\s\S]*?<\/helmet>/, '');
  const styles = (helmet.match(/<style[\s\S]*?<\/style>/g) || []).join('\n');
  const sm = src.match(/<script type="text\/x-dc"[^>]*data-props='([^']*)'[^>]*>([\s\S]*?)<\/script>/);
  const props = sm ? sm[1].replace(/&#39;/g, "'").replace(/&amp;/g, '&') : '{}';
  const code = sm ? sm[2] : 'class Component extends DCLogic { renderVals(){ return {}; } }';
  const fixBlobs = s => s.replace(/\/_blob\/([0-9a-f]{32})/g, (m, id) =>
    assetExt[id] ? 'file://' + path.join(path.resolve(assetsDir), assetExt[id]) : m);
  return `<!doctype html><html><head><meta charset="utf-8">
<style>${fontCss}
@page{size:794px 1123px;margin:0} html,body{margin:0;padding:0}</style>
${fixBlobs(styles)}
</head><body><div id="root"></div>
<template id="tpl">${fixBlobs(body)}</template>
<script>
class DCLogic { constructor(p){ this.props=p; this.state={}; } setState(){} forceUpdate(){} }
const defs = ${props};
const p = {}; for (const k in defs) if (defs[k] && 'default' in defs[k]) p[k] = defs[k].default;
${code}
const vals = new Component(p).renderVals();
const look = (k) => k.split('.').reduce((o, x) => (o == null ? o : o[x]), vals);
document.getElementById('root').innerHTML =
  document.getElementById('tpl').innerHTML.replace(/\\{\\{\\s*([\\w.$]+)\\s*\\}\\}/g, (m, k) => { const v = look(k); return v == null ? '' : v; });
</script></body></html>`;
}

// Kontur (text-stroke) yazıları vektör yola çevirir: PDF'te Type 3 font oluşmaz.
const opentype = require('opentype.js');
const antonFonts = ['anton-latin-400-normal.woff', 'anton-latin-ext-400-normal.woff'].map(n =>
  opentype.parse(new Uint8Array(fs.readFileSync(path.join(FONT_DIR, n))).buffer));
function pickFont(text) {
  for (const fnt of antonFonts) if ([...text].every(ch => ch === ' ' || fnt.charToGlyphIndex(ch) > 0)) return fnt;
  return antonFonts[0];
}
async function outlineStrokedText(page) {
  const items = await page.evaluate(() => {
    const out = [];
    document.querySelectorAll('#root *').forEach(el => {
      const cs = getComputedStyle(el);
      const sw = parseFloat(cs.webkitTextStrokeWidth);
      if (!(sw > 0)) return;
      const textNodes = [...el.childNodes].filter(n => n.nodeType === 3 && n.textContent.trim());
      if (!textNodes.length) return;
      if (!/Anton/i.test(cs.fontFamily)) return;
      const range = document.createRange();
      range.selectNodeContents(el);
      const rect = range.getBoundingClientRect();
      const marker = document.createElement('span');
      marker.style.cssText = 'display:inline-block;width:0;height:0;vertical-align:baseline';
      el.insertBefore(marker, el.firstChild);
      const baseline = marker.getBoundingClientRect().top;
      const startX = marker.getBoundingClientRect().left;
      marker.remove();
      out.push({ text: el.textContent.replace(/\s+/g, ' ').trim(), x: startX, y: baseline, size: parseFloat(cs.fontSize),
        ls: cs.letterSpacing === 'normal' ? 0 : parseFloat(cs.letterSpacing), sw, color: cs.webkitTextStrokeColor, w: rect.width });
      el.setAttribute('data-outlined', '1');
    });
    return out;
  });
  if (!items.length) return 0;
  const paths = items.map(it => {
    const fnt = pickFont(it.text);
    const p = fnt.getPath(it.text, it.x, it.y, it.size, { kerning: true, letterSpacing: it.ls / it.size });
    return `<path d="${p.toPathData(3)}" fill="none" stroke="${it.color}" stroke-width="${it.sw}" stroke-linejoin="miter"/>`;
  }).join('');
  await page.evaluate((svgInner) => {
    document.querySelectorAll('[data-outlined]').forEach(el => { el.style.webkitTextStroke = '0'; el.style.color = 'transparent'; });
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('width', '794'); svg.setAttribute('height', '1123');
    svg.setAttribute('style', 'position:absolute;left:0;top:0;pointer-events:none;overflow:visible;z-index:2147483647');
    svg.innerHTML = svgInner;
    document.body.appendChild(svg);
  }, paths);
  return items.length;
}

(async () => {
  if (!files.length) files = fs.readdirSync(projectDir).filter(f => f.endsWith('.dc.html'));
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 794, height: 1123 }, deviceScaleFactor: flags.has('--hires') ? 2 : 1 });
  const page = await ctx.newPage();
  const measures = {};
  for (const f of files) {
    const html = standalone(fs.readFileSync(path.join(projectDir, f), 'utf8'));
    const tmp = path.join(outDir, f.replace('.dc.html', '.html'));
    fs.writeFileSync(tmp, html);
    await page.goto('file://' + path.resolve(tmp), { waitUntil: 'load' });
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(150);
    const base = path.join(outDir, f.replace('.dc.html', ''));
    if (flags.has('--outline')) await outlineStrokedText(page);
    if (flags.has('--png')) await page.screenshot({ path: base + '.png', clip: { x: 0, y: 0, width: 794, height: 1123 } });
    if (flags.has('--pdf')) await page.pdf({ path: base + '.pdf', width: '794px', height: '1123px', printBackground: true, preferCSSPageSize: true });
    if (flags.has('--measure')) {
      measures[f] = await page.evaluate(() => {
        const out = [];
        const all = document.querySelectorAll('#root *');
        all.forEach((el, i) => {
          const hasText = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
          if (!hasText) return;
          const r = el.getBoundingClientRect();
          const cs = getComputedStyle(el);
          out.push({ i, w: Math.round(r.width), h: Math.round(r.height), r: Math.round(r.right), b: Math.round(r.bottom),
            sw: el.scrollWidth, cw: el.clientWidth, t: el.textContent.trim().slice(0, 60), ws: cs.whiteSpace });
        });
        return out;
      });
    }
  }
  if (flags.has('--measure')) fs.writeFileSync(path.join(outDir, 'measure.json'), JSON.stringify(measures));
  await browser.close();
})();
