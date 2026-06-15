import React from "react";
import {
  AbsoluteFill,
  Audio,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

interface Lyric {
  text: string;
  start: number; // segundos
  end: number;
}

const LYRICS: Lyric[] = [
  { text: "Qué caro estoy pagando",                          start: 14,    end: 23    },
  { text: "El haber traicionado",                            start: 23,    end: 32    },
  { text: "El amor que me daba, por una locura",             start: 32,    end: 41.5  },
  { text: "Qué estúpido fui",                                start: 41.5,  end: 50    },
  { text: "Ella fue una aventura",                           start: 50,    end: 57    },
  { text: "Tan solo un pasatiempo",                          start: 57,    end: 64    },
  { text: "Con arrepentimiento sincero, hoy vengo",          start: 64,    end: 72    },
  { text: "A pedirte perdón",                                start: 72,    end: 78    },
  { text: "De rodillas te pido, te ruego, te digo",          start: 78,    end: 86    },
  { text: "Que regreses conmigo, que no te he olvidado",     start: 86,    end: 94    },
  { text: "Que te extrañan mis manos, que muero de ganas",   start: 94,    end: 102   },
  { text: "Por volverte a besar",                            start: 102,   end: 110   },
  { text: "En las noches despierto gritando tu nombre",      start: 110,   end: 117   },
  { text: "Y me lleno de miedo al pensar que a otro hombre", start: 117,   end: 124   },
  { text: "Le estarás entregando tus besos, tu cuerpo",      start: 124,   end: 131   },
  { text: "No quiero ni pensar",                             start: 131,   end: 138   },
  { text: "De rodillas te pido",                             start: 138,   end: 145   },
  { text: "Ella fue una aventura",                           start: 145,   end: 152   },
  { text: "Tan solo un pasatiempo",                          start: 152,   end: 159   },
  { text: "Con arrepentimiento sincero, hoy vengo",          start: 159,   end: 166   },
  { text: "A pedirte perdón",                                start: 166,   end: 172   },
  { text: "De rodillas te pido, te ruego, te digo",          start: 172,   end: 177.5 },
  { text: "Que regreses conmigo, que no te he olvidado",     start: 177.5, end: 183   },
  { text: "Que te extrañan mis manos, que muero de ganas",   start: 183,   end: 188.5 },
  { text: "Por volverte a besar",                            start: 188.5, end: 194   },
  { text: "En las noches despierto gritando tu nombre",      start: 194,   end: 198.5 },
  { text: "Y me lleno de miedo al pensar que a otro hombre", start: 198.5, end: 203   },
  { text: "Le estarás entregando tus besos, tu cuerpo",      start: 203,   end: 207.5 },
  { text: "No quiero ni pensar",                             start: 207.5, end: 212   },
  { text: "De rodillas te pido",                             start: 212,   end: 216   },
];

const FADE_IN_DURATION = 0.4;  // segundos
const FADE_OUT_DURATION = 0.4; // segundos

export const LyricVideo: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentTime = frame / fps;

  const lyric = LYRICS.find(
    (l) => currentTime >= l.start && currentTime < l.end
  ) ?? null;

  const opacity = lyric
    ? Math.min(
        interpolate(
          currentTime - lyric.start,
          [0, FADE_IN_DURATION],
          [0, 1],
          { extrapolateRight: "clamp" }
        ),
        interpolate(
          lyric.end - currentTime,
          [0, FADE_OUT_DURATION],
          [0, 1],
          { extrapolateRight: "clamp" }
        )
      )
    : 0;

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#000000",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "0 120px",
      }}
    >
      <Audio src={staticFile("DE_RODILLAS_TE_PIDO_MASTER_2026.wav")} />

      {lyric && (
        <p
          style={{
            opacity,
            color: "#ffffff",
            fontSize: 64,
            fontFamily:
              "Helvetica Neue, Helvetica, Arial, sans-serif",
            fontWeight: 300,
            textAlign: "center",
            lineHeight: 1.35,
            margin: 0,
            letterSpacing: "0.02em",
          }}
        >
          {lyric.text}
        </p>
      )}
    </AbsoluteFill>
  );
};
