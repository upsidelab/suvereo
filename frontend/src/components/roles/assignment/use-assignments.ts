import { useCallback, useEffect, useState } from "react";
import { AssignmentOption } from "@/components/roles/assignment/assignment-option.ts";

export interface UseAssignmentsOptions {
  canAssign: boolean;
  /** Null when there is nothing to load yet - no data set chosen, say. */
  loadItems: (() => Promise<AssignmentOption[]>) | null;
  /** Only called when `canAssign`. */
  loadCandidates: (granted: AssignmentOption[]) => Promise<AssignmentOption[]>;
  itemsError: string;
  candidatesNotice: string;
  onChanged?: () => void;
}

export interface Assignments {
  items: AssignmentOption[];
  candidates: AssignmentOption[];
  error: string | null;
  pickerNotice: string | null;
  /** Surfaces the server's message on failure, reloads on success. */
  submit: (request: Promise<Response>, fallback: string) => Promise<void>;
}

/** `loadItems` and `loadCandidates` must be memoized by the caller - they are effect dependencies. */
export function useAssignments({
  canAssign,
  loadItems,
  loadCandidates,
  itemsError,
  candidatesNotice,
  onChanged,
}: UseAssignmentsOptions): Assignments {
  const [items, setItems] = useState<AssignmentOption[]>([]);
  const [candidates, setCandidates] = useState<AssignmentOption[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [pickerNotice, setPickerNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (loadItems === null) {
      setItems([]);
      setCandidates([]);
      return;
    }
    setError(null);

    let granted: AssignmentOption[];
    try {
      granted = await loadItems();
    } catch {
      setError(itemsError);
      return;
    }
    setItems(granted);

    if (!canAssign) return;

    try {
      setCandidates(await loadCandidates(granted));
      setPickerNotice(null);
    } catch {
      setCandidates([]);
      setPickerNotice(candidatesNotice);
    }
  }, [loadItems, loadCandidates, canAssign, itemsError, candidatesNotice]);

  useEffect(() => {
    load();
  }, [load]);

  const submit = async (request: Promise<Response>, fallback: string) => {
    const response = await request;
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      setError(body.detail ?? fallback);
      return;
    }
    await load();
    onChanged?.();
  };

  return { items, candidates, error, pickerNotice, submit };
}
