import { useId } from "react";
import { Checkbox } from "@/components/ui/checkbox.tsx";
import { ScrollArea } from "@/components/ui/scroll-area.tsx";

export interface CheckboxListOption {
  id: number;
  label: string;
  description?: string;
}

export interface CheckboxListInputProps {
  options: CheckboxListOption[];
  selectedIds: number[];
  onChange: (ids: number[]) => void;
  disabled?: boolean;
}

export function CheckboxListInput({ options, selectedIds, onChange, disabled }: CheckboxListInputProps) {
  const instanceId = useId();

  return (
    <ScrollArea className="h-[200px] w-full rounded-md border px-4 py-2">
      <div className="space-y-2">
        {options.map((option) => {
          const checked = selectedIds.includes(option.id);
          const checkboxId = `${instanceId}-${option.id}`;
          return (
            <div key={option.id} className="flex flex-row items-start space-x-3 space-y-0">
              <Checkbox
                id={checkboxId}
                checked={checked}
                disabled={disabled}
                onCheckedChange={(value) => {
                  onChange(value ? [...selectedIds, option.id] : selectedIds.filter((id) => id !== option.id));
                }}
                className="mt-0.5"
              />
              <div>
                <label htmlFor={checkboxId} className="text-sm font-normal">{option.label}</label>
                {option.description && <p className="text-xs text-muted-foreground">{option.description}</p>}
              </div>
            </div>
          );
        })}
      </div>
    </ScrollArea>
  );
}
