// ProfileModal.js
// Full-screen profile sheet, opened from an avatar button in the app
// header. Photo sits large and left-aligned at the top; Basic / Contact /
// Documents / Family / More are a vertical accordion below it -- tap a
// section name to expand its fields in place, tap again to collapse.
// Reuses the app's existing theme tokens -- no new palette introduced.
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

  const renderBasic = (basic) => (
    <View>
      <SectionHeader title="Personal" />
      <Field label="Employee code" value={basic.emp_code} />
      <Field label="Username" value={basic.username} />
      <Field label="Date of birth" value={basic.date_of_birth} />
      <Field label="Gender" value={basic.gender} />
      <Field label="Marital status" value={basic.marital_status} />
      <Field label="Anniversary" value={basic.anniversary} />
      <Field label="Qualification" value={basic.qualification_code} />
      <Field label="Blood group" value={basic.blood_group} />
      <Field label="Height" value={basic.height} />
      <Field label="Weight" value={basic.weight} />
      <Field label="Aadhar no." value={basic.aadhar_no} />

      <SectionHeader title="Employment" />
      <Field label="Department" value={basic.department_code} />
      <Field label="Designation" value={basic.designation_code} />
      <Field label="Joining date" value={basic.joining_date} />
      <Field label="Leaving date" value={basic.leaving_date} />
      <Field label="Work place" value={basic.work_place} />

      <SectionHeader title="Address" />
      <Field label="Resident address" value={basic.resident_address} />
      <Field label="Native address" value={basic.native_address} />
      <Field label="Short address" value={basic.short_address} />

      <SectionHeader title="Financial" />
      <Field label="Bank" value={basic.bank_code} />
      <Field label="Account no." value={basic.account_no} />
      <Field label="RTGS/NEFT/IFSC" value={basic.rtgs} />
      <Field label="Cash account" value={basic.cash_account_code} />
      <Field label="UAN no." value={basic.uan_no} />
      <Field label="ESIC no." value={basic.esic_no} />
      <Field label="PAN no." value={basic.pan_no} />
    </View>
  );

  const renderMoreInfo = (info) => (
    <View>
      <SectionHeader title="Identification" />
      <Field label="Identification mark" value={info.identification_mark} />
      <Field label="Total experience (yrs)" value={info.total_experience} />
      <Field label="Referred by (emp ID)" value={info.referred_by_emp_id} />

      <SectionHeader title="Nearest police station" />
      <Field label="Police station" value={info.police_station} />
      <Field label="Address" value={info.police_address} />
      <Field label="Contact no." value={info.police_contact} />

      <SectionHeader title="Witnesses (if left the org)" />
      <Field label="1) Witness (emp ID)" value={info.witness1_emp_id} />
      <Field label="2) Witness (emp ID)" value={info.witness2_emp_id} />
      <Field label="Inform UAN about leaving" value={info.inform_uan_on_leaving ? "Yes" : "No"} />
      <Field label="Inform ESIC about leaving" value={info.inform_esic_on_leaving ? "Yes" : "No"} />

      <SectionHeader title="Personalities who know employee" />
      <Field label="1) Name" value={info.personality1_name} />
      <Field label="1) Designation" value={info.personality1_designation_code} />
      <Field label="1) Address" value={info.personality1_address} />
      <Field label="1) Contact no." value={info.personality1_contact} />
      <Field label="2) Name" value={info.personality2_name} />
      <Field label="2) Designation" value={info.personality2_designation_code} />
      <Field label="2) Address" value={info.personality2_address} />
      <Field label="2) Contact no." value={info.personality2_contact} />
    </View>
  );

  const renderContact = (contacts) =>
    contacts.length === 0 ? (
      <EmptyState text="No contact details on file." />
    ) : (
      contacts.map((c, i) => (
        <View key={i} style={styles.entryCard}>
          <Text style={styles.entryTitle}>{c.contact_type_code}</Text>
          <Text style={styles.entryBody}>{c.contact}{c.ext ? ` ext. ${c.ext}` : ""}</Text>
        </View>
      ))
    );

  const renderDocuments = (documents) =>
    documents.length === 0 ? (
      <EmptyState text="No documents on file." />
    ) : (
      documents.map((d, i) => (
        <View key={i} style={styles.entryCard}>
          <Text style={styles.entryTitle}>{d.document_type_code}</Text>
          <Text style={styles.entryBody}>{d.doc_file}</Text>
          {d.valid_until ? (
            <Text style={styles.entryMeta}>Valid until {new Date(d.valid_until).toLocaleDateString()}</Text>
          ) : null}
        </View>
      ))
    );

  const renderFamily = (family) =>
    family.length === 0 ? (
      <EmptyState text="No family details on file." />
    ) : (
      family.map((r, i) => (
        <View key={i} style={styles.entryCard}>
          <Text style={styles.entryTitle}>{r.relative_name}</Text>
          <Text style={styles.entryBody}>{r.relationship_code} · {r.marital_status}</Text>
          {r.date_of_birth ? (
            <Text style={styles.entryMeta}>Born {new Date(r.date_of_birth).toLocaleDateString()}</Text>
          ) : null}
        </View>
      ))
    );

  function SectionHeader({ title }) {
    return <Text style={styles.sectionHeader}>{title}</Text>;
  }

  function Field({ label, value }) {
    return (
      <View style={styles.fieldRow}>
        <Text style={styles.fieldLabel}>{label}</Text>
        <Text style={styles.fieldValue}>{value || "—"}</Text>
      </View>
    );
  }

  function EmptyState({ text }) {
    return <Text style={styles.emptyText}>{text}</Text>;
  }

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <View style={styles.screen}>
        <View style={styles.header}>
          <TouchableOpacity onPress={onClose} style={styles.closeButton} activeOpacity={0.8}>
            <Text style={styles.closeButtonText}>✕</Text>
          </TouchableOpacity>
          <View style={styles.headerAvatar}>
            {profile?.basic?.photo_base64 ? (
              <Image
                source={{ uri: profile.basic.photo_base64 }}
                style={styles.headerAvatarImage}
              />
            ) : (
              <Text style={styles.headerAvatarText}>
                {initials(profile?.basic?.name)}
              </Text>
            )}
          </View>
          <Text style={styles.headerName} numberOfLines={1}>
            {profile?.basic?.name || "Employee"}
          </Text>
          <Text style={styles.headerSub}>
            {profile?.basic?.emp_code ? `Code ${profile.basic.emp_code}` : ""}
          </Text>
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

function createStyles({ colors, radius, spacing, shadow, typography }) {
  return StyleSheet.create({
    screen: { flex: 1, backgroundColor: colors.bg },
    header: {
      paddingTop: 56,
      paddingHorizontal: spacing.lg,
      paddingBottom: spacing.lg,
      borderBottomWidth: 1,
      borderBottomColor: colors.border,
    },
    headerAvatar: {
      width: 84,
      height: 84,
      borderRadius: radius.pill,
      backgroundColor: colors.primary,
      alignItems: "center",
      justifyContent: "center",
      marginBottom: spacing.sm,
      overflow: "hidden",
    },
    headerAvatarText: { color: "#fff", fontWeight: "700", fontSize: 28 },
    headerAvatarImage: { width: 84, height: 84 },
    sectionHeader: {
      ...typography.label,
      color: colors.primary,
      marginTop: spacing.md,
      marginBottom: 4,
      textTransform: "uppercase",
      fontSize: 11,
    },
    headerName: { ...typography.h2 },
    headerSub: { ...typography.small, marginTop: 2 },
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
    fieldRow: {
      flexDirection: "row",
      justifyContent: "space-between",
      paddingVertical: 10,
      borderBottomWidth: 1,
      borderBottomColor: colors.border,
    },
    fieldLabel: { ...typography.label },
    fieldValue: { ...typography.body, maxWidth: "60%", textAlign: "right" },
    entryCard: {
      backgroundColor: colors.card,
      borderRadius: radius.md,
      borderWidth: 1,
      borderColor: colors.border,
      padding: spacing.md,
      marginBottom: spacing.sm,
    },
    entryTitle: { ...typography.h2, fontSize: 15, marginBottom: 2 },
    entryBody: { ...typography.body, color: colors.textMuted },
    entryMeta: { ...typography.small, marginTop: 4 },
    emptyText: {
      ...typography.body,
      color: colors.textFaint,
      textAlign: "center",
      marginTop: spacing.xl,
    },
  });
}