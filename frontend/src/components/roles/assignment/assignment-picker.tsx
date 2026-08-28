import { useState } from "react";
import { Button } from "@/components/ui/button.tsx";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select.tsx";
import {
  AssignmentOption,
  assignmentOptionDescription,
  assignmentOptionKey
} from "@/components/roles/assignment/assignment-option.ts";

export interface AssignmentPickerProps {
  candidates: AssignmentOption[];
  placeholder: string;
  /** Shown on the disabled picker when there is nothing left to pick. */
  emptyPlaceholder: string;
  addLabel: string;
  onAdd: (option: AssignmentOption) => void;
}

export function AssignmentPicker({
  candidates,
  placeholder,
  emptyPlaceholder,
  addLabel,
  onAdd,
}: AssignmentPickerProps) {
  const [selectedKey, setSelectedKey] = useState<string>("");
  const selected = candidates.find((candidate) => assignmentOptionKey(candidate) === selectedKey);
  const isEmpty = candidates.length === 0;

  const handleAdd = () => {
    if (!selected) return;
    setSelectedKey("");
    onAdd(selected);
  };

  return (
    <div className="flex space-x-4 mb-4">
      <Select value={selectedKey} onValueChange={setSelectedKey} disabled={isEmpty}>
        <SelectTrigger className="w-[300px]">
          <SelectValue placeholder={isEmpty ? emptyPlaceholder : placeholder} />
        </SelectTrigger>
        <SelectContent>
          {candidates.map((candidate) => (
            <SelectItem key={assignmentOptionKey(candidate)} value={assignmentOptionKey(candidate)}>
              {assignmentOptionDescription(candidate)}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Button onClick={handleAdd} disabled={!selected}>{addLabel}</Button>
    </div>
  );
}
