import { useState, useEffect } from "react";
import { Label } from "@/components/ui/label.tsx";
import { Input } from "@/components/ui/input.tsx";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select.tsx";
import { FormModal } from "@/components/ui/form-modal.tsx";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { IntegrationType } from "@/lib/types.ts";

const api = new ApiClient(authenticationProviderInstance);

type ConfigSchemaProperty = {
  title?: string;
  type?: string;
  description?: string;
};

type ConfigSchema = {
  properties?: Record<string, ConfigSchemaProperty>;
  required?: string[];
};

interface AddIntegrationModalProps {
  dataSetId: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

export function AddIntegrationModal({ dataSetId, open, onOpenChange, onSuccess }: AddIntegrationModalProps) {
  const [integrationTypes, setIntegrationTypes] = useState<IntegrationType[]>([]);
  const [loadingTypes, setLoadingTypes] = useState(true);
  const [selectedType, setSelectedType] = useState<string>("");
  const [config, setConfig] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setLoadingTypes(true);
    api.integrations().listTypes()
      .then(setIntegrationTypes)
      .finally(() => setLoadingTypes(false));
  }, [open]);

  useEffect(() => {
    if (!open) {
      setSelectedType("");
      setConfig({});
      setError(null);
    }
  }, [open]);

  const selectedIntegrationType = integrationTypes.find(t => t.type === selectedType);
  const schema = selectedIntegrationType?.config_schema as ConfigSchema | undefined;
  const properties = schema?.properties ?? {};
  const required = schema?.required ?? [];

  const handleFieldChange = (key: string, value: string) => {
    setConfig(prev => ({ ...prev, [key]: value }));
  };

  const isValid = !!selectedType && required.every(key => !!config[key]);

  const handleSubmit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await api.integrations().create(dataSetId, selectedType, config);
      onSuccess();
      onOpenChange(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create integration");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <FormModal
      open={open}
      onOpenChange={onOpenChange}
      title="Add Integration"
      onSubmit={handleSubmit}
      onCancel={() => onOpenChange(false)}
      submitLabel="Add"
      submitting={submitting}
      disabled={!isValid}
      loading={loadingTypes}
      loadingText="Loading integration types..."
      dependencies={[selectedType, config, error]}
    >
      {error && (
        <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-md">
          <p className="text-sm text-destructive">{error}</p>
        </div>
      )}

      <div className="flex flex-col gap-1">
        <Label htmlFor="integration-type">Type</Label>
        <Select
          value={selectedType}
          onValueChange={setSelectedType}
          disabled={integrationTypes.length === 0}
        >
          <SelectTrigger id="integration-type">
            <SelectValue placeholder="Select integration type" />
          </SelectTrigger>
          <SelectContent>
            {integrationTypes.map(t => (
              <SelectItem key={t.type} value={t.type}>{t.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {selectedType && Object.entries(properties).map(([key, prop]) => (
        <div key={key} className="flex flex-col gap-1">
          <Label htmlFor={`config-${key}`}>
            {prop.title ?? key}
            {required.includes(key) && <span className="text-destructive ml-1">*</span>}
          </Label>
          <Input
            id={`config-${key}`}
            placeholder={prop.description ?? prop.title ?? key}
            value={config[key] ?? ""}
            onChange={e => handleFieldChange(key, e.target.value)}
          />
        </div>
      ))}
    </FormModal>
  );
}
