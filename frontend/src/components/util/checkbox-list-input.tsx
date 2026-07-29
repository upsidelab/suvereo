import { Checkbox } from "@/components/ui/checkbox.tsx";
import { ScrollArea } from "@/components/ui/scroll-area.tsx";

export interface CheckboxListOption {
  id: number;
  label: string;
}

export interface CheckboxListInputProps {
  options: CheckboxListOption[];
  selectedIds: number[];
  onChange: (ids: number[]) => void;
}

export function CheckboxListInput({ options, selectedIds, onChange }: CheckboxListInputProps) {
  return (
    <ScrollArea className="h-[200px] w-full rounded-md border px-4 py-2">
      <div className="space-y-2">
        {options.map((option) => {
          const checked = selectedIds.includes(option.id);
          return (
            <div key={option.id} className="flex flex-row items-center space-x-3 space-y-0">
              <Checkbox
                checked={checked}
                onCheckedChange={(value) => {
                  onChange(value ? [...selectedIds, option.id] : selectedIds.filter((id) => id !== option.id));
                }}
              />
              <label className="text-sm font-normal">{option.label}</label>
            </div>
          );
        })}
      </div>
    </ScrollArea>
  );
}
