import { BaseApiClient } from "@/lib/api/base.ts";
import { PermissionEntity } from "@/lib/permissions/types.ts";
import { ApiError } from "@/lib/api-error.ts";

export class PermissionsApiClient extends BaseApiClient {
  async getPermissions(scope: "global" | "data_set"): Promise<PermissionEntity[]> {
    const response = await fetch(`${this.apiBase}/api/permissions?scope=${scope}`, this._requestConfiguration());
    if (!response.ok) {
      throw new ApiError(`Failed to list permissions: ${response.statusText}`, {
        data: await response.json().catch(() => ({})),
        status: response.status,
      });
    }
    return await response.json() as PermissionEntity[];
  }
}
