import { BaseApiClient } from "@/lib/api/base.ts";
import { PermissionOption } from "@/lib/types.ts";

export class PermissionsApiClient extends BaseApiClient {
  async getPermissions(scope: "global" | "dataset"): Promise<PermissionOption[]> {
    const response = await fetch(`${this.apiBase}/api/permissions?scope=${scope}`, this._requestConfiguration());
    return (await response.json()) as PermissionOption[];
  }
}
