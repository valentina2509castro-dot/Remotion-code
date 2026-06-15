import React from "react";
import {
  AbsoluteFill,
  Audio,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

// ─── Estructura de la canción ────────────────────────────────────────────────
// Tiempos en segundos. Ajusta start/end escuchando la canción si es necesario.

type Section = "verse" | "prechorus" | "chorus" | "bridge" | "link";

interface Lyric {
  text: string;
  start: number;
  end: number;
  section: Section;
}

const LYRICS: Lyric[] = [
  // VERSO 1 — Confesión (0:14 - 0:50)
  { text: "Qué caro estoy pagando",                         start: 14,    end: 23,    section: "verse" },
  { text: "El haber traicionado",                           start: 23,    end: 32,    section: "verse" },
  { text: "El amor que me daba, por una locura",            start: 32,    end: 41.5,  section: "verse" },
  { text: "Qué estúpido fui",                               start: 41.5,  end: 50,    section: "verse" },
  // PRE-CORO 1 — Arrepentimiento (0:50 - 1:18)
  { text: "Ella fue una aventura",                          start: 50,    end: 57,    section: "prechorus" },
  { text: "Tan solo un pasatiempo",                         start: 57,    end: 64,    section: "prechorus" },
  { text: "Con arrepentimiento sincero, hoy vengo",         start: 64,    end: 72,    section: "prechorus" },
  { text: "A pedirte perdón",                               start: 72,    end: 78,    section: "prechorus" },
  // CORO 1 — Súplica (1:18 - 1:50)
  { text: "De rodillas te pido, te ruego, te digo",         start: 78,    end: 86,    section: "chorus" },
  { text: "Que regreses conmigo, que no te he olvidado",    start: 86,    end: 94,    section: "chorus" },
  { text: "Que te extrañan mis manos, que muero de ganas",  start: 94,    end: 102,   section: "chorus" },
  { text: "Por volverte a besar",                           start: 102,   end: 110,   section: "chorus" },
  // PUENTE — Miedo y celos (1:50 - 2:18)
  { text: "En las noches despierto gritando tu nombre",     start: 110,   end: 117,   section: "bridge" },
  { text: "Y me lleno de miedo al pensar que a otro hombre",start: 117,   end: 124,   section: "bridge" },
  { text: "Le estarás entregando tus besos, tu cuerpo",     start: 124,   end: 131,   section: "bridge" },
  { text: "No quiero ni pensar",                            start: 131,   end: 138,   section: "bridge" },
  // LINK — Respiro dramático (2:18 - 2:25)
  { text: "De rodillas te pido",                            start: 138,   end: 145,   section: "link" },
  // PRE-CORO 2 (2:25 - 2:52)
  { text: "Ella fue una aventura",                          start: 145,   end: 152,   section: "prechorus" },
  { text: "Tan solo un pasatiempo",                         start: 152,   end: 159,   section: "prechorus" },
  { text: "Con arrepentimiento sincero, hoy vengo",         start: 159,   end: 166,   section: "prechorus" },
  { text: "A pedirte perdón",                               start: 166,   end: 172,   section: "prechorus" },
  // CORO 2 — Clímax (2:52 - 3:14)
  { text: "De rodillas te pido, te ruego, te digo",         start: 172,   end: 177.5, section: "chorus" },
  { text: "Que regreses conmigo, que no te he olvidado",    start: 177.5, end: 183,   section: "chorus" },
  { text: "Que te extrañan mis manos, que muero de ganas",  start: 183,   end: 188.5, section: "chorus" },
  { text: "Por volverte a besar",                           start: 188.5, end: 194,   section: "chorus" },
  // OUTRO — Fade emocional (3:14 - 3:36)
  { text: "En las noches despierto gritando tu nombre",     start: 194,   end: 198.5, section: "bridge" },
  { text: "Y me lleno de miedo al pensar que a otro hombre",start: 198.5, end: 203,   section: "bridge" },
  { text: "Le estarás entregando tus besos, tu cuerpo",     start: 203,   end: 207.5, section: "bridge" },
  { text: "No quiero ni pensar",                            start: 207.5, end: 212,   section: "bridge" },
  { text: "De rodillas te pido",                            start: 212,   end: 216,   section: "link" },
];

// ─── Estilos por sección ─────────────────────────────────────────────────────

const SECTION_STYLE: Record<Section, React.CSSProperties> = {
  verse: {
    color: "#F5E6C8",       // crema cálido
    fontSize: 56,
    fontStyle: "italic",
    textShadow: "0 2px 24px rgba(0,0,0,0.9)",
  },
  prechorus: {
    color: "#D4A843",       // ocre dorado
    fontSize: 58,
    fontStyle: "italic",
    textShadow: "0 2px 24px rgba(0,0,0,0.9)",
  },
  chorus: {
    color: "#F0C040",       // dorado brillante
    fontSize: 66,
    fontStyle: "italic",
    textShadow:
      "0 0 40px rgba(240,192,64,0.35), 0 2px 24px rgba(0,0,0,0.95)",
  },
  bridge: {
    color: "#C8D8E8",       // blanco azulado — angustia
    fontSize: 52,
    fontStyle: "italic",
    textShadow: "0 2px 24px rgba(0,0,0,0.9)",
  },
  link: {
    color: "#F0C040",
    fontSize: 72,
    fontStyle: "italic",
    textShadow:
      "0 0 60px rgba(240,192,64,0.5), 0 0 20px rgba(240,192,64,0.3), 0 2px 30px rgba(0,0,0,1)",
  },
};

// ─── Componente ──────────────────────────────────────────────────────────────

export const LyricVideo: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentTime = frame / fps;

  const lyric = LYRICS.find(
    (l) => currentTime >= l.start && currentTime < l.end
  ) ?? null;

  const isChorus = lyric?.section === "chorus" || lyric?.section === "link";

  // Fade-in: 0.4s suave con leve subida desde abajo
  const fadeIn = lyric
    ? interpolate(currentTime - lyric.start, [0, 0.4], [0, 1], {
        extrapolateRight: "clamp",
      })
    : 0;

  // Fade-out: 0.35s al final de cada línea
  const fadeOut = lyric
    ? interpolate(lyric.end - currentTime, [0, 0.35], [0, 1], {
        extrapolateRight: "clamp",
      })
    : 1;

  const opacity = Math.min(fadeIn, fadeOut);

  // Entrada: texto sube ligeramente
  const translateY = lyric
    ? interpolate(currentTime - lyric.start, [0, 0.5], [18, 0], {
        extrapolateRight: "clamp",
      })
    : 0;

  // Escala: coro y link aparecen con un leve zoom-in
  const scale = isChorus
    ? interpolate(currentTime - (lyric?.start ?? 0), [0, 0.7], [0.93, 1], {
        extrapolateRight: "clamp",
      })
    : 1;

  // Oscurecimiento progresivo del outro (últimos 22 segundos)
  const outroDim =
    currentTime > 194
      ? interpolate(currentTime, [194, 216], [0, 0.6], {
          extrapolateRight: "clamp",
        })
      : 0;

  const sectionStyle = lyric ? SECTION_STYLE[lyric.section] : {};

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#0D0806",
        fontFamily: "Georgia, 'Playfair Display', 'Times New Roman', serif",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {/* Audio */}
      <Audio src={staticFile("DE_RODILLAS_TE_PIDO_MASTER_2026.wav")} />

      {/* Viñeta cinematográfica */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "radial-gradient(ellipse at 50% 60%, transparent 35%, rgba(0,0,0,0.75) 100%)",
          pointerEvents: "none",
        }}
      />

      {/* Oscurecimiento del outro */}
      {outroDim > 0 && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            backgroundColor: `rgba(0,0,0,${outroDim})`,
            pointerEvents: "none",
          }}
        />
      )}

      {/* Texto de la lírica */}
      {lyric && (
        <p
          style={{
            opacity,
            transform: `translateY(${translateY}px) scale(${scale})`,
            textAlign: "center",
            padding: "0 100px",
            maxWidth: 1200,
            lineHeight: 1.4,
            margin: 0,
            letterSpacing: "0.01em",
            ...sectionStyle,
          }}
        >
          {lyric.text}
        </p>
      )}

      {/* Nombre del artista — solo en el intro */}
      {currentTime < 12 && (
        <div
          style={{
            position: "absolute",
            bottom: 80,
            left: 0,
            right: 0,
            textAlign: "center",
            color: "#D4A843",
            fontSize: 28,
            fontStyle: "italic",
            letterSpacing: "0.15em",
            opacity: interpolate(currentTime, [0, 1.5, 10, 12], [0, 1, 1, 0], {
              extrapolateRight: "clamp",
            }),
          }}
        >
          De Rodillas Te Pido
        </div>
      )}
    </AbsoluteFill>
  );
};
