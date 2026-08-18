import { useId } from "react";
import { Checkbox } from "@/components/ui/checkbox.tsx";

export interface CheckboxListOption {
  code: string;
  label: string;
  note?: string;
}

export interface CheckboxListInputProps {
  options: CheckboxListOption[];
  selectedCodes: string[];
  onChange: (codes: string[]) => void;
  disabled?: boolean;
}

export function CheckboxListInput({ options, selectedCodes, onChange, disabled }: CheckboxListInputProps) {
  const instanceId = useId();

  return (
    <div className="space-y-2">
      {options.map((option) => {
        const checked = selectedCodes.includes(option.code);
        const checkboxId = `${instanceId}-${option.code}`;
        return (
          <div key={option.code} className="flex flex-row items-start space-x-3 space-y-0">
            <Checkbox
              id={checkboxId}
              checked={checked}
              disabled={disabled}
              onCheckedChange={(value) => {
                onChange(value
                  ? [...selectedCodes, option.code]
                  : selectedCodes.filter((code) => code !== option.code));
              }}
              className="mt-0.5"
            />
            <div>
              <label htmlFor={checkboxId} className="text-sm font-normal">{option.label}</label>
              {option.note && <p className="text-xs text-muted-foreground">{option.note}</p>}
            </div>
          </div>
        );
      })}
    </div>
  );
}
