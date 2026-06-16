#!/usr/bin/env python3
"""
Fondo fotorrealista — desierto Sonorense, atardecer dorado.
Terreno fractal con sombreado de pendiente, perspectiva atmosférica,
grano de película, movimiento de cámara sutil.
"""
import math, io, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

FFMPEG = "/home/user/Remotion-code/node_modules/@remotion/compositor-linux-x64-gnu/ffmpeg"
OUTPUT = "/home/user/Remotion-code/public/fondo_regional.mp4"
W, H   = 1920, 1080
FPS    = 30
DUR    = 20
FRAMES = FPS * DUR

HORIZON = 500   # px desde arriba

# Deriva de cámara muy sutil — como trípode en viento ligero
PAN    = 260
P_SKY  = 0.012
P_MFAR = 0.065
P_MMID = 0.18
P_DST  = 0.52
P_FORE = 0.85

rng = np.random.default_rng(42)

def lw(f): return W + int(PAN * f) + 40

# ── Paleta fotográfica — atardecer Sonorense ──────────────────────────────────
SKY_ZEN  = np.array([ 14,  30,  80], np.float32)   # azul índigo en cenit
SKY_MED  = np.array([ 52,  95, 158], np.float32)   # azul cerúleo
SKY_HAZY = np.array([148, 130, 162], np.float32)   # lila-gris prehorizonte
SKY_WARM = np.array([210, 152,  88], np.float32)   # melocotón dorado
SKY_HOR  = np.array([245, 198, 118], np.float32)   # horizonte brillante

MFA_LIT  = np.array([142, 132, 155], np.float32)   # mont. lejana iluminada
MFA_BASE = np.array([115, 106, 128], np.float32)
MFA_SHD  = np.array([ 84,  76, 100], np.float32)

MMD_LIT  = np.array([200, 148,  88], np.float32)   # mont. media iluminada
MMD_BASE = np.array([148, 108,  64], np.float32)   # terracota
MMD_SHD  = np.array([ 88,  58,  36], np.float32)   # sombra oscura

DST_FAR  = np.array([198, 168, 112], np.float32)   # arena lejana (pálida)
DST_NEAR = np.array([182, 145,  80], np.float32)   # arena cercana (ocre)

CAC_D  = ( 32,  50,  24)
CAC_M  = ( 48,  72,  36)
CAC_L  = ( 65,  98,  50)
CAC_HL = ( 88, 125,  65)

# ── Utilidades ────────────────────────────────────────────────────────────────

def lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))

def make_ridge(width, height_range, seed=0):
    """Ridge fractal multi-octava con interpolación lineal suavizada."""
    r2 = np.random.default_rng(seed)
    y  = np.zeros(width, dtype=np.float64)
    for k in range(7):
        n   = max(4, width >> k)
        amp = height_range / (2.0 ** (k * 0.85))
        pts = r2.random(n) * amp
        xs  = np.linspace(0, width - 1, n)
        y  += np.interp(np.arange(width), xs, pts)
    y -= y.min()
    y  = y / (y.max() + 1e-6) * height_range
    kernel = np.ones(11) / 11
    y = np.convolve(y, kernel, mode="same")
    return y

def _paint_ridge(arr, ridge_y, y_bot, c_lit, c_base, c_shd, fog, atm, sun_dir=1.0):
    """
    Pinta una cordillera en arr (H, W, 4) float32 con sombreado de pendiente.
    Painter's algorithm: sobreescribe lo que haya debajo.
    """
    IH, LW = arr.shape[:2]
    y_bot = min(int(y_bot), IH)

    dx     = np.gradient(ridge_y)
    dx_max = max(np.percentile(np.abs(dx), 88), 0.4)
    light  = np.clip(0.5 + dx * sun_dir / (dx_max * 2.5), 0.05, 0.95)

    ri  = ridge_y.astype(np.int32).clip(0, IH - 1)
    yy  = np.arange(IH, dtype=np.float32)[:, np.newaxis]   # (IH, 1)
    ri2 = ri.astype(np.float32)[np.newaxis, :]              # (1, LW)

    in_mnt = (yy >= ri2) & (yy < y_bot)                    # (IH, LW)
    span   = np.maximum(1.0, float(y_bot) - ri2)
    t      = np.clip((yy - ri2) / span, 0.0, 1.0)

    lf    = light[np.newaxis, :, np.newaxis]
    col_l = c_lit  + t[:, :, np.newaxis] * (c_base - c_lit)
    col_s = c_shd  + t[:, :, np.newaxis] * (c_base - c_shd)
    col   = col_l * lf + col_s * (1.0 - lf)
    col   = col * (1.0 - atm) + fog * atm

    mask          = in_mnt[:, :, np.newaxis]
    arr[:, :, :3] = np.where(mask, col, arr[:, :, :3])
    arr[:, :,  3] = np.where(in_mnt, 255.0, arr[:, :, 3])

# ── Capa: Cielo ───────────────────────────────────────────────────────────────

def make_sky():
    LW  = lw(P_SKY)
    yy  = np.arange(HORIZON, dtype=np.float32) / HORIZON   # [0, 1]

    # Gradiente de 4 paradas usando umbrales
    col = np.zeros((HORIZON, 3), dtype=np.float32)
    s   = [0.0, 0.35, 0.65, 0.85, 1.0]
    stops = [SKY_ZEN, SKY_MED, SKY_HAZY, SKY_WARM, SKY_HOR]
    for i in range(4):
        mask = (yy >= s[i]) & (yy < s[i+1])
        t_seg = (yy[mask] - s[i]) / (s[i+1] - s[i])
        col[mask] = stops[i] + t_seg[:, np.newaxis] * (stops[i+1] - stops[i])
    col[yy >= s[4]] = SKY_HOR

    sky_arr = np.broadcast_to(col[:, np.newaxis, :], (HORIZON, LW, 3)).copy()

    # Suave resplandor solar en horizonte (columna ~28% desde la izquierda)
    sun_x  = int(LW * 0.28)
    glow_x = np.exp(-((np.arange(LW) - sun_x) ** 2) / (LW * 0.035) ** 2)
    glow_y = np.clip(1.0 - yy / 0.25, 0, 1) ** 2                      # solo en zona baja
    glow   = glow_x[np.newaxis, :] * glow_y[:, np.newaxis]             # (HORIZON, LW)
    sky_arr[:, :, 0] += glow * 28
    sky_arr[:, :, 1] += glow * 14

    # Finas estrías de cirros (ruido horizontal suavizado, solo en el tercio superior)
    cirrus_h = HORIZON // 3
    base_noise = rng.random((cirrus_h // 8, LW // 4))
    cirrus = np.array(
        Image.fromarray((base_noise * 255).astype(np.uint8)).resize((LW, cirrus_h), Image.BICUBIC)
    ) / 255.0 - 0.5
    cirrus_mask = (1.0 - np.arange(cirrus_h, dtype=np.float32) / cirrus_h)[:, np.newaxis]
    sky_arr[:cirrus_h] += cirrus[:, :, np.newaxis] * 14 * cirrus_mask[:, :, np.newaxis]

    # Ruido de textura fotográfica
    tex = rng.integers(-5, 6, (HORIZON, LW, 3), dtype=np.int16)
    sky_arr = np.clip(sky_arr + tex, 0, 255).astype(np.uint8)

    return Image.fromarray(sky_arr, "RGB")

# ── Capa: Montañas lejanas ────────────────────────────────────────────────────

def make_mfar():
    LW  = lw(P_MFAR)
    IH  = HORIZON + 25
    arr = np.zeros((IH, LW, 4), dtype=np.float32)
    fog = SKY_HOR.copy()

    configs = [
        # y_base, h_range, seed, atm_fog
        (HORIZON - 35,  92, 10, 0.72),
        (HORIZON -  8,  72, 20, 0.55),
        (HORIZON + 15,  52, 30, 0.38),
    ]
    for y_base, h_rng, seed, atm in configs:
        ridge = make_ridge(LW, h_rng, seed)
        _paint_ridge(arr, y_base - ridge, y_base + 8, MFA_LIT, MFA_BASE, MFA_SHD, fog, atm, 1.2)

    img = Image.fromarray(arr.clip(0, 255).astype(np.uint8), "RGBA")
    img = img.filter(ImageFilter.GaussianBlur(4.5))
    return img

# ── Capa: Montañas medias ─────────────────────────────────────────────────────

def make_mmid():
    LW  = lw(P_MMID)
    IH  = HORIZON + 115
    arr = np.zeros((IH, LW, 4), dtype=np.float32)
    fog = SKY_HOR.copy()

    configs = [
        (HORIZON + 18, 145, 40, 0.18),
        (HORIZON + 50, 105, 50, 0.08),
    ]
    for y_base, h_rng, seed, atm in configs:
        ridge = make_ridge(LW, h_rng, seed)
        _paint_ridge(arr, y_base - ridge, y_base + 10, MMD_LIT, MMD_BASE, MMD_SHD, fog, atm, 1.0)

    # Textura de roca sobre los píxeles de montaña
    mask_3d = arr[:, :, 3:4] / 255.0
    rock_noise = rng.integers(-16, 17, (IH, LW, 3), dtype=np.int16)
    arr[:, :, :3] = np.clip(arr[:, :, :3] + rock_noise * mask_3d * 0.65, 0, 255)

    img = Image.fromarray(arr.clip(0, 255).astype(np.uint8), "RGBA")
    img = img.filter(ImageFilter.GaussianBlur(0.9))
    return img

# ── Capa: Desierto ────────────────────────────────────────────────────────────

def make_desert():
    LW  = lw(P_DST)
    DH  = H - HORIZON + 25

    yy  = np.arange(DH, dtype=np.float32)[:, np.newaxis] / DH
    arr = (DST_FAR + yy * (DST_NEAR - DST_FAR)).astype(np.float32)
    arr = np.broadcast_to(arr[:, np.newaxis, :], (DH, LW, 3)).copy()

    # Textura de arena multi-escala
    for scale, amp in [(96, 9), (48, 6), (24, 4), (12, 2.5), (6, 1.5)]:
        gh = max(3, DH // scale)
        gw = max(3, LW // scale)
        n  = rng.random((gh, gw))
        n_full = np.array(
            Image.fromarray((n * 255).astype(np.uint8)).resize((LW, DH), Image.BICUBIC)
        ) / 255.0 - 0.5
        arr += n_full[:, :, np.newaxis] * amp

    # Perspectiva atmosférica: horizonte más pálido
    atm   = np.clip((1.0 - yy * 2.8), 0, 1) * 0.48  # (DH, 1)
    arr   = arr * (1.0 - atm[:, :, np.newaxis]) + SKY_HOR * atm[:, :, np.newaxis]

    # Duna diagonal sutil en tercio cercano
    xx    = np.arange(LW, dtype=np.float32)[np.newaxis, :]
    dune  = np.sin(xx * 0.0032 + yy * 0.012) * 5.5 * (yy > 0.5)
    arr  += dune[:, :, np.newaxis]

    tex   = rng.integers(-7, 8, (DH, LW, 3), dtype=np.int16)
    arr   = np.clip(arr + tex, 0, 255).astype(np.uint8)

    # Piedras pequeñas en franja cercana
    img = Image.fromarray(arr, "RGB")
    d   = ImageDraw.Draw(img)
    rock_r = np.random.default_rng(7)
    for _ in range(28):
        rx = int(rock_r.uniform(0, LW))
        ry = int(rock_r.uniform(DH * 0.62, DH - 10))
        rw = int(rock_r.uniform(14, 55))
        rh = int(rock_r.uniform(8, 24))
        base_t = ry / DH
        rock_c = tuple(int(DST_FAR[i] + (DST_NEAR[i] - DST_FAR[i]) * base_t * 0.6) for i in range(3))
        shd_c  = tuple(max(0, c - 35) for c in rock_c)
        d.ellipse([rx, ry, rx+rw, ry+rh], fill=shd_c)
        d.ellipse([rx+3, ry+2, rx+rw-3, ry+rh-2], fill=rock_c)
        hl = tuple(min(255, c + 28) for c in rock_c)
        d.ellipse([rx+4, ry+3, rx+rw//2, ry+rh//2], fill=hl)

    img = img.filter(ImageFilter.GaussianBlur(0.4))
    return img

# ── Capa: Cactos (silueta fotorrealista) ──────────────────────────────────────

def _seg(d, cx, y_top, y_bot, r, cd, cm, cl, chl):
    steps = max(r * 2, 4)
    for i in range(steps):
        x = cx - r + i
        t = i / (steps - 1)
        if   t < 0.28: c = lerp(cd,  cm,  t / 0.28)
        elif t < 0.54: c = lerp(cm,  cl,  (t - 0.28) / 0.26)
        elif t < 0.72: c = lerp(cl,  chl, (t - 0.54) / 0.18)
        elif t < 0.82: c = lerp(chl, cl,  (t - 0.72) / 0.10)
        else:          c = lerp(cl,  cd,  (t - 0.82) / 0.18)
        d.line([(x, y_top), (x, y_bot)], fill=c)

def draw_saguaro(d, cx, base, s=1.0):
    rt  = max(int(21 * s), 3)
    ht  = int(235 * s)
    top = base - ht
    _seg(d, cx, top, base, rt, CAC_D, CAC_M, CAC_L, CAC_HL)
    for dx in [-rt // 2, rt // 3]:
        for y in range(top, base, 13):
            d.ellipse([cx+dx-1, y, cx+dx+1, y+2], fill=(*CAC_D, 70))

    ra   = max(int(13 * s), 2)
    ay   = top + int(58 * s);  aex  = cx - int(78 * s); atop  = ay - int(82 * s)
    _seg(d, aex, atop, ay, ra, CAC_D, CAC_M, CAC_L, CAC_HL)
    for x in range(aex, cx - rt, 5):
        d.ellipse([x-1, ay-ra, x+1, ay+ra], fill=CAC_M)

    ay2  = top + int(93 * s);  aex2 = cx + int(70 * s); atop2 = ay2 - int(68 * s)
    _seg(d, aex2, atop2, ay2, ra, CAC_D, CAC_M, CAC_L, CAC_HL)
    for x in range(cx + rt, aex2, 5):
        d.ellipse([x-1, ay2-ra, x+1, ay2+ra], fill=CAC_M)

def make_cactus():
    LW  = lw(P_FORE)
    img = Image.new("RGBA", (LW, H), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img, "RGBA")
    cacti = [
        (480, H-42, 1.28), (820, H-72, 0.88), (1120, H-62, 0.70),
        (1440, H-22, 1.52), (1810, H-52, 1.12), (220, H-188, 0.34),
        (680, H-198, 0.30), (1300, H-193, 0.31), (1660, H-203, 0.28),
        (2100, H-42, 1.23), (2410, H-62, 0.90), (2710, H-32, 1.40),
        (2200, H-198, 0.32), (2610, H-188, 0.30), (3000, H-48, 1.10),
        (355, H-182, 0.27), (995, H-188, 0.25), (1840, H-193, 0.28),
    ]
    for cx, base, sc in cacti:
        draw_saguaro(d, cx, base, sc)
    img = img.filter(ImageFilter.GaussianBlur(0.55))
    return img

# ── Render ────────────────────────────────────────────────────────────────────

def main():
    print("Construyendo capas...", file=sys.stderr)
    sky_l  = make_sky()
    mfar_l = make_mfar()
    mmid_l = make_mmid()
    dst_l  = make_desert()
    cact_l = make_cactus()

    # Grano de película — array fijo (se añade por frame con offset aleatorio)
    grain_base = rng.integers(0, 28, (H + 32, W + 32), dtype=np.uint8)

    print("Capas listas. Renderizando frames...", file=sys.stderr)

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

    grain_rng = np.random.default_rng(99)

    for f in range(FRAMES):
        if f % 60 == 0:
            print(f"  {f * 100 // FRAMES}% — frame {f}/{FRAMES}", file=sys.stderr, flush=True)

        t   = f / FRAMES
        pan = int(t * PAN)

        frame = Image.new("RGB", (W, H))

        # 1. Cielo
        ox = int(pan * P_SKY)
        frame.paste(sky_l.crop((ox, 0, ox + W, HORIZON)), (0, 0))

        # 2. Neblina en el horizonte (fusiona cielo y desierto)
        haze = Image.new("RGB", (W, 60))
        hd   = ImageDraw.Draw(haze)
        for y in range(60):
            tt  = y / 59
            c0  = tuple(int(SKY_HOR[i]) for i in range(3))
            c1  = tuple(int(DST_FAR[i]) for i in range(3))
            col = lerp(c0, c1, tt)
            hd.line([(0, y), (W, y)], fill=col)
        frame.paste(haze.filter(ImageFilter.GaussianBlur(5)), (0, HORIZON - 30))

        # 3. Montañas lejanas
        ox   = int(pan * P_MFAR)
        crop = mfar_l.crop((ox, 0, ox + W, HORIZON + 25))
        frame.paste(crop, (0, 0), crop)

        # 4. Montañas medias
        ox   = int(pan * P_MMID)
        crop = mmid_l.crop((ox, 0, ox + W, HORIZON + 115))
        frame.paste(crop, (0, 0), crop)

        # 5. Desierto
        ox  = int(pan * P_DST)
        DH  = H - HORIZON + 25
        frame.paste(dst_l.crop((ox, 0, ox + W, DH)), (0, HORIZON - 12))

        # 6. Cactos
        ox   = int(pan * P_FORE)
        crop = cact_l.crop((ox, 0, ox + W, H))
        frame.paste(crop, (0, 0), crop)

        # 7. Grano de película (desplazado aleatoriamente por frame)
        gy = int(grain_rng.integers(0, 32))
        gx = int(grain_rng.integers(0, 32))
        g  = grain_base[gy:gy + H, gx:gx + W].astype(np.int16) - 14
        fa = np.array(frame).astype(np.int16)
        fa = np.clip(fa + g[:, :, np.newaxis] * 0.28, 0, 255).astype(np.uint8)

        # 8. Grading fotográfico: sutil
        final = Image.fromarray(fa, "RGB")
        final = ImageEnhance.Color(final).enhance(1.10)      # +10% saturación
        final = ImageEnhance.Contrast(final).enhance(1.05)   # +5% contraste
        final = ImageEnhance.Brightness(final).enhance(0.97) # ligeramente más oscuro

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
