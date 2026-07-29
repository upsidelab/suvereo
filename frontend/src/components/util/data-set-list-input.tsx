import { DataSet } from "@/lib/types.ts";
import { UseFormReturn } from "react-hook-form";
import { FormControl, FormField, FormItem } from "@/components/ui/form.tsx";
import { CheckboxListInput } from "@/components/util/checkbox-list-input.tsx";

export interface DataSetListInputProps {
  availableDataSets: DataSet[];
  name: string;
  form: UseFormReturn<any, any, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
}

export function DataSetListInput({ availableDataSets, name, form }: DataSetListInputProps) {
  return (
    <FormField
      name={name}
      control={form.control}
      render={({ field }) => (
        <FormItem>
          <FormControl>
            <CheckboxListInput
              options={availableDataSets.map((dataSet) => ({ id: dataSet.id as number, label: dataSet.name }))}
              selectedIds={(field.value as number[]) ?? []}
              onChange={field.onChange}
            />
          </FormControl>
        </FormItem>
      )}
    />
  );
}
