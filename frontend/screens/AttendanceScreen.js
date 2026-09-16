import React, { useState, useMemo, useRef, useEffect, useCallback } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ActivityIndicator,
  ScrollView,
  StatusBar,
} from "react-native";
import * as Location from "expo-location";
import { CameraView, useCameraPermissions } from "expo-camera";
import api from "../api";
import { useTheme } from "../ThemeContext";
import ProfileModal, { ProfileAvatarButton } from "./ProfileModal";

// FastAPI returns `detail` as a plain string for most errors (e.g. rejected
// check-in), but as an ARRAY of validation-error objects for 422s (e.g. a
// malformed request body). Handle both so we never render an object/array
// directly as a React child.
function getErrorMessage(err) {
  const detail = err.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => d.msg || JSON.stringify(d)).join("\n");
  }
  return "Check-in failed";
}

export default function AttendanceScreen() {
  const theme = useTheme();
  const { colors, mode, isDark, cycleTheme } = theme;
  const styles = useMemo(() => createStyles(theme), [theme]);
  const themeLabel = { light: "Light", dark: "Dark", reader: "Reader" }[mode];

  const [cameraPermission, requestCameraPermission] = useCameraPermissions();
  const cameraRef = useRef(null);

  // "idle" -> "camera" -> back to "idle" (success or timeout/failure)
  const [stage, setStage] = useState("idle");
  const [loading, setLoading] = useState(false);
  const [lastResult, setLastResult] = useState(null);

  // Live, phone-lock-style face feedback while the camera is open.
  // "no-face" -> red border, "detecting" -> face seen but not yet matched
  // (amber), "matched" -> green border + auto check-in.
  const [liveStatus, setLiveStatus] = useState("no-face");
  const [livePct, setLivePct] = useState(0);
  const pollingRef = useRef(null);
  const timeoutRef = useRef(null);
  const isPollingRequestInFlightRef = useRef(false);
  const consecutiveMatchesRef = useRef(0);
  // Location captured during the pre-check in startCheckIn(), reused by
  // confirmCheckIn() so the user isn't prompted for GPS twice.
  const checkedLocationRef = useRef(null);
  const [profileVisible, setProfileVisible] = useState(false);

  const POLL_INTERVAL_MS = 900;
  // A single confident match is enough to trigger the check-in attempt --
  // /attendance/check-in re-runs face matching server-side anyway, so this
  // only affects how quickly the UI reacts, not whether the check-in
  // actually succeeds. Requiring 2+ in a row was too easily reset by one
  // flaky frame and was stalling people into the timeout below.
  const REQUIRED_CONSECUTIVE_MATCHES = 1;
  const TOTAL_TIMEOUT_MS = 15000; // give up after 15s of no confident match

  const today = new Date().toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
  });

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  const clearTotalTimeout = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  const pollFace = useCallback(async () => {
    if (!cameraRef.current || isPollingRequestInFlightRef.current) return;
    isPollingRequestInFlightRef.current = true;
    try {
      const frame = await cameraRef.current.takePictureAsync({
        // Higher quality than before (was 0.3) -- heavy compression was
        // making the face match confidence noisy frame-to-frame.
        quality: 0.6,
        skipProcessing: true,
        shutterSound: false, // avoid a shutter click on every poll (Android)
      });

      const form = new FormData();
      form.append("photo", {
        uri: frame.uri,
        name: "live.jpg",
        type: "image/jpeg",
      });

      const res = await api.post("/face/live-check", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const { face_detected, is_match, similarity_percent } = res.data;

      if (!face_detected) {
        consecutiveMatchesRef.current = 0;
        setLiveStatus("no-face");
        setLivePct(0);
      } else if (is_match) {
        consecutiveMatchesRef.current += 1;
        setLiveStatus("matched");
        setLivePct(similarity_percent);
        if (consecutiveMatchesRef.current >= REQUIRED_CONSECUTIVE_MATCHES) {
          stopPolling();
          clearTotalTimeout();
          confirmCheckIn(frame);
        }
      } else {
        consecutiveMatchesRef.current = 0;
        setLiveStatus("detecting");
        setLivePct(similarity_percent);
      }
    } catch (err) {
      // Silent on a single failed poll (e.g. transient network hiccup) --
      // the next tick will just try again.
    } finally {
      isPollingRequestInFlightRef.current = false;
    }
  }, [stopPolling, clearTotalTimeout]);

  useEffect(() => {
    if (stage === "camera") {
      consecutiveMatchesRef.current = 0;
      setLiveStatus("no-face");
      setLivePct(0);
      pollingRef.current = setInterval(pollFace, POLL_INTERVAL_MS);
      timeoutRef.current = setTimeout(() => {
        stopPolling();
        setStage("idle");
        setLastResult({
          success: false,
          detail: "Couldn't verify your face in time. Please try again.",
        });
      }, TOTAL_TIMEOUT_MS);
    }
    return () => {
      stopPolling();
      clearTotalTimeout();
    };
  }, [stage, pollFace, stopPolling, clearTotalTimeout]);

  const startCheckIn = async () => {
    setLastResult(null);

    // 1. Location first -- no point opening the camera if they're not even
    // at the right site.
    const { status: locStatus } = await Location.requestForegroundPermissionsAsync();
    if (locStatus !== "granted") {
      Alert.alert("Permission needed", "Location access is required to check in");
      return;
    }

    setLoading(true);
    let location;
    try {
      location = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.High,
      });
    } catch (err) {
      setLoading(false);
      Alert.alert("Location error", "Couldn't get your current location. Please try again.");
      return;
    }

    try {
      const form = new FormData();
      form.append("latitude", String(location.coords.latitude));
      form.append("longitude", String(location.coords.longitude));

      const res = await api.post("/attendance/check-location", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const { within_range, distance_meters, allowed_radius_meters, photo_required } = res.data;

      if (!within_range) {
        setLastResult({
          success: false,
          detail: `You're ${distance_meters.toFixed(1)}m from your assigned site (must be within ${allowed_radius_meters}m). Move closer and try again.`,
        });
        setLoading(false);
        return;
      }

      checkedLocationRef.current = location;

      if (!photo_required) {
        // No reference photo on file for this account -- face check is
        // skipped entirely, no need to open the camera at all.
        setLoading(false);
        await confirmCheckIn(null);
        return;
      }
    } catch (err) {
      setLoading(false);
      Alert.alert("Error", getErrorMessage(err));
      return;
    }
    setLoading(false);

    if (!cameraPermission?.granted) {
      const perm = await requestCameraPermission();
      if (!perm.granted) {
        Alert.alert("Permission needed", "Camera access is required to check in");
        return;
      }
    }
    setStage("camera");
  };

  const cancelCheckIn = () => {
    stopPolling();
    clearTotalTimeout();
    setStage("idle");
  };

  const confirmCheckIn = async (photo) => {
    setLoading(true);
    try {
      // Reuse the location captured in startCheckIn's pre-check -- already
      // confirmed in range, no need to prompt for GPS a second time.
      const location = checkedLocationRef.current;
      if (!location) {
        setLastResult({ success: false, detail: "Location not available. Please try again." });
        setStage("idle");
        return;
      }

      const form = new FormData();
      form.append("latitude", String(location.coords.latitude));
      form.append("longitude", String(location.coords.longitude));
      // photo is null when this account has no reference photo on file --
      // the backend skips the face check entirely in that case.
      if (photo) {
        form.append("photo", {
          uri: photo.uri,
          name: "checkin.jpg",
          type: "image/jpeg",
        });
      }

      const res = await api.post("/attendance/check-in", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      setLastResult({ success: true, ...res.data });
      setStage("idle");
    } catch (err) {
      setLastResult({ success: false, detail: getErrorMessage(err) });
      setStage("idle");
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <StatusBar barStyle={isDark ? "light-content" : "dark-content"} />
      <View style={styles.header}>
        <View style={styles.headerTopRow}>
          <Text style={styles.date}>{today}</Text>
          <View style={{ flexDirection: "row", gap: 8 }}>
            <ProfileAvatarButton onPress={() => setProfileVisible(true)} />
            <TouchableOpacity
              style={styles.themeToggle}
              onPress={cycleTheme}
              activeOpacity={0.8}
            >
              <Text style={styles.themeToggleText}>{themeLabel}</Text>
            </TouchableOpacity>
          </View>
        </View>
        <Text style={styles.title}>Mark attendance</Text>
      </View>

      <View style={styles.card}>
        {stage === "idle" && (
          <>
            <View style={styles.iconCircle}>
              <View style={styles.iconDot} />
            </View>
            <Text style={styles.cardTitle}>Check in for today</Text>
            <Text style={styles.cardSubtitle}>
              We'll check your location and take a quick selfie to verify it's you before marking you present
            </Text>

            <TouchableOpacity
              style={[styles.button, loading && styles.buttonDisabled]}
              onPress={startCheckIn}
              disabled={loading}
              activeOpacity={0.85}
            >
              {loading ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.buttonText}>Check in</Text>
              )}
            </TouchableOpacity>
          </>
        )}

        {stage === "camera" && (
          <>
            <Text style={styles.cardTitle}>Line up your face</Text>
            <Text style={styles.cardSubtitle}>
              {liveStatus === "no-face"
                ? "Hold the phone up so your face is in frame"
                : "Hold still — checking it's you"}
            </Text>
            <View
              style={[
                styles.cameraBox,
                styles.liveBorder,
                liveStatus === "matched"
                  ? styles.liveBorderMatched
                  : liveStatus === "detecting"
                  ? styles.liveBorderDetecting
                  : styles.liveBorderNoFace,
              ]}
            >
              <CameraView
                ref={cameraRef}
                style={StyleSheet.absoluteFill}
                facing="front"
                animateShutter={false}
              />
              <View
                style={[
                  styles.liveStatusPill,
                  liveStatus === "matched"
                    ? styles.liveStatusPillMatched
                    : liveStatus === "detecting"
                    ? styles.liveStatusPillDetecting
                    : styles.liveStatusPillNoFace,
                ]}
              >
                <Text style={styles.liveStatusText}>
                  {liveStatus === "no-face" && "No face detected"}
                  {liveStatus === "detecting" && `Detecting… ${Math.round(livePct)}%`}
                  {liveStatus === "matched" && `Matched ${Math.round(livePct)}% ✓`}
                </Text>
              </View>
            </View>
            <View style={styles.rowButtons}>
              <TouchableOpacity
                style={styles.secondaryButton}
                onPress={cancelCheckIn}
                activeOpacity={0.85}
              >
                <Text style={styles.secondaryButtonText}>Cancel</Text>
              </TouchableOpacity>
            </View>
          </>
        )}
      </View>

      {lastResult && (
        <View
          style={[
            styles.resultCard,
            lastResult.success ? styles.resultSuccess : styles.resultDanger,
          ]}
        >
          <View style={styles.resultRow}>
            <View
              style={[
                styles.statusBadge,
                lastResult.success ? styles.badgeSuccess : styles.badgeDanger,
              ]}
            >
              <Text
                style={[
                  styles.statusBadgeText,
                  lastResult.success
                    ? styles.badgeTextSuccess
                    : styles.badgeTextDanger,
                ]}
              >
                {lastResult.success ? "Present" : "Rejected"}
              </Text>
            </View>
            {lastResult.success ? (
              <Text style={styles.resultMeta}>
                {[
                  typeof lastResult.distance_meters === "number"
                    ? `${lastResult.distance_meters.toFixed(1)}m from office`
                    : null,
                  typeof lastResult.face_similarity_percent === "number"
                    ? `${lastResult.face_similarity_percent}% face match`
                    : null,
                ]
                  .filter(Boolean)
                  .join(" · ") || "Verified"}
              </Text>
            ) : null}
          </View>
          <Text style={styles.resultText}>
            {lastResult.success
              ? "You're marked present for today."
              : lastResult.detail}
          </Text>
        </View>
      )}
      <ProfileModal visible={profileVisible} onClose={() => setProfileVisible(false)} />
    </ScrollView>
  );
}

function createStyles({ colors, radius, spacing, shadow, typography, isDark }) {
  return StyleSheet.create({
    screen: { flex: 1, backgroundColor: colors.bg },
    content: { padding: spacing.lg, paddingTop: spacing.xl },
    header: { marginBottom: spacing.lg },
    headerTopRow: {
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "space-between",
      marginBottom: 2,
    },
    date: { ...typography.label },
    themeToggle: {
      height: 36,
      paddingHorizontal: 14,
      borderRadius: radius.pill,
      backgroundColor: colors.card,
      borderWidth: 1,
      borderColor: colors.border,
      alignItems: "center",
      justifyContent: "center",
    },
    themeToggleText: { fontSize: 12, fontWeight: "600", color: colors.textMuted },
    title: { ...typography.h1 },
    card: {
      backgroundColor: colors.card,
      borderRadius: radius.lg,
      borderWidth: 1,
      borderColor: colors.border,
      padding: spacing.lg,
      alignItems: "center",
      ...shadow,
    },
    iconCircle: {
      width: 56,
      height: 56,
      borderRadius: 28,
      backgroundColor: colors.primarySoft,
      alignItems: "center",
      justifyContent: "center",
      marginBottom: spacing.md,
    },
    iconDot: {
      width: 16,
      height: 16,
      borderRadius: 8,
      backgroundColor: colors.primary,
    },
    cardTitle: { ...typography.h2, marginBottom: 4 },
    cardSubtitle: {
      ...typography.body,
      color: colors.textMuted,
      textAlign: "center",
      marginBottom: spacing.lg,
    },
    button: {
      backgroundColor: colors.primary,
      borderRadius: radius.sm,
      paddingVertical: 14,
      paddingHorizontal: spacing.xl,
      alignItems: "center",
      alignSelf: "stretch",
    },
    buttonDisabled: { opacity: 0.6 },
    buttonText: { color: "#fff", fontWeight: "600", fontSize: 15 },
    secondaryButton: {
      backgroundColor: colors.primarySoft,
      borderRadius: radius.sm,
      paddingVertical: 14,
      paddingHorizontal: spacing.xl,
      alignItems: "center",
      alignSelf: "stretch",
    },
    secondaryButtonText: { color: colors.primary, fontWeight: "600", fontSize: 15 },
    rowButtons: {
      flexDirection: "row",
      alignSelf: "stretch",
    },
    cameraBox: {
      width: "100%",
      height: 280,
      borderRadius: radius.md,
      overflow: "hidden",
      backgroundColor: "#000",
      marginBottom: spacing.md,
    },
    liveBorder: {
      borderWidth: 4,
    },
    liveBorderNoFace: { borderColor: colors.danger },
    liveBorderDetecting: { borderColor: colors.amber },
    liveBorderMatched: { borderColor: "#22C55E" },
    liveStatusPill: {
      position: "absolute",
      bottom: 12,
      alignSelf: "center",
      paddingHorizontal: 14,
      paddingVertical: 6,
      borderRadius: radius.pill,
    },
    liveStatusPillNoFace: { backgroundColor: "rgba(220, 38, 38, 0.85)" },
    liveStatusPillDetecting: { backgroundColor: "rgba(217, 119, 6, 0.85)" },
    liveStatusPillMatched: { backgroundColor: "rgba(34, 197, 94, 0.85)" },
    liveStatusText: {
      color: "#fff",
      fontWeight: "700",
      fontSize: 13,
    },
    resultCard: {
      marginTop: spacing.md,
      borderRadius: radius.md,
      borderWidth: 1,
      padding: spacing.md,
    },
    resultSuccess: {
      backgroundColor: colors.primarySoft,
      borderColor: colors.successBorder,
    },
    resultDanger: {
      backgroundColor: colors.dangerSoft,
      borderColor: colors.dangerBorder,
    },
    resultRow: {
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "space-between",
      marginBottom: 6,
    },
    statusBadge: {
      paddingHorizontal: 10,
      paddingVertical: 4,
      borderRadius: radius.pill,
    },
    badgeSuccess: { backgroundColor: colors.successBadgeBg },
    badgeDanger: { backgroundColor: colors.dangerBadgeBg },
    statusBadgeText: { fontSize: 12, fontWeight: "700" },
    badgeTextSuccess: { color: colors.successText },
    badgeTextDanger: { color: colors.dangerText },
    resultMeta: { ...typography.small },
    resultText: { ...typography.body, color: colors.text },
  });
}