// AppearanceModal.js
// Bottom sheet for choosing the app's look after login: theme mode
// (Light / Dark / Reader) and accent color (Purple / Blue). Opened from
// AppearanceButton in the screen header. Pass `visible` + `onClose`,
// same as ProfileModal / RequestModal.
//
// Uses only the existing theme context (mode, accent, setThemePreference,
// setAccent, accentOptions) -- no new dependencies.
import React, { useMemo } from "react";
import {
  Modal,
  View,
  Text,
  TouchableOpacity,
  Pressable,
  StyleSheet,
} from "react-native";
import { useTheme } from "../ThemeContext";

const MODE_OPTIONS = [
  { key: "light", label: "Light", hint: "Bright & clean" },
  { key: "dark", label: "Dark", hint: "Easy at night" },
  { key: "reader", label: "Reader", hint: "Warm paper tint" },
];

// Small round header button (same 36px size as the other header buttons).
// Shows the current accent as a dot inside a ring so it also acts as a
// quick visual cue of what's selected.
export function AppearanceButton({ onPress, style }) {
  const { colors, radius } = useTheme();
  return (
    <TouchableOpacity
      style={[
        {
          width: 36,
          height: 36,
          borderRadius: radius.pill,
          backgroundColor: colors.card,
          borderWidth: 1,
          borderColor: colors.border,
          alignItems: "center",
          justifyContent: "center",
        },
        style,
      ]}
      onPress={onPress}
      activeOpacity={0.8}
      accessibilityRole="button"
      accessibilityLabel="Appearance settings"
    >
      <View
        style={{
          width: 18,
          height: 18,
          borderRadius: 9,
          borderWidth: 2,
          borderColor: colors.primary,
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <View
          style={{
            width: 8,
            height: 8,
            borderRadius: 4,
            backgroundColor: colors.primary,
          }}
        />
      </View>
    </TouchableOpacity>
  );
}

export default function AppearanceModal({ visible, onClose }) {
  const theme = useTheme();
  const {
    colors,
    mode,
    accent,
    setThemePreference,
    setAccent,
    accentOptions,
  } = theme;
  const styles = useMemo(() => createStyles(theme), [theme]);

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent
      onRequestClose={onClose}
    >
      <View style={styles.overlay}>
        {/* Tap outside the sheet to dismiss */}
        <Pressable style={StyleSheet.absoluteFill} onPress={onClose} />

        <View style={styles.sheet}>
          <View style={styles.grabber} />

          <View style={styles.headerRow}>
            <Text style={styles.title}>Appearance</Text>
            <TouchableOpacity
              onPress={onClose}
              style={styles.doneButton}
              activeOpacity={0.8}
            >
              <Text style={styles.doneText}>Done</Text>
            </TouchableOpacity>
          </View>

          {/* ---------- Theme ---------- */}
          <Text style={styles.sectionLabel}>THEME</Text>
          <View style={styles.segment}>
            {MODE_OPTIONS.map((opt) => {
              const selected = opt.key === mode;
              return (
                <TouchableOpacity
                  key={opt.key}
                  style={[styles.segmentItem, selected && styles.segmentItemActive]}
                  onPress={() => setThemePreference(opt.key)}
                  activeOpacity={0.85}
                  accessibilityRole="button"
                  accessibilityState={{ selected }}
                >
                  <Text
                    style={[
                      styles.segmentLabel,
                      selected && styles.segmentLabelActive,
                    ]}
                  >
                    {opt.label}
                  </Text>
                  <Text
                    style={[
                      styles.segmentHint,
                      selected && styles.segmentHintActive,
                    ]}
                    numberOfLines={1}
                  >
                    {opt.hint}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </View>

          {/* ---------- Accent ---------- */}
          <Text style={styles.sectionLabel}>ACCENT COLOR</Text>
          <View style={styles.accentRow}>
            {accentOptions.map((opt) => {
              const selected = opt.key === accent;
              return (
                <TouchableOpacity
                  key={opt.key}
                  style={[
                    styles.accentCard,
                    selected && { borderColor: opt.swatch, borderWidth: 2 },
                  ]}
                  onPress={() => setAccent(opt.key)}
                  activeOpacity={0.85}
                  accessibilityRole="button"
                  accessibilityLabel={`${opt.label} accent`}
                  accessibilityState={{ selected }}
                >
                  <View style={[styles.accentSwatch, { backgroundColor: opt.swatch }]}>
                    {selected ? <Text style={styles.check}>✓</Text> : null}
                  </View>
                  <Text style={styles.accentLabel}>{opt.label}</Text>
                </TouchableOpacity>
              );
            })}
          </View>

          {/* ---------- Live preview ---------- */}
          <Text style={styles.sectionLabel}>PREVIEW</Text>
          <View style={styles.preview}>
            <View style={styles.previewIcon}>
              <View style={styles.previewDot} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.previewTitle}>Check in for today</Text>
              <Text style={styles.previewSub}>This is how buttons and cards will look</Text>
            </View>
            <View style={styles.previewButton}>
              <Text style={styles.previewButtonText}>Go</Text>
            </View>
          </View>
        </View>
      </View>
    </Modal>
  );
}

function createStyles({ colors, radius, spacing, shadow, typography }) {
  return StyleSheet.create({
    overlay: {
      flex: 1,
      justifyContent: "flex-end",
      backgroundColor: "rgba(0,0,0,0.45)",
    },
    sheet: {
      backgroundColor: colors.bg,
      borderTopLeftRadius: radius.lg,
      borderTopRightRadius: radius.lg,
      paddingHorizontal: spacing.lg,
      paddingTop: spacing.sm,
      paddingBottom: spacing.xl,
      borderTopWidth: 1,
      borderColor: colors.border,
    },
    grabber: {
      alignSelf: "center",
      width: 40,
      height: 4,
      borderRadius: 2,
      backgroundColor: colors.border,
      marginBottom: spacing.md,
    },
    headerRow: {
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "space-between",
      marginBottom: spacing.md,
    },
    title: { ...typography.h1 },
    doneButton: {
      paddingHorizontal: 14,
      height: 34,
      borderRadius: radius.pill,
      backgroundColor: colors.primarySoft,
      alignItems: "center",
      justifyContent: "center",
    },
    doneText: { color: colors.primary, fontWeight: "700", fontSize: 13 },
    sectionLabel: {
      ...typography.small,
      fontWeight: "700",
      letterSpacing: 0.8,
      marginTop: spacing.md,
      marginBottom: spacing.xs,
    },

    // Theme segmented control
    segment: {
      flexDirection: "row",
      backgroundColor: colors.card,
      borderWidth: 1,
      borderColor: colors.border,
      borderRadius: radius.md,
      padding: 4,
    },
    segmentItem: {
      flex: 1,
      paddingVertical: 10,
      paddingHorizontal: 6,
      borderRadius: radius.sm,
      alignItems: "center",
    },
    segmentItemActive: { backgroundColor: colors.primary },
    segmentLabel: { fontSize: 14, fontWeight: "700", color: colors.text },
    segmentLabelActive: { color: "#fff" },
    segmentHint: { fontSize: 11, color: colors.textFaint, marginTop: 2 },
    segmentHintActive: { color: "rgba(255,255,255,0.85)" },

    // Accent cards
    accentRow: { flexDirection: "row", gap: 12 },
    accentCard: {
      flex: 1,
      alignItems: "center",
      paddingVertical: spacing.md,
      borderRadius: radius.md,
      backgroundColor: colors.card,
      borderWidth: 1,
      borderColor: colors.border,
    },
    accentSwatch: {
      width: 44,
      height: 44,
      borderRadius: 22,
      alignItems: "center",
      justifyContent: "center",
      marginBottom: 8,
    },
    check: { color: "#fff", fontSize: 20, fontWeight: "800" },
    accentLabel: { fontSize: 14, fontWeight: "600", color: colors.text },

    // Live preview
    preview: {
      flexDirection: "row",
      alignItems: "center",
      backgroundColor: colors.card,
      borderWidth: 1,
      borderColor: colors.border,
      borderRadius: radius.md,
      padding: spacing.md,
      gap: 12,
      ...shadow,
    },
    previewIcon: {
      width: 40,
      height: 40,
      borderRadius: 20,
      backgroundColor: colors.primarySoft,
      alignItems: "center",
      justifyContent: "center",
    },
    previewDot: {
      width: 12,
      height: 12,
      borderRadius: 6,
      backgroundColor: colors.primary,
    },
    previewTitle: { fontSize: 14, fontWeight: "700", color: colors.text },
    previewSub: { fontSize: 12, color: colors.textMuted, marginTop: 2 },
    previewButton: {
      backgroundColor: colors.primary,
      borderRadius: radius.sm,
      paddingHorizontal: 16,
      paddingVertical: 8,
    },
    previewButtonText: { color: "#fff", fontWeight: "700", fontSize: 13 },
  });
}
