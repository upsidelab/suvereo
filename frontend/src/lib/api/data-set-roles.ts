import { BaseApiClient } from "@/lib/api/base.ts";
import { DataSetRoleDetail, DataSetRoleOption, PaginatedResult } from "@/lib/types.ts";
import { ApiError } from "@/lib/api-error.ts";

export class DataSetRolesApiClient extends BaseApiClient {
  async getDataSetRoles(): Promise<DataSetRoleOption[]> {
    const results: DataSetRoleOption[] = [];
    let url: string | null = `${this.apiBase}/api/data_set_roles`;

    while (url) {
      const response: Response = await fetch(url, this._requestConfiguration());
      if (!response.ok) {
        throw new ApiError(`Failed to list data set roles: ${response.statusText}`, {
          data: await response.json().catch(() => ({})),
          status: response.status,
        });
      }
      const page = await response.json() as PaginatedResult<DataSetRoleOption>;
      results.push(...page.results);
      url = page.next ?? null;
    }

    return results;
  }

  async getDataSetRoleDetail(roleId: number): Promise<DataSetRoleDetail> {
    const response = await fetch(`${this.apiBase}/api/data_set_roles/${roleId}`, this._requestConfiguration());
    if (!response.ok) {
      throw new ApiError(`Failed to load data set role: ${response.statusText}`, {
        data: await response.json().catch(() => ({})),
        status: response.status,
      });
    }
    return await response.json() as DataSetRoleDetail;
  }

  async createDataSetRole(name: string, permissions: string[] = []): Promise<Response> {
    return await fetch(`${this.apiBase}/api/data_set_roles`, {
      ...this._requestConfiguration(),
      method: "POST",
      body: JSON.stringify({ name, permissions })
    });
  }

  async updateDataSetRole(roleId: number, name: string, permissions: string[]): Promise<Response> {
    return await fetch(`${this.apiBase}/api/data_set_roles/${roleId}`, {
      ...this._requestConfiguration(),
      method: "PATCH",
      body: JSON.stringify({ name, permissions })
    });
  }

  async deleteDataSetRole(roleId: number): Promise<Response> {
    return await fetch(`${this.apiBase}/api/data_set_roles/${roleId}`, {
      ...this._requestConfiguration(),
      method: "DELETE"
    });
  }
}
