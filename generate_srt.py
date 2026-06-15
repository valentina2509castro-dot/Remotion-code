#!/usr/bin/env python3
"""
Genera SRT sincronizado usando los límites de sección detectados
por análisis cromático del audio real.
"""

LYRICS = [
    # ── VERSO 1 (14.85 - 66.82s = 51.97s / 8 líneas = 6.50s c/u) ──────────
    ("Qué caro estoy pagando",                          14.85,  21.35),
    ("El haber traicionado",                            21.35,  27.85),
    ("El amor que me daba, por una locura",             27.85,  34.35),
    ("Qué estúpido fui",                                34.35,  40.85),
    # ── PRE-CORO 1 ──────────────────────────────────────────────────────────
    ("Ella fue una aventura",                           40.85,  47.35),
    ("Tan solo un pasatiempo",                          47.35,  53.85),
    ("Con arrepentimiento sincero, hoy vengo",          53.85,  60.35),
    ("A pedirte perdón",                                60.35,  66.82),
    # ── CORO 1 (límites exactos: 66.82 / 74.75 / 82.69 / 96.00) ────────────
    ("De rodillas te pido, te ruego, te digo",          66.82,  74.75),
    ("Que regreses conmigo, que no te he olvidado",     74.75,  82.69),
    ("Que te extrañan mis manos, que muero de ganas",   82.69,  89.35),
    ("Por volverte a besar",                            89.35,  96.00),
    # ── PUENTE 1 (96.00 - 118.78s = 22.78s / 4 líneas = 5.70s c/u) ─────────
    ("En las noches despierto gritando tu nombre",      96.00, 101.70),
    ("Y me lleno de miedo al pensar que a otro hombre",101.70, 107.40),
    ("Le estarás entregando tus besos, tu cuerpo",     107.40, 113.10),
    ("No quiero ni pensar",                            113.10, 118.78),
    # ── LINK (límite detectado: 135.17 - 141.82s) ───────────────────────────
    ("De rodillas te pido",                            135.17, 141.82),
    # ── PRE-CORO 2 (141.82 - 169.98s = 28.16s / 4 líneas = 7.04s c/u) ──────
    ("Ella fue una aventura",                          141.82, 148.86),
    ("Tan solo un pasatiempo",                         148.86, 155.90),
    ("Con arrepentimiento sincero, hoy vengo",         155.90, 162.94),
    ("A pedirte perdón",                               162.94, 169.98),
    # ── CORO 2 (169.98 - 193.02s = 23.04s / 4 líneas = 5.76s c/u) ──────────
    ("De rodillas te pido, te ruego, te digo",         169.98, 175.74),
    ("Que regreses conmigo, que no te he olvidado",    175.74, 181.50),
    ("Que te extrañan mis manos, que muero de ganas",  181.50, 187.26),
    ("Por volverte a besar",                           187.26, 193.02),
    # ── OUTRO (193.02 - 212.00s / 5 líneas) ─────────────────────────────────
    ("En las noches despierto gritando tu nombre",     193.02, 196.73),
    ("Y me lleno de miedo al pensar que a otro hombre",196.73, 200.44),
    ("Le estarás entregando tus besos, tu cuerpo",     200.44, 204.15),
    ("No quiero ni pensar",                            204.15, 207.87),
    ("De rodillas te pido",                            207.87, 212.00),
]

def seconds_to_srt(s):
    h   = int(s // 3600)
    m   = int((s % 3600) // 60)
    sec = int(s % 60)
    ms  = int(round((s - int(s)) * 1000))
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"

srt_path = "/home/user/Remotion-code/public/de-rodillas-te-pido.srt"
with open(srt_path, "w", encoding="utf-8") as f:
    for i, (text, start, end) in enumerate(LYRICS, 1):
        f.write(f"{i}\n")
        f.write(f"{seconds_to_srt(start)} --> {seconds_to_srt(end)}\n")
        f.write(f"{text}\n\n")

print(f"SRT generado: {srt_path}")
print(f"Total líneas: {len(LYRICS)}")
print("\nPrimeras 5 entradas:")
for i, (text, start, end) in enumerate(LYRICS[:5], 1):
    print(f"  {i}. [{start:.2f}s - {end:.2f}s] {text}")
