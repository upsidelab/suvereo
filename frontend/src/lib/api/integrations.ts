import { BaseApiClient } from "@/lib/api/base.ts";
import { Integration, IntegrationType } from "@/lib/types.ts";
import { ApiError } from "@/lib/api-error.ts";

export class IntegrationsApiClient extends BaseApiClient {
  async listTypes(): Promise<IntegrationType[]> {
    const response = await this.authenticatedFetch(`${this.apiBase}/api/integration-types/`);
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(`Failed to list integration types: ${response.statusText}`, {
        data: errorData,
        status: response.status,
      });
    }
    return await response.json() as IntegrationType[];
  }

  async startOAuth(
    dataSetId: number,
    type: string,
    config: Record<string, unknown>
  ): Promise<{ authorizationUrl?: string; state?: string; expiresInMs: number; authorizationRequired: boolean; detail?: string }> {
    const response = await fetch(`${this.apiBase}/api/data_sets/${dataSetId}/integrations/oauth/start/`, {
      ...this._requestConfiguration(),
      method: "POST",
      body: JSON.stringify({ type, config }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new ApiError(data.detail ?? `Failed to start authorization: ${response.statusText}`, {
        data,
        status: response.status,
      });
    }
    const body = data as {
      authorization_url?: string;
      state?: string;
      expires_in?: number;
      authorization_required?: boolean;
      detail?: string;
    };
    return {
      authorizationUrl: body.authorization_url,
      state: body.state,
      expiresInMs: (body.expires_in ?? 0) * 1000,
      authorizationRequired: body.authorization_required !== false,
      detail: body.detail,
    };
  }

  async refreshOAuth(
    dataSetId: number,
    type: string,
    config: Record<string, unknown>,
    integrationId?: number
  ): Promise<Record<string, string>> {
    const response = await fetch(`${this.apiBase}/api/data_sets/${dataSetId}/integrations/oauth/refresh/`, {
      ...this._requestConfiguration(),
      method: "POST",
      body: JSON.stringify({ type, config, integration_id: integrationId }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new ApiError(data.detail ?? `Failed to renew the token: ${response.statusText}`, {
        data,
        status: response.status,
      });
    }
    return (data as { config: Record<string, string> }).config;
  }

  async getOAuthResult(state: string): Promise<{ status: string; config?: Record<string, string>; error?: string }> {
    const response = await fetch(
      `${this.apiBase}/api/integrations/oauth/result/?state=${encodeURIComponent(state)}`,
      this._requestConfiguration()
    );
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      return { status: "failed", error: data.detail ?? `Could not read the result: ${response.statusText}` };
    }
    return await response.json();
  }

  async list(dataSetId: number): Promise<Integration[]> {
    const response = await this.authenticatedFetch(`${this.apiBase}/api/data_sets/${dataSetId}/integrations/`);
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(`Failed to list integrations: ${response.statusText}`, {
        data: errorData,
        status: response.status,
      });
    }
    return await response.json() as Integration[];
  }

  async create(dataSetId: number, type: string, config: Record<string, unknown>): Promise<Integration> {
    const response = await this.authenticatedFetch(`${this.apiBase}/api/data_sets/${dataSetId}/integrations/`, {
      method: "POST",
      body: JSON.stringify({ type, config }),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(`Failed to create integration: ${response.statusText}`, {
        data: errorData,
        status: response.status,
      });
    }
    return await response.json() as Integration;
  }

  async sync(dataSetId: number, id: number): Promise<{ task_id: string }> {
    const response = await this.authenticatedFetch(`${this.apiBase}/api/data_sets/${dataSetId}/integrations/${id}/sync/`, {
      method: "POST",
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(`Failed to sync integration: ${response.statusText}`, {
        data: errorData,
        status: response.status,
      });
    }
    return await response.json() as { task_id: string };
  }

  async update(dataSetId: number, id: number, config: Record<string, unknown>): Promise<Integration> {
    const response = await this.authenticatedFetch(`${this.apiBase}/api/data_sets/${dataSetId}/integrations/${id}/`, {
      method: "PATCH",
      body: JSON.stringify({ config }),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(`Failed to update integration: ${response.statusText}`, {
        data: errorData,
        status: response.status,
      });
    }
    return await response.json() as Integration;
  }

  async delete(dataSetId: number, id: number): Promise<void> {
    const response = await this.authenticatedFetch(`${this.apiBase}/api/data_sets/${dataSetId}/integrations/${id}/`, {
      method: "DELETE",
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(`Failed to delete integration: ${response.statusText}`, {
        data: errorData,
        status: response.status,
      });
    }
  }
}
