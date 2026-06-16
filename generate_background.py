#!/usr/bin/env python3
"""
Fondo animado regional mexicano — 1920x1080, 20s loop.
Desierto con cactos, mesas, nubes en movimiento y aves.
"""
import math, io, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter

FFMPEG = "/home/user/Remotion-code/node_modules/@remotion/compositor-linux-x64-gnu/ffmpeg"
OUTPUT = "/home/user/Remotion-code/public/fondo_regional.mp4"
W, H   = 1920, 1080
FPS    = 30
DUR    = 20          # segundos — loop perfecto
FRAMES = FPS * DUR   # 600 frames

HORIZON = 520        # y donde cielo toca desierto

# ── Paleta ────────────────────────────────────────────────────────────────────
SKY_TOP      = ( 58, 110, 175)
SKY_MID      = ( 98, 162, 210)
SKY_HOR      = (200, 180, 148)
HAZE         = (215, 198, 165)
MTN_FAR_L    = (158, 122, 102)
MTN_FAR_D    = (128,  96,  76)
MTN_MID_L    = (172, 132, 100)
MTN_MID_D    = (138, 100,  72)
MTN_ROCK_L   = (198, 160, 118)
MTN_ROCK_D   = (148, 108,  76)
DST_FAR      = (200, 172, 122)
DST_MID      = (210, 178, 112)
DST_NEAR     = (220, 185, 105)
DST_SHADOW   = (185, 152,  90)
CACTUS_D     = ( 44,  78,  38)
CACTUS_L     = ( 62, 105,  52)
CACTUS_SPEC  = ( 80, 128,  66)
CLOUD_W      = (252, 252, 250)
CLOUD_S      = (215, 218, 225)
BIRD         = ( 38,  38,  48)

# ── Helpers ───────────────────────────────────────────────────────────────────

def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

def draw_hline_gradient(draw, y0, y1, c0, c1):
    for y in range(y0, y1):
        t = (y - y0) / max(y1 - y0 - 1, 1)
        draw.line([(0, y), (W, y)], fill=lerp(c0, c1, t))

# ── Escena estática (se renderiza una vez) ────────────────────────────────────

def build_static():
    img = Image.new("RGB", (W, H))
    d   = ImageDraw.Draw(img)

    # Cielo — gradiente 3 paradas
    mid = int(HORIZON * 0.45)
    draw_hline_gradient(d, 0,   mid,     SKY_TOP, SKY_MID)
    draw_hline_gradient(d, mid, HORIZON, SKY_MID, SKY_HOR)

    # Neblina en el horizonte
    draw_hline_gradient(d, HORIZON - 30, HORIZON + 30, HAZE, DST_FAR)

    # Desierto — gradiente
    draw_hline_gradient(d, HORIZON, H, DST_FAR, DST_NEAR)

    # ── Mesas lejanas (izquierda) ─────────────────────────────────────────
    _mesa(d,  80, HORIZON - 10, 320, 160, MTN_FAR_L, MTN_FAR_D)
    _mesa(d, 340, HORIZON +  5, 240, 120, MTN_FAR_L, MTN_FAR_D)

    # Mesa grande central-izquierda
    _mesa(d, 120, HORIZON + 20, 480, 200, MTN_MID_L, MTN_MID_D)

    # Rocas pequeñas centro y derecha
    _mesa(d, 900, HORIZON + 10, 160,  80, MTN_ROCK_L, MTN_ROCK_D)
    _mesa(d,1100, HORIZON +  5, 100,  55, MTN_ROCK_L, MTN_ROCK_D)
    _mesa(d,1550, HORIZON +  8, 220, 110, MTN_FAR_L,  MTN_FAR_D)
    _mesa(d,1700, HORIZON +  2, 150,  70, MTN_FAR_L,  MTN_FAR_D)

    # ── Piedras en el suelo ───────────────────────────────────────────────
    for rx, ry, rw, rh in [
        (300, 700, 80, 35), (640, 780, 55, 22), (1200, 660, 90, 38),
        (1500, 750, 70, 28), (800, 850, 110, 40), (1750, 820, 65, 25),
        (150, 900, 95, 32), (1050, 900, 75, 28),
    ]:
        d.ellipse([rx, ry, rx+rw, ry+rh], fill=DST_SHADOW)
        d.ellipse([rx+6, ry+4, rx+rw-4, ry+rh-6], fill=DST_MID)

    # ── Cactus ────────────────────────────────────────────────────────────
    # Saguaro grande izquierda
    _saguaro(d,  480, H - 50, 1.30)
    # Saguaro grande derecha
    _saguaro(d, 1440, H - 30, 1.50)
    # Saguaro mediano
    _saguaro(d,  820, H - 80, 0.85)
    _saguaro(d, 1120, H - 70, 0.70)
    # Pequeños al fondo
    _saguaro(d,  220, HORIZON + 60, 0.35)
    _saguaro(d,  680, HORIZON + 50, 0.30)
    _saguaro(d, 1300, HORIZON + 55, 0.32)
    _saguaro(d, 1650, HORIZON + 45, 0.28)
    _saguaro(d, 1820, HORIZON + 70, 0.40)

    # Suavizar horizonte con leve blur
    img = img.filter(ImageFilter.GaussianBlur(radius=0.4))
    return img

def _mesa(d, x, base, w, h, c_light, c_dark):
    cx  = x + w // 2
    tw  = int(w * 0.72)
    top = base - h
    # Cara principal (lit)
    d.polygon([
        (x,            base),
        (cx - tw // 2, top),
        (cx + tw // 2, top),
        (x + w,        base),
    ], fill=c_light)
    # Cara oscura (sombra derecha)
    d.polygon([
        (cx,           top),
        (cx + tw // 2, top),
        (x + w,        base),
        (x + int(w*0.58), base),
    ], fill=c_dark)
    # Línea superior (arista)
    d.line([(cx - tw//2, top), (cx + tw//2, top)], fill=lerp(c_light, (255,255,255), 0.15), width=2)

def _saguaro(d, cx, base, s=1.0):
    tw = max(int(28 * s), 4)
    th = int(260 * s)
    top = base - th

    def rect(x0, y0, x1, y1, fill):
        if x1 > x0 and y1 > y0:
            d.rectangle([x0, y0, x1, y1], fill=fill)

    # Tronco
    rect(cx - tw, top, cx + tw, base, CACTUS_D)
    rect(cx - tw//2, top, cx, base, CACTUS_L)
    rect(cx - tw//4, top, cx + tw//4, base, CACTUS_SPEC)

    # Brazo izquierdo
    ay1  = top + int(70 * s)
    aex  = cx - int(90 * s)
    atop = ay1 - int(85 * s)
    aw   = max(int(18 * s), 3)
    rect(aex, ay1 - aw, cx - tw, ay1 + aw, CACTUS_D)
    rect(aex - aw, atop, aex + aw, ay1, CACTUS_D)
    rect(aex - aw//2, atop, aex, ay1, CACTUS_L)

    # Brazo derecho
    ay2  = top + int(105 * s)
    aex2 = cx + int(80 * s)
    atop2= ay2 - int(70 * s)
    rect(cx + tw, ay2 - aw, aex2, ay2 + aw, CACTUS_D)
    rect(aex2 - aw, atop2, aex2 + aw, ay2, CACTUS_D)
    rect(aex2, atop2, aex2 + aw//2, ay2, CACTUS_L)

# ── Nubes (posición y tamaño fijos, solo se mueven en x) ─────────────────────
CLOUDS = [
    # (x_start, y, w, h, speed_px_per_frame, alpha)
    (  200, 100, 340, 90, 0.28, 1.00),
    (  700, 155, 260, 72, 0.20, 0.90),
    ( 1200,  80, 310, 85, 0.24, 0.95),
    ( 1600, 130, 200, 58, 0.18, 0.85),
    ( -150, 200, 180, 50, 0.15, 0.80),
    (  450, 240, 140, 40, 0.12, 0.70),
    ( 1050, 210, 160, 45, 0.14, 0.75),
]

def draw_cloud(d, cx, y, w, h, alpha):
    a = int(255 * alpha)
    # Sombra inferior
    d.ellipse([cx + w//8, y + int(h*0.55), cx + int(w*0.9), y + int(h*1.15)], fill=CLOUD_S)
    # Puffs principales
    for dx, dy, ew, eh in [
        (0,        0,        w,        h       ),
        (w//5,    -h//4,    int(w*0.75), int(h*0.8)),
        (int(w*0.5), 0,     int(w*0.65), int(h*0.72)),
        (int(w*0.72), h//8, int(w*0.42), int(h*0.60)),
        (-w//8,    h//8,    int(w*0.40), int(h*0.58)),
    ]:
        d.ellipse([cx+dx, y+dy, cx+dx+ew, y+dy+eh], fill=CLOUD_W)

# ── Aves ──────────────────────────────────────────────────────────────────────
BIRDS_CFG = [
    # (x_start, y, speed, wing_size, phase)
    (  300,  95, 0.55, 36, 0.00),
    (  550,  75, 0.48, 30, 1.20),
    (  750, 115, 0.60, 28, 0.60),
    ( 1100,  65, 0.45, 34, 2.10),
    ( 1350,  90, 0.52, 26, 3.00),
    (  900, 135, 0.38, 22, 1.80),
    (  200, 150, 0.42, 20, 0.90),
]

def draw_bird(d, bx, by, ws, phase, frame):
    flap = math.sin(frame * 0.18 + phase) * 10
    d.line([(bx - ws, by + flap), (bx, by)],             fill=BIRD, width=4)
    d.line([(bx,      by),        (bx + ws, by + flap)], fill=BIRD, width=4)

# ── Render ────────────────────────────────────────────────────────────────────

def main():
    print("Construyendo escena estática...", file=sys.stderr)
    static = build_static()

    ffmpeg_cmd = [
        FFMPEG, "-y",
        "-f", "image2pipe", "-framerate", str(FPS), "-vcodec", "png",
        "-i", "pipe:0",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        OUTPUT,
    ]

    print("Iniciando FFmpeg...", file=sys.stderr)
    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    for f in range(FRAMES):
        if f % 60 == 0:
            print(f"  {f*100//FRAMES}% — frame {f}/{FRAMES}", file=sys.stderr, flush=True)

        frame_img = static.copy()
        d         = ImageDraw.Draw(frame_img)

        # Nubes animadas
        for x0, y, w, h, spd, alpha in CLOUDS:
            cx = (x0 + f * spd) % (W + w + 100) - w - 50
            draw_cloud(d, int(cx), y, w, h, alpha)

        # Aves animadas
        for x0, y, spd, ws, phase in BIRDS_CFG:
            bx = (x0 + f * spd) % (W + 100) - 50
            draw_bird(d, int(bx), y, ws, phase, f)


        buf = io.BytesIO()
        frame_img.save(buf, format="PNG", compress_level=1)
        try:
            proc.stdin.write(buf.getvalue())
        except BrokenPipeError:
            break

    try:
        proc.stdin.close()
    except BrokenPipeError:
        pass
    _, stderr = proc.communicate()
    if proc.returncode not in (0, None):
        print("FFmpeg error:", stderr.decode(), file=sys.stderr)
        sys.exit(1)

    print(f"\nFondo listo: {OUTPUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
