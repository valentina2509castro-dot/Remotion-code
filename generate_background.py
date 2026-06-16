#!/usr/bin/env python3
"""
Fondo animado regional mexicano — 1920x1080, 20s loop.
Desplazamiento horizontal con parallax por capas.
"""
import math, io, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter

FFMPEG  = "/home/user/Remotion-code/node_modules/@remotion/compositor-linux-x64-gnu/ffmpeg"
OUTPUT  = "/home/user/Remotion-code/public/fondo_regional.mp4"
W, H    = 1920, 1080
FPS     = 30
DUR     = 20
FRAMES  = FPS * DUR      # 600 frames

HORIZON = 520

PAN     = 1600            # píxeles totales que recorre el plano más cercano

# Factores parallax por capa (0 = no se mueve, 1 = velocidad máxima)
P_SKY   = 0.05
P_MFAR  = 0.18
P_MMID  = 0.40
P_DST   = 0.70
P_FORE  = 1.00

# Ancho de cada capa (1920 + PAN × factor, redondeado arriba)
def lw(factor): return 1920 + int(PAN * factor) + 40

# ── Paleta ────────────────────────────────────────────────────────────────────
SKY_TOP     = ( 58, 110, 175)
SKY_MID     = ( 98, 162, 210)
SKY_HOR     = (200, 180, 148)
HAZE        = (215, 198, 165)
MTN_FAR_L   = (158, 122, 102)
MTN_FAR_D   = (128,  96,  76)
MTN_MID_L   = (172, 132, 100)
MTN_MID_D   = (138, 100,  72)
MTN_ROCK_L  = (198, 160, 118)
MTN_ROCK_D  = (148, 108,  76)
DST_FAR     = (200, 172, 122)
DST_MID     = (210, 178, 112)
DST_NEAR    = (220, 185, 105)
DST_SHADOW  = (185, 152,  90)
CACTUS_D    = ( 44,  78,  38)
CACTUS_L    = ( 62, 105,  52)
CACTUS_SPEC = ( 80, 128,  66)
CLOUD_W     = (252, 252, 250)
CLOUD_S     = (215, 218, 225)
BIRD        = ( 38,  38,  48)

# ── Helpers ───────────────────────────────────────────────────────────────────

def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

def hgrad(draw, width, y0, y1, c0, c1):
    for y in range(y0, y1):
        t = (y - y0) / max(y1 - y0 - 1, 1)
        draw.line([(0, y), (width, y)], fill=lerp(c0, c1, t))

def mesa(d, x, base, w, h, cl, cd):
    cx  = x + w // 2
    tw  = int(w * 0.72)
    top = base - h
    d.polygon([(x, base), (cx-tw//2, top), (cx+tw//2, top), (x+w, base)], fill=cl)
    d.polygon([(cx, top), (cx+tw//2, top), (x+w, base), (x+int(w*0.58), base)], fill=cd)
    d.line([(cx-tw//2, top), (cx+tw//2, top)], fill=lerp(cl,(255,255,255),0.15), width=2)

def saguaro(d, cx, base, s=1.0):
    tw = max(int(28*s), 4)
    th = int(260*s)
    top = base - th

    def rect(x0,y0,x1,y1,fill):
        if x1>x0 and y1>y0: d.rectangle([x0,y0,x1,y1], fill=fill)

    rect(cx-tw, top, cx+tw, base, CACTUS_D)
    rect(cx-tw//2, top, cx, base, CACTUS_L)
    rect(cx-tw//4, top, cx+tw//4, base, CACTUS_SPEC)

    aw   = max(int(18*s), 3)
    ay1  = top + int(70*s);  aex  = cx - int(90*s);  atop  = ay1 - int(85*s)
    rect(aex, ay1-aw, cx-tw, ay1+aw, CACTUS_D)
    rect(aex-aw, atop, aex+aw, ay1, CACTUS_D)
    rect(aex-aw//2, atop, aex, ay1, CACTUS_L)

    ay2  = top + int(105*s); aex2 = cx + int(80*s);  atop2 = ay2 - int(70*s)
    rect(cx+tw, ay2-aw, aex2, ay2+aw, CACTUS_D)
    rect(aex2-aw, atop2, aex2+aw, ay2, CACTUS_D)
    rect(aex2, atop2, aex2+aw//2, ay2, CACTUS_L)

def cloud(d, cx, y, w, h):
    d.ellipse([cx+w//8, y+int(h*.55), cx+int(w*.9), y+int(h*1.15)], fill=CLOUD_S)
    for dx,dy,ew,eh in [(0,0,w,h),(w//5,-h//4,int(w*.75),int(h*.8)),
                        (int(w*.5),0,int(w*.65),int(h*.72)),
                        (int(w*.72),h//8,int(w*.42),int(h*.60)),
                        (-w//8,h//8,int(w*.40),int(h*.58))]:
        d.ellipse([cx+dx, y+dy, cx+dx+ew, y+dy+eh], fill=CLOUD_W)

def bird(d, bx, by, ws, phase, f):
    flap = math.sin(f*0.18 + phase) * 10
    d.line([(bx-ws, by+flap), (bx, by)],         fill=BIRD, width=4)
    d.line([(bx, by),         (bx+ws, by+flap)], fill=BIRD, width=4)

# ── Capas estáticas pre-renderizadas ─────────────────────────────────────────

def make_sky_layer():
    LW = lw(P_SKY)
    img = Image.new("RGB", (LW, HORIZON))
    d   = ImageDraw.Draw(img)
    mid = int(HORIZON * 0.45)
    hgrad(d, LW, 0,   mid,     SKY_TOP, SKY_MID)
    hgrad(d, LW, mid, HORIZON, SKY_MID, SKY_HOR)
    return img

def make_mountain_far_layer():
    LW  = lw(P_MFAR)
    img = Image.new("RGBA", (LW, HORIZON), (0,0,0,0))
    d   = ImageDraw.Draw(img)
    # Mesas lejanas distribuidas a lo largo del ancho ampliado
    mesas = [
        ( 80, HORIZON-10, 320, 160), (340, HORIZON+5, 240, 120),
        (680, HORIZON-5,  280, 140), (980, HORIZON+3, 200, 100),
        (1250,HORIZON-8,  310, 155), (1600,HORIZON+5, 260, 130),
        (1900,HORIZON-3,  230, 115),
    ]
    for x,base,w,h in mesas:
        mesa(d, x, base, w, h, MTN_FAR_L, MTN_FAR_D)
    return img

def make_mountain_mid_layer():
    LW  = lw(P_MMID)
    img = Image.new("RGBA", (LW, HORIZON+80), (0,0,0,0))
    d   = ImageDraw.Draw(img)
    mesas = [
        (120, HORIZON+20, 480, 200), (640, HORIZON+15, 360, 180),
        (1050,HORIZON+18, 420, 190), (1500,HORIZON+12, 380, 170),
        (1900,HORIZON+20, 440, 195),
        (900, HORIZON+10, 160,  80), (1100,HORIZON+5,  100,  55),
    ]
    for x,base,w,h in mesas:
        mesa(d, x, base, w, h, MTN_MID_L, MTN_MID_D)
    rocks = [
        (400,HORIZON+8, 160,80, MTN_ROCK_L, MTN_ROCK_D),
        (750,HORIZON+3, 100,55, MTN_ROCK_L, MTN_ROCK_D),
        (1550,HORIZON+8,220,110,MTN_FAR_L,  MTN_FAR_D),
        (1750,HORIZON+2,150, 70,MTN_FAR_L,  MTN_FAR_D),
    ]
    for x,base,w,h,cl,cd in rocks:
        mesa(d, x, base, w, h, cl, cd)
    return img

def make_desert_layer():
    LW  = lw(P_DST)
    img = Image.new("RGB", (LW, H-HORIZON))
    d   = ImageDraw.Draw(img)
    hgrad(d, LW, 0, H-HORIZON, DST_FAR, DST_NEAR)
    # Piedras
    rocks = [
        (300,180,80,35),(640,260,55,22),(1200,140,90,38),(1500,230,70,28),
        (800,330,110,40),(1750,300,65,25),(150,380,95,32),(1050,380,75,28),
        (2100,200,80,35),(2400,280,60,24),(2700,150,85,36),(3000,310,70,28),
    ]
    for rx,ry,rw,rh in rocks:
        d.ellipse([rx,ry,rx+rw,ry+rh], fill=DST_SHADOW)
        d.ellipse([rx+6,ry+4,rx+rw-4,ry+rh-6], fill=DST_MID)
    return img

def make_cactus_layer():
    LW  = lw(P_FORE)
    img = Image.new("RGBA", (LW, H), (0,0,0,0))
    d   = ImageDraw.Draw(img)
    cacti = [
        # (cx, base, scale)
        ( 480, H-50,  1.30), ( 820, H-80,  0.85), (1120, H-70,  0.70),
        (1440, H-30,  1.50), (1800, H-60,  1.10), ( 220, H-200, 0.35),
        ( 680, H-210, 0.30), (1300, H-205, 0.32), (1650, H-215, 0.28),
        (2100, H-50,  1.20), (2400, H-70,  0.90), (2700, H-40,  1.40),
        (2200, H-210, 0.33), (2600, H-200, 0.30), (3000, H-55,  1.10),
    ]
    for cx, base, s in cacti:
        saguaro(d, cx, base, s)
    return img

# Nubes — se animan sobre el cielo (posición base + offset por frame)
CLOUDS = [
    (  200,  95, 340,  90, 0.60),
    (  750, 150, 260,  72, 0.45),
    ( 1250,  75, 310,  85, 0.52),
    ( 1650, 125, 200,  58, 0.38),
    ( -200, 195, 180,  50, 0.30),
    (  500, 235, 140,  40, 0.28),
    ( 1050, 210, 160,  45, 0.32),
    ( 2000, 110, 290,  80, 0.48),
]

BIRDS_CFG = [
    (  300,  95, 0.55, 36, 0.00),
    (  550,  75, 0.48, 30, 1.20),
    (  750, 115, 0.60, 28, 0.60),
    ( 1100,  65, 0.45, 34, 2.10),
    ( 1350,  90, 0.52, 26, 3.00),
    (  900, 135, 0.38, 22, 1.80),
    (  200, 150, 0.42, 20, 0.90),
]

# ── Render ────────────────────────────────────────────────────────────────────

def main():
    print("Construyendo capas estáticas...", file=sys.stderr)
    sky_l  = make_sky_layer()
    mfar_l = make_mountain_far_layer()
    mmid_l = make_mountain_mid_layer()
    dst_l  = make_desert_layer()
    cact_l = make_cactus_layer()
    print("Capas listas.", file=sys.stderr)

    ffmpeg_cmd = [
        FFMPEG, "-y",
        "-f", "image2pipe", "-framerate", str(FPS), "-vcodec", "png",
        "-i", "pipe:0",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        OUTPUT,
    ]

    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    for f in range(FRAMES):
        if f % 60 == 0:
            print(f"  {f*100//FRAMES}% — frame {f}/{FRAMES}", file=sys.stderr, flush=True)

        # Progresión suave de pan (0→1) usando función ease in-out
        t = f / FRAMES
        ease = t  # lineal — loop perfecto
        pan = int(ease * PAN)

        frame = Image.new("RGB", (W, H))

        # ── Cielo (mueve muy poco) ──────────────────────────────────────
        ox_sky = int(pan * P_SKY)
        frame.paste(sky_l.crop((ox_sky, 0, ox_sky+W, HORIZON)), (0, 0))

        # Neblina horizonte
        haze_img = Image.new("RGB", (W, 60))
        hd = ImageDraw.Draw(haze_img)
        for y in range(60):
            t2 = y / 59
            hd.line([(0, y), (W, y)], fill=lerp(SKY_HOR, DST_FAR, t2))
        frame.paste(haze_img, (0, HORIZON-30))

        # ── Montañas lejanas ────────────────────────────────────────────
        ox_mfar = int(pan * P_MFAR)
        mfar_crop = mfar_l.crop((ox_mfar, 0, ox_mfar+W, HORIZON))
        frame.paste(mfar_crop, (0, 0), mfar_crop)

        # ── Montañas medias ─────────────────────────────────────────────
        ox_mmid = int(pan * P_MMID)
        mmid_crop = mmid_l.crop((ox_mmid, 0, ox_mmid+W, HORIZON+80))
        frame.paste(mmid_crop, (0, 0), mmid_crop)

        # ── Desierto ────────────────────────────────────────────────────
        ox_dst = int(pan * P_DST)
        dst_crop = dst_l.crop((ox_dst, 0, ox_dst+W, H-HORIZON))
        frame.paste(dst_crop, (0, HORIZON))

        # ── Nubes (sobre cielo, movimiento propio + parallax cielo) ────
        sky_canvas = Image.new("RGBA", (W, HORIZON), (0,0,0,0))
        cd = ImageDraw.Draw(sky_canvas)
        for x0, y, cw, ch, spd in CLOUDS:
            # Posición: desplazamiento propio + corrección parallax del cielo
            cx = (x0 + f * spd - ox_sky) % (W + cw + 100) - cw - 50
            cloud(cd, int(cx), y, cw, ch)
        frame.paste(sky_canvas, (0, 0), sky_canvas)

        # ── Aves ────────────────────────────────────────────────────────
        bird_canvas = Image.new("RGBA", (W, HORIZON), (0,0,0,0))
        bd = ImageDraw.Draw(bird_canvas)
        for x0, y, spd, ws, phase in BIRDS_CFG:
            bx = (x0 + f * spd - ox_sky) % (W + 100) - 50
            bird(bd, int(bx), y, ws, phase, f)
        frame.paste(bird_canvas, (0, 0), bird_canvas)

        # ── Cactos (primer plano, velocidad máxima) ─────────────────────
        ox_fore = int(pan * P_FORE)
        cact_crop = cact_l.crop((ox_fore, 0, ox_fore+W, H))
        frame.paste(cact_crop, (0, 0), cact_crop)

        buf = io.BytesIO()
        frame.save(buf, format="PNG", compress_level=1)
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
