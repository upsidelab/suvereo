import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Agent } from "@/lib/types";
import { useAgentForm } from "./hooks/use-agent-form";
import { AgentConfigurationForm } from "./agent-configuration-form";
import {AgentChoice} from "@/lib/api/agents.ts";
import {Textarea} from "@/components/ui/textarea.tsx";
import { FormModal } from "@/components/ui/form-modal";
import { useEffect } from "react";

interface AgentFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  agent: Agent | null;
  agentTypes: AgentChoice[];
  loadingTypes: boolean;
  dataSetId: number | null;
  onSuccess: () => void;
  readOnly?: boolean;
}

export function AgentFormModal({
  open,
  onOpenChange,
  agent,
  agentTypes,
  loadingTypes,
  dataSetId,
  onSuccess,
  readOnly = false
}: AgentFormModalProps) {
  const {
    name,
    setName,
    description,
    setDescription,
    type,
    setType,
    agentTypeName,
    config,
    setConfig,
    agentConfigSections,
    openSections,
    setOpenSections,
    fieldErrors,
    generalError,
    submitting,
    handleSubmit,
    resetForm
  } = useAgentForm(agent, agentTypes, dataSetId, onSuccess, readOnly);

  // Reset form when modal closes
  useEffect(() => {
    if (!open) {
      resetForm();
    }
  }, [open, resetForm]);

  const onSubmit = async () => {
    await handleSubmit();
  };

  const isEditing = !!agent;
  const title = readOnly ? `Agent ${agent?.name ?? ""}`.trim() : (isEditing ? `Edit Agent` : `New Agent`);

  // Read-only, the type catalog needs the change permission, so the Select carries this agent's
  // type alone - and nothing until its details arrive, since an option cannot have an empty value.
  const typeOptions = readOnly
    ? (type ? [{ key: type, name: agentTypeName || type }] : [])
    : agentTypes.map(agentChoice => ({ key: agentChoice.key, name: agentChoice.name }));

  return (
    <FormModal
      open={open}
      onOpenChange={onOpenChange}
      title={title}
      onSubmit={onSubmit}
      onCancel={() => onOpenChange(false)}
      submitLabel={isEditing ? "Save" : "Create"}
      submitting={submitting}
      disabled={!name || !type}
      loading={readOnly ? false : loadingTypes}
      loadingText="Loading agent types..."
      readOnly={readOnly}
      dependencies={[type, agentConfigSections, openSections, generalError, fieldErrors]}
    >
      {generalError && (
        <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-md">
          <p className="text-sm text-destructive">{generalError}</p>
        </div>
      )}

      <div className="flex flex-col gap-1">
        <Label htmlFor="agent-type">Type</Label>
        <Select value={type} onValueChange={setType} disabled={readOnly || agentTypes.length == 0 || !!agent}>
          <SelectTrigger id="agent-type" className={fieldErrors.type ? "border-destructive" : ""}>
            <SelectValue placeholder="Select type"/>
          </SelectTrigger>
          <SelectContent>
            {typeOptions.map(t => (
              <SelectItem key={t.key} value={t.key}>{t.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        {!readOnly && agentTypes.length == 0 &&
          <p className="text-[0.8rem] text-muted-foreground">First, you'll need to install an agent.<br /> To get started quickly, you can choose on of our <a href="https://upsidelab.io/tools/enthusiast/agents" className="underline">pre-built ones</a> to get started quick.</p>
        }
        {fieldErrors.type && (
          <p className="text-xs text-destructive">{fieldErrors.type}</p>
        )}
      </div>

      <div className="flex flex-col gap-1">
        <Label htmlFor="agent-name">Name</Label>
        <Input
          id="agent-name"
          placeholder="Name"
          value={name}
          onChange={e => setName(e.target.value)}
          readOnly={readOnly}
          className={fieldErrors.name ? "border-destructive" : ""}
        />
        {fieldErrors.name && (
          <p className="text-xs text-destructive">{fieldErrors.name}</p>
        )}
      </div>

      <div className="flex flex-col gap-1">
        <Label htmlFor="agent-description">Description</Label>
        <Textarea
          id="agent-description"
          placeholder="Description"
          value={description}
          onChange={e => setDescription(e.target.value)}
          readOnly={readOnly}
        />
        {fieldErrors.description && (
          <p className="text-xs text-destructive">{fieldErrors.description}</p>
        )}
      </div>

      {type && (
        <AgentConfigurationForm
          agentConfigSections={agentConfigSections}
          openSections={openSections}
          setOpenSections={setOpenSections}
          config={config}
          setConfig={setConfig}
          fieldErrors={fieldErrors}
          readOnly={readOnly}
        />
      )}
    </FormModal>
  );
}
