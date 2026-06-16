#!/usr/bin/env python3
"""
Fondo cinemático regional mexicano — hora dorada, parallax, sin look de videojuego.
Siluetas orgánicas, textura de ruido, grano de película, perspectiva atmosférica.
"""
import math, io, subprocess, sys, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance, ImageChops

FFMPEG  = "/home/user/Remotion-code/node_modules/@remotion/compositor-linux-x64-gnu/ffmpeg"
OUTPUT  = "/home/user/Remotion-code/public/fondo_regional.mp4"
W, H    = 1920, 1080
FPS     = 30
DUR     = 20
FRAMES  = FPS * DUR

HORIZON = 530
PAN     = 1400   # px totales que recorre el plano más cercano

P_SKY   = 0.05
P_MFAR  = 0.15
P_MMID  = 0.38
P_DST   = 0.68
P_FORE  = 1.00

def lw(f): return 1920 + int(PAN * f) + 60

rng = np.random.default_rng(42)

# ── Paleta cinemática — hora dorada ──────────────────────────────────────────
# Cielo
C_SKY_TOP   = ( 18,  42,  98)   # azul noche profundo
C_SKY_MID   = ( 68, 120, 185)   # azul cielo
C_SKY_WARM  = (185, 135,  72)   # naranja dorado en horizonte
C_SKY_HOR   = (235, 175, 100)   # horizonte brillante
# Montañas lejanas (silhouette azulada por perspectiva atmosférica)
C_MFA_1     = (110,  95, 118)   # púrpura azulado, muy lejano
C_MFA_2     = (130, 108, 120)
C_MFA_3     = (148, 122, 118)
# Montañas medias (cálidas, iluminadas)
C_MMD_L     = (172, 122,  78)   # cara iluminada
C_MMD_D     = (105,  72,  48)   # cara en sombra
C_MMD_R     = (148,  98,  60)   # roca media
# Desierto
C_DST_H     = (195, 158, 100)   # arena lejana
C_DST_N     = (210, 170, 108)   # arena cercana
C_DST_S     = (155, 120,  68)   # sombra en arena
# Cactos — orgánicos, verde militar
C_CAC_D     = ( 42,  62,  32)
C_CAC_M     = ( 58,  85,  44)
C_CAC_L     = ( 78, 110,  58)
C_CAC_HL    = (105, 145,  78)   # highlight solar
# Aves — silueta oscura
C_BIRD      = ( 22,  18,  14)

# ── Helpers ───────────────────────────────────────────────────────────────────

def lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i]-a[i])*t) for i in range(3))

def lerp3(a, b, c, t):
    if t < 0.5: return lerp(a, b, t*2)
    return lerp(b, c, (t-0.5)*2)

def hgrad(arr, y0, y1, c0, c1):
    for y in range(y0, y1):
        t = (y-y0)/max(y1-y0-1,1)
        arr[y] = lerp(c0, c1, t)

def add_noise(img_arr, intensity=8, seed=0):
    rng2 = np.random.default_rng(seed)
    noise = rng2.integers(-intensity, intensity+1, img_arr.shape, dtype=np.int16)
    return np.clip(img_arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)

def blur_layer(img, radius):
    return img.filter(ImageFilter.GaussianBlur(radius))

def smooth_ridge(x_start, x_end, y_base, amplitude, freq, seed=0, n_pts=60):
    """Genera una silueta de montaña orgánica con Perlin-like noise."""
    rng2 = np.random.default_rng(seed)
    xs = np.linspace(x_start, x_end, n_pts)
    # Suma de sinusoides con frecuencias y fases aleatorias
    ys = np.zeros(n_pts)
    for k in range(1, 6):
        phase = rng2.uniform(0, 2*math.pi)
        amp   = amplitude / (k**1.3)
        ys   += amp * np.sin(xs * freq * k + phase)
    # Normalizar y centrar en y_base
    ys = y_base - (ys - ys.min())
    # Suavizar con media móvil
    kernel = np.ones(5)/5
    ys = np.convolve(ys, kernel, mode='same')
    pts = list(zip(xs.astype(int), ys.astype(int)))
    pts += [(x_end, y_base + 20), (x_start, y_base + 20)]
    return pts

# ── Capa: Cielo ───────────────────────────────────────────────────────────────

def make_sky():
    LW  = lw(P_SKY)
    arr = np.zeros((HORIZON, LW, 3), dtype=np.uint8)
    row = np.zeros((HORIZON, 3), dtype=np.uint8)
    for y in range(HORIZON):
        t = y / HORIZON
        row[y] = lerp3(C_SKY_TOP, C_SKY_MID, C_SKY_WARM, t)
    arr[:] = row[:, np.newaxis, :]
    # Glow horizontal cálido en el horizonte (izq→der varía un poco)
    for x in range(LW):
        tx = x / LW
        glow_int = 0.12 * math.sin(tx * math.pi)
        for y in range(int(HORIZON*0.65), HORIZON):
            ty   = (y - HORIZON*0.65) / (HORIZON*0.35)
            c    = arr[y, x].astype(float)
            warm = np.array(C_SKY_HOR, dtype=float)
            arr[y, x] = np.clip(c + (warm-c)*ty*glow_int*2, 0, 255).astype(np.uint8)
    arr = add_noise(arr, 5, seed=1)
    img = Image.fromarray(arr, "RGB")
    return img

# ── Capa: Montañas lejanas ────────────────────────────────────────────────────

def make_mfar():
    LW  = lw(P_MFAR)
    img = Image.new("RGBA", (LW, HORIZON+10), (0,0,0,0))
    d   = ImageDraw.Draw(img)
    # 3 cordilleras con siluetas diferentes, distancias distintas
    ridges = [
        # (x_start, x_end, y_base, amplitude, freq, seed, color_top, color_bot)
        (  -80, LW+80, HORIZON-10, 95, 0.0028, 10, C_MFA_1, C_MFA_2),
        ( -120, LW+120,HORIZON+5,  70, 0.0038, 20, C_MFA_2, C_MFA_3),
        (  -60, LW+60, HORIZON+12, 50, 0.0055, 30, C_MFA_3, C_MMD_R),
    ]
    for xs, xe, yb, amp, freq, seed, ct, cb in ridges:
        pts = smooth_ridge(xs, xe, yb, amp, freq, seed)
        # Relleno con gradiente vertical (truco: pintar en dos pasos)
        d.polygon(pts, fill=ct)
    # Blur atmosférico fuerte (muy lejos)
    img = img.filter(ImageFilter.GaussianBlur(3.5))
    # Añadir un velo de niebla atmosférica
    fog = Image.new("RGBA", (LW, HORIZON+10), (C_SKY_HOR[0], C_SKY_HOR[1], C_SKY_HOR[2], 55))
    img = Image.alpha_composite(img, fog)
    return img

# ── Capa: Montañas medias ─────────────────────────────────────────────────────

def make_mmid():
    LW  = lw(P_MMID)
    img = Image.new("RGBA", (LW, HORIZON+120), (0,0,0,0))
    d   = ImageDraw.Draw(img)
    # Cordillera principal con textura
    ridges = [
        ( -80, LW+80, HORIZON+10,  130, 0.0022, 40, C_MMD_D),
        ( -60, LW+60, HORIZON+30,  100, 0.0032, 50, C_MMD_R),
    ]
    for xs, xe, yb, amp, freq, seed, col in ridges:
        pts = smooth_ridge(xs, xe, yb, amp, freq, seed)
        d.polygon(pts, fill=col)
    # Detalle iluminado en crestas — superponemos una cordillera más alta y más clara
    pts_lit = smooth_ridge(-80, LW+80, HORIZON+10, 130, 0.0022, 40)
    # Simular cara iluminada: dibujar versión desplazada 2px arriba en color claro
    pts_shifted = [(x, y-3) for x,y in pts_lit[:-2]] + pts_lit[-2:]
    d.polygon(pts_shifted, fill=(*C_MMD_L, 160))
    # Textura de roca con ruido sobre la capa
    arr = np.array(img)
    mask = arr[:,:,3] > 0
    noise = rng.integers(-14, 14, arr[:,:,:3].shape, dtype=np.int16)
    arr[:,:,:3] = np.clip(arr[:,:,:3].astype(np.int16) + noise*mask[:,:,np.newaxis], 0, 255).astype(np.uint8)
    img = Image.fromarray(arr, "RGBA")
    img = img.filter(ImageFilter.GaussianBlur(1.2))
    return img

# ── Capa: Desierto ────────────────────────────────────────────────────────────

def make_desert():
    LW  = lw(P_DST)
    arr = np.zeros((H-HORIZON, LW, 3), dtype=np.uint8)
    # Gradiente base
    for y in range(H-HORIZON):
        t = y / (H-HORIZON)
        arr[y] = lerp(C_DST_H, C_DST_N, t)
    # Textura de arena — noise de baja frecuencia
    for scale in [80, 40, 20]:
        freq_x = 1.0/scale; freq_y = 1.0/(scale*0.5)
        xx = np.arange(LW)
        yy = np.arange(H-HORIZON)
        # Suma de sinusoides para simular arena
        wave_x = np.sin(xx * freq_x * rng.uniform(0.8,1.2) + rng.uniform(0, 6.28))
        wave_y = np.sin(yy * freq_y * rng.uniform(0.8,1.2) + rng.uniform(0, 6.28))
        texture = np.outer(wave_y, wave_x)  # (H, LW)
        intensity = 6 if scale==80 else (4 if scale==40 else 2)
        arr = np.clip(arr.astype(np.int16) + (texture[:,:,np.newaxis]*intensity).astype(np.int16), 0, 255).astype(np.uint8)
    # Ruido granular fino
    arr = add_noise(arr, 10, seed=2)
    # Sombras de piedras — manchas oscuras irregulares
    img = Image.fromarray(arr, "RGB")
    d   = ImageDraw.Draw(img)
    rock_positions = [
        (310, 185, 95, 38), (670, 265, 68, 26), (1220, 148, 105, 42),
        (1520, 238, 82, 32), (820, 338, 125, 48), (1770, 308, 78, 30),
        (155, 385, 110, 36), (1065, 388, 88, 32), (2120, 205, 92, 36),
        (2450, 285, 72, 28), (2720, 158, 98, 40), (3020, 318, 84, 32),
        (450, 480, 60, 20),  (900, 540, 75, 24),  (1400, 460, 55, 18),
    ]
    for rx, ry, rw, rh in rock_positions:
        # Sombra
        d.ellipse([rx, ry, rx+rw, ry+rh], fill=C_DST_S)
        # Roca encima (más clara)
        inset = 5
        base = lerp(C_DST_H, C_DST_N, min(ry/(H-HORIZON),1))
        rock_col = lerp(base, (90,70,45), 0.55)
        d.ellipse([rx+inset, ry+inset//2, rx+rw-inset, ry+rh-inset//2], fill=rock_col)
        # Highlight solar en esquina superior izquierda
        hl_col = lerp(rock_col, (220, 185, 140), 0.4)
        d.ellipse([rx+inset+3, ry+inset//2+2,
                   rx+rw-inset-rw//3, ry+rh//2], fill=hl_col)
    img = img.filter(ImageFilter.GaussianBlur(0.5))
    return img

# ── Capa: Cactos orgánicos ────────────────────────────────────────────────────

def _cactus_segment(d, cx, y_top, y_bot, r, col_d, col_m, col_l, col_hl):
    """Segmento cilíndrico de cactus — ancho 2r, con gradiente lateral."""
    steps = max(r*2, 4)
    for i in range(steps):
        x = cx - r + i
        t = i / (steps-1)
        # Gradiente lateral: oscuro-medio-claro-medio-oscuro (curvatura)
        if t < 0.3:    c = lerp(col_d, col_m, t/0.3)
        elif t < 0.55: c = lerp(col_m, col_l, (t-0.3)/0.25)
        elif t < 0.7:  c = lerp(col_l, col_hl, (t-0.55)/0.15)
        elif t < 0.8:  c = lerp(col_hl, col_l, (t-0.7)/0.1)
        else:          c = lerp(col_l, col_d, (t-0.8)/0.2)
        d.line([(x, y_top), (x, y_bot)], fill=c)

def saguaro_organic(d, cx, base, s=1.0):
    r_trunk = max(int(24*s), 3)
    h_trunk = int(255*s)
    top     = base - h_trunk

    # Tronco principal
    _cactus_segment(d, cx, top, base, r_trunk, C_CAC_D, C_CAC_M, C_CAC_L, C_CAC_HL)
    # Líneas de costilla verticales
    for dx in [-r_trunk//2, 0, r_trunk//2]:
        for y in range(top, base, 10):
            d.ellipse([cx+dx-1, y, cx+dx+1, y+3], fill=(*C_CAC_D, 90))

    r_arm = max(int(16*s), 2)
    # Brazo izquierdo
    ay   = top + int(65*s)
    aex  = cx - int(85*s)
    atop = ay - int(90*s)
    _cactus_segment(d, aex, atop, ay, r_arm, C_CAC_D, C_CAC_M, C_CAC_L, C_CAC_HL)
    for x in range(aex, cx - r_trunk, 5):
        d.ellipse([x-1, ay-r_arm, x+1, ay+r_arm], fill=C_CAC_M)

    # Brazo derecho
    ay2  = top + int(100*s)
    aex2 = cx + int(78*s)
    atop2= ay2 - int(75*s)
    _cactus_segment(d, aex2, atop2, ay2, r_arm, C_CAC_D, C_CAC_M, C_CAC_L, C_CAC_HL)
    for x in range(cx + r_trunk, aex2, 5):
        d.ellipse([x-1, ay2-r_arm, x+1, ay2+r_arm], fill=C_CAC_M)

def make_cactus():
    LW  = lw(P_FORE)
    img = Image.new("RGBA", (LW, H), (0,0,0,0))
    d   = ImageDraw.Draw(img)
    cacti = [
        # cx, base, scale
        ( 490, H-45,  1.30), ( 830, H-75,  0.90), (1130, H-65,  0.72),
        (1450, H-25,  1.55), (1820, H-55,  1.15), ( 220, H-195, 0.36),
        ( 690, H-205, 0.31), (1310, H-200, 0.33), (1670, H-210, 0.29),
        (2110, H-45,  1.25), (2420, H-65,  0.95), (2720, H-35,  1.45),
        (2210, H-205, 0.34), (2620, H-195, 0.31), (3010, H-50,  1.15),
        ( 350, H-185, 0.28), (1000, H-190, 0.26), (1850, H-200, 0.30),
    ]
    for cx, base, sc in cacti:
        saguaro_organic(d, cx, base, sc)
    # Suavizar bordes ligeramente
    img = img.filter(ImageFilter.GaussianBlur(0.6))
    return img

# ── Nubes cinemáticas — voluminosas con gradiente ────────────────────────────

CLOUDS = [
    (  150, 108, 380, 100, 0.55, 0.92),
    (  720, 152, 290,  80, 0.42, 0.85),
    ( 1230,  72, 340,  92, 0.50, 0.90),
    ( 1680, 128, 220,  62, 0.35, 0.80),
    ( -250, 198, 195,  54, 0.28, 0.72),
    (  510, 230, 155,  44, 0.25, 0.68),
    ( 1070, 215, 175,  50, 0.30, 0.74),
    ( 2020, 105, 310,  86, 0.46, 0.88),
]

def draw_cloud(d, cx, y, w, h, alpha):
    # Sombra base
    d.ellipse([cx+w//6, y+int(h*.6), cx+int(w*.88), y+int(h*1.18)],
              fill=(195, 185, 175))
    # Cuerpo principal con varios círculos ponderados
    puffs = [
        (0,        0,        w,        h,        1.00),
        (w//5,    -h//3,    int(w*.78),int(h*.82),0.95),
        (int(w*.52), 0,     int(w*.68),int(h*.74),0.90),
        (int(w*.74), h//9,  int(w*.40),int(h*.62),0.85),
        (-w//9,    h//9,    int(w*.38),int(h*.60),0.85),
        (w//3,    -h//5,    int(w*.50),int(h*.60),0.80),
    ]
    for dx, dy, pw, ph, opa in puffs:
        r = int(245 * alpha * opa)
        g = int(242 * alpha * opa)
        b = int(238 * alpha * opa)
        d.ellipse([cx+dx, y+dy, cx+dx+pw, y+dy+ph], fill=(r,g,b))

# ── Aves orgánicas ────────────────────────────────────────────────────────────

BIRDS = [
    ( 300,  92, 0.55, 38, 0.00),
    ( 560,  72, 0.48, 32, 1.20),
    ( 760, 112, 0.60, 30, 0.60),
    (1110,  62, 0.45, 36, 2.10),
    (1360,  88, 0.52, 28, 3.00),
    ( 910, 132, 0.38, 24, 1.80),
    ( 210, 148, 0.42, 22, 0.90),
]

def draw_bird(d, bx, by, ws, phase, f):
    flap = math.sin(f * 0.18 + phase) * 11
    # Ala izquierda con curva (2 segmentos)
    mid_l = (bx - ws//2, by + flap//2)
    d.line([(bx-ws, by+flap), mid_l],       fill=C_BIRD, width=3)
    d.line([mid_l,             (bx, by)],    fill=C_BIRD, width=3)
    # Ala derecha
    mid_r = (bx + ws//2, by + flap//2)
    d.line([(bx, by),     mid_r],            fill=C_BIRD, width=3)
    d.line([mid_r,  (bx+ws, by+flap)],      fill=C_BIRD, width=3)

# ── Grano de película (overlay estático, se añade por frame) ─────────────────

def make_grain():
    g = rng.integers(0, 22, (H, W), dtype=np.uint8)
    grain = np.stack([g,g,g], axis=-1)
    return Image.fromarray(grain, "RGB")

# ── Render ────────────────────────────────────────────────────────────────────

def main():
    print("Construyendo capas...", file=sys.stderr)
    sky_l   = make_sky()
    mfar_l  = make_mfar()
    mmid_l  = make_mmid()
    dst_l   = make_desert()
    cact_l  = make_cactus()
    grain_l = make_grain()
    print("Capas listas.", file=sys.stderr)

    ffmpeg_cmd = [
        FFMPEG, "-y",
        "-f", "image2pipe", "-framerate", str(FPS), "-vcodec", "png",
        "-i", "pipe:0",
        "-c:v", "libx264", "-preset", "fast", "-crf", "16",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        OUTPUT,
    ]
    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    for f in range(FRAMES):
        if f % 60 == 0:
            print(f"  {f*100//FRAMES}% — frame {f}/{FRAMES}", file=sys.stderr, flush=True)

        t   = f / FRAMES
        pan = int(t * PAN)

        frame = Image.new("RGB", (W, H))

        # Cielo
        ox = int(pan * P_SKY)
        frame.paste(sky_l.crop((ox, 0, ox+W, HORIZON)), (0, 0))

        # Neblina cálida en horizonte
        haze = Image.new("RGB", (W, 70))
        hd   = ImageDraw.Draw(haze)
        for y in range(70):
            t2 = y/69
            col = lerp(C_SKY_HOR, C_DST_H, t2)
            hd.line([(0,y),(W,y)], fill=col)
        frame.paste(haze.filter(ImageFilter.GaussianBlur(3)), (0, HORIZON-35))

        # Montañas lejanas
        ox = int(pan * P_MFAR)
        mfc = mfar_l.crop((ox, 0, ox+W, HORIZON+10))
        frame.paste(mfc, (0, 0), mfc)

        # Montañas medias
        ox = int(pan * P_MMID)
        mmc = mmid_l.crop((ox, 0, ox+W, HORIZON+120))
        frame.paste(mmc, (0, 0), mmc)

        # Desierto
        ox = int(pan * P_DST)
        frame.paste(dst_l.crop((ox, 0, ox+W, H-HORIZON)), (0, HORIZON))

        # Nubes
        sky_c = Image.new("RGBA", (W, HORIZON), (0,0,0,0))
        cd    = ImageDraw.Draw(sky_c)
        ox_sky = int(pan * P_SKY)
        for x0, y, cw, ch, spd, alpha in CLOUDS:
            cx = (x0 + f*spd - ox_sky) % (W+cw+200) - cw - 100
            draw_cloud(cd, int(cx), y, cw, ch, alpha)
        frame.paste(sky_c, (0, 0), sky_c)

        # Aves
        bird_c = Image.new("RGBA", (W, HORIZON), (0,0,0,0))
        bd     = ImageDraw.Draw(bird_c)
        for x0, y, spd, ws, phase in BIRDS:
            bx = (x0 + f*spd - ox_sky) % (W+150) - 75
            draw_bird(bd, int(bx), y, ws, phase, f)
        frame.paste(bird_c, (0, 0), bird_c)

        # Cactos primer plano
        ox = int(pan * P_FORE)
        cc = cact_l.crop((ox, 0, ox+W, H))
        frame.paste(cc, (0, 0), cc)

        # Grano de película sutil
        frame_arr = np.array(frame).astype(np.int16)
        g_arr     = np.array(grain_l).astype(np.int16) - 11
        frame_arr = np.clip(frame_arr + g_arr * 0.35, 0, 255).astype(np.uint8)

        # Grading final: leve aumento de saturación y calor
        final = Image.fromarray(frame_arr, "RGB")
        final = ImageEnhance.Color(final).enhance(1.18)
        final = ImageEnhance.Contrast(final).enhance(1.08)

        buf = io.BytesIO()
        final.save(buf, format="PNG", compress_level=1)
        try:
            proc.stdin.write(buf.getvalue())
        except BrokenPipeError:
            break

    try:
        proc.stdin.close()
    except (BrokenPipeError, ValueError):
        pass
    try:
        _, stderr = proc.communicate()
    except ValueError:
        proc.wait()
        stderr = b""
    if proc.returncode not in (0, None):
        print("FFmpeg error:", stderr.decode(), file=sys.stderr)
        sys.exit(1)
    print(f"\nFondo listo: {OUTPUT}", file=sys.stderr)

if __name__ == "__main__":
    main()
