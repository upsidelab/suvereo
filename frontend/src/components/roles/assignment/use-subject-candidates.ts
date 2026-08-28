import { useCallback } from "react";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import {
  AssignmentOption,
  assignmentOptionKey,
  groupOption,
  subjectOption
} from "@/components/roles/assignment/assignment-option.ts";

const api = new ApiClient(authenticationProviderInstance);

export const SUBJECT_PICKER_NOTICE =
  "You need the User → View and Group → View permissions to add members by name.";

/** Keyed by kind, so the caller knows which endpoint a grant goes to. */
export function useSubjectCandidates() {
  return useCallback(async (): Promise<AssignmentOption[]> => {
    const [users, serviceAccounts, groups] = await Promise.all([
      api.getAllUsers(),
      api.serviceAccounts().getAllServiceAccounts(),
      api.groups().getGroups(),
    ]);

    return [
      ...users.map((user) => subjectOption({ ...user, isServiceAccount: false })),
      ...serviceAccounts.map((account) => subjectOption({ ...account, isServiceAccount: true })),
      ...groups.map(groupOption),
    ];
  }, []);
}

export function withoutGranted(candidates: AssignmentOption[], granted: AssignmentOption[]): AssignmentOption[] {
  const grantedKeys = new Set(granted.map(assignmentOptionKey));
  return candidates.filter((candidate) => !grantedKeys.has(assignmentOptionKey(candidate)));
}
