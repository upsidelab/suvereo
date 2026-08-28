/** Absent when a panel lists roles rather than subjects. */
export type AssignmentKind = "user" | "service-account" | "group";

export type AssignmentOption = {
  id: number;
  label: string;
  kind?: AssignmentKind;
  /** Extra detail beside the label - a group's member count. */
  note?: string;
};

const KIND_LABELS: Record<AssignmentKind, string> = {
  "user": "User",
  "service-account": "Service account",
  "group": "Group",
};

export function assignmentKindLabel(kind: AssignmentKind): string {
  return KIND_LABELS[kind];
}

/** Unique across kinds: a user and a group can share an id. */
export function assignmentOptionKey(option: AssignmentOption): string {
  return `${option.kind ?? "item"}-${option.id}`;
}

/** For pickers, which have no separate column to carry the kind. */
export function assignmentOptionDescription(option: AssignmentOption): string {
  const named = option.kind ? `${assignmentKindLabel(option.kind)}: ${option.label}` : option.label;
  return option.note ? `${named} (${option.note})` : named;
}

export function memberCountNote(memberCount: number): string {
  return `${memberCount} ${memberCount === 1 ? "member" : "members"}`;
}

export function subjectOption(subject: { id: number; email: string; isServiceAccount: boolean }): AssignmentOption {
  return {
    id: subject.id,
    label: subject.email,
    kind: subject.isServiceAccount ? "service-account" : "user",
  };
}

export function groupOption(group: { id: number; name: string; memberCount: number }): AssignmentOption {
  return { id: group.id, label: group.name, kind: "group", note: memberCountNote(group.memberCount) };
}

/** No kind, so no Type column and no prefix in the picker. */
export function roleOption(role: { id: number; name: string }): AssignmentOption {
  return { id: role.id, label: role.name };
}
