import { ReactNode } from "react";
import { AssignmentOption } from "@/components/roles/assignment/assignment-option.ts";
import { AssignmentPicker } from "@/components/roles/assignment/assignment-picker.tsx";
import { AssignmentList } from "@/components/roles/assignment/assignment-list.tsx";

export interface AssignmentPanelProps {
  items: AssignmentOption[];
  candidates: AssignmentOption[];
  canAssign: boolean;
  columnLabel: string;
  emptyMessage: string;
  pickerPlaceholder: string;
  addLabel?: string;
  removeLabel?: string;
  error?: string | null;
  /** Replaces the picker when the candidates can't be listed. */
  pickerNotice?: string | null;
  onAdd: (option: AssignmentOption) => void;
  onRemove: (option: AssignmentOption) => void;
  /** Rendered above the picker. */
  children?: ReactNode;
}

export function AssignmentPanel({
  items,
  candidates,
  canAssign,
  columnLabel,
  emptyMessage,
  pickerPlaceholder,
  addLabel = "Add",
  removeLabel = "Remove",
  error,
  pickerNotice,
  onAdd,
  onRemove,
  children,
}: AssignmentPanelProps) {
  return (
    <div className="flex flex-col grow min-h-0">
      {error && <p className="text-sm text-destructive mb-4">{error}</p>}
      {children}
      {canAssign && (
        pickerNotice
          ? <p className="text-sm text-muted-foreground mb-4">{pickerNotice}</p>
          : (
            <AssignmentPicker
              candidates={candidates}
              placeholder={pickerPlaceholder}
              addLabel={addLabel}
              onAdd={onAdd}
            />
          )
      )}
      <AssignmentList
        items={items}
        columnLabel={columnLabel}
        emptyMessage={emptyMessage}
        removeLabel={removeLabel}
        onRemove={canAssign ? onRemove : undefined}
      />
    </div>
  );
}
