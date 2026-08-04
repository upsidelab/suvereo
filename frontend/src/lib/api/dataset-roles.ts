import { BaseApiClient } from "@/lib/api/base.ts";
import { DatasetRoleDetail, DatasetRoleOption } from "@/lib/types.ts";

type DatasetRoleResponse = {
  id: number;
  name: string;
  is_system: boolean;
};

export class DatasetRolesApiClient extends BaseApiClient {
  async getDatasetRoles(): Promise<DatasetRoleOption[]> {
    const response = await fetch(`${this.apiBase}/api/dataset-roles`, this._requestConfiguration());
    const result = await response.json() as DatasetRoleResponse[];
    return result.map((item) => ({ id: item.id, name: item.name, isSystem: item.is_system }));
  }

  async getDatasetRoleDetail(roleId: number): Promise<DatasetRoleDetail> {
    const response = await fetch(`${this.apiBase}/api/dataset-roles/${roleId}`, this._requestConfiguration());
    const result = await response.json() as { id: number; name: string; permission_ids: number[]; is_system: boolean };
    return { id: result.id, name: result.name, permissionIds: result.permission_ids, isSystem: result.is_system };
  }

  async createDatasetRole(name: string, permissionIds: number[]): Promise<Response> {
    return await fetch(`${this.apiBase}/api/dataset-roles`, {
      ...this._requestConfiguration(),
      method: "POST",
      body: JSON.stringify({ name, permission_ids: permissionIds })
    });
  }

  async updateDatasetRole(roleId: number, name: string, permissionIds: number[]): Promise<Response> {
    return await fetch(`${this.apiBase}/api/dataset-roles/${roleId}`, {
      ...this._requestConfiguration(),
      method: "PATCH",
      body: JSON.stringify({ name, permission_ids: permissionIds })
    });
  }

  async deleteDatasetRole(roleId: number): Promise<Response> {
    return await fetch(`${this.apiBase}/api/dataset-roles/${roleId}`, {
      ...this._requestConfiguration(),
      method: "DELETE"
    });
  }

  async getDatasetRoleUsageCount(roleId: number): Promise<number> {
    const response = await fetch(`${this.apiBase}/api/dataset-roles/${roleId}/usage`, this._requestConfiguration());
    const result = await response.json() as { count: number };
    return result.count;
  }
}
