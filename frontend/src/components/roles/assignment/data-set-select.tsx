import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select.tsx";
import { DataSet } from "@/lib/types.ts";

export interface DataSetSelectProps {
  dataSets: DataSet[];
  selectedDataSetId: number | null;
  onChange: (dataSetId: number) => void;
}

export function DataSetSelect({ dataSets, selectedDataSetId, onChange }: DataSetSelectProps) {
  return (
    <div className="flex items-center space-x-4 mb-4">
      <p className="text-sm font-medium leading-none whitespace-nowrap">Data set</p>
      <Select
        value={selectedDataSetId === null ? "" : String(selectedDataSetId)}
        onValueChange={(value) => onChange(Number(value))}
      >
        <SelectTrigger className="w-[300px]">
          <SelectValue placeholder="Select a data set..." />
        </SelectTrigger>
        <SelectContent>
          {dataSets.map((dataSet) => (
            <SelectItem key={dataSet.id} value={String(dataSet.id)}>{dataSet.name}</SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
