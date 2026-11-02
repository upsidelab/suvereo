import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { ChevronDownIcon, ChevronRightIcon } from "lucide-react";
import { useEffect } from "react";
import { DynamicConfigInput } from "./dynamic-config-input";
import { ToolConfigSchema, TypeInfo } from "@/lib/types";
import { TOOLS_SECTION, isToolFieldKey, toolFieldKey } from "./tool-config-keys";

interface AgentConfigurationFormProps {
  agentConfigSections: Record<string, Record<string, unknown>>;
  openSections: Record<string, boolean>;
  setOpenSections: (sections: Record<string, boolean>) => void;
  config: Record<string, string | number | boolean>;
  setConfig: (config: Record<string, string | number | boolean>) => void;
  fieldErrors: Record<string, string>;
  readOnly?: boolean;
}

export function AgentConfigurationForm({
  agentConfigSections,
  openSections,
  setOpenSections,
  config,
  setConfig,
  fieldErrors,
  readOnly = false
}: AgentConfigurationFormProps) {
  const handleConfigChange = (key: string, value: string | number | boolean) => {
    setConfig({ ...config, [key]: value });
  };

  useEffect(() => {
    const checkForSectionErrors = (section: string, fields: Record<string, unknown>) => {
      if (section === TOOLS_SECTION) {
        return Object.keys(fieldErrors).some(isToolFieldKey);
      }
      return Object.keys(fields).some(key => fieldErrors[`${section}_${key}`]);
    };

    const expandSectionsWithErrors = () => {
      if (Object.keys(fieldErrors).length === 0) return;

      const sectionsToExpand: Record<string, boolean> = { ...openSections };
      let hasChanges = false;

      Object.entries(agentConfigSections).forEach(([section, fields]) => {
        const sectionHasErrors = checkForSectionErrors(section, fields);
        
        if (sectionHasErrors && !openSections[section]) {
          sectionsToExpand[section] = true;
          hasChanges = true;
        }
      });

      if (hasChanges) {
        setOpenSections(sectionsToExpand);
      }
    };

    expandSectionsWithErrors();
  }, [fieldErrors, agentConfigSections, openSections, setOpenSections]);

  const sectionHasFields = (section: string, fields: Record<string, unknown>) => {
    if (section === TOOLS_SECTION) {
      return Object.values(fields as Record<string, ToolConfigSchema>).some(
        tool => Object.keys(tool?.fields ?? {}).length > 0
      );
    }
    return Object.keys(fields).length > 0;
  };

  const hasConfigFields = Object.entries(agentConfigSections).some(([section, fields]) =>
    sectionHasFields(section, fields)
  );

  const renderConfigField = (key: string, schema: unknown, configKey: string) => {
    const s = schema as Record<string, unknown>;
    const fieldTitle = (s && typeof s.title === 'string') ? s.title || key : String(key);
    const typeInfo = s?.type as TypeInfo | undefined;
    const description = typeof s?.description === 'string' ? s.description : undefined;
    const currentValue = config[configKey] ?? '';

    return (
      <DynamicConfigInput
        key={key}
        id={`agent-arg-${configKey}`}
        label={fieldTitle}
        placeholder={fieldTitle}
        value={currentValue}
        onChange={(value) => handleConfigChange(configKey, value)}
        typeInfo={typeInfo}
        description={description}
        error={fieldErrors[configKey]}
        required={!!s?.required}
        readOnly={readOnly}
      />
    );
  };

  const renderToolFields = (tools: Record<string, ToolConfigSchema>) => {
    return Object.entries(tools).map(([toolName, tool]) => {
      const fields = tool?.fields ?? {};
      if (Object.keys(fields).length === 0) return null;

      return (
        <div key={toolName} className="pl-4 border-l-2 border-muted bg-muted/20 rounded-r-md p-3">
          <div className="mb-3">
            <p className="text-sm font-medium text-foreground">{tool.title || toolName}</p>
            {tool.used_by?.length > 0 && (
              <p className="text-xs text-muted-foreground">Used by: {tool.used_by.join(", ")}</p>
            )}
          </div>
          <div className="space-y-3">
            {Object.entries(fields).map(([key, schema]) =>
              renderConfigField(key, schema, toolFieldKey(toolName, key))
            )}
          </div>
        </div>
      );
    });
  };

  const renderRegularFields = (section: string, fields: Record<string, unknown>) => {
    return Object.entries(fields).map(([key, schema]) => {
      const configKey = `${section}_${key}`;
      return typeof key === 'string' ? renderConfigField(key, schema, configKey) : null;
    });
  };

  const renderConfigSection = (section: string, fields: Record<string, unknown>) => {
    if (!sectionHasFields(section, fields)) return null;

    const sectionTitle = String(section).replace(/_/g, ' ');

    return (
      <Collapsible 
        key={section} 
        open={openSections[section]} 
        onOpenChange={(open) => setOpenSections({ ...openSections, [section]: open })}
      >
        <CollapsibleTrigger asChild>
          <Button variant="ghost" className="w-full justify-between p-0 h-auto">
            <div className="flex items-center gap-2">
              {openSections[section] ? <ChevronDownIcon className="h-4 w-4" /> : <ChevronRightIcon className="h-4 w-4" />}
              <span className="text-sm font-medium text-foreground capitalize">
                {sectionTitle}
              </span>
            </div>
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent className="space-y-4 mt-2">
          <div className="pl-4 space-y-4">
            {section === TOOLS_SECTION
              ? renderToolFields(fields as Record<string, ToolConfigSchema>)
              : renderRegularFields(section, fields)}
          </div>
        </CollapsibleContent>
      </Collapsible>
    );
  };

  if (!hasConfigFields) {
    return (
      <div className="p-4 bg-muted/20 rounded-md border border-dashed border-muted-foreground/20">
        <div className="text-center">
          <p className="text-sm text-muted-foreground mb-2">No configuration required</p>
          <p className="text-xs text-muted-foreground">This agent type doesn't require any additional configuration parameters.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium text-foreground">Configuration</h4>
        <p className="text-xs text-muted-foreground">
          {readOnly ? "Read-only" : "Configure agent parameters"}
        </p>
      </div>
      
      {Object.entries(agentConfigSections).map(([section, fields]) => 
        renderConfigSection(section, fields)
      )}
    </div>
  );
}
