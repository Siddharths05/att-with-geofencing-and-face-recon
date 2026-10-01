// theme.js
// Defines the light, dark, and reader palettes plus shared design tokens.
// Light mode  = white surfaces + accent.
// Dark mode   = black/near-black surfaces + a deeper accent.
// Reader mode = the light palette with a warm paper tint on the surfaces.
//
// The accent ("secondary color") can be "purple" or "blue" and works in
// every mode. Use getPalette(mode, accent) to get a full palette.

import { Platform } from "react-native";

export const ACCENT_OPTIONS = [
  { key: "purple", label: "Purple", swatch: "#A64DFF" },
  { key: "blue", label: "Blue", swatch: "#3B82F6" },
];

// ---- Neutral parts of each palette (do not change with the accent) ----
const lightBase = {
  bg: "#FFFFFF",
  card: "#FFFFFF",
  inputBg: "#FBFBFC",
  danger: "#DC2626",
  dangerSoft: "#FDECEC",
  amber: "#D97706",
  amberSoft: "#FEF3E2",
  dangerBorder: "#F7C6C6",
  dangerBadgeBg: "#F6D0D0",
  dangerText: "#B02323",
};

const darkBase = {
  bg: "#000000",
  danger: "#F87171",
  dangerSoft: "#3A1B1B",
  amber: "#FBBF24",
  amberSoft: "#3A2E12",
  dangerBorder: "#5A2B2B",
  dangerBadgeBg: "#5A2B2B",
  dangerText: "#FCA5A5",
};

// ---- Accent-dependent tokens, per accent and per light/dark ----
// (primary + its soft fill, the "success" status colors, and the slightly
// accent-tinted borders / text greys / dark surfaces.)
const ACCENT_TOKENS = {
  purple: {
    light: {
      primary: "#A64DFF",
      primarySoft: "#F2E6FF",
      border: "#ECE6F9",
      text: "#1A1523",
      textMuted: "#6B6478",
      textFaint: "#A79FB8",
      successBorder: "#E3CBFF",
      successBadgeBg: "#EBD9FF",
      successText: "#7A1FCB",
    },
    dark: {
      primary: "#7A1FCB",
      primarySoft: "#241333",
      card: "#150F1D",
      inputBg: "#0D0D10",
      border: "#2B2136",
      text: "#F5F2FA",
      textMuted: "#B4A9C4",
      textFaint: "#847893",
      successBorder: "#3A2A55",
      successBadgeBg: "#3A2A55",
      successText: "#D6B4FF",
    },
  },
  blue: {
    light: {
      primary: "#3B82F6",
      primarySoft: "#E6F0FF",
      border: "#E3EAF7",
      text: "#131A28",
      textMuted: "#5F6B80",
      textFaint: "#9AA5B8",
      successBorder: "#C7DBFF",
      successBadgeBg: "#D6E5FF",
      successText: "#1D4ED8",
    },
    dark: {
      primary: "#2563EB",
      primarySoft: "#12203A",
      card: "#0F1522",
      inputBg: "#0B0D12",
      border: "#1F2B42",
      text: "#F2F5FA",
      textMuted: "#A9B6CC",
      textFaint: "#76849C",
      successBorder: "#24406B",
      successBadgeBg: "#24406B",
      successText: "#A9C8FF",
    },
  },
};

// ---- Reader mode: light palette + warm paper tint on the surfaces ----
// Accent, text, and status colors are unchanged -- only the
// backgrounds/borders/soft fills pick up the tint.
const READER_TINT = "#F4E4C1"; // warm sepia
const READER_TINT_STRENGTH = 0.45; // 0 = no tint, 1 = fully sepia. Adjust to taste.

function tint(hex, amount = READER_TINT_STRENGTH) {
  const parse = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  const [r, g, b] = parse(hex);
  const [tr, tg, tb] = parse(READER_TINT);
  const mix = (a, t) =>
    Math.round(a + (t - a) * amount).toString(16).padStart(2, "0");
  return `#${mix(r, tr)}${mix(g, tg)}${mix(b, tb)}`.toUpperCase();
}

function buildReader(light) {
  return {
    ...light,
    bg: tint(light.bg),
    card: tint(light.card, 0.3), // a bit lighter than bg so cards still lift
    inputBg: tint(light.inputBg, 0.35),
    border: tint(light.border),
    primarySoft: tint(light.primarySoft),
    dangerSoft: tint(light.dangerSoft),
    amberSoft: tint(light.amberSoft),
  };
}

// mode: "light" | "dark" | "reader"; accent: "purple" | "blue"
export function getPalette(mode, accent = "purple") {
  const tokens = ACCENT_TOKENS[accent] || ACCENT_TOKENS.purple;
  if (mode === "dark") return { ...darkBase, ...tokens.dark };
  const light = { ...lightBase, ...tokens.light };
  return mode === "reader" ? buildReader(light) : light;
}

// Default (purple) palettes, kept for backward compatibility with any file
// that imports these directly.
export const lightColors = getPalette("light", "purple");
export const darkColors = getPalette("dark", "purple");
export const readerColors = getPalette("reader", "purple");

// Backward-compatible default export (light palette), in case any other
// file imports `colors` directly without going through the theme context.
export const colors = lightColors;

export const radius = {
  sm: 8,
  md: 14,
  lg: 20,
  pill: 999,
};

export const spacing = {
  xs: 6,
  sm: 12,
  md: 16,
  lg: 24,
  xl: 32,
};

export function getShadow(isDark) {
  return {
    shadowColor: isDark ? "#000000" : "#0F172A",
    shadowOpacity: isDark ? 0.5 : 0.06,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 6 },
    elevation: 2,
  };
}

// Kept for backward compatibility (light mode shadow).
export const shadow = getShadow(false);

export function getTypography(themeColors, mode) {
  const isReader = mode === "reader";
  const fontFamily = isReader
    ? Platform.select({ ios: "Georgia", android: "serif", default: "serif" })
    : undefined;

  return {
    h1: { fontSize: isReader ? 24 : 26, fontWeight: "700", color: themeColors.text, fontFamily },
    h2: { fontSize: 18, fontWeight: "600", color: themeColors.text, fontFamily },
    body: {
      fontSize: isReader ? 16 : 15,
      fontWeight: "400",
      color: themeColors.text,
      fontFamily,
      lineHeight: isReader ? 24 : undefined,
    },
    label: { fontSize: 13, fontWeight: "600", color: themeColors.textMuted },
    small: { fontSize: 12, fontWeight: "400", color: themeColors.textFaint },
  };
}

// Kept for backward compatibility (light mode typography).
export const typography = getTypography(lightColors);