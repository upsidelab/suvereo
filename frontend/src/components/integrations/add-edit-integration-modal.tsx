import { useState, useEffect, useRef } from "react";
import { Label } from "@/components/ui/label.tsx";
import { Input } from "@/components/ui/input.tsx";
import { Button } from "@/components/ui/button.tsx";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select.tsx";
import { FormModal } from "@/components/ui/form-modal.tsx";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { Integration, IntegrationType } from "@/lib/types.ts";
import { OAUTH_CHANNEL } from "@/pages/oauth-complete.tsx";

const api = new ApiClient(authenticationProviderInstance);

type ConfigSchemaProperty = {
  title?: string;
  type?: string;
  description?: string;
  enum?: string[];
  default?: unknown;
};

type ConfigSchema = {
  properties?: Record<string, ConfigSchemaProperty>;
  required?: string[];
};

interface AddEditIntegrationModalProps {
  dataSetId: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
  integrationTypeName?: string;
  integration?: Integration | null;
  readOnly?: boolean;
}

export function AddEditIntegrationModal({
  dataSetId,
  open,
  onOpenChange,
  onSuccess,
  integrationTypeName,
  integration,
  readOnly = false,
}: AddEditIntegrationModalProps) {
  const [integrationTypes, setIntegrationTypes] = useState<IntegrationType[]>([]);
  const [loadingTypes, setLoadingTypes] = useState(true);
  const [selectedType, setSelectedType] = useState<string>("");
  const [config, setConfig] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [connected, setConnected] = useState(false);
  const [flowState, setFlowState] = useState<string>("");
  const [flowExpiresInMs, setFlowExpiresInMs] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const popupRef = useRef<Window | null>(null);

  const isEditing = !!integration;

  useEffect(() => {
    if (!open) return;
    if (readOnly) {
      setLoadingTypes(false);
      return;
    }
    setLoadingTypes(true);
    api.integrations().listTypes()
      .then(setIntegrationTypes)
      .catch(() => setError("Failed to load the integration types."))
      .finally(() => setLoadingTypes(false));
  }, [open, readOnly]);

  useEffect(() => {
    if (!open) {
      setSelectedType("");
      setConfig({});
      setError(null);
      setConnected(false);
      setConnecting(false);
      setFlowState("");
      setFlowExpiresInMs(0);
      popupRef.current?.close();
      return;
    }
    if (integration) {
      setSelectedType(integration.type);
      setConfig(Object.fromEntries(
        Object.entries(integration.config).map(([key, value]) => [key, String(value ?? "")])
      ));
    }
  }, [open, integration]);

  const selectedIntegrationType = integrationTypes.find(t => t.type === selectedType);
  // The type catalog needs the change permission, so read-only reads the schema the integration
  // carries for its own type.
  const schema = (readOnly ? integration?.config_schema : selectedIntegrationType?.config_schema) as ConfigSchema | undefined;
  const properties = schema?.properties ?? {};
  const required = schema?.required ?? [];

  const titleTypeName = integration?.integration_type_name ?? integrationTypeName ?? "Integration";

  // `selectedType` is empty until the modal opens, and an option cannot have an empty value.
  const typeOptions = readOnly
    ? (selectedType ? [{ type: selectedType, name: titleTypeName }] : [])
    : (integrationTypeName
      ? integrationTypes.filter(t => t.integration_type_name === integrationTypeName)
      : integrationTypes);

  const showTypeSelect = readOnly || typeOptions.length > 1;
  const oauthField = selectedIntegrationType?.supports_oauth ? selectedIntegrationType.oauth_field : "";
  const canConnect = !readOnly && !!selectedType && !!oauthField;

  useEffect(() => {
    if (!open || readOnly || isEditing) return;
    const options = integrationTypeName
      ? integrationTypes.filter(t => t.integration_type_name === integrationTypeName)
      : integrationTypes;
    if (selectedType && options.some(t => t.type === selectedType)) return;
    setSelectedType(options.length === 1 ? options[0].type : "");
  }, [open, integrationTypes, integrationTypeName, selectedType, readOnly, isEditing]);

  useEffect(() => {
    if (!open || integration || !selectedType) return;
    const chosen = integrationTypes.find(t => t.type === selectedType);
    const props = (chosen?.config_schema as ConfigSchema | undefined)?.properties ?? {};
    setConfig(Object.fromEntries(
      Object.entries(props)
        .filter(([, prop]) => prop.default !== undefined && prop.default !== "")
        .map(([key, prop]) => [key, String(prop.default)])
    ));
  }, [open, integration, selectedType, integrationTypes]);

  const handleFieldChange = (key: string, value: string) => {
    setConfig(prev => ({ ...prev, [key]: value }));
  };

  useEffect(() => {
    if (!connecting || !flowState) return;
    let settled = false;
    const channel = new BroadcastChannel(OAUTH_CHANNEL);

    const stop = () => {
      settled = true;
      window.clearInterval(watchClosed);
      window.clearTimeout(giveUp);
      setConnecting(false);
      popupRef.current?.close();
    };

    channel.onmessage = async (event: MessageEvent<{ state?: string }>) => {
      if (settled || event.data?.state !== flowState) return;
      settled = true;
      const result = await api.integrations().getOAuthResult(flowState);
      stop();
      if (result.error) {
        setError(result.error);
      } else if (result.config) {
        setConfig(prev => ({ ...prev, ...result.config }));
        setConnected(true);
      } else {
        setError("Authorization did not complete.");
      }
    };

    let closedTicks = 0;
    const watchClosed = window.setInterval(() => {
      if (settled || !popupRef.current?.closed) return;
      if (++closedTicks < 4) return;
      stop();
      setError("Authorization was cancelled before it finished.");
    }, 500);

    const giveUp = window.setTimeout(() => {
      if (settled) return;
      stop();
      setError("Authorization timed out. Try again.");
    }, flowExpiresInMs);

    return () => {
      settled = true;
      channel.close();
      window.clearInterval(watchClosed);
      window.clearTimeout(giveUp);
    };
  }, [connecting, flowState, flowExpiresInMs]);

  const handleConnect = async () => {
    setError(null);
    setConnected(false);
    setConnecting(true);
    const popup = window.open("", "_blank", "width=600,height=760");
    popupRef.current = popup;
    if (!popup) {
      setConnecting(false);
      setError("Allow pop-ups for this site to connect, or paste a token manually.");
      return;
    }
    try {
      const { authorizationUrl, state, expiresInMs } = await api.integrations().startOAuth(
        dataSetId,
        selectedType,
        config
      );
      popup.location.href = authorizationUrl;
      setFlowExpiresInMs(expiresInMs);
      setFlowState(state);
    } catch (e) {
      popup.close();
      setConnecting(false);
      setError(e instanceof Error ? e.message : "Failed to start authorization");
    }
  };

  const isValid = !!selectedType && required.every(key => !!config[key]);

  const handleSubmit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      if (integration) {
        await api.integrations().update(dataSetId, integration.id, config);
      } else {
        await api.integrations().create(dataSetId, selectedType, config);
      }
      onSuccess();
      onOpenChange(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : `Failed to ${integration ? "update" : "create"} integration`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <FormModal
      open={open}
      onOpenChange={onOpenChange}
      title={readOnly ? titleTypeName : `${isEditing ? "Edit" : "Add"} ${titleTypeName}`}
      onSubmit={handleSubmit}
      onCancel={() => onOpenChange(false)}
      submitLabel={isEditing ? "Save" : "Add"}
      submitting={submitting}
      disabled={!isValid}
      loading={loadingTypes}
      loadingText="Loading integration types..."
      readOnly={readOnly}
      dependencies={[selectedType, config, error]}
    >
      {error && (
        <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-md">
          <p className="text-sm text-destructive">{error}</p>
        </div>
      )}

      {showTypeSelect && (
        <div className="flex flex-col gap-1">
          <Label htmlFor="integration-type">Type</Label>
          <Select
            value={selectedType}
            onValueChange={setSelectedType}
            disabled={readOnly || isEditing || typeOptions.length === 0}
          >
            <SelectTrigger id="integration-type">
              <SelectValue placeholder="Select integration type" />
            </SelectTrigger>
            <SelectContent>
              {typeOptions.map(t => (
                <SelectItem key={t.type} value={t.type}>{t.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      {selectedType && Object.entries(properties).map(([key, prop]) => (
        <div key={key} className="flex flex-col gap-1">
          <Label htmlFor={`config-${key}`}>
            {prop.title ?? key}
            {required.includes(key) && <span className="text-destructive ml-1">*</span>}
          </Label>
          {prop.enum ? (
            <Select
              value={config[key] ?? ""}
              onValueChange={value => handleFieldChange(key, value)}
              disabled={readOnly}
            >
              <SelectTrigger id={`config-${key}`}>
                <SelectValue placeholder={`Select ${(prop.title ?? key).toLowerCase()}`} />
              </SelectTrigger>
              <SelectContent>
                {prop.enum.map(option => (
                  <SelectItem key={option} value={option}>{option}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : (
            <Input
              id={`config-${key}`}
              placeholder={prop.title ?? key}
              value={config[key] ?? ""}
              onChange={e => handleFieldChange(key, e.target.value)}
              readOnly={readOnly}
            />
          )}
          {prop.description && (
            <p className="text-xs text-muted-foreground">{prop.description}</p>
          )}
          {canConnect && key === oauthField && config[key] && (
            <div className="flex items-center gap-3 pt-1">
              <Button type="button" variant="outline" size="sm" onClick={handleConnect} disabled={connecting}>
                {connecting ? "Waiting for authorization…" : connected ? "Reconnect" : "Connect"}
              </Button>
              {connected ? (
                <p className="text-xs text-green-700">Connected — token filled in below.</p>
              ) : (
                <p className="text-xs text-muted-foreground">Sign in to fill the token in automatically.</p>
              )}
            </div>
          )}
        </div>
      ))}
    </FormModal>
  );
}
