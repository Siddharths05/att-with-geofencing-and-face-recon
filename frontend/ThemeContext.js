// ThemeContext.js
// Provides the active theme (light / dark / reader) to the whole app.
// "light" and "dark" can follow the device's system setting; "reader" is
// always an explicit manual choice (there's no OS-level "reader mode").
// The choice is persisted to AsyncStorage.
//
// Usage:
//   1. Wrap your app root once:
//        import { ThemeProvider } from "./ThemeContext";
//        export default function App() {
//          return (
//            <ThemeProvider>
//              <YourNavigator />
//            </ThemeProvider>
//          );
//        }
//
//   2. In any screen:
//        import { useTheme } from "../ThemeContext";
//        const { colors, spacing, radius, shadow, typography, mode, isDark, cycleTheme } = useTheme();

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useMemo,
} from "react";
import { useColorScheme } from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import {
  lightColors,
  darkColors,
  readerColors,
  radius,
  spacing,
  getShadow,
  getTypography,
} from "./theme";

const THEME_STORAGE_KEY = "theme_preference"; // "light" | "dark" | "reader" | "system"
const MODE_ORDER = ["light", "dark", "reader"];

const ThemeContext = createContext(null);

export function ThemeProvider({ children }) {
  const systemScheme = useColorScheme(); // "light" | "dark" | null
  const [preference, setPreference] = useState("system");
  const [ready, setReady] = useState(false);

  // Load any saved manual preference on mount.
  useEffect(() => {
    let isMounted = true;
    AsyncStorage.getItem(THEME_STORAGE_KEY)
      .then((saved) => {
        if (isMounted && (saved === "light" || saved === "dark" || saved === "reader" || saved === "system")) {
          setPreference(saved);
        }
      })
      .catch(() => {
        // If storage read fails, just fall back to system preference.
      })
      .finally(() => {
        if (isMounted) setReady(true);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  // "reader" has no system equivalent, so "system" only ever resolves to
  // light or dark based on the device setting.
  const mode = preference === "system" ? systemScheme || "light" : preference;
  const isDark = mode === "dark";

  const setThemePreference = async (next) => {
    setPreference(next);
    try {
      await AsyncStorage.setItem(THEME_STORAGE_KEY, next);
    } catch (e) {
      // Non-fatal: preference just won't persist across app restarts.
    }
  };

  // Cycles light -> dark -> reader -> light.
  const cycleTheme = () => {
    const currentIndex = MODE_ORDER.indexOf(mode);
    const next = MODE_ORDER[(currentIndex + 1) % MODE_ORDER.length];
    setThemePreference(next);
  };

  // Kept for backward compatibility with older screens; just toggles
  // between light and dark (skips reader).
  const toggleTheme = () => setThemePreference(isDark ? "light" : "dark");

  const value = useMemo(() => {
    const palettes = { light: lightColors, dark: darkColors, reader: readerColors };
    const activeColors = palettes[mode] || lightColors;
    return {
      mode, // "light" | "dark" | "reader"
      isDark,
      preference, // "light" | "dark" | "reader" | "system"
      colors: activeColors,
      radius,
      spacing,
      shadow: getShadow(isDark),
      typography: getTypography(activeColors, mode),
      setThemePreference,
      cycleTheme,
      toggleTheme,
    };
  }, [mode, isDark, preference]);

  // Avoid a flash of the wrong theme while the saved preference loads.
  if (!ready) return null;

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error("useTheme() must be used inside a <ThemeProvider>");
  }
  return ctx;
}