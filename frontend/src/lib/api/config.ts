import { BaseApiClient } from "@/lib/api/base.ts";
import { EmbeddingModelsConfig, ProvidersConfig } from "@/lib/types.ts";

type ProvidersConfigResponse = {
  language_model_providers: string[];
  embedding_providers: string[];
};

type EmbeddingModelsConfigResponse = {
  models: string[];
  vector_size_constraints: Record<string, number[]>;
};

export class ConfigApiClient extends BaseApiClient {
  async getAvailableProviders(): Promise<ProvidersConfig> {
    const response = await this.authenticatedFetch(`${this.apiBase}/api/config`);
    const result = await response.json() as ProvidersConfigResponse;

    return {
      embeddingProviders: result.embedding_providers,
      languageModelProviders: result.language_model_providers
    };
  }

  async getLanguageModelsForProvider(name: string): Promise<string[]> {
    const response = await this.authenticatedFetch(`${this.apiBase}/api/config/language_model_providers/${name}`);
    return await response.json() as string[];
  }

  async getEmbeddingModelsForProvider(name: string): Promise<EmbeddingModelsConfig> {
    const response = await this.authenticatedFetch(`${this.apiBase}/api/config/embedding_providers/${name}`);
    const result = await response.json() as EmbeddingModelsConfigResponse;

    return {
      models: result.models,
      vectorSizeConstraints: result.vector_size_constraints,
    };
  }
}
