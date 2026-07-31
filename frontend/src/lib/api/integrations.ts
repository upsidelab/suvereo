import { BaseApiClient } from "@/lib/api/base.ts";
import { Integration, IntegrationType } from "@/lib/types.ts";
import { ApiError } from "@/lib/api-error.ts";

export class IntegrationsApiClient extends BaseApiClient {
  async listTypes(): Promise<IntegrationType[]> {
    const response = await fetch(`${this.apiBase}/api/integration-types/`, this._requestConfiguration());
    return await response.json() as IntegrationType[];
  }

  async list(dataSetId: number): Promise<Integration[]> {
    const response = await fetch(
      `${this.apiBase}/api/data_sets/${dataSetId}/integrations/`,
      this._requestConfiguration()
    );
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
    const response = await fetch(`${this.apiBase}/api/data_sets/${dataSetId}/integrations/`, {
      ...this._requestConfiguration(),
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
    const response = await fetch(`${this.apiBase}/api/data_sets/${dataSetId}/integrations/${id}/sync/`, {
      ...this._requestConfiguration(),
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
    const response = await fetch(`${this.apiBase}/api/data_sets/${dataSetId}/integrations/${id}/`, {
      ...this._requestConfiguration(),
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
    const response = await fetch(`${this.apiBase}/api/data_sets/${dataSetId}/integrations/${id}/`, {
      ...this._requestConfiguration(),
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
