// Build a single self-contained HTML file (JS + CSS + images inlined) that runs on any static host
// or independent domain without the Node backend. Gemini is then called directly from the browser
// using the key the user enters in the app (stored only in their browser).
//
//   npm run build:standalone   →  dist-standalone/index.html
import { build } from "esbuild";
import fs from "node:fs";
import path from "node:path";

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const outDir = path.join(root, "dist-standalone");
fs.mkdirSync(outDir, { recursive: true });

const result = await build({
  entryPoints: [path.join(root, "src/main.tsx")],
  bundle: true,
  minify: true,
  write: false,
  format: "esm",
  target: "es2020",
  jsx: "automatic",
  outdir: outDir,
  loader: { ".png": "dataurl" },
  define: { "process.env.NODE_ENV": '"production"', __STANDALONE__: "true" },
  nodePaths: (process.env.NODE_PATH || "").split(path.delimiter).filter(Boolean),
  logLevel: "warning"
});

let js = "";
let css = "";
for (const f of result.outputFiles) {
  if (f.path.endsWith(".js")) js += f.text;
  if (f.path.endsWith(".css")) css += f.text;
}

// Inline images referenced by absolute public paths ("/logo.png").
const pub = path.join(root, "public");
const dataUri = (name) => `data:image/png;base64,${fs.readFileSync(path.join(pub, name)).toString("base64")}`;
for (const name of fs.readdirSync(pub).filter((n) => n.endsWith(".png"))) {
  if (js.includes(`/${name}`)) js = js.split(`"/${name}"`).join(JSON.stringify(dataUri(name)));
}

let html = fs.readFileSync(path.join(root, "index.html"), "utf8");
html = html.replace(/<link rel="icon"[^>]*>/, `<link rel="icon" type="image/png" href="${dataUri("hub-favicon.png")}" />`);
html = html.replace(/<script type="module" src="\/src\/main.tsx"><\/script>/, () =>
  `<script type="module">${js.replace(/<\/script/gi, "<\\/script")}</script>`
);
html = html.replace("</head>", () => `<style>${css}</style>\n  </head>`);

fs.writeFileSync(path.join(outDir, "index.html"), html);
console.log(`✓ dist-standalone/index.html (${(html.length / 1024).toFixed(0)} KB)`);
