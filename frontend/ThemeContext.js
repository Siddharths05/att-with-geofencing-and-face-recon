// ThemeContext.js
// Provides the active theme (light / dark / reader) and accent color
// (purple / blue) to the whole app.
// "light" and "dark" can follow the device's system setting; "reader" is
// always an explicit manual choice (there's no OS-level "reader mode").
// Both choices are persisted to AsyncStorage.
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
//        const {
//          colors, spacing, radius, shadow, typography,
//          mode, isDark, cycleTheme,
//          accent, setAccent, accentOptions,
//        } = useTheme();

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
  ACCENT_OPTIONS,
  getPalette,
  radius,
  spacing,
  getShadow,
  getTypography,
} from "./theme";

const THEME_STORAGE_KEY = "theme_preference"; // "light" | "dark" | "reader" | "system"
const ACCENT_STORAGE_KEY = "accent_preference"; // "purple" | "blue"
const MODE_ORDER = ["light", "dark", "reader"];
const ACCENT_KEYS = ACCENT_OPTIONS.map((a) => a.key);

const ThemeContext = createContext(null);

export function ThemeProvider({ children }) {
  const systemScheme = useColorScheme(); // "light" | "dark" | null
  const [preference, setPreference] = useState("system");
  const [accent, setAccentState] = useState("purple");
  const [ready, setReady] = useState(false);

  // Load any saved manual preferences on mount.
  useEffect(() => {
    let isMounted = true;
    AsyncStorage.multiGet([THEME_STORAGE_KEY, ACCENT_STORAGE_KEY])
      .then((pairs) => {
        if (!isMounted) return;
        const saved = Object.fromEntries(pairs);
        const savedTheme = saved[THEME_STORAGE_KEY];
        const savedAccent = saved[ACCENT_STORAGE_KEY];
        if (
          savedTheme === "light" ||
          savedTheme === "dark" ||
          savedTheme === "reader" ||
          savedTheme === "system"
        ) {
          setPreference(savedTheme);
        }
        if (ACCENT_KEYS.includes(savedAccent)) {
          setAccentState(savedAccent);
        }
      })
      .catch(() => {
        // If storage read fails, just fall back to defaults.
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

  // Choose the accent color: "purple" | "blue". Works in every mode.
  const setAccent = async (next) => {
    if (!ACCENT_KEYS.includes(next)) return;
    setAccentState(next);
    try {
      await AsyncStorage.setItem(ACCENT_STORAGE_KEY, next);
    } catch (e) {
      // Non-fatal: accent just won't persist across app restarts.
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
    const activeColors = getPalette(mode, accent);
    return {
      mode, // "light" | "dark" | "reader"
      isDark,
      preference, // "light" | "dark" | "reader" | "system"
      accent, // "purple" | "blue"
      accentOptions: ACCENT_OPTIONS, // [{ key, label, swatch }]
      colors: activeColors,
      radius,
      spacing,
      shadow: getShadow(isDark),
      typography: getTypography(activeColors, mode),
      setThemePreference,
      setAccent,
      cycleTheme,
      toggleTheme,
    };
  }, [mode, isDark, preference, accent]);

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