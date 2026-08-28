import { BaseApiClient } from "@/lib/api/base.ts";
import { DatasetRoleDetail, DatasetRoleOption, PaginatedResult } from "@/lib/types.ts";
import { ApiError } from "@/lib/api-error.ts";

export class DatasetRolesApiClient extends BaseApiClient {
  async getDatasetRoles(): Promise<DatasetRoleOption[]> {
    const results: DatasetRoleOption[] = [];
    let url: string | null = `${this.apiBase}/api/dataset_roles`;

    while (url) {
      const response: Response = await fetch(url, this._requestConfiguration());
      if (!response.ok) {
        throw new ApiError(`Failed to list dataset roles: ${response.statusText}`, {
          data: await response.json().catch(() => ({})),
          status: response.status,
        });
      }
      const page = await response.json() as PaginatedResult<DatasetRoleOption>;
      results.push(...page.results);
      url = page.next ?? null;
    }

    return results;
  }

  async getDatasetRoleDetail(roleId: number): Promise<DatasetRoleDetail> {
    const response = await fetch(`${this.apiBase}/api/dataset_roles/${roleId}`, this._requestConfiguration());
    if (!response.ok) {
      throw new ApiError(`Failed to load dataset role: ${response.statusText}`, {
        data: await response.json().catch(() => ({})),
        status: response.status,
      });
    }
    return await response.json() as DatasetRoleDetail;
  }

  async createDatasetRole(name: string, permissions: string[] = []): Promise<Response> {
    return await fetch(`${this.apiBase}/api/dataset_roles`, {
      ...this._requestConfiguration(),
      method: "POST",
      body: JSON.stringify({ name, permissions })
    });
  }

  async updateDatasetRole(roleId: number, name: string, permissions: string[]): Promise<Response> {
    return await fetch(`${this.apiBase}/api/dataset_roles/${roleId}`, {
      ...this._requestConfiguration(),
      method: "PATCH",
      body: JSON.stringify({ name, permissions })
    });
  }

  async deleteDatasetRole(roleId: number): Promise<Response> {
    return await fetch(`${this.apiBase}/api/dataset_roles/${roleId}`, {
      ...this._requestConfiguration(),
      method: "DELETE"
    });
  }
}
