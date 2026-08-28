import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form.tsx";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Input } from "@/components/ui/input.tsx";
import { Button } from "@/components/ui/button.tsx";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible.tsx";
import { useEffect, useState } from "react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select.tsx";
import { ChevronDownIcon, ChevronUpIcon } from "lucide-react";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { DataSet, EmbeddingModelsConfig, ProvidersConfig } from "@/lib/types.ts";
import { Alert, AlertDescription } from "@/components/ui/alert.tsx";
import { InfoIcon } from "lucide-react";
import { formSchema, DataSetFormSchema } from "./data-set-form-schema.ts";
import { ApiError } from "@/lib/api-error.ts";
import { Label } from "@/components/ui/label.tsx";

const api = new ApiClient(authenticationProviderInstance);

const FORM_FIELD_BY_RESPONSE_KEY: Record<string, keyof DataSetFormSchema> = {
  name: "name",
  language_model_provider: "languageModelProvider",
  language_model: "languageModel",
  embedding_provider: "embeddingProvider",
  embedding_model: "embeddingModel",
  embedding_vector_dimensions: "embeddingVectorSize",
};

const ADVANCED_FIELDS: (keyof DataSetFormSchema)[] = ["embeddingProvider", "embeddingModel", "embeddingVectorSize"];

function errorMessage(value: unknown): string {
  if (Array.isArray(value)) return value.map(String).join(" ");
  if (typeof value === "string") return value;
  return JSON.stringify(value);
}

function formatList(items: (string | number)[]): string {
  if (items.length <= 1) return String(items[0] ?? "");
  return `${items.slice(0, -1).join(", ")} or ${items[items.length - 1]}`;
}

interface DataSetFormProps {
  initialData?: DataSet;
  onSubmit: (values: DataSetFormSchema) => Promise<void>;
  submitButtonText: string;
  isOnboarding?: boolean;
  disabledFields?: string[];
  readOnly?: boolean;
}

function ReadOnlyMessage() {
  return (
    <Alert className="mb-4">
      <div className="flex items-start gap-2">
        <InfoIcon className="h-4 w-4 mt-0.5 flex-shrink-0" />
        <AlertDescription>
          You can view this data set's configuration, but not change it.
        </AlertDescription>
      </div>
    </Alert>
  );
}

// Helper component to show disabled field message
function DisabledFieldMessage() {
  return (
    <Alert className="mb-4">
      <div className="flex items-start gap-2">
        <InfoIcon className="h-4 w-4 mt-0.5 flex-shrink-0" />
        <AlertDescription>
          Some fields cannot be edited on existing data sets as they affect the underlying data structure.
        </AlertDescription>
      </div>
    </Alert>
  );
}

export function DataSetForm({ initialData, onSubmit, submitButtonText, isOnboarding = false, disabledFields = [], readOnly = false }: DataSetFormProps) {
  const [providersConfig, setProvidersConfig] = useState<ProvidersConfig | undefined>(undefined);
  const [languageModelNames, setLanguageModelNames] = useState<string[] | undefined>(undefined);
  const [embeddingModelsConfig, setEmbeddingModelsConfig] = useState<EmbeddingModelsConfig | undefined>(undefined);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const form = useForm<DataSetFormSchema>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: initialData?.name || (isOnboarding ? "Default" : ""),
      languageModelProvider: initialData?.languageModelProvider || undefined,
      languageModel: initialData?.languageModel || undefined,
      embeddingProvider: initialData?.embeddingProvider || undefined,
      embeddingModel: initialData?.embeddingModel || undefined,
      embeddingVectorSize: initialData?.embeddingVectorSize || 512,
      preconfigureAgents: isOnboarding,
    }
  });

  useEffect(() => {
    const loadProvidersConfig = async () => {
      try {
        const result = await api.config().getAvailableProviders();
        setProvidersConfig(result);

        // Set default values if not already set
        if (!form.getValues('languageModelProvider') && result.languageModelProviders.length > 0) {
          form.setValue("languageModelProvider", result.languageModelProviders[0]);
        }
        if (!form.getValues('embeddingProvider') && result.embeddingProviders.length > 0) {
          form.setValue("embeddingProvider", result.embeddingProviders[0]);
        }
      } catch (error) {
        console.error("Failed to load the available providers:", error);
        setLoadError("Failed to load the available providers.");
      }
    }

    if (!readOnly) {
      loadProvidersConfig();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const languageModelProvider = form.watch('languageModelProvider');

  useEffect(() => {
    const loadLanguageModels = async () => {
      if (languageModelProvider) {
        setLanguageModelNames(undefined);
        try {
          const result = await api.config().getLanguageModelsForProvider(languageModelProvider);
          setLanguageModelNames(result);

          // Set default value if not already set
          if (!form.getValues('languageModel') && result.length > 0) {
            form.setValue("languageModel", result[0]);
          }
        } catch (error) {
          console.error("Failed to load the language models:", error);
          setLoadError("Failed to load the language models for this provider.");
        }
      }
    }
    if (!readOnly) {
      loadLanguageModels();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [languageModelProvider]);

  const embeddingProvider = form.watch('embeddingProvider');

  useEffect(() => {
    const loadEmbeddingModels = async () => {
      if (embeddingProvider) {
        setEmbeddingModelsConfig(undefined);
        try {
          const result = await api.config().getEmbeddingModelsForProvider(embeddingProvider);
          setEmbeddingModelsConfig(result);

          // Set default value if not already set
          if (!form.getValues('embeddingModel') && result.models.length > 0) {
            form.setValue("embeddingModel", result.models[0]);
          }
        } catch (error) {
          console.error("Failed to load the embedding models:", error);
          setLoadError("Failed to load the embedding models for this provider.");
        }
      }
    }
    if (!readOnly) {
      loadEmbeddingModels();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [embeddingProvider]);

  const embeddingModel = form.watch('embeddingModel');

  useEffect(() => {
    if (!embeddingModelsConfig || !embeddingModel) return;
    const allowedSizes = embeddingModelsConfig.vectorSizeConstraints[embeddingModel];
    if (allowedSizes && allowedSizes.length > 0) {
      form.setValue("embeddingVectorSize", allowedSizes[0]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [embeddingModel, embeddingModelsConfig]);

  const [advancedOpen, setAdvancedOpen] = useState<boolean>(false);

  // The provider and model catalogs need the change permission, so read-only offers the one value
  // the data set already holds.
  const optionsFor = (current: string | undefined, available: string[] | undefined) =>
    (readOnly ? [current].filter((value): value is string => !!value) : available);
  const languageModelProviderOptions = optionsFor(initialData?.languageModelProvider, providersConfig?.languageModelProviders);
  const languageModelOptions = optionsFor(initialData?.languageModel, languageModelNames);
  const embeddingProviderOptions = optionsFor(initialData?.embeddingProvider, providersConfig?.embeddingProviders);
  const embeddingModelOptions = optionsFor(initialData?.embeddingModel, embeddingModelsConfig?.models);

  const handleSubmit = async (values: DataSetFormSchema) => {
    setSubmitError(null);
    try {
      await onSubmit(values);
    } catch (error) {
      showSaveError(error);
    }
  };

  const showSaveError = (error: unknown) => {
    const body = error instanceof ApiError ? error.response.data : null;
    if (!body || typeof body !== "object") {
      setSubmitError("Could not save this data set.");
      return;
    }

    const unattributed: string[] = [];
    for (const [key, value] of Object.entries(body as Record<string, unknown>)) {
      const field = FORM_FIELD_BY_RESPONSE_KEY[key];
      if (!field) {
        unattributed.push(errorMessage(value));
        continue;
      }
      form.setError(field, { message: errorMessage(value) });
      if (ADVANCED_FIELDS.includes(field)) {
        setAdvancedOpen(true);
      }
    }

    const attributed = Object.keys(body).some((key) => FORM_FIELD_BY_RESPONSE_KEY[key]);
    if (unattributed.length > 0 || !attributed) {
      setSubmitError(unattributed.join(" ") || "Could not save this data set.");
    }
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(handleSubmit)}>
        {loadError && (
          <Alert className="mb-4">
            <AlertDescription>{loadError}</AlertDescription>
          </Alert>
        )}
        {submitError && (
          <Alert variant="destructive" className="mb-4">
            <AlertDescription>{submitError}</AlertDescription>
          </Alert>
        )}
        {readOnly ? <ReadOnlyMessage /> : disabledFields.length > 0 && <DisabledFieldMessage />}
        <div className="space-y-6">
          {!isOnboarding &&
            <FormField
              control={form.control}
              name="name"
              render={({field}) => (
                <FormItem>
                  <FormLabel>Name</FormLabel>
                  <FormControl>
                    <Input placeholder="Name of the data set" readOnly={readOnly} {...field}/>
                  </FormControl>
                  <FormDescription>
                    This is the name of the data set visible to your users
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
          }

          <div>
            <Label>Language Model</Label>
            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="languageModelProvider"
                render={({field}) => (
                  <FormItem>
                    <FormLabel className="hidden">Language Model Provider</FormLabel>
                    <Select value={field.value} onValueChange={field.onChange} defaultValue={field.value}>
                      <SelectTrigger disabled={readOnly || !providersConfig}>
                        <SelectValue placeholder="Loading..."/>
                      </SelectTrigger>
                      <SelectContent>
                        {
                          languageModelProviderOptions &&
                          <>
                            {languageModelProviderOptions.map((provider) => (
                              <SelectItem key={provider} value={provider}>{provider}</SelectItem>
                            ))}
                          </>
                        }
                      </SelectContent>
                    </Select>
                    <FormDescription>The language model to be used by the agent</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="languageModel"
                render={({field}) => (
                  <FormItem>
                    <FormLabel className="hidden">Language Model</FormLabel>
                    <Select value={field.value} onValueChange={field.onChange} defaultValue={field.value}>
                      <SelectTrigger disabled={readOnly || !languageModelNames}>
                          <SelectValue placeholder="Loading..."/>
                      </SelectTrigger>
                      <SelectContent>
                        {
                          languageModelOptions &&
                          <>
                            {languageModelOptions.map((modelName) => (
                              <SelectItem key={modelName} value={modelName}>{modelName}</SelectItem>
                            ))}
                          </>
                        }
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
          </div>
        </div>

        <Collapsible className="py-4" open={advancedOpen} onOpenChange={setAdvancedOpen}>
          <CollapsibleTrigger asChild>
            <Button variant="link" className="pl-0">
              {advancedOpen ? <ChevronUpIcon/> : <ChevronDownIcon/>}
              Advanced settings
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <div className="space-y-6">
              <FormField
                control={form.control}
                name="embeddingProvider"
                render={({field}) => (
                  <FormItem>
                    <FormLabel>Embedding Provider</FormLabel>
                    <Select value={field.value} onValueChange={field.onChange} defaultValue={field.value}>
                      <SelectTrigger disabled={readOnly || !providersConfig || disabledFields.includes('embeddingProvider')}>
                        <FormControl>
                          <SelectValue placeholder="Select a provider for embeddings"/>
                        </FormControl>
                      </SelectTrigger>
                      <SelectContent>
                        {
                          embeddingProviderOptions &&
                          <>
                          {embeddingProviderOptions.map((provider) => (
                            <SelectItem key={provider} value={provider}>{provider}</SelectItem>
                          ))}
                          </>
                        }
                      </SelectContent>
                    </Select>
                    <FormDescription>The plugin used to create embeddings</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="embeddingModel"
                render={({field}) => (
                  <FormItem>
                    <FormLabel>Embedding Model</FormLabel>
                    <Select value={field.value} onValueChange={field.onChange} defaultValue={field.value}>
                      <SelectTrigger disabled={readOnly || !embeddingModelsConfig || disabledFields.includes('embeddingModel')}>
                        <FormControl>
                          <SelectValue placeholder="Select a model for embeddings"/>
                        </FormControl>
                      </SelectTrigger>
                      <SelectContent>
                        {
                          embeddingModelOptions &&
                          <>
                            {embeddingModelOptions.map((modelName) => (
                              <SelectItem key={modelName} value={modelName}>{modelName}</SelectItem>
                            ))}
                          </>
                        }
                      </SelectContent>
                    </Select>
                    <FormDescription>The model provided by the plugin</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              {(() => {
                const allowedSizes = embeddingModelsConfig?.vectorSizeConstraints[embeddingModel ?? ""];
                const isConstrained = allowedSizes && allowedSizes.length > 0;
                const isDisabled = readOnly || disabledFields.includes('embeddingVectorSize');
                return (
                  <FormField
                    control={form.control}
                    name="embeddingVectorSize"
                    disabled={isDisabled || isConstrained}
                    render={({field}) => (
                      <FormItem>
                        <FormLabel>Vector Size</FormLabel>
                        <FormControl>
                          {isConstrained && !isDisabled ? (
                            <Select
                              value={String(field.value)}
                              onValueChange={(v) => field.onChange(Number(v))}
                            >
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                {allowedSizes.map((size) => (
                                  <SelectItem key={size} value={String(size)}>{size}</SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          ) : (
                            <Input readOnly={readOnly} {...field} />
                          )}
                        </FormControl>
                        <FormDescription>
                          {isConstrained
                            ? `This model only supports a fixed vector size of ${formatList(allowedSizes)}.`
                            : "The size of the embedding vector to use"}
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                );
              })()}
            </div>
          </CollapsibleContent>
        </Collapsible>
        {!readOnly && <Button type="submit">{submitButtonText}</Button>}
      </form>
    </Form>
  )
} 
