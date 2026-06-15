#!/usr/bin/env python3
"""
Lyric video generator — pipes raw frames to FFmpeg.
No intermediate files needed.
"""
import subprocess
import sys
import math
from PIL import Image, ImageDraw, ImageFont

FFMPEG = "/home/user/Remotion-code/node_modules/@remotion/compositor-linux-x64-gnu/ffmpeg"
AUDIO  = "/home/user/Remotion-code/public/DE_RODILLAS_TE_PIDO_MASTER_2026.wav"
OUTPUT = "/home/user/Remotion-code/lyric_video.mp4"
FONT   = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"

W, H   = 1920, 1080
FPS    = 30
TOTAL_SECONDS = 216.0
TOTAL_FRAMES  = int(TOTAL_SECONDS * FPS)

FADE_IN_FRAMES  = 12   # 0.4 s
FADE_OUT_FRAMES = 12   # 0.4 s
FONT_SIZE       = 64
MAX_LINE_WIDTH  = 1680  # pixels before wrapping

LYRICS = [
    # Verso 1 (ancla intro: 14.85s)
    ("Qué caro estoy pagando",                          14.85,  21.35),
    ("El haber traicionado",                            21.35,  27.85),
    ("El amor que me daba, por una locura",             27.85,  34.35),
    ("Qué estúpido fui",                                34.35,  40.85),
    # Pre-coro 1
    ("Ella fue una aventura",                           40.85,  47.35),
    ("Tan solo un pasatiempo",                          47.35,  53.85),
    ("Con arrepentimiento sincero, hoy vengo",          53.85,  60.35),
    ("A pedirte perdón",                                60.35,  66.82),
    # Coro 1 (anclas exactas del cromograma: 66.82 / 74.75 / 82.69 / 96.00)
    ("De rodillas te pido, te ruego, te digo",          66.82,  74.75),
    ("Que regreses conmigo, que no te he olvidado",     74.75,  82.69),
    ("Que te extrañan mis manos, que muero de ganas",   82.69,  89.35),
    ("Por volverte a besar",                            89.35,  96.00),
    # Puente 1 (96.00 - 118.78s)
    ("En las noches despierto gritando tu nombre",      96.00, 101.70),
    ("Y me lleno de miedo al pensar que a otro hombre",101.70, 107.40),
    ("Le estarás entregando tus besos, tu cuerpo",     107.40, 113.10),
    ("No quiero ni pensar",                            113.10, 118.78),
    # Link (ancla cromograma: 135.17 - 141.82s)
    ("De rodillas te pido",                            135.17, 141.82),
    # Pre-coro 2 (141.82 - 169.98s)
    ("Ella fue una aventura",                          141.82, 148.86),
    ("Tan solo un pasatiempo",                         148.86, 155.90),
    ("Con arrepentimiento sincero, hoy vengo",         155.90, 162.94),
    ("A pedirte perdón",                               162.94, 169.98),
    # Coro 2 (169.98 - 193.02s)
    ("De rodillas te pido, te ruego, te digo",         169.98, 175.74),
    ("Que regreses conmigo, que no te he olvidado",    175.74, 181.50),
    ("Que te extrañan mis manos, que muero de ganas",  181.50, 187.26),
    ("Por volverte a besar",                           187.26, 193.02),
    # Outro (193.02 - 212.00s)
    ("En las noches despierto gritando tu nombre",     193.02, 196.73),
    ("Y me lleno de miedo al pensar que a otro hombre",196.73, 200.44),
    ("Le estarás entregando tus besos, tu cuerpo",     200.44, 204.15),
    ("No quiero ni pensar",                            204.15, 207.87),
    ("De rodillas te pido",                            207.87, 212.00),
]


def build_lookup(fps, total_frames, lyrics, fade_in, fade_out):
    """Return array: frame_index → (text, alpha 0.0-1.0)"""
    table = [(None, 0.0)] * total_frames
    for text, t_start, t_end in lyrics:
        f_start = int(t_start * fps)
        f_end   = min(int(t_end * fps), total_frames)
        for f in range(f_start, f_end):
            elapsed = f - f_start
            remaining = f_end - f
            alpha_in  = min(elapsed / fade_in,  1.0)
            alpha_out = min(remaining / fade_out, 1.0)
            alpha = min(alpha_in, alpha_out)
            table[f] = (text, alpha)
    return table


def make_font(size):
    return ImageFont.truetype(FONT, size)


def render_frame(draw, img, font, text, alpha):
    img.paste((0, 0, 0), [0, 0, W, H])
    if text is None or alpha <= 0:
        return
    color = (int(255 * alpha),) * 3

    # Word-wrap if text exceeds max width
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        bbox = font.getbbox(test)
        if bbox[2] - bbox[0] > MAX_LINE_WIDTH and current:
            lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)

    line_height = font.getbbox("A")[3] + 10
    total_height = line_height * len(lines)
    y = (H - total_height) // 2

    for line in lines:
        bbox = font.getbbox(line)
        lw = bbox[2] - bbox[0]
        x = (W - lw) // 2
        draw.text((x, y), line, font=font, fill=color)
        y += line_height


def main():
    print(f"Building frame lookup ({TOTAL_FRAMES} frames)...", file=sys.stderr)
    table = build_lookup(FPS, TOTAL_FRAMES, LYRICS, FADE_IN_FRAMES, FADE_OUT_FRAMES)

    font = make_font(FONT_SIZE)
    img  = Image.new("RGB", (W, H), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    import io

    ffmpeg_cmd = [
        FFMPEG, "-y",
        "-f", "image2pipe", "-framerate", str(FPS), "-vcodec", "png",
        "-i", "pipe:0",
        "-i", AUDIO,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        "-pix_fmt", "yuv420p",
        OUTPUT,
    ]

    print("Starting FFmpeg...", file=sys.stderr)
    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    prev_text, prev_alpha = None, -1.0
    for i, (text, alpha) in enumerate(table):
        if i % 300 == 0:
            pct = i * 100 // TOTAL_FRAMES
            print(f"  {pct}% — frame {i}/{TOTAL_FRAMES}", file=sys.stderr, flush=True)

        # Only re-render if something changed
        if text != prev_text or abs(alpha - prev_alpha) > 0.004:
            render_frame(draw, img, font, text, alpha)
            prev_text, prev_alpha = text, alpha

        try:
            buf = io.BytesIO()
            img.save(buf, format="PNG", compress_level=1)
            proc.stdin.write(buf.getvalue())
        except BrokenPipeError:
            break  # FFmpeg consumed all it needed (audio ended)

    try:
        proc.stdin.close()
    except BrokenPipeError:
        pass
    _, stderr = proc.communicate()
    if proc.returncode not in (0, None):
        print("FFmpeg error:", stderr.decode(), file=sys.stderr)
        sys.exit(1)

    print(f"\nVideo listo: {OUTPUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
