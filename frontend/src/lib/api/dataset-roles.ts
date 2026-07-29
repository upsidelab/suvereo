import { BaseApiClient } from "@/lib/api/base.ts";
import { DatasetRoleOption } from "@/lib/types.ts";

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
}
