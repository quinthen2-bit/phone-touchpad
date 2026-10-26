"""Phone Touchpad - teken met je telefoon op je pc.

Start een kleine webserver op je lokale netwerk. Scan de QR-code met je telefoon,
je ziet dan een screenshot van je pc waarop je kunt tekenen. Na het loslaten van je
vinger wordt de hele streek in één request naar de pc gestuurd en daar getekend
met ingedrukte muisknop.
"""

import logging
import math
import os
import secrets
import socket
import sys
import threading
import time
import tkinter as tk
from io import BytesIO
from urllib.parse import quote

import pyautogui
import qrcode
from flask import Flask, abort, jsonify, render_template_string, request, send_file

# ---------------- Configuration ----------------
PORT = 8765
HOST = "0.0.0.0"
TOKEN = secrets.token_urlsafe(24)
STEP_DELAY = 0.002      # pauze tussen punten op de pc (sec); hoger = rustiger/nauwkeuriger tekenen
STEP_PX = 3             # max. afstand (px) tussen twee muispunten op de pc; 0 = niet aanvullen
SMOOTH_WINDOW = 3       # gemiddelde over n punten tegen trillende vinger; 1 = uit (alleen oneven getallen)
MAX_POINTS = 5000       # veiligheidslimiet per streek (ontvangen punten)
MAX_TOTAL_POINTS = 20000  # veiligheidslimiet na aanvullen
FRAME = 14              # dikte van de witte rand (px)
TAB_H = 38              # hoogte van de tabjes (X en titel)
X_W = 52                # breedte van het X-tabje
TITLE_W = 210           # breedte van het titel-tabje
R_OUT = 26              # ronding buitenkant van de rand
R_IN = 16               # ronding binnenkant van de rand
R_TAB = 16              # ronding van de tabjes
KEY = "#010101"         # transparante kleur (Windows)
FRAME_ALPHA = 0.75      # doorzichtigheid van de witte rand: 1.0 = ondoorzichtig, 0.3 = bijna onzichtbaar
REFRESH_MS = 8000       # automatisch screenshot vernieuwen (ms); 0 = alleen met de knop

pyautogui.PAUSE = 0

app = Flask(__name__)
# Geen "POST /api/..." regels meer in de cmd
logging.getLogger("werkzeug").setLevel(logging.ERROR)

draw_lock = threading.Lock()
connected = threading.Event()   # wordt gezet zodra de telefoon de pagina opent
screen_width, screen_height = pyautogui.size()

PAGE = r"""
<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<title>Phone Touchpad</title>
<style>
:root { color-scheme: dark; font-family: system-ui, sans-serif; }
* { box-sizing: border-box; }
html, body { margin:0; height:100%; }
body { background:#101218; color:#f5f6fa; height:100dvh;
       display:flex; flex-direction:column; padding:8px; gap:7px; overflow:hidden; }
p { color:#b8bfce; margin:0; font-size:.78rem; }
#stage { position:relative; flex:1; min-height:0; background:#080a0e;
         border:1px solid #343b4b; border-radius:10px; overflow:hidden; }
#preview, #overlay { position:absolute; inset:0; width:100%; height:100%; }
#preview { object-fit:contain; pointer-events:none; }
#overlay { touch-action:none; user-select:none; -webkit-user-select:none; }
.row { display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; }
button { border:0; border-radius:12px; padding:12px 6px; background:#343c50;
         color:white; font-size:.9rem; font-weight:600; touch-action:manipulation; }
button:active { background:#53617f; }
#status { min-height:1.3em; font-size:.85rem; color:#aeb9ce; }
/* Mini-balk: zit IN het (gedraaide) vlak, dus tekst staat goed als je je telefoon kantelt */
#miniBar { display:none; position:absolute; top:6px; left:6px; z-index:5;
           align-items:center; gap:6px; }
#miniBar button { padding:7px 11px; font-size:.85rem; opacity:.7; border-radius:10px; }
#miniStatus { font-size:.75rem; color:#e3e8f5; background:rgba(0,0,0,.55);
              padding:3px 8px; border-radius:8px; }
body.rotated { padding:0; }
body.rotated #hint, body.rotated #controls { display:none; }
body.rotated #stage { border:0; border-radius:0; }
body.rotated #miniBar { display:flex; }
</style>
</head>
<body>
<p id="hint">Teken met je vinger direct op de screenshot. Zodra je loslaat wordt de hele streek in één keer op je pc getekend (muisknop ingedrukt).</p>
<div id="stage">
  <img id="preview" alt="Screenshot van je pc-scherm">
  <canvas id="overlay"></canvas>
  <div id="miniBar">
    <button id="miniRefresh">Vernieuw</button>
    <button id="miniRotate">Draai</button>
    <button id="miniFull">Volledig</button>
    <span id="miniStatus"></span>
  </div>
</div>
<div id="controls">
  <div class="row">
    <button id="refreshBtn">Vernieuwen</button>
    <button id="rotateBtn">Draai</button>
    <button id="fullBtn">Volledig scherm</button>
  </div>
  <div id="status">Verbonden met je pc.</div>
</div>
<script>
const token = {{ token|tojson }};
const refreshMs = {{ refresh_ms|tojson }};
const screenW = {{ screen_w|tojson }};
const screenH = {{ screen_h|tojson }};
const stage = document.getElementById('stage');
const preview = document.getElementById('preview');
const canvas = document.getElementById('overlay');
const ctx = canvas.getContext('2d');
const statusEl = document.getElementById('status');
const miniStatus = document.getElementById('miniStatus');

let stopped = false;
let drawing = false;
let busy = false;           // bezig met versturen/tekenen op pc
let clearAfterLoad = false;
let points = [];            // genormaliseerde punten [x, y] van de huidige streek
let lastPx = null;
let lastUrl = null;
let rot = 0;                // 0 = normaal, 90 = zijwaarts (rechtsom), 270 = zijwaarts (linksom)

function setStatus(t) { statusEl.textContent = t; miniStatus.textContent = t; }
setStatus('Verbonden met je pc.');

function resizeCanvas() {
  canvas.width = stage.clientWidth;
  canvas.height = stage.clientHeight;
}

function applyLayout() {
  const W = window.innerWidth, H = window.innerHeight;
  document.body.classList.toggle('rotated', rot !== 0);
  if (rot === 0) {
    stage.style.cssText = '';
  } else {
    stage.style.position = 'fixed';
    stage.style.top = '0';
    stage.style.left = '0';
    stage.style.flex = 'none';
    stage.style.width = H + 'px';     // gedraaid vlak: breedte = schermhoogte
    stage.style.height = W + 'px';
    stage.style.transformOrigin = '0 0';
    stage.style.transform = rot === 90
      ? 'translate(' + W + 'px,0) rotate(90deg)'
      : 'translate(0,' + H + 'px) rotate(-90deg)';
  }
  resizeCanvas();
}
window.addEventListener('resize', applyLayout);
window.addEventListener('orientationchange', () => setTimeout(applyLayout, 150));
applyLayout();

function rotate() {
  rot = rot === 0 ? 90 : (rot === 90 ? 270 : 0);
  applyLayout();
}

async function goFullscreen() {
  try {
    await document.documentElement.requestFullscreen();
    try {
      await screen.orientation.lock('landscape');
      rot = 0;
      applyLayout();
      setStatus('Volledig scherm, liggend.');
    } catch (_) {
      setStatus('Volledig scherm. Gebruik Draai voor zijwaarts.');
    }
  } catch (_) {
    setStatus('Volledig scherm wordt niet ondersteund in deze browser.');
  }
}

// Het echte gebied waar de screenshot getekend wordt (object-fit: contain)
function imageBox() {
  const W = canvas.width, H = canvas.height;
  // Altijd de echte schermverhouding van de pc gebruiken, ook voordat de screenshot geladen is
  const nw = screenW, nh = screenH;
  const s = Math.min(W / nw, H / nh);
  const w = nw * s, h = nh * s;
  return { x: (W - w) / 2, y: (H - h) / 2, w, h };
}

// Scherm-coördinaten -> lokale coördinaten van het (eventueel gedraaide) vlak
function toLocal(e) {
  if (rot === 90)  return { x: e.clientY, y: window.innerWidth - e.clientX };
  if (rot === 270) return { x: window.innerHeight - e.clientY, y: e.clientX };
  const r = stage.getBoundingClientRect();
  return { x: e.clientX - r.left, y: e.clientY - r.top };
}

function pointFromEvent(e) {
  const { x: px, y: py } = toLocal(e);
  const b = imageBox();
  return {
    px, py,
    nx: Math.max(0, Math.min(1, (px - b.x) / b.w)),
    ny: Math.max(0, Math.min(1, (py - b.y) / b.h))
  };
}

async function refreshPreview() {
  if (drawing || busy || stopped) return;
  try {
    const response = await fetch('/screen.jpg?token=' + encodeURIComponent(token) + '&t=' + Date.now());
    if (response.status === 403) {
      stopped = true;
      setStatus('Sessie verlopen. Scan de QR-code opnieuw.');
      return;
    }
    if (!response.ok) return;
    const url = URL.createObjectURL(await response.blob());
    preview.onload = () => {
      if (lastUrl) URL.revokeObjectURL(lastUrl);
      lastUrl = url;
      if (clearAfterLoad) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        clearAfterLoad = false;
      }
    };
    preview.src = url;
  } catch (_) {}
}
refreshPreview();
if (refreshMs > 0) setInterval(refreshPreview, refreshMs);

for (const id of ['refreshBtn', 'miniRefresh']) document.getElementById(id).addEventListener('click', refreshPreview);
for (const id of ['rotateBtn', 'miniRotate']) document.getElementById(id).addEventListener('click', rotate);
for (const id of ['fullBtn', 'miniFull']) document.getElementById(id).addEventListener('click', goFullscreen);

async function sendStroke(pts) {
  busy = true;
  setStatus('Bezig met tekenen op pc...');
  try {
    const response = await fetch('/api/stroke?token=' + encodeURIComponent(token), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ points: pts })
    });
    if (!response.ok) throw new Error('HTTP ' + response.status);
    setStatus('Getekend.');
  } catch (e) {
    setStatus('Verbinding verbroken. Controleer wifi en firewall.');
  }
  busy = false;
  clearAfterLoad = true;      // eigen rode lijn weg zodra de nieuwe screenshot er is
  refreshPreview();
}

canvas.addEventListener('pointerdown', e => {
  if (busy) return;
  e.preventDefault();
  canvas.setPointerCapture(e.pointerId);
  drawing = true;
  const p = pointFromEvent(e);
  points = [[p.nx, p.ny]];
  lastPx = p;
  ctx.strokeStyle = '#ff3b3b';
  ctx.lineWidth = 3;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.beginPath();
  ctx.moveTo(p.px, p.py);
});

canvas.addEventListener('pointermove', e => {
  if (!drawing) return;
  e.preventDefault();
  const events = e.getCoalescedEvents ? e.getCoalescedEvents() : [e];
  for (const ev of (events.length ? events : [e])) {
    const p = pointFromEvent(ev);
    // alleen opslaan als de vinger écht bewogen is (minder data)
    if (Math.hypot(p.px - lastPx.px, p.py - lastPx.py) < 1.0) continue;
    points.push([+p.nx.toFixed(5), +p.ny.toFixed(5)]);
    ctx.lineTo(p.px, p.py);
    ctx.stroke();
    lastPx = p;
  }
});

function endPointer(e) {
  if (!drawing) return;
  e.preventDefault();
  drawing = false;
  const pts = points;
  points = [];
  if (pts.length) sendStroke(pts);   // één request voor de hele streek
}
canvas.addEventListener('pointerup', endPointer);
canvas.addEventListener('pointercancel', endPointer);
window.addEventListener('contextmenu', e => e.preventDefault());
</script>
</body>
</html>
"""


def local_ip():
    """Find the LAN address used to reach the internet/router."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("192.0.2.1", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def authorized():
    if request.args.get("token", "") != TOKEN:
        abort(403)


@app.get("/")
def index():
    authorized()
    connected.set()
    return render_template_string(PAGE, token=TOKEN, refresh_ms=REFRESH_MS,
                                  screen_w=screen_width, screen_h=screen_height)


@app.get("/screen.jpg")
def screen_jpg():
    authorized()
    image = pyautogui.screenshot().convert("RGB")
    output = BytesIO()
    image.save(output, format="JPEG", quality=75)
    output.seek(0)
    response = send_file(output, mimetype="image/jpeg")
    response.headers["Cache-Control"] = "no-store"
    return response


def smooth_points(pts, window):
    """Glad de lijn met een voortschrijdend gemiddelde; begin- en eindpunt blijven exact."""
    if window < 3 or len(pts) < 3:
        return pts
    half = window // 2
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        h = min(half, i, len(pts) - 1 - i)
        seg = pts[i - h:i + h + 1]
        out.append((sum(p[0] for p in seg) / len(seg), sum(p[1] for p in seg) / len(seg)))
    out.append(pts[-1])
    return out


def densify(pts, step):
    """Vul grote sprongen (snelle vingerbewegingen) aan met tussenpunten."""
    if step <= 0:
        return pts
    out = [pts[0]]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        dist = math.hypot(x1 - x0, y1 - y0)
        for k in range(1, int(dist // step) + 1):
            t = k * step / dist
            out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
        out.append((x1, y1))
    return out


def draw_stroke(points):
    """Muisknop in, alle punten volgen, muisknop los."""
    with draw_lock:
        old_failsafe = pyautogui.FAILSAFE
        pyautogui.FAILSAFE = False  # voorkomt dat de muisknop blijft hangen bij een scherm-hoek
        try:
            pyautogui.moveTo(points[0][0], points[0][1], duration=0)
            pyautogui.mouseDown()
            time.sleep(0.01)
            for px, py in points[1:]:
                # dragTo geeft echte "drag"-events (nodig op macOS); op Windows hetzelfde als moveTo
                pyautogui.dragTo(px, py, duration=0, button="left", mouseDownUp=False)
                time.sleep(STEP_DELAY)
        finally:
            pyautogui.mouseUp()
            pyautogui.FAILSAFE = old_failsafe


@app.post("/api/stroke")
def stroke():
    authorized()
    data = request.get_json(silent=True) or {}
    raw = data.get("points")
    if not isinstance(raw, list) or not raw:
        return jsonify(error="Geen punten"), 400

    pts = []
    try:
        for p in raw[:MAX_POINTS]:
            x = max(0.0, min(1.0, float(p[0])))
            y = max(0.0, min(1.0, float(p[1])))
            pts.append((x * max(0, screen_width - 1), y * max(0, screen_height - 1)))
    except (IndexError, KeyError, TypeError, ValueError):
        return jsonify(error="Ongeldige coördinaten"), 400

    pts = densify(smooth_points(pts, SMOOTH_WINDOW), STEP_PX)
    if len(pts) > MAX_TOTAL_POINTS:
        pts = pts[::math.ceil(len(pts) / MAX_TOTAL_POINTS)]

    # Afronden, binnen de witte rand blijven en de X/titel-tabjes nooit aanraken
    points = []
    for x, y in pts:
        pt = (max(FRAME, min(screen_width - 1 - FRAME, round(x))),
              max(FRAME, min(screen_height - 1 - FRAME, round(y))))
        if in_tab(*pt) or (points and points[-1] == pt):
            continue
        points.append(pt)
    if not points:
        return jsonify(ok=True, points=0)

    draw_stroke(points)  # klaar pas als de streek getekend is
    return jsonify(ok=True, points=len(points))


# ---------------- Witte rand om het scherm ----------------
def tab_rects():
    x_rect = (0, 0, X_W, TAB_H)
    title_rect = ((screen_width - TITLE_W) // 2, 0, (screen_width + TITLE_W) // 2, TAB_H)
    return x_rect, title_rect


def in_tab(px, py):
    return any(x1 <= px <= x2 and y1 <= py <= y2 for x1, y1, x2, y2 in tab_rects())


def make_window(root, x, y, w, h):
    win = tk.Toplevel(root)
    win.overrideredirect(True)
    win.attributes("-topmost", True)
    win.attributes("-alpha", FRAME_ALPHA)
    win.configure(bg="white")
    win.geometry(f"{w}x{h}+{x}+{y}")
    return win


def show_frame_strips(root):
    """(Fallback voor niet-Windows) Vier smalle randen + titel-tab + X-tab. Het midden blijft helemaal vrij."""
    W, H = screen_width, screen_height
    wins = [
        make_window(root, 0, 0, W, FRAME),             # boven
        make_window(root, 0, H - FRAME, W, FRAME),     # onder
        make_window(root, 0, 0, FRAME, H),             # links
        make_window(root, W - FRAME, 0, FRAME, H),     # rechts
    ]

    x_rect, title_rect = tab_rects()

    title = make_window(root, title_rect[0], 0, title_rect[2] - title_rect[0], TAB_H)
    tk.Label(title, text="Phone Touchpad", bg="white", fg="black",
             font=("Helvetica", 16, "bold")).pack(expand=True, fill="both")
    wins.append(title)

    close = make_window(root, 0, 0, X_W, TAB_H)
    x_label = tk.Label(close, text="X", bg="white", fg="black",
                       font=("Helvetica", 18, "bold"), cursor="hand2")
    x_label.pack(expand=True, fill="both")
    x_label.bind("<Button-1>", lambda e: os._exit(0))   # afsluiten
    wins.append(close)
    return wins


def rounded_rect(cv, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return cv.create_polygon(pts, smooth=True, **kw)


def show_frame_win(root):
    """Windows: één venster waarvan het midden transparant (en doorklikbaar) is."""
    W, H = screen_width, screen_height
    win = tk.Toplevel(root)
    win.overrideredirect(True)
    win.attributes("-topmost", True)
    win.configure(bg=KEY)
    win.attributes("-transparentcolor", KEY)
    win.attributes("-alpha", FRAME_ALPHA)
    win.geometry(f"{W}x{H}+0+0")

    cv = tk.Canvas(win, width=W, height=H, bg=KEY, highlightthickness=0, bd=0)
    cv.pack(fill="both", expand=True)

    # witte rand met ronde buiten- en binnenhoeken
    rounded_rect(cv, 0, 0, W, H, R_OUT, fill="white", outline="white")
    rounded_rect(cv, FRAME, FRAME, W - FRAME, H - FRAME, R_IN, fill=KEY, outline=KEY)

    x_rect, t_rect = tab_rects()

    # titel-tab: bovenkant buiten beeld, onderhoeken rond
    rounded_rect(cv, t_rect[0], -R_TAB, t_rect[2], TAB_H, R_TAB, fill="white", outline="white")
    cv.create_text((t_rect[0] + t_rect[2]) // 2, TAB_H // 2, text="Phone Touchpad",
                   font=("Segoe UI", 13, "bold"), fill="black")

    # X-tab: alleen de rechteronderhoek is rond
    rounded_rect(cv, -R_TAB, -R_TAB, X_W, TAB_H, R_TAB, fill="white", outline="white", tags="close")
    cv.create_text(X_W // 2 - 3, TAB_H // 2, text="X",
                   font=("Segoe UI", 15, "bold"), fill="black", tags="close")
    cv.tag_bind("close", "<Button-1>", lambda e: os._exit(0))   # afsluiten
    return [win]


def show_frame(root):
    if sys.platform == "win32":
        return show_frame_win(root)
    return show_frame_strips(root)


def wait_for_phone(root):
    """Wacht tot de telefoon verbonden is; sluit dan het QR-venster en toon de rand."""
    if connected.is_set():
        root.withdraw()
        root.frame_windows = show_frame(root)   # referentie bewaren
    else:
        root.after(300, lambda: wait_for_phone(root))


def start_server():
    # Only reachable from the local network; don't expose this port on the internet.
    app.run(host=HOST, port=PORT, debug=False, threaded=True, use_reloader=False)


def main():
    ip = local_ip()
    url = f"http://{ip}:{PORT}/?token={quote(TOKEN)}"

    root = tk.Tk()
    root.title("Phone Touchpad")
    root.geometry("460x600")
    root.minsize(420, 540)
    root.configure(bg="#151922")

    tk.Label(root, text="Phone Touchpad", bg="#151922", fg="white",
             font=("Segoe UI", 20, "bold")).pack(pady=(18, 4))
    tk.Label(root, text="Scan deze QR-code met je telefoon",
             bg="#151922", fg="#c5cada", font=("Segoe UI", 11)).pack()

    qr_img = qrcode.make(url).convert("RGB").resize((260, 260))
    from PIL import ImageTk
    # Keep a reference so Tkinter doesn't discard the image.
    root.qr_photo = ImageTk.PhotoImage(qr_img)
    tk.Label(root, image=root.qr_photo, bg="white", padx=8, pady=8).pack(pady=14)

    tk.Label(root, text=url, bg="#151922", fg="#78dce8",
             wraplength=420, justify="center", font=("Consolas", 9)).pack(padx=12)

    tk.Label(root, text=f"Server actief op {ip}:{PORT}",
             bg="#151922", fg="#9fe3b0", font=("Segoe UI", 10)).pack(pady=12)

    tk.Label(root, text="Teken met je vinger op de screenshot op je telefoon. Na loslaten wordt de streek in één keer op de pc getekend.",
             bg="#151922", fg="#c5cada", wraplength=420, justify="center").pack(pady=(8, 14))

    threading.Thread(target=start_server, daemon=True).start()
    root.after(300, lambda: wait_for_phone(root))
    root.mainloop()


if __name__ == "__main__":
    main()
