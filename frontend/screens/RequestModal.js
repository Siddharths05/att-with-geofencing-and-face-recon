// RequestModal.js
// Full-screen "Requests" sheet, opened the same way ProfileModal is --
// pass `visible` + `onClose`. Top of the sheet has two tabs: Loan and
// Leave. Leave is left as a placeholder for now (not built yet); Loan
// has the actual request form plus a list of the employee's past
// requests underneath, fetched from GET /loan-requests.
//
// Reuses the app's existing theme tokens -- no new palette, no new
// dependencies. Error-message handling follows the same
// string-or-validation-array pattern used in LoginScreen/AttendanceScreen.
import React, { useState, useEffect, useMemo, useCallback } from "react";
import {
  Modal,
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
import api from "../api";
import { useTheme } from "../ThemeContext";
import LeaveRequestForm from "./LeaveRequestForm";

const TOP_TABS = [
  { key: "loan", label: "Loan" },
  { key: "leave", label: "Leave" },
];

const LOAN_TYPES = [
  { key: "Advance", label: "Advance" },
  { key: "Loan", label: "Loan" },
];

function getErrorMessage(err) {
  const detail = err.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => d.msg || JSON.stringify(d)).join("\n");
  }
  return "Request failed";
}

function prettyDate(dateStr) {
  if (!dateStr) return "—";
  const d = new Date(dateStr);
  if (Number.isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

export default function RequestModal({ visible, onClose }) {
  const theme = useTheme();
  const { colors, radius, spacing, shadow, typography } = theme;
  const styles = useMemo(() => createStyles(theme), [theme]);

  const [activeTab, setActiveTab] = useState("loan");

  // --- Loan form state ---
  const [loanType, setLoanType] = useState("Loan"); // "Advance" | "Loan"
  const [amount, setAmount] = useState("");
  const [installments, setInstallments] = useState("1");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);
  const [lastSubmitted, setLastSubmitted] = useState(null); // successful LoanRequestOut, for the confirmation card

  // --- Recent requests list ---
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  // Advance is always a single installment -- force it in the UI too
  // (the backend enforces this regardless, but reflecting it here avoids
  // showing an editable field that would just get overridden on submit).
  useEffect(() => {
    if (loanType === "Advance") {
      setInstallments("1");
    }
  }, [loanType]);

  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const res = await api.get("/loan-requests");
      setHistory(res.data || []);
    } catch (err) {
      // Silent -- the form itself still works even if the history list
      // can't load (e.g. backend not wired up yet).
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    if (visible) {
      setFormError(null);
      setLastSubmitted(null);
      loadHistory();
    }
  }, [visible, loadHistory]);

  const handleSubmit = async () => {
    setFormError(null);

    const parsedAmount = parseFloat(amount);
    if (!amount || Number.isNaN(parsedAmount) || parsedAmount <= 0) {
      setFormError("Enter a valid amount greater than 0.");
      return;
    }

    const parsedInstallments = loanType === "Advance" ? 1 : parseInt(installments, 10);
    if (loanType === "Loan" && (!installments || Number.isNaN(parsedInstallments) || parsedInstallments <= 0)) {
      setFormError("Enter a valid number of installments.");
      return;
    }

    setSubmitting(true);
    try {
      const res = await api.post("/loan-requests", {
        loan_type: loanType,
        amount: parsedAmount,
        installments: parsedInstallments,
      });
      setLastSubmitted(res.data);
      setAmount("");
      setInstallments(loanType === "Advance" ? "1" : "");
      loadHistory();
    } catch (err) {
      setFormError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <View style={styles.screen}>
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Requests</Text>
          <TouchableOpacity style={styles.closeButton} onPress={onClose} activeOpacity={0.8}>
            <Text style={styles.closeButtonText}>✕</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.tabRow}>
          {TOP_TABS.map((tab) => {
            const isActive = activeTab === tab.key;
            return (
              <TouchableOpacity
                key={tab.key}
                style={[styles.tabButton, isActive && styles.tabButtonActive]}
                onPress={() => setActiveTab(tab.key)}
                activeOpacity={0.85}
              >
                <Text style={[styles.tabButtonText, isActive && styles.tabButtonTextActive]}>
                  {tab.label}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>

        {activeTab === "leave" ? (
          <LeaveRequestForm visible={visible} />
        ) : (
          <KeyboardAvoidingView
            style={{ flex: 1 }}
            behavior={Platform.OS === "ios" ? "padding" : undefined}
          >
            <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
              <View style={styles.card}>
                <Text style={styles.label}>Loan type</Text>
                <View style={styles.segmentRow}>
                  {LOAN_TYPES.map((t) => {
                    const isActive = loanType === t.key;
                    return (
                      <TouchableOpacity
                        key={t.key}
                        style={[styles.segmentButton, isActive && styles.segmentButtonActive]}
                        onPress={() => setLoanType(t.key)}
                        activeOpacity={0.85}
                      >
                        <Text
                          style={[
                            styles.segmentButtonText,
                            isActive && styles.segmentButtonTextActive,
                          ]}
                        >
                          {t.label}
                        </Text>
                      </TouchableOpacity>
                    );
                  })}
                </View>

                <View style={styles.field}>
                  <Text style={styles.label}>Amount</Text>
                  <TextInput
                    style={styles.input}
                    placeholder="e.g. 5000"
                    placeholderTextColor={colors.textFaint}
                    keyboardType="numeric"
                    value={amount}
                    onChangeText={setAmount}
                  />
                </View>

                <View style={styles.field}>
                  <Text style={styles.label}>
                    Installments{loanType === "Advance" ? " (fixed for Advance)" : ""}
                  </Text>
                  <TextInput
                    style={[styles.input, loanType === "Advance" && styles.inputDisabled]}
                    placeholder="e.g. 6"
                    placeholderTextColor={colors.textFaint}
                    keyboardType="number-pad"
                    value={installments}
                    onChangeText={setInstallments}
                    editable={loanType !== "Advance"}
                  />
                  {loanType === "Advance" ? (
                    <Text style={styles.helperText}>
                      An Advance is always recovered in a single installment.
                    </Text>
                  ) : null}
                </View>

                {formError ? <Text style={styles.errorText}>{formError}</Text> : null}

                <TouchableOpacity
                  style={[styles.button, submitting && styles.buttonDisabled]}
                  onPress={handleSubmit}
                  disabled={submitting}
                  activeOpacity={0.85}
                >
                  {submitting ? (
                    <ActivityIndicator color="#fff" />
                  ) : (
                    <Text style={styles.buttonText}>Submit request</Text>
                  )}
                </TouchableOpacity>
              </View>

              {lastSubmitted ? (
                <View style={styles.resultCard}>
                  <View style={styles.resultRow}>
                    <View style={styles.statusBadge}>
                      <Text style={styles.statusBadgeText}>Submitted</Text>
                    </View>
                    <Text style={styles.resultMeta}>{lastSubmitted.loan_req_no}</Text>
                  </View>
                  <Text style={styles.resultText}>
                    {lastSubmitted.loan_type} request for ₹{lastSubmitted.amount} over{" "}
                    {lastSubmitted.installments}{" "}
                    {lastSubmitted.installments === 1 ? "installment" : "installments"} submitted
                    on {prettyDate(lastSubmitted.date_applied)}.
                  </Text>
                </View>
              ) : null}

              <Text style={styles.sectionHeading}>Recent requests</Text>
              {historyLoading ? (
                <ActivityIndicator color={colors.primary} style={{ marginTop: spacing.md }} />
              ) : history.length === 0 ? (
                <Text style={styles.emptyInline}>No loan or advance requests yet.</Text>
              ) : (
                history.map((item) => (
                  <View key={item.loan_req_no} style={styles.entryCard}>
                    <View style={styles.entryHeaderRow}>
                      <Text style={styles.entryTitle}>{item.loan_type}</Text>
                      <Text style={styles.entryReqNo}>{item.loan_req_no}</Text>
                    </View>
                    <Text style={styles.entryBody}>
                      ₹{item.amount} · {item.installments}{" "}
                      {item.installments === 1 ? "installment" : "installments"}
                    </Text>
                    <Text style={styles.entryMeta}>{prettyDate(item.date_applied)}</Text>
                  </View>
                ))
              )}
            </ScrollView>
          </KeyboardAvoidingView>
        )}
      </View>
    </Modal>
  );
}

function createStyles({ colors, radius, spacing, shadow, typography }) {
  return StyleSheet.create({
    screen: { flex: 1, backgroundColor: colors.bg },
    header: {
      paddingTop: 56,
      paddingHorizontal: spacing.lg,
      paddingBottom: spacing.md,
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "center",
      borderBottomWidth: 1,
      borderBottomColor: colors.border,
    },
    headerTitle: { ...typography.h2 },
    closeButton: {
      position: "absolute",
      top: 56,
      right: spacing.lg,
      width: 32,
      height: 32,
      borderRadius: radius.pill,
      backgroundColor: colors.card,
      borderWidth: 1,
      borderColor: colors.border,
      alignItems: "center",
      justifyContent: "center",
    },
    closeButtonText: { color: colors.textMuted, fontSize: 14, fontWeight: "600" },

    tabRow: {
      flexDirection: "row",
      paddingHorizontal: spacing.lg,
      paddingTop: spacing.md,
      gap: 8,
    },
    tabButton: {
      flex: 1,
      paddingVertical: 10,
      borderRadius: radius.sm,
      backgroundColor: colors.card,
      borderWidth: 1,
      borderColor: colors.border,
      alignItems: "center",
    },
    tabButtonActive: { backgroundColor: colors.primary, borderColor: colors.primary },
    tabButtonText: { fontWeight: "600", fontSize: 14, color: colors.textMuted },
    tabButtonTextActive: { color: "#fff" },

    emptyState: {
      flex: 1,
      alignItems: "center",
      justifyContent: "center",
      padding: spacing.lg,
    },
    emptyStateTitle: { ...typography.h2, marginBottom: 4 },
    emptyStateText: { ...typography.body, color: colors.textMuted },

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
    segmentRow: {
      flexDirection: "row",
      gap: 8,
      marginBottom: spacing.md,
    },
    segmentButton: {
      flex: 1,
      paddingVertical: 12,
      borderRadius: radius.sm,
      borderWidth: 1,
      borderColor: colors.border,
      alignItems: "center",
      backgroundColor: colors.inputBg,
    },
    segmentButtonActive: { backgroundColor: colors.primarySoft, borderColor: colors.primary },
    segmentButtonText: { fontWeight: "600", fontSize: 14, color: colors.textMuted },
    segmentButtonTextActive: { color: colors.primary },
    field: { marginBottom: spacing.md },
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
    inputDisabled: { opacity: 0.5 },
    helperText: { ...typography.small, color: colors.textFaint, marginTop: 6 },
    errorText: {
      ...typography.small,
      color: colors.dangerText,
      marginBottom: spacing.sm,
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