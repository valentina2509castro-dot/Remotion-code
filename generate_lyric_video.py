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
    ("Qué caro estoy pagando",                          14.0,   23.0),
    ("El haber traicionado",                            23.0,   32.0),
    ("El amor que me daba, por una locura",             32.0,   41.5),
    ("Qué estúpido fui",                                41.5,   50.0),
    ("Ella fue una aventura",                           50.0,   57.0),
    ("Tan solo un pasatiempo",                          57.0,   64.0),
    ("Con arrepentimiento sincero, hoy vengo",          64.0,   72.0),
    ("A pedirte perdón",                                72.0,   78.0),
    ("De rodillas te pido, te ruego, te digo",          78.0,   86.0),
    ("Que regreses conmigo, que no te he olvidado",     86.0,   94.0),
    ("Que te extrañan mis manos, que muero de ganas",   94.0,  102.0),
    ("Por volverte a besar",                           102.0,  110.0),
    ("En las noches despierto gritando tu nombre",     110.0,  117.0),
    ("Y me lleno de miedo al pensar que a otro hombre",117.0,  124.0),
    ("Le estarás entregando tus besos, tu cuerpo",     124.0,  131.0),
    ("No quiero ni pensar",                            131.0,  138.0),
    ("De rodillas te pido",                            138.0,  145.0),
    ("Ella fue una aventura",                          145.0,  152.0),
    ("Tan solo un pasatiempo",                         152.0,  159.0),
    ("Con arrepentimiento sincero, hoy vengo",         159.0,  166.0),
    ("A pedirte perdón",                               166.0,  172.0),
    ("De rodillas te pido, te ruego, te digo",         172.0,  177.5),
    ("Que regreses conmigo, que no te he olvidado",    177.5,  183.0),
    ("Que te extrañan mis manos, que muero de ganas",  183.0,  188.5),
    ("Por volverte a besar",                           188.5,  194.0),
    ("En las noches despierto gritando tu nombre",     194.0,  198.5),
    ("Y me lleno de miedo al pensar que a otro hombre",198.5,  203.0),
    ("Le estarás entregando tus besos, tu cuerpo",     203.0,  207.5),
    ("No quiero ni pensar",                            207.5,  212.0),
    ("De rodillas te pido",                            212.0,  216.0),
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
