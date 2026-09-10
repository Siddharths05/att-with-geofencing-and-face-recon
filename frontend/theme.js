// theme.js
// Defines the light, dark, and reader palettes plus shared design tokens.
// Light mode  = white surfaces + a lighter purple accent.
// Dark mode   = black/near-black surfaces + a darker purple accent.
// Reader mode = warm sepia paper + a muted brown-amber accent.

import { Platform } from "react-native";

export const lightColors = {
  bg: "#FFFFFF",
  card: "#FFFFFF",
  border: "#ECE6F9",
  text: "#1A1523",
  textMuted: "#6B6478",
  textFaint: "#A79FB8",
  primary: "#A64DFF", // lighter purple
  primarySoft: "#F2E6FF",
  inputBg: "#FBFBFC",
  danger: "#DC2626",
  dangerSoft: "#FDECEC",
  amber: "#D97706",
  amberSoft: "#FEF3E2",
  // Status accents used e.g. for the "Present"/"Rejected" result card.
  successBorder: "#E3CBFF",
  successBadgeBg: "#EBD9FF",
  successText: "#7A1FCB",
  dangerBorder: "#F7C6C6",
  dangerBadgeBg: "#F6D0D0",
  dangerText: "#B02323",
};

export const darkColors = {
  bg: "#000000",
  card: "#150F1D",
  border: "#2B2136",
  text: "#F5F2FA",
  textMuted: "#B4A9C4",
  textFaint: "#847893",
  primary: "#7A1FCB", // darker purple
  primarySoft: "#241333",
  inputBg: "#0D0D10",
  danger: "#F87171",
  dangerSoft: "#3A1B1B",
  amber: "#FBBF24",
  amberSoft: "#3A2E12",
  successBorder: "#3A2A55",
  successBadgeBg: "#3A2A55",
  successText: "#D6B4FF",
  dangerBorder: "#5A2B2B",
  dangerBadgeBg: "#5A2B2B",
  dangerText: "#FCA5A5",
};

// Reader mode: warm sepia "paper" surfaces with a muted brown-amber accent —
// meant to be easy on the eyes for reading-heavy screens.
export const readerColors = {
  bg: "#F4ECD8",
  card: "#FBF6E9",
  border: "#E4D6B8",
  text: "#3B2E20",
  textMuted: "#7A6A4E",
  textFaint: "#A79877",
  primary: "#8B5E34",
  primarySoft: "#EADFC4",
  inputBg: "#F7EFDC",
  danger: "#B23A2E",
  dangerSoft: "#F3DDD6",
  amber: "#A9752E",
  amberSoft: "#F1E2C2",
  successBorder: "#D7C193",
  successBadgeBg: "#E3D2A6",
  successText: "#5C3A1E",
  dangerBorder: "#E3B7A8",
  dangerBadgeBg: "#F0DCCF",
  dangerText: "#8A3A2A",
};

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