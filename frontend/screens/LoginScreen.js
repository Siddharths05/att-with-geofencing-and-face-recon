import React, { useState, useMemo } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StatusBar,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import api from "../api";
import { useTheme } from "../ThemeContext";

// FastAPI returns `detail` as a plain string for most errors (e.g. wrong
// credentials), but as an ARRAY of validation-error objects for 422s (e.g.
// missing/malformed fields). Handle both so Alert.alert always gets a string.
function getErrorMessage(err) {
  const detail = err.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => d.msg).join("\n");
  }
  return "Login failed";
}

export default function LoginScreen({ navigation }) {
  const theme = useTheme();
  const {
    colors,
    mode,
    isDark,
    cycleTheme,
    accent,
    setAccent,
    accentOptions,
  } = theme;
  const styles = useMemo(() => createStyles(theme), [theme]);
  const themeLabel = { light: "Light", dark: "Dark", reader: "Reader" }[mode];

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    if (!username || !password) {
      Alert.alert("Missing fields", "Please enter username and password");
      return;
    }
    setLoading(true);
    try {
      const res = await api.post("/login", { username, password });
      await AsyncStorage.setItem("token", res.data.access_token);
      navigation.replace("Attendance");
    } catch (err) {
      Alert.alert("Error", getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.screen}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <StatusBar barStyle={isDark ? "light-content" : "dark-content"} />
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.toggleRow}>
          {/* Accent (secondary color) picker */}
          <View style={styles.accentPicker}>
            {accentOptions.map((opt) => {
              const selected = opt.key === accent;
              return (
                <TouchableOpacity
                  key={opt.key}
                  onPress={() => setAccent(opt.key)}
                  activeOpacity={0.8}
                  accessibilityRole="button"
                  accessibilityLabel={`${opt.label} accent`}
                  accessibilityState={{ selected }}
                  style={[
                    styles.swatchRing,
                    selected && { borderColor: opt.swatch },
                  ]}
                >
                  <View
                    style={[styles.swatch, { backgroundColor: opt.swatch }]}
                  />
                </TouchableOpacity>
              );
            })}
          </View>

          <TouchableOpacity
            style={styles.themeToggle}
            onPress={cycleTheme}
            activeOpacity={0.8}
          >
            <Text style={styles.themeToggleText}>{themeLabel}</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.brandRow}>
          <View style={styles.logoMark}>
            <Text style={styles.logoMarkText}>A</Text>
          </View>
          <Text style={styles.brandName}>Attendance</Text>
        </View>

        <View style={styles.card}>
          <Text style={styles.title}>Welcome back</Text>
          <Text style={styles.subtitle}>Sign in to mark today's attendance</Text>

          <View style={styles.field}>
            <Text style={styles.label}>Username</Text>
            <TextInput
              style={styles.input}
              placeholder="e.g. testuser1"
              placeholderTextColor={colors.textFaint}
              autoCapitalize="none"
              autoCorrect={false}
              value={username}
              onChangeText={setUsername}
            />
          </View>

          <View style={styles.field}>
            <Text style={styles.label}>Password</Text>
            <TextInput
              style={styles.input}
              placeholder="••••••••"
              placeholderTextColor={colors.textFaint}
              secureTextEntry
              value={password}
              onChangeText={setPassword}
            />
          </View>

          <TouchableOpacity
            style={[styles.button, loading && styles.buttonDisabled]}
            onPress={handleLogin}
            disabled={loading}
            activeOpacity={0.85}
          >
            <Text style={styles.buttonText}>
              {loading ? "Signing in…" : "Sign in"}
            </Text>
          </TouchableOpacity>
        </View>

        <Text style={styles.footerNote}>
          Location access is required to mark attendance
        </Text>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

function createStyles({ colors, radius, spacing, shadow, typography }) {
  return StyleSheet.create({
    screen: { flex: 1, backgroundColor: colors.bg },
    scrollContent: {
      flexGrow: 1,
      justifyContent: "center",
      padding: spacing.lg,
    },
    toggleRow: {
      position: "absolute",
      top: spacing.md,
      right: spacing.lg,
      flexDirection: "row",
      alignItems: "center",
      zIndex: 1,
    },
    accentPicker: {
      flexDirection: "row",
      alignItems: "center",
      marginRight: spacing.sm,
    },
    swatchRing: {
      width: 34,
      height: 34,
      borderRadius: radius.pill,
      borderWidth: 2,
      borderColor: "transparent",
      alignItems: "center",
      justifyContent: "center",
      marginLeft: 4,
    },
    swatch: {
      width: 22,
      height: 22,
      borderRadius: radius.pill,
    },
    themeToggle: {
      height: 40,
      paddingHorizontal: 16,
      borderRadius: radius.pill,
      backgroundColor: colors.card,
      borderWidth: 1,
      borderColor: colors.border,
      alignItems: "center",
      justifyContent: "center",
    },
    themeToggleText: { fontSize: 13, fontWeight: "600", color: colors.textMuted },
    brandRow: {
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "center",
      marginBottom: spacing.xl,
    },
    logoMark: {
      width: 36,
      height: 36,
      borderRadius: radius.sm,
      backgroundColor: colors.primary,
      alignItems: "center",
      justifyContent: "center",
      marginRight: spacing.xs,
    },
    logoMarkText: { color: "#fff", fontWeight: "700", fontSize: 16 },
    brandName: { ...typography.h2, color: colors.text },
    card: {
      backgroundColor: colors.card,
      borderRadius: radius.lg,
      borderWidth: 1,
      borderColor: colors.border,
      padding: spacing.lg,
      ...shadow,
    },
    title: { ...typography.h1, marginBottom: 4 },
    subtitle: { ...typography.body, color: colors.textMuted, marginBottom: spacing.lg },
    field: { marginBottom: spacing.md },
    label: { ...typography.label, marginBottom: 6 },
    input: {
      borderWidth: 1,
      borderColor: colors.border,
      borderRadius: radius.sm,
      paddingVertical: 12,
      paddingHorizontal: 14,
      fontSize: 15,
      color: colors.text,
      backgroundColor: colors.inputBg,
    },
    button: {
      backgroundColor: colors.primary,
      borderRadius: radius.sm,
      paddingVertical: 14,
      alignItems: "center",
      marginTop: spacing.sm,
    },
    buttonDisabled: { opacity: 0.6 },
    buttonText: { color: "#fff", fontWeight: "600", fontSize: 15 },
    footerNote: {
      ...typography.small,
      textAlign: "center",
      marginTop: spacing.lg,
    },
  });
}