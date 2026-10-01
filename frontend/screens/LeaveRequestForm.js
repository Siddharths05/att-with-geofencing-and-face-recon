// LeaveRequestForm.js
// Body of the "Leave" tab in RequestModal. Layout, top to bottom:
//   From / To dates -> table (Leave type | Balance | Apply) where Apply is a
//   number field with - / + -> Reason -> one Submit button -> recent requests.
// The employee splits the chargeable days (range minus holidays) across the
// leave types with the number fields; Submit is enabled once they add up.
//
// Needs one new dependency:  npx expo install @react-native-community/datetimepicker
import React, { useState, useEffect, useMemo, useCallback } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import DateTimePicker from "@react-native-community/datetimepicker";
import api from "../api";
import { useTheme } from "../ThemeContext";

function getErrorMessage(err) {
  const detail = err.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => d.msg || JSON.stringify(d)).join("\n");
  }
  return "Request failed";
}

const pad = (n) => String(n).padStart(2, "0");
const toISO = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const startOfDay = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate());

function prettyDate(value) {
  const d = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

function formatDays(n) {
  return Number.isInteger(n) ? String(n) : n.toFixed(1);
}

// iOS renders the picker inline ("compact"); Android opens a dialog on tap.
function DateField({ label, value, onChange, minimumDate, styles }) {
  const [open, setOpen] = useState(false);
  return (
    <View style={styles.dateField}>
      <Text style={styles.label}>{label}</Text>
      {Platform.OS === "ios" ? (
        <View style={[styles.dateBox, { alignItems: "flex-start" }]}>
          <DateTimePicker
            value={value}
            mode="date"
            display="compact"
            minimumDate={minimumDate}
            onChange={(_, d) => d && onChange(d)}
          />
        </View>
      ) : (
        <>
          <TouchableOpacity style={styles.dateBox} onPress={() => setOpen(true)} activeOpacity={0.8}>
            <Text style={styles.dateText}>{prettyDate(value)}</Text>
          </TouchableOpacity>
          {open ? (
            <DateTimePicker
              value={value}
              mode="date"
              display="default"
              minimumDate={minimumDate}
              onChange={(e, d) => {
                setOpen(false);
                if (e.type === "set" && d) onChange(d);
              }}
            />
          ) : null}
        </>
      )}
    </View>
  );
}

// Number field with - / + buttons. `max` is the most this row can take right now.
function DaysStepper({ value, max, onChange, disabled, styles, colors }) {
  const canDec = !disabled && value > 0;
  const canInc = !disabled && value < max;
  return (
    <View style={[styles.stepper, disabled && styles.stepperDisabled]}>
      <TouchableOpacity
        style={[styles.stepBtn, !canDec && styles.stepBtnOff]}
        onPress={() => onChange(value - 1)}
        disabled={!canDec}
        activeOpacity={0.7}
        hitSlop={{ top: 6, bottom: 6, left: 4, right: 2 }}
      >
        <Text style={styles.stepBtnText}>-</Text>
      </TouchableOpacity>
      <TextInput
        style={styles.stepInput}
        value={String(value)}
        onChangeText={(t) => {
          const n = parseInt(t.replace(/[^0-9]/g, ""), 10);
          onChange(Number.isNaN(n) ? 0 : n);
        }}
        keyboardType="number-pad"
        maxLength={3}
        editable={!disabled}
        selectTextOnFocus
        placeholderTextColor={colors.textFaint}
      />
      <TouchableOpacity
        style={[styles.stepBtn, !canInc && styles.stepBtnOff]}
        onPress={() => onChange(value + 1)}
        disabled={!canInc}
        activeOpacity={0.7}
        hitSlop={{ top: 6, bottom: 6, left: 2, right: 4 }}
      >
        <Text style={styles.stepBtnText}>+</Text>
      </TouchableOpacity>
    </View>
  );
}

export default function LeaveRequestForm({ visible }) {
  const theme = useTheme();
  const { colors, spacing } = theme;
  const styles = useMemo(() => createStyles(theme), [theme]);

  const [fromDate, setFromDate] = useState(() => startOfDay(new Date()));
  const [toDate, setToDate] = useState(() => startOfDay(new Date()));
  const [reason, setReason] = useState("");

  const [balances, setBalances] = useState([]);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);

  const [preview, setPreview] = useState(null); // {total_days, holidays, chargeable_days}
  const [alloc, setAlloc] = useState({}); // {CL: 2, SL: 1, ...}
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);
  const [lastSubmitted, setLastSubmitted] = useState(null);

  const fromISO = toISO(fromDate);
  const toISOStr = toISO(toDate);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [b, h] = await Promise.all([api.get("/leave-balances"), api.get("/leave-requests")]);
      setBalances(b.data || []);
      setHistory(h.data || []);
    } catch (err) {
      setFormError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (visible) {
      setFormError(null);
      setLastSubmitted(null);
      loadData();
    }
  }, [visible, loadData]);

  // Whenever the date range changes: clear the split and ask the server how
  // many of those days are holidays vs. chargeable to leave.
  useEffect(() => {
    if (!visible) return undefined;
    let cancelled = false;
    setAlloc({});
    setPreview(null);
    api
      .get("/leave-preview", { params: { from_date: fromISO, to_date: toISOStr } })
      .then((r) => {
        if (!cancelled) setPreview(r.data);
      })
      .catch((err) => {
        if (!cancelled) setFormError(getErrorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [visible, fromISO, toISOStr]);

  const handleFromChange = (d) => {
    setFromDate(d);
    if (toDate < d) setToDate(d);
  };

  const chargeable = preview ? preview.chargeable_days : null;
  const holidayCount = preview ? preview.holidays.length : 0;
  const allocated = Object.values(alloc).reduce((s, n) => s + n, 0);
  const left = chargeable === null ? 0 : chargeable - allocated;

  // Most days this row can take: its own balance, and whatever of the
  // chargeable days isn't already given to other rows.
  const maxFor = (b) => {
    if (chargeable === null) return 0;
    const cap = b.remaining === null ? Infinity : Math.max(0, Math.floor(b.remaining));
    const others = allocated - (alloc[b.leave_type] || 0);
    return Math.max(0, Math.min(cap, chargeable - others));
  };

  const setDays = (b, n) => {
    const v = Math.max(0, Math.min(n, maxFor(b)));
    setAlloc((prev) => ({ ...prev, [b.leave_type]: v }));
  };

  const canSubmit =
    !submitting && chargeable !== null && chargeable > 0 && left === 0 && reason.trim().length > 0;

  const handleSubmit = async () => {
    setFormError(null);
    if (!reason.trim()) {
      setFormError("Please enter a reason before submitting.");
      return;
    }
    const allocations = Object.entries(alloc)
      .filter(([, days]) => days > 0)
      .map(([leave_type, days]) => ({ leave_type, days }));
    setSubmitting(true);
    try {
      const res = await api.post("/leave-requests", {
        allocations,
        from_date: fromISO,
        to_date: toISOStr,
        reason: reason.trim(),
      });
      setLastSubmitted(res.data);
      setReason("");
      setAlloc({});
      loadData();
    } catch (err) {
      setFormError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <View style={styles.card}>
          <View style={styles.dateRow}>
            <DateField label="From" value={fromDate} onChange={handleFromChange} styles={styles} />
            <DateField
              label="To"
              value={toDate}
              onChange={setToDate}
              minimumDate={fromDate}
              styles={styles}
            />
          </View>
          <Text style={styles.helperText}>
            {preview
              ? `${preview.total_days} ${preview.total_days === 1 ? "day" : "days"} selected` +
                (holidayCount
                  ? ` - ${holidayCount} paid ${holidayCount === 1 ? "holiday" : "holidays"} (${preview.holidays
                      .map((h) => h.name)
                      .join(", ")})`
                  : "")
              : "Checking dates..."}
          </Text>
          {preview && chargeable === 0 ? (
            <Text style={styles.errorText}>
              Every selected day is a paid holiday, so no leave is needed.
            </Text>
          ) : null}

          <View style={styles.tableHead}>
            <Text style={[styles.th, { flex: 1 }]}>Leave type</Text>
            <Text style={[styles.th, styles.colBalance]}>Balance</Text>
            <Text style={[styles.th, styles.colApply]}>Apply</Text>
          </View>
          {loading && balances.length === 0 ? (
            <ActivityIndicator color={colors.primary} style={{ marginVertical: spacing.md }} />
          ) : (
            balances.map((b) => {
              const isAuto = b.leave_type === "PH";
              return (
                <View key={b.leave_type} style={styles.leaveRow}>
                  <Text style={[styles.leaveName, { flex: 1 }]}>{b.label}</Text>
                  <View style={styles.colBalance}>
                    <Text style={styles.balanceNum}>
                      {b.total === null ? "No limit" : formatDays(b.remaining)}
                    </Text>
                    {b.total !== null ? (
                      <Text style={styles.balanceOf}>of {formatDays(b.total)}</Text>
                    ) : null}
                  </View>
                  <View style={styles.colApply}>
                    {isAuto ? (
                      <Text style={styles.autoText}>Automatic</Text>
                    ) : (
                      <DaysStepper
                        value={alloc[b.leave_type] || 0}
                        max={maxFor(b)}
                        onChange={(n) => setDays(b, n)}
                        disabled={chargeable === null || chargeable === 0 || submitting}
                        styles={styles}
                        colors={colors}
                      />
                    )}
                  </View>
                </View>
              );
            })
          )}
          {chargeable ? (
            <Text style={[styles.helperText, left !== 0 && styles.helperWarn]}>
              {left === 0
                ? `All ${chargeable} ${chargeable === 1 ? "day" : "days"} assigned`
                : `Assigned ${allocated} of ${chargeable} - ${left} ${left === 1 ? "day" : "days"} to go`}
            </Text>
          ) : null}

          <View style={[styles.field, { marginTop: spacing.md }]}>
            <Text style={styles.label}>Reason</Text>
            <TextInput
              style={[styles.input, styles.inputMultiline]}
              placeholder="Why are you taking this leave?"
              placeholderTextColor={colors.textFaint}
              value={reason}
              onChangeText={setReason}
              multiline
              maxLength={255}
              textAlignVertical="top"
            />
          </View>

          {formError ? <Text style={styles.errorText}>{formError}</Text> : null}

          <TouchableOpacity
            style={[styles.submitButton, !canSubmit && styles.applyButtonDisabled]}
            onPress={handleSubmit}
            disabled={!canSubmit}
            activeOpacity={0.85}
          >
            {submitting ? (
              <ActivityIndicator color="#fff" size="small" />
            ) : (
              <Text style={styles.submitButtonText}>Submit leave request</Text>
            )}
          </TouchableOpacity>
        </View>

        {lastSubmitted ? (
          <View style={styles.resultCard}>
            <View style={styles.resultRow}>
              <View style={styles.statusBadge}>
                <Text style={styles.statusBadgeText}>Submitted</Text>
              </View>
              <Text style={styles.resultMeta}>{lastSubmitted.leave_req_no}</Text>
            </View>
            <Text style={styles.resultText}>
              {lastSubmitted.leave_label}: {prettyDate(lastSubmitted.from_date)} to{" "}
              {prettyDate(lastSubmitted.to_date)} ({lastSubmitted.days}{" "}
              {lastSubmitted.days === 1 ? "day" : "days"}
              {lastSubmitted.holiday_days > 0
                ? `, ${lastSubmitted.holiday_days} of them holidays`
                : ""}
              ).
            </Text>
          </View>
        ) : null}

        <Text style={styles.sectionHeading}>Recent leave requests</Text>
        {history.length === 0 ? (
          <Text style={styles.emptyInline}>No leave requests yet.</Text>
        ) : (
          history.map((item) => (
            <View key={item.leave_req_no} style={styles.entryCard}>
              <View style={styles.entryHeaderRow}>
                <Text style={styles.entryTitle}>{item.leave_label}</Text>
                <Text style={styles.entryReqNo}>{item.leave_req_no}</Text>
              </View>
              <Text style={styles.entryBody}>
                {prettyDate(item.from_date)} to {prettyDate(item.to_date)} · {item.days}{" "}
                {item.days === 1 ? "day" : "days"}
              </Text>
              <Text style={styles.entryMeta}>{item.reason}</Text>
            </View>
          ))
        )}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

function createStyles({ colors, radius, spacing, shadow, typography }) {
  return StyleSheet.create({
    content: { padding: spacing.lg },
    card: {
      backgroundColor: colors.card,
      borderRadius: radius.lg,
      borderWidth: 1,
      borderColor: colors.border,
      padding: spacing.lg,
      ...shadow,
    },
    label: { ...typography.label, marginBottom: 6 },
    dateRow: { flexDirection: "row", gap: 12 },
    dateField: { flex: 1 },
    dateBox: {
      minHeight: 46,
      borderWidth: 1,
      borderColor: colors.border,
      borderRadius: radius.sm,
      paddingHorizontal: 10,
      justifyContent: "center",
      backgroundColor: colors.inputBg,
    },
    dateText: { fontSize: 15, color: colors.text },
    helperText: { ...typography.small, color: colors.textFaint, marginTop: 6 },

    tableHead: {
      flexDirection: "row",
      alignItems: "center",
      marginTop: spacing.md,
      paddingBottom: 6,
      borderBottomWidth: 1,
      borderBottomColor: colors.border,
    },
    th: { ...typography.small, fontWeight: "700", color: colors.textMuted },
    colBalance: { width: 70, alignItems: "center" },
    colApply: { width: 112, alignItems: "flex-end" },
    leaveRow: {
      flexDirection: "row",
      alignItems: "center",
      paddingVertical: 10,
      borderBottomWidth: 1,
      borderBottomColor: colors.border,
    },
    leaveName: { ...typography.body, fontWeight: "600", color: colors.text, paddingRight: 8 },
    balanceNum: { ...typography.body, fontWeight: "700", color: colors.text },
    balanceOf: { ...typography.small, color: colors.textFaint },
    autoText: { ...typography.small, color: colors.textFaint },
    helperWarn: { color: colors.dangerText },

    stepper: {
      flexDirection: "row",
      alignItems: "center",
      borderWidth: 1,
      borderColor: colors.border,
      borderRadius: radius.sm,
      backgroundColor: colors.inputBg,
      overflow: "hidden",
    },
    stepperDisabled: { opacity: 0.5 },
    stepBtn: {
      width: 32,
      height: 36,
      alignItems: "center",
      justifyContent: "center",
      backgroundColor: colors.primarySoft,
    },
    stepBtnOff: { opacity: 0.35 },
    stepBtnText: { fontSize: 18, fontWeight: "700", color: colors.primary },
    stepInput: {
      width: 44,
      height: 36,
      textAlign: "center",
      fontSize: 15,
      fontWeight: "600",
      color: colors.text,
      padding: 0,
    },

    submitButton: {
      marginTop: spacing.md,
      paddingVertical: 14,
      borderRadius: radius.sm,
      backgroundColor: colors.primary,
      alignItems: "center",
    },
    submitButtonText: { color: "#fff", fontWeight: "600", fontSize: 15 },
    applyButtonDisabled: { opacity: 0.4 },

    field: { marginBottom: spacing.sm },
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
    inputMultiline: { minHeight: 90 },
    errorText: { ...typography.small, color: colors.dangerText, marginTop: spacing.xs },

    resultCard: {
      marginTop: spacing.md,
      borderRadius: radius.md,
      borderWidth: 1,
      borderColor: colors.successBorder,
      backgroundColor: colors.primarySoft,
      padding: spacing.md,
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
      backgroundColor: colors.successBadgeBg,
    },
    statusBadgeText: { fontSize: 12, fontWeight: "700", color: colors.successText },
    resultMeta: { ...typography.small, fontWeight: "600" },
    resultText: { ...typography.body, color: colors.text },

    sectionHeading: {
      ...typography.h2,
      fontSize: 15,
      marginTop: spacing.lg,
      marginBottom: spacing.sm,
    },
    emptyInline: { ...typography.small, color: colors.textFaint },
    entryCard: {
      backgroundColor: colors.card,
      borderRadius: radius.md,
      borderWidth: 1,
      borderColor: colors.border,
      padding: spacing.md,
      marginBottom: spacing.sm,
    },
    entryHeaderRow: {
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "space-between",
      marginBottom: 2,
    },
    entryTitle: { ...typography.h2, fontSize: 15 },
    entryReqNo: { ...typography.small, color: colors.textFaint },
    entryBody: { ...typography.body, color: colors.textMuted },
    entryMeta: { ...typography.small, marginTop: 4 },
  });
}