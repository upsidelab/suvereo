import { useState, useEffect, useCallback } from "react";
import { ApiClient } from "@/lib/api";
import { authenticationProviderInstance } from "@/lib/authentication-provider";
import { Agent, ToolConfigSchema } from "@/lib/types";
import {AgentChoice} from "@/lib/api/agents.ts";
import { ApiError } from "@/lib/api-error";
import { flattenConfigForForm, parseFieldErrors as parseFieldErrorsBase, toFormValue } from "@/lib/form-utils";
import { TOOLS_SECTION, toolFieldKey } from "../tool-config-keys";

const apiClient = new ApiClient(authenticationProviderInstance);

type ConfigSections = Record<string, Record<string, unknown>>;
type FormConfig = Record<string, string | number | boolean>;

function extractConfigSections(schema: Record<string, unknown>): ConfigSections {
  const configSections: ConfigSections = {};
  Object.entries(schema).forEach(([section, value]) => {
    if (section !== 'key' && section !== 'name' && value && typeof value === 'object' && !Array.isArray(value)) {
      configSections[section] = value as Record<string, unknown>;
    }
  });
  return configSections;
}

function toolFields(toolsSchema: Record<string, unknown>): Array<[string, string]> {
  return Object.entries(toolsSchema as Record<string, ToolConfigSchema>).flatMap(([toolName, tool]) =>
    Object.keys(tool?.fields ?? {}).map((field): [string, string] => [toolName, field])
  );
}

function flattenToolsConfig(tools: unknown): FormConfig {
  const flattened: FormConfig = {};
  if (!tools || typeof tools !== 'object' || Array.isArray(tools)) return flattened;
  Object.entries(tools as Record<string, Record<string, unknown>>).forEach(([toolName, settings]) => {
    Object.entries(settings ?? {}).forEach(([field, value]) => {
      const formValue = toFormValue(value);
      if (formValue !== undefined) flattened[toolFieldKey(toolName, field)] = formValue;
    });
  });
  return flattened;
}

function collapsedSections(configSections: ConfigSections): Record<string, boolean> {
  return Object.fromEntries(Object.keys(configSections).map((section) => [section, false]));
}

export function useAgentForm(
  agent: Agent | null,
  agentTypes: AgentChoice[],
  dataSetId: number | null,
  onSuccess: () => void,
  readOnly: boolean = false
) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [type, setType] = useState("");
  const [toolProvidingIntegrations, setToolProvidingIntegrations] = useState<number[]>([]);
  const [config, setConfig] = useState<FormConfig>({});
  const [agentConfigSections, setAgentConfigSections] = useState<ConfigSections>({});
  const [agentTypeName, setAgentTypeName] = useState("");
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({});
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [generalError, setGeneralError] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const loadAgentDetailsForEditing = async () => {
      if (!agent) return;
      
      try {
        const agentDetails = await apiClient.agents().getAgentById(agent.id);
        setName(agentDetails.name);
        setDescription(agentDetails.description || "");
        setType(agentDetails.agent_type);
        setAgentTypeName(agentDetails.agent_type_name);
        setToolProvidingIntegrations(agentDetails.tool_providing_integrations);

        const { tools, ...sections } = agentDetails.config ?? {};
        setConfig({ ...flattenConfigForForm(sections), ...flattenToolsConfig(tools) });

        if (readOnly) {
          // The type catalog needs the change permission, so read-only reads the schema the agent
          // carries for its own type.
          const sections = extractConfigSections(agentDetails.config_schema as Record<string, unknown>);
          setAgentConfigSections(sections);
          setOpenSections(collapsedSections(sections));
        }
      } catch (error) {
        console.error('Failed to load agent details:', error);
      }
    };

    loadAgentDetailsForEditing();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agent?.id]);

  useEffect(() => {
    const resetFormForNewAgent = () => {
      if (!agent) {
        setName("");
        setDescription("");
        setType("");
        setToolProvidingIntegrations([]);
        setConfig({});
        setAgentConfigSections({});
        setOpenSections({});
        setFieldErrors({});
        setGeneralError("");
      }
    };

    resetFormForNewAgent();
  }, [agent]);
  
  useEffect(() => {
    const clearFormWhenNoType = () => {
      if (!type) {
        setConfig({});
        setAgentConfigSections({});
        setOpenSections({});
        return true;
      }
      return false;
    };

    const createDefaultConfigValues = (configSections: ConfigSections) => {
      const defaults: FormConfig = {};
      Object.entries(configSections).forEach(([section, sectionData]) => {
        if (section === TOOLS_SECTION) {
          toolFields(sectionData).forEach(([toolName, field]) => { defaults[toolFieldKey(toolName, field)] = ""; });
        } else {
          Object.keys(sectionData).forEach(k => { defaults[`${section}_${k}`] = ""; });
        }
      });
      return defaults;
    };

    const updateFormForSelectedType = () => {
      if (readOnly) return;

      const wasCleared = clearFormWhenNoType();
      if (wasCleared) return;

      const selected = agentTypes.find((t) => t.key === type);
      if (!selected) return;

      const configSections = extractConfigSections(selected as unknown as Record<string, unknown>);
      setAgentConfigSections(configSections);

      setOpenSections(collapsedSections(configSections));
      
      if (!agent && Object.keys(config).length === 0) {
        const defaults = createDefaultConfigValues(configSections);
        setConfig(defaults);
      }

      if (!agent) {
        setName(selected.name);
      }
    };

    updateFormForSelectedType();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [type, agentTypes, agent]);

  const handleConfigChange = (key: string, value: string) => {
    setConfig(prev => ({ ...prev, [key]: value }));
  };

  const buildNestedConfigFromFlattened = () => {
    const configObj: Record<string, unknown> = {};
    Object.entries(agentConfigSections).forEach(([section, fields]) => {
      configObj[section] = section === TOOLS_SECTION
        ? buildToolsConfig(fields)
        : buildRegularSectionConfig(section, fields);
    });
    return configObj;
  };

  const buildToolsConfig = (toolsSchema: Record<string, unknown>) => {
    const out: Record<string, FormConfig> = {};
    Object.keys(toolsSchema).forEach(toolName => { out[toolName] = {}; });
    toolFields(toolsSchema).forEach(([toolName, field]) => {
      const v = config[toolFieldKey(toolName, field)];
      if (v !== '' && v !== null && v !== undefined) out[toolName][field] = v;
    });
    return out;
  };

  const buildRegularSectionConfig = (section: string, fields: Record<string, unknown>) => {
    const out: Record<string, string | number | boolean> = {};
    Object.keys(fields).forEach(k => {
      const v = config[`${section}_${k}`];
      if (v !== '' && v !== null && v !== undefined) out[k] = v;
    });
    return out;
  };

  const saveAgentToApi = async (configObj: Record<string, unknown>) => {
    if (!dataSetId) return;
    
    const agentData = {
      name,
      description,
      agent_type: type,
      dataset: dataSetId,
      config: configObj,
      tool_providing_integrations: toolProvidingIntegrations
    };

    if (agent) {
      await apiClient.agents().updateAgent(agent.id, agentData);
    } else {
      await apiClient.agents().createAgent(agentData);
    }
  };

  const parseFieldErrors = (errorData: unknown) => {
    const newFieldErrors = parseFieldErrorsBase(errorData);
    let toolMessages: string[] = [];
    
    // Add agent-specific error parsing for complex sections
    if (typeof errorData === 'object' && errorData && 'config' in errorData) {
      const configErrors = (errorData as { config: unknown }).config;
      if (typeof configErrors === 'object' && configErrors) {
        const sectionNames = ['agent_args', 'prompt_input'];
        
        sectionNames.forEach(sectionName => {
          parseSingleConfigSection(sectionName, (configErrors as Record<string, unknown>)[sectionName], newFieldErrors);
        });
        
        delete newFieldErrors[`configuration_${TOOLS_SECTION}`];
        toolMessages = parseToolErrors((configErrors as Record<string, unknown>)[TOOLS_SECTION], newFieldErrors);
      }
    }
    
    return { fieldErrors: newFieldErrors, toolMessages };
  };

  const parseSingleConfigSection = (sectionName: string, sectionErrors: unknown, newFieldErrors: Record<string, string>) => {
    if (sectionErrors && typeof sectionErrors === 'object') {
      Object.entries(sectionErrors as Record<string, unknown>).forEach(([field, error]) => {
        newFieldErrors[`${sectionName}_${field}`] = Array.isArray(error) ? String(error[0]) : String(error);
      });
    }
  };

  const parseToolErrors = (toolsErrors: unknown, newFieldErrors: Record<string, string>): string[] => {
    if (Array.isArray(toolsErrors)) return toolsErrors.map(String);
    if (!toolsErrors || typeof toolsErrors !== 'object') return [];
    const messages: string[] = [];
    Object.entries(toolsErrors as Record<string, unknown>).forEach(([toolName, toolErrors]) => {
      if (Array.isArray(toolErrors)) {
        messages.push(...toolErrors.map(error => `${toolName}: ${String(error)}`));
      } else if (toolErrors && typeof toolErrors === 'object') {
        Object.entries(toolErrors as Record<string, unknown>).forEach(([field, error]) => {
          newFieldErrors[toolFieldKey(toolName, field)] = Array.isArray(error) ? String(error[0]) : String(error);
        });
      }
    });
    return messages;
  };

  const handleSubmit = async () => {
    if (!dataSetId) return;
    
    setSubmitting(true);
    setFieldErrors({});
    setGeneralError("");
    
    try {
      const configObj = buildNestedConfigFromFlattened();
      await saveAgentToApi(configObj);
      onSuccess();
    } catch (e) {
      if (e instanceof ApiError && e.response?.data) {
        const errorData = e.response.data;
        const { fieldErrors: newFieldErrors, toolMessages } = parseFieldErrors(errorData);
        
        setFieldErrors(newFieldErrors);
        
        if (toolMessages.length > 0) {
          setGeneralError(toolMessages.join(" "));
        } else if (Object.keys(newFieldErrors).length === 0) {
          const errorDetail = typeof errorData === 'object' && errorData && 'detail' in errorData ? String(errorData.detail) : undefined;
          const errorMessage = typeof errorData === 'object' && errorData && 'message' in errorData ? String(errorData.message) : undefined;
          setGeneralError(errorDetail || errorMessage || 'Failed to save agent');
        }
      } else {
        setGeneralError(e instanceof Error ? e.message : 'Failed to save agent');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const resetForm = useCallback(() => {
    setName("");
    setDescription("");
    setType("");
    setToolProvidingIntegrations([]);
    setConfig({});
    setAgentConfigSections({});
    setOpenSections({});
    setFieldErrors({});
    setGeneralError("");
  }, []);


  return {
    name,
    setName,
    description,
    setDescription,
    type,
    setType,
    agentTypeName,
    toolProvidingIntegrations,
    setToolProvidingIntegrations,
    config,
    setConfig,
    agentConfigSections,
    openSections,
    setOpenSections,
    fieldErrors,
    generalError,
    submitting,
    handleSubmit,
    handleConfigChange,
    resetForm
  };
}
