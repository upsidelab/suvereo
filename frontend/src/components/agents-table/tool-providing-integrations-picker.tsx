import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { ToolProvidingIntegrationOption } from "@/lib/types";

interface ToolProvidingIntegrationsPickerProps {
  options: ToolProvidingIntegrationOption[];
  loading: boolean;
  failed: boolean;
  selected: number[];
  onChange: (selected: number[]) => void;
  error?: string;
  readOnly: boolean;
}

export function ToolProvidingIntegrationsPicker({
  options,
  loading,
  failed,
  selected,
  onChange,
  error,
  readOnly
}: ToolProvidingIntegrationsPickerProps) {
  const toggle = (id: number, checked: boolean) =>
    onChange(checked ? [...selected, id] : selected.filter(selectedId => selectedId !== id));
  // A selected integration that is no longer offered stays listed, so it can be unticked before saving.
  const unavailable = selected
    .filter(id => !options.some(option => option.id === id))
    .map(id => ({ id, name: "Unavailable tool source" }));
  const rows = [...options, ...unavailable];

  const renderRows = () => {
    if (loading) {
      return <p className="text-sm text-muted-foreground">Loading tool sources…</p>;
    }
    if (failed) {
      return <p className="text-sm text-destructive">Couldn't load tool sources. The current selection is kept.</p>;
    }
    if (rows.length === 0) {
      return <p className="text-sm text-muted-foreground">No tool sources are connected to this data set.</p>;
    }
    return rows.map(option => {
      const checkboxId = `tool-providing-integration-${option.id}`;
      return (
        <div key={option.id} className="flex items-center space-x-3">
          <Checkbox
            id={checkboxId}
            checked={selected.includes(option.id)}
            disabled={readOnly}
            onCheckedChange={value => toggle(option.id, value === true)}
          />
          <label htmlFor={checkboxId} className="text-sm">{option.name}</label>
        </div>
      );
    });
  };

  return (
    <div className="flex flex-col gap-2 rounded-lg border p-4">
      <div className="space-y-0.5">
        <Label>Tool sources</Label>
        <p className="text-[0.8rem] text-muted-foreground">
          Connected services this agent can call tools from, such as MCP servers.
        </p>
      </div>
      {renderRows()}
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}
