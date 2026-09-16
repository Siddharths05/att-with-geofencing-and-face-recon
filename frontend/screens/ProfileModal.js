// ProfileModal.js
// Full-screen profile sheet, opened from an avatar button in the app
// header. Photo + computed stats sit large at the top; Basic / Contact /
// Documents / Family / More are a vertical accordion below it -- tap a
// section name to expand its fields in place, tap again to collapse.
// Reuses the app's existing theme tokens -- no new palette introduced,
// no new dependencies added.
import React, { useState, useEffect, useMemo } from "react";
import {
  Modal,
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
  Image,
} from "react-native";
import api from "../api";
import { useTheme } from "../ThemeContext";

const TABS = [
  { key: "basic", label: "Basic" },
  { key: "contact", label: "Contact" },
  { key: "documents", label: "Documents" },
  { key: "family", label: "Family" },
  { key: "more", label: "More" },
];

// Shown if the /profile call fails (e.g. backend not wired up yet) so the
// UI can still be reviewed/tested end-to-end with realistic shapes.
const SAMPLE_PROFILE = {
  basic: {
    emp_code: "799",
    name: "Sample Employee",
    username: "testuser1",
    date_of_birth: "1995-04-12",
    gender: "Male",
    marital_status: "Unmarried",
    department_code: "DEP01",
    designation_code: "DEG01",
    joining_date: "2023-06-01",
    leaving_date: null,
    blood_group: "O+",
    aadhar_no: "XXXX-XXXX-1234",
    qualification_code: "BSC01",
    anniversary: null,
    resident_address: "221B Test Street, Bandra, Mumbai",
    native_address: "Village Road, Nashik, Maharashtra",
    bank_code: "HDFC01",
    account_no: "123456789012",
    uan_no: "UAN100000000014",
    esic_no: "ESIC0014",
    pan_no: "ABCDE1234F",
    rtgs: "HDFC0001234",
    short_address: "Bandra, Mumbai",
    work_place: "Mumbai HQ",
    height: "175",
    weight: "70.5",
    cash_account_code: "CASH01",
    photo_base64: null,
  },
  contacts: [{ contact_type_code: "MOB", contact: "9876543210", ext: "" }],
  documents: [{ document_type_code: "PAN", doc_file: "sample_pan.pdf", valid_until: null }],
  family: [{ relative_name: "Sample Relative", relationship_code: "SPOU", date_of_birth: null, marital_status: "Married" }],
  more_info: {
    identification_mark: "Mole on left cheek",
    total_experience: "3.6",
    referred_by_emp_id: "799012",
    police_station: "Bandra Police Station",
    police_address: "Bandra West, Mumbai",
    police_contact: "022-12345678",
    witness1_emp_id: "799012",
    witness2_emp_id: "799013",
    inform_uan_on_leaving: true,
    inform_esic_on_leaving: false,
    personality1_name: "Sample Referee One",
    personality1_designation_code: "MGR01",
    personality1_address: "Andheri, Mumbai",
    personality1_contact: "9876500001",
    personality2_name: "Sample Referee Two",
    personality2_designation_code: "MGR02",
    personality2_address: "Powai, Mumbai",
    personality2_contact: "9876500002",
  },
};

function initials(name) {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/);
  return (parts[0]?.[0] || "").toUpperCase() + (parts[1]?.[0] || "").toUpperCase();
}

// ==================================================
// DERIVED / COMPUTED DISPLAY VALUES
// None of this is stored anywhere -- it's computed client-side from
// dates the API already returns, purely to make the header read like a
// real profile summary instead of a list of raw fields.
// ==================================================

function prettyDate(dateStr) {
  if (!dateStr) return null;
  const d = new Date(dateStr);
  if (Number.isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

function calcAge(dobStr) {
  if (!dobStr) return null;
  const dob = new Date(dobStr);
  if (Number.isNaN(dob.getTime())) return null;
  const now = new Date();
  let age = now.getFullYear() - dob.getFullYear();
  const monthDiff = now.getMonth() - dob.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && now.getDate() < dob.getDate())) age--;
  return age >= 0 ? age : null;
}

// Returns { label, active } -- e.g. { label: "2y 3m", active: true } while
// still employed, or { label: "3y 1m", active: false } once DOL is set.
function calcTenure(dojStr, dolStr) {
  if (!dojStr) return null;
  const start = new Date(dojStr);
  if (Number.isNaN(start.getTime())) return null;
  const end = dolStr ? new Date(dolStr) : new Date();
  let years = end.getFullYear() - start.getFullYear();
  let months = end.getMonth() - start.getMonth();
  if (end.getDate() < start.getDate()) months--;
  if (months < 0) {
    years--;
    months += 12;
  }
  if (years < 0) return null;
  const label = years > 0 ? `${years}y ${months}m` : `${months}m`;
  return { label, active: !dolStr };
}

export function ProfileAvatarButton({ onPress, style }) {
  const { colors, radius } = useTheme();
  const [photo, setPhoto] = useState(null);
  const [name, setName] = useState(null);

  useEffect(() => {
    let cancelled = false;
    api
      .get("/profile")
      .then((res) => {
        if (cancelled) return;
        setPhoto(res.data?.basic?.photo_base64 || null);
        setName(res.data?.basic?.name || null);
      })
      .catch(() => {
        // No network / not logged in yet -- just show the placeholder.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <TouchableOpacity
      style={[
        {
          width: 36,
          height: 36,
          borderRadius: radius.pill,
          backgroundColor: colors.primary,
          alignItems: "center",
          justifyContent: "center",
          overflow: "hidden",
        },
        style,
      ]}
      onPress={onPress}
      activeOpacity={0.8}
    >
      {photo ? (
        <Image source={{ uri: photo }} style={{ width: 36, height: 36 }} />
      ) : (
        <Text style={{ color: "#fff", fontWeight: "700", fontSize: 13 }}>
          {initials(name)}
        </Text>
      )}
    </TouchableOpacity>
  );
}

export default function ProfileModal({ visible, onClose }) {
  const theme = useTheme();
  const { colors, radius, spacing, shadow, typography } = theme;
  const styles = useMemo(() => createStyles(theme), [theme]);

  const [expandedSection, setExpandedSection] = useState("basic");
  const [loading, setLoading] = useState(false);
  const [profile, setProfile] = useState(null);
  const [usingSample, setUsingSample] = useState(false);

  useEffect(() => {
    if (!visible) return;
    let cancelled = false;
    setLoading(true);
    setUsingSample(false);
    api
      .get("/profile")
      .then((res) => {
        if (!cancelled) setProfile(res.data);
      })
      .catch(() => {
        // Backend route not mounted yet, or schema not wired -- fall back
        // to sample data so the UI itself can still be reviewed.
        if (!cancelled) {
          setProfile(SAMPLE_PROFILE);
          setUsingSample(true);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [visible]);

  const basic = profile?.basic;
  const age = basic ? calcAge(basic.date_of_birth) : null;
  const tenure = basic ? calcTenure(basic.joining_date, basic.leaving_date) : null;

  // --------------------------------------------------
  // SHARED PRESENTATIONAL PIECES
  // --------------------------------------------------

  function SectionCard({ title, children }) {
    return (
      <View style={styles.sectionCard}>
        <View style={styles.sectionCardHeader}>
          <View style={styles.sectionDot} />
          <Text style={styles.sectionCardTitle}>{title}</Text>
        </View>
        {children}
      </View>
    );
  }

  function InfoGrid({ items }) {
    // Drop fields with nothing to show rather than rendering a wall of
    // "—" placeholders -- a section quietly gets shorter instead.
    const visible = items.filter((item) => item.value !== undefined);
    if (visible.length === 0) {
      return <Text style={styles.emptyInline}>Nothing on file for this section.</Text>;
    }
    return (
      <View style={styles.infoGrid}>
        {visible.map((item, i) => (
          <View
            key={i}
            style={[styles.infoTile, item.wide && styles.infoTileWide]}
          >
            <Text style={styles.infoLabel}>{item.label}</Text>
            <Text style={styles.infoValue} numberOfLines={3}>
              {item.value || "—"}
            </Text>
          </View>
        ))}
      </View>
    );
  }

  function EmptyState({ text }) {
    return <Text style={styles.emptyText}>{text}</Text>;
  }

  // --------------------------------------------------
  // BASIC TAB -- same fields as before, regrouped into cards with a
  // denser two-column grid instead of one long list of full-width rows.
  // --------------------------------------------------

  const renderBasic = (b) => (
    <View>
      <SectionCard title="Personal">
        <InfoGrid
          items={[
            { label: "Date of birth", value: prettyDate(b.date_of_birth) },
            { label: "Age", value: age !== null ? `${age} yrs` : undefined },
            { label: "Gender", value: b.gender },
            { label: "Marital status", value: b.marital_status },
            { label: "Anniversary", value: prettyDate(b.anniversary) },
            { label: "Qualification", value: b.qualification_code },
            { label: "Blood group", value: b.blood_group },
            { label: "Height / Weight", value: b.height || b.weight ? `${b.height || "—"} cm · ${b.weight || "—"} kg` : undefined },
            { label: "Aadhar no.", value: b.aadhar_no, wide: true },
          ]}
        />
      </SectionCard>

      <SectionCard title="Employment">
        <InfoGrid
          items={[
            { label: "Department", value: b.department_code },
            { label: "Designation", value: b.designation_code },
            { label: "Joining date", value: prettyDate(b.joining_date) },
            {
              label: tenure?.active ? "Time with company" : "Time served",
              value: tenure?.label,
            },
            { label: "Leaving date", value: prettyDate(b.leaving_date) },
            { label: "Work place", value: b.work_place },
          ]}
        />
      </SectionCard>

      <SectionCard title="Address">
        <InfoGrid
          items={[
            { label: "Resident address", value: b.resident_address, wide: true },
            { label: "Native address", value: b.native_address, wide: true },
            { label: "Short address", value: b.short_address, wide: true },
          ]}
        />
      </SectionCard>

      <SectionCard title="Financial">
        <InfoGrid
          items={[
            { label: "Bank", value: b.bank_code },
            { label: "Cash account", value: b.cash_account_code },
            { label: "Account no.", value: b.account_no },
            { label: "RTGS/NEFT/IFSC", value: b.rtgs },
            { label: "UAN no.", value: b.uan_no },
            { label: "ESIC no.", value: b.esic_no },
            { label: "PAN no.", value: b.pan_no },
          ]}
        />
      </SectionCard>
    </View>
  );

  const renderMoreInfo = (info) => (
    <View>
      <SectionCard title="Identification">
        <InfoGrid
          items={[
            { label: "Identification mark", value: info.identification_mark, wide: true },
            { label: "Total experience", value: info.total_experience ? `${info.total_experience} yrs` : undefined },
            { label: "Referred by (emp ID)", value: info.referred_by_emp_id },
          ]}
        />
      </SectionCard>

      <SectionCard title="Nearest police station">
        <InfoGrid
          items={[
            { label: "Police station", value: info.police_station },
            { label: "Contact no.", value: info.police_contact },
            { label: "Address", value: info.police_address, wide: true },
          ]}
        />
      </SectionCard>

      <SectionCard title="Witnesses (if left the org)">
        <InfoGrid
          items={[
            { label: "1) Witness (emp ID)", value: info.witness1_emp_id },
            { label: "2) Witness (emp ID)", value: info.witness2_emp_id },
            { label: "Inform UAN on leaving", value: info.inform_uan_on_leaving === null || info.inform_uan_on_leaving === undefined ? undefined : (info.inform_uan_on_leaving ? "Yes" : "No") },
            { label: "Inform ESIC on leaving", value: info.inform_esic_on_leaving === null || info.inform_esic_on_leaving === undefined ? undefined : (info.inform_esic_on_leaving ? "Yes" : "No") },
          ]}
        />
      </SectionCard>

      <SectionCard title="Personalities who know employee">
        <InfoGrid
          items={[
            { label: "1) Name", value: info.personality1_name },
            { label: "1) Designation", value: info.personality1_designation_code },
            { label: "1) Contact no.", value: info.personality1_contact },
            { label: "1) Address", value: info.personality1_address, wide: true },
            { label: "2) Name", value: info.personality2_name },
            { label: "2) Designation", value: info.personality2_designation_code },
            { label: "2) Contact no.", value: info.personality2_contact },
            { label: "2) Address", value: info.personality2_address, wide: true },
          ]}
        />
      </SectionCard>
    </View>
  );

  // --------------------------------------------------
  // CONTACT / DOCUMENTS / FAMILY -- entry cards get a small colored
  // marker keyed off type so a long list is scannable at a glance
  // instead of every card looking identical.
  // --------------------------------------------------

  const renderContact = (contacts) =>
    contacts.length === 0 ? (
      <EmptyState text="No contact details on file." />
    ) : (
      contacts.map((c, i) => (
        <View key={i} style={styles.entryCard}>
          <View style={styles.entryHeaderRow}>
            <View style={styles.entryMarker} />
            <Text style={styles.entryTitle}>{c.contact_type_code || "Contact"}</Text>
          </View>
          <Text style={styles.entryBody}>
            {c.contact}
            {c.ext ? ` ext. ${c.ext}` : ""}
          </Text>
        </View>
      ))
    );

  const renderDocuments = (documents) =>
    documents.length === 0 ? (
      <EmptyState text="No documents on file." />
    ) : (
      documents.map((d, i) => {
        const expired = d.valid_until ? new Date(d.valid_until) < new Date() : false;
        return (
          <View key={i} style={styles.entryCard}>
            <View style={styles.entryHeaderRow}>
              <View style={[styles.entryMarker, expired && styles.entryMarkerWarn]} />
              <Text style={styles.entryTitle}>{d.document_type_code || "Document"}</Text>
              {expired ? (
                <View style={styles.expiredPill}>
                  <Text style={styles.expiredPillText}>Expired</Text>
                </View>
              ) : null}
            </View>
            <Text style={styles.entryBody}>{d.doc_file}</Text>
            {d.valid_until ? (
              <Text style={styles.entryMeta}>Valid until {prettyDate(d.valid_until)}</Text>
            ) : null}
          </View>
        );
      })
    );

  const renderFamily = (family) =>
    family.length === 0 ? (
      <EmptyState text="No family details on file." />
    ) : (
      family.map((r, i) => (
        <View key={i} style={styles.entryCard}>
          <View style={styles.entryHeaderRow}>
            <View style={styles.entryAvatar}>
              <Text style={styles.entryAvatarText}>{initials(r.relative_name)}</Text>
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.entryTitle}>{r.relative_name || "Relative"}</Text>
              <Text style={styles.entryBody}>
                {[r.relationship_code, r.marital_status].filter(Boolean).join(" · ") || "—"}
              </Text>
            </View>
          </View>
          {r.date_of_birth ? (
            <Text style={styles.entryMeta}>Born {prettyDate(r.date_of_birth)}</Text>
          ) : null}
        </View>
      ))
    );

  const isActive = !basic?.leaving_date;

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <View style={styles.screen}>
        <View style={styles.header}>
          <TouchableOpacity onPress={onClose} style={styles.closeButton} activeOpacity={0.8}>
            <Text style={styles.closeButtonText}>✕</Text>
          </TouchableOpacity>

          <View style={styles.headerAvatar}>
            {basic?.photo_base64 ? (
              <Image source={{ uri: basic.photo_base64 }} style={styles.headerAvatarImage} />
            ) : (
              <Text style={styles.headerAvatarText}>{initials(basic?.name)}</Text>
            )}
          </View>

          <Text style={styles.headerName} numberOfLines={1}>
            {basic?.name || "Employee"}
          </Text>

          <View style={styles.headerSubRow}>
            <Text style={styles.headerSub}>
              {basic?.emp_code ? `Code ${basic.emp_code}` : ""}
              {basic?.designation_code ? ` · ${basic.designation_code}` : ""}
            </Text>
            {basic ? (
              <View style={[styles.statusPill, isActive ? styles.statusPillActive : styles.statusPillLeft]}>
                <Text style={[styles.statusPillText, isActive ? styles.statusPillTextActive : styles.statusPillTextLeft]}>
                  {isActive ? "Active" : `Left ${prettyDate(basic.leaving_date)}`}
                </Text>
              </View>
            ) : null}
          </View>

          {basic ? (
            <View style={styles.chipRow}>
              {age !== null ? <Chip label={`${age} yrs old`} styles={styles} /> : null}
              {tenure ? (
                <Chip
                  label={`${tenure.label} ${tenure.active ? "at company" : "served"}`}
                  styles={styles}
                />
              ) : null}
              {basic.blood_group ? <Chip label={basic.blood_group} styles={styles} /> : null}
              {basic.marital_status ? <Chip label={basic.marital_status} styles={styles} /> : null}
            </View>
          ) : null}
        </View>

        {usingSample ? (
          <Text style={styles.sampleNote}>Showing sample data — backend not connected yet</Text>
        ) : null}

        <ScrollView contentContainerStyle={styles.content}>
          {loading || !profile ? (
            <ActivityIndicator color={colors.primary} style={{ marginTop: spacing.xl }} />
          ) : (
            TABS.map((tab) => {
              const isOpen = expandedSection === tab.key;
              return (
                <View key={tab.key} style={styles.accordionSection}>
                  <TouchableOpacity
                    style={styles.accordionHeader}
                    onPress={() => setExpandedSection(isOpen ? null : tab.key)}
                    activeOpacity={0.8}
                  >
                    <Text style={styles.accordionTitle}>{tab.label}</Text>
                    <Text style={styles.accordionChevron}>{isOpen ? "–" : "+"}</Text>
                  </TouchableOpacity>
                  {isOpen && (
                    <View style={styles.accordionBody}>
                      {tab.key === "basic" && renderBasic(profile.basic)}
                      {tab.key === "contact" && renderContact(profile.contacts)}
                      {tab.key === "documents" && renderDocuments(profile.documents)}
                      {tab.key === "family" && renderFamily(profile.family)}
                      {tab.key === "more" && renderMoreInfo(profile.more_info)}
                    </View>
                  )}
                </View>
              );
            })
          )}
        </ScrollView>
      </View>
    </Modal>
  );
}

function Chip({ label, styles }) {
  return (
    <View style={styles.chip}>
      <Text style={styles.chipText}>{label}</Text>
    </View>
  );
}

function createStyles({ colors, radius, spacing, shadow, typography }) {
  return StyleSheet.create({
    screen: { flex: 1, backgroundColor: colors.bg },
    header: {
      paddingTop: 56,
      paddingHorizontal: spacing.lg,
      paddingBottom: spacing.lg,
      borderBottomWidth: 1,
      borderBottomColor: colors.border,
      alignItems: "center",
    },
    headerAvatar: {
      width: 88,
      height: 88,
      borderRadius: radius.pill,
      backgroundColor: colors.primary,
      alignItems: "center",
      justifyContent: "center",
      marginBottom: spacing.sm,
      overflow: "hidden",
      borderWidth: 3,
      borderColor: colors.primarySoft,
    },
    headerAvatarText: { color: "#fff", fontWeight: "700", fontSize: 28 },
    headerAvatarImage: { width: 88, height: 88 },
    headerName: { ...typography.h2, textAlign: "center" },
    headerSubRow: {
      flexDirection: "row",
      alignItems: "center",
      marginTop: 4,
      gap: 8,
    },
    headerSub: { ...typography.small },
    statusPill: {
      paddingHorizontal: 8,
      paddingVertical: 2,
      borderRadius: radius.pill,
    },
    statusPillActive: { backgroundColor: colors.successBadgeBg },
    statusPillLeft: { backgroundColor: colors.card, borderWidth: 1, borderColor: colors.border },
    statusPillText: { fontSize: 10, fontWeight: "700" },
    statusPillTextActive: { color: colors.successText },
    statusPillTextLeft: { color: colors.textMuted },
    chipRow: {
      flexDirection: "row",
      flexWrap: "wrap",
      justifyContent: "center",
      gap: 6,
      marginTop: spacing.sm,
    },
    chip: {
      backgroundColor: colors.primarySoft,
      borderRadius: radius.pill,
      paddingHorizontal: 10,
      paddingVertical: 5,
    },
    chipText: { color: colors.primary, fontWeight: "600", fontSize: 12 },
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
      zIndex: 1,
    },
    closeButtonText: { color: colors.textMuted, fontSize: 14, fontWeight: "600" },
    accordionSection: {
      borderBottomWidth: 1,
      borderBottomColor: colors.border,
    },
    accordionHeader: {
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "space-between",
      paddingVertical: spacing.md,
    },
    accordionTitle: { ...typography.h2, fontSize: 15 },
    accordionChevron: { ...typography.h2, fontSize: 15, color: colors.primary },
    accordionBody: { paddingBottom: spacing.md },
    sampleNote: {
      ...typography.small,
      color: colors.amber,
      textAlign: "center",
      marginTop: spacing.sm,
    },
    content: { paddingHorizontal: spacing.lg },

    // --- Section cards (Basic / More tabs) ---
    sectionCard: {
      backgroundColor: colors.card,
      borderRadius: radius.md,
      borderWidth: 1,
      borderColor: colors.border,
      padding: spacing.md,
      marginTop: spacing.sm,
    },
    sectionCardHeader: {
      flexDirection: "row",
      alignItems: "center",
      marginBottom: spacing.sm,
    },
    sectionDot: {
      width: 8,
      height: 8,
      borderRadius: 4,
      backgroundColor: colors.primary,
      marginRight: 8,
    },
    sectionCardTitle: {
      ...typography.label,
      color: colors.primary,
      textTransform: "uppercase",
      fontSize: 11,
    },
    infoGrid: {
      flexDirection: "row",
      flexWrap: "wrap",
      justifyContent: "space-between",
    },
    infoTile: {
      width: "48%",
      marginBottom: spacing.sm,
    },
    infoTileWide: { width: "100%" },
    infoLabel: { ...typography.small, color: colors.textFaint, marginBottom: 2 },
    infoValue: { ...typography.body, color: colors.text },
    emptyInline: { ...typography.small, color: colors.textFaint },

    // --- Entry cards (Contact / Documents / Family) ---
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
      marginBottom: 2,
    },
    entryMarker: {
      width: 8,
      height: 8,
      borderRadius: 4,
      backgroundColor: colors.primary,
      marginRight: 8,
    },
    entryMarkerWarn: { backgroundColor: colors.danger },
    entryAvatar: {
      width: 32,
      height: 32,
      borderRadius: radius.pill,
      backgroundColor: colors.primarySoft,
      alignItems: "center",
      justifyContent: "center",
      marginRight: spacing.sm,
    },
    entryAvatarText: { color: colors.primary, fontWeight: "700", fontSize: 12 },
    entryTitle: { ...typography.h2, fontSize: 15, flex: 1 },
    entryBody: { ...typography.body, color: colors.textMuted },
    entryMeta: { ...typography.small, marginTop: 4 },
    expiredPill: {
      backgroundColor: colors.dangerBadgeBg,
      borderRadius: radius.pill,
      paddingHorizontal: 8,
      paddingVertical: 2,
    },
    expiredPillText: { color: colors.dangerText, fontSize: 10, fontWeight: "700" },
    emptyText: {
      ...typography.body,
      color: colors.textFaint,
      textAlign: "center",
      marginTop: spacing.xl,
    },
  });
}