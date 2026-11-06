// Baut Vorschaubilder aller Entwürfe: node tools/entwuerfe.mjs <ordner-mit-gebauten-seiten> <ziel>
import { chromium } from "playwright";
import { createServer } from "http";
import { readFileSync, existsSync, mkdirSync, writeFileSync } from "fs";
import { join, extname } from "path";

const [root, out] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const types = { ".html": "text/html", ".css": "text/css", ".js": "text/javascript", ".png": "image/png", ".json": "application/json" };
const server = createServer((req, res) => {
  const p = join(root, decodeURIComponent(req.url.split("?")[0]));
  if (!existsSync(p)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { "content-type": types[extname(p)] || "application/octet-stream" });
  res.end(readFileSync(p));
}).listen(8899);

const designs = { swiss: "1 · Swiss", magazin: "2 · Magazin", terminal: "3 · Terminal", kacheln: "4 · Kacheln", brief: "5 · Morgenbrief", klassik: "0 · Klassik (aktuell)" };
const b = await chromium.launch();
for (const [d, label] of Object.entries(designs)) {
  if (!existsSync(join(root, d, "index.html"))) continue;
  const shot = async (w, h, full, name) => {
    const p = await b.newPage({ viewport: { width: w, height: h } });
    await p.goto(`http://localhost:8899/${d}/index.html`, { waitUntil: "networkidle" });
    await p.waitForTimeout(800);
    await p.screenshot({ path: join(out, `${d}-${name}.png`), fullPage: full });
    await p.close();
  };
  await shot(1440, 900, true, "desktop");
  await shot(884, 1104, false, "fold-auf");
  await shot(384, 860, true, "fold-zu");
  const img = (n) => "data:image/png;base64," + readFileSync(join(out, `${d}-${n}.png`)).toString("base64");
  const html = `<html><body style="margin:0;background:#2a2a2a;font:600 28px system-ui;color:#fff">
  <div style="padding:24px 32px">${label}</div>
  <div style="display:flex;gap:32px;padding:0 32px 32px;align-items:flex-start">
    <div><div style="font-size:16px;opacity:.7;margin-bottom:8px">Desktop</div><div style="width:1200px;height:1500px;overflow:hidden;border-radius:8px"><img src="${img("desktop")}" style="width:1200px"></div></div>
    <div><div style="font-size:16px;opacity:.7;margin-bottom:8px">Fold aufgeklappt</div><img src="${img("fold-auf")}" style="width:600px;border-radius:8px;display:block"></div>
    <div><div style="font-size:16px;opacity:.7;margin-bottom:8px">Fold zugeklappt</div><div style="width:384px;height:1500px;overflow:hidden;border-radius:8px"><img src="${img("fold-zu")}" style="width:384px"></div></div>
  </div></body></html>`;
  const p = await b.newPage({ viewport: { width: 2300, height: 1640 } });
  await p.setContent(html);
  await p.screenshot({ path: join(out, `entwurf-${d}.png`) });
  await p.close();
  console.log("fertig", d);
}
await b.close();
server.close();
