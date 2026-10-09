/**
 * Jolly VN chapter server (prototype).
 *
 * Host-side only: no emulator source is modified. The server
 *   1. serves the self-hosted WebNP2-style player page + disk images,
 *   2. accepts the player's Chapter 1 choice + run log at the chapter
 *      boundary (POST /api/chapter),
 *   3. generates a branch Chapter 2 (real Suika NovelML), packs it
 *      into a data floppy (.xdf, for the FDD2 hot-swap [load]) and a
 *      reboot hard disk (.thd whose start.novel is Chapter 2),
 *      appends the run to data/run-log.jsonl, and returns the URLs.
 *
 * Start:  node server.mjs            (http://localhost:4173)
 * Port:   PORT env, default 4173.
 */
import { createServer } from "node:http";
import { readFile, writeFile, appendFile, mkdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.PORT || 4173);
const RUN_LOG = path.join(ROOT, "data", "run-log.jsonl");

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".novel": "text/plain; charset=utf-8",
  ".png": "image/png",
  ".webp": "image/webp",
  ".jpg": "image/jpeg",
  ".md": "text/markdown; charset=utf-8",
};

function cors(res) {
  // Disk images may be hosted cross-origin in production; the player
  // fetches hdd=/fd1= URLs, so images must allow CORS (Phase 2 note).
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
}

function sendJson(res, status, obj) {
  cors(res);
  const body = JSON.stringify(obj, null, 2);
  res.writeHead(status, { "Content-Type": "application/json; charset=utf-8" });
  res.end(body);
}

const CHAPTERS = {
  ringo: {
    chapterId: "ch02-ringo",
    title: "Chapter 2 - Shrine Morning (apple candy)",
    dosName: "CH02-RIN.NOV",
    source: "game/ch02-ringo.novel",
    preview: [
      "Shrine morning after the apple-candy choice (bg: shrine, then rooftop).",
      "Second choice: make a wish vs. follow the pawprints.",
      "Two endings, both completable.",
    ],
  },
  wataame: {
    chapterId: "ch02-wataame",
    title: "Chapter 2 - Lake Morning (cotton candy)",
    dosName: "CH02-WAT.NOV",
    source: "game/ch02-wataame.novel",
    preview: [
      "Lake morning after the cotton-candy choice (bg: lake, then ramen shop).",
      "Second choice: skip a stone vs. sit with the mist.",
      "Two endings, both completable.",
    ],
  },
};

async function handleChapter(req, res) {
  let raw = "";
  req.on("data", (c) => (raw += c));
  req.on("end", async () => {
    let payload;
    try {
      payload = JSON.parse(raw || "{}");
    } catch {
      return sendJson(res, 400, { error: "Invalid JSON body." });
    }
    const choiceId = payload.choiceId;
    if (choiceId !== "ringo" && choiceId !== "wataame") {
      return sendJson(res, 400, { error: "choiceId must be 'ringo' or 'wataame'.", got: choiceId ?? null });
    }
    const meta = CHAPTERS[choiceId];
    const createdAt = new Date().toISOString();
    const runId = "run-" + createdAt.replace(/[:.]/g, "-") + "-" + choiceId;
    // Real-emulation packing: stamp the hand-written branch script with
    // the run id, then pack REAL FAT images with the repo tools (no
    // JSON disks, no emulator code touched).
    const srcNovel = await readFile(path.join(ROOT, meta.source), "utf8");
    const stamped = `# Generated run ${runId} at ${createdAt} choice=${choiceId}\n` + srcNovel;
    const buildDir = path.join(ROOT, "build");
    const genRoot = path.join(buildDir, `gen-${runId}`);
    await mkdir(genRoot, { recursive: true });
    await mkdir(path.join(ROOT, "disks-real", "generated"), { recursive: true });
    await mkdir(path.join(ROOT, "data"), { recursive: true });
    const tmpNovel = path.join(buildDir, `generated-${meta.chapterId}.novel`);
    await writeFile(tmpNovel, stamped, "utf8");
    // Stage a game tree whose start.novel is the generated chapter so
    // its assets.arc boots straight into Chapter 2 (reboot path). The
    // same stamped file also goes on the data floppy under its 8.3
    // name for the in-game [load file="B:/..."] hot-swap path.
    const { cp } = await import("node:fs/promises");
    await cp(path.join(ROOT, "game", "images"), path.join(genRoot, "images"), { recursive: true });
    await cp(path.join(ROOT, "game", "system"), path.join(genRoot, "system"), { recursive: true });
    await cp(path.join(ROOT, "game", "config.ini"), path.join(genRoot, "config.ini"));
    await cp(path.join(ROOT, "game", "main.ray"), path.join(genRoot, "main.ray"));
    await writeFile(path.join(genRoot, "start.novel"), stamped, "utf8");
    const genArc = path.join(genRoot, "assets.arc");
    const { execFile } = await import("node:child_process");
    const run = (args) => new Promise((resolve, reject) =>
      execFile("python3", args, { cwd: ROOT }, (e, stdout, stderr) => e ? reject(new Error(stderr || stdout || String(e))) : resolve(stdout)));
    const fdiName = `${meta.chapterId}-${runId}.xdf`;
    const rebootName = `reboot-${meta.chapterId}-${runId}.thd`;
    try {
      await run(["tools/pack_assets.py", "--out", genArc, "--root", genRoot,
        "config.ini", "start.novel", "main.ray", "images", "system"]);
      await run(["tools/build_disk.py", "fd", "--out", `disks-real/generated/${fdiName}`,
        "--add", `${tmpNovel}=${meta.dosName}`]);
      await run(["tools/build_disk.py", "thd", "--out", `disks-real/generated/${rebootName}`,
        "--add", "engine/SUIKA3-98.EXE=SUIKA-98.EXE", "--add", `${genArc}=ASSETS.ARC`,
        "--add", "game/config.ini=CONFIG.INI", "--add", "game/main.ray=MAIN.RAY",
        "--add", `${tmpNovel}=START.NOV`, "--add", `${tmpNovel}=${meta.dosName}`,
        "--add", "vendor/DOS4GW.EXE=DOS4GW.EXE"]);
    } catch (e) {
      return sendJson(res, 500, { error: "Disk packing failed: " + e.message });
    }
    const logLine = {
      runId, createdAt, endpoint: "POST /api/chapter",
      choiceId, chapterId: meta.chapterId,
      runLog: payload.runLog ?? [],
      fdi: `disks-real/generated/${fdiName}`,
      reboot: `disks-real/generated/${rebootName}`,
    };
    await appendFile(RUN_LOG, JSON.stringify(logLine) + "\n", "utf8");
    sendJson(res, 200, {
      ok: true,
      runId,
      choiceId,
      chapterId: meta.chapterId,
      title: meta.title,
      fdiUrl: `/disks-real/generated/${fdiName}`,
      rebootUrl: `/disks-real/generated/${rebootName}`,
      novelPathInDisk: meta.dosName,
      preview: meta.preview,
      beats: stamped.split("\n").filter((l) => l.startsWith("[text")).length,
    });
  });
}

const server = createServer(async (req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);
  if (req.method === "OPTIONS") { cors(res); res.writeHead(204); return res.end(); }
  if (url.pathname === "/api/health") return sendJson(res, 200, { ok: true, service: "jolly-vn-chapter-server", port: PORT });
  if (url.pathname === "/api/chapter" && req.method === "POST") return handleChapter(req, res);
  if (req.method !== "GET" && req.method !== "HEAD") return sendJson(res, 405, { error: "Method not allowed." });

  let pathname = decodeURIComponent(url.pathname);
  if (pathname === "/") pathname = "/index.html";
  if (pathname.endsWith("/")) pathname += "index.html";
  const filePath = path.join(ROOT, pathname);
  if (!filePath.startsWith(ROOT)) { res.writeHead(403); return res.end("Forbidden"); }
  if (!existsSync(filePath)) { cors(res); res.writeHead(404, { "Content-Type": "text/plain" }); return res.end("Not found: " + pathname); }
  try {
    const data = await readFile(filePath);
    cors(res);
    res.writeHead(200, { "Content-Type": MIME[path.extname(filePath)] || "application/octet-stream" });
    res.end(req.method === "HEAD" ? undefined : data);
  } catch (err) {
    res.writeHead(500); res.end(String(err));
  }
});

server.listen(PORT, () => {
  console.log(`Jolly VN prototype: http://localhost:${PORT}/`);
  console.log(`Chapter API: POST http://localhost:${PORT}/api/chapter  {choiceId: "ringo"|"wataame"}`);
});
