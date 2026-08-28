import { BaseApiClient } from "@/lib/api/base.ts";
import { GlobalRoleDetail, GlobalRoleMember, GlobalRoleOption, PaginatedResult } from "@/lib/types.ts";
import { ApiError } from "@/lib/api-error.ts";

type GlobalRoleMemberResponse = {
  id: number;
  email: string;
  is_service_account: boolean;
};

export class GlobalRolesApiClient extends BaseApiClient {
  async getGlobalRoles(): Promise<GlobalRoleOption[]> {
    const results: GlobalRoleOption[] = [];
    let url: string | null = `${this.apiBase}/api/global_roles`;

    while (url) {
      const response: Response = await fetch(url, this._requestConfiguration());
      if (!response.ok) {
        throw new ApiError(`Failed to list global roles: ${response.statusText}`, {
          data: await response.json().catch(() => ({})),
          status: response.status,
        });
      }
      const page = await response.json() as PaginatedResult<GlobalRoleOption>;
      results.push(...page.results);
      url = page.next ?? null;
    }

    return results;
  }

  async createGlobalRole(name: string, permissions: string[] = []): Promise<Response> {
    return await fetch(`${this.apiBase}/api/global_roles`, {
      ...this._requestConfiguration(),
      method: "POST",
      body: JSON.stringify({ name, permissions })
    });
  }

  async getGlobalRoleDetail(globalRoleId: number): Promise<GlobalRoleDetail> {
    const response = await fetch(`${this.apiBase}/api/global_roles/${globalRoleId}`, this._requestConfiguration());
    if (!response.ok) {
      throw new ApiError(`Failed to load global role: ${response.statusText}`, {
        data: await response.json().catch(() => ({})),
        status: response.status,
      });
    }
    return await response.json() as GlobalRoleDetail;
  }

  async updateGlobalRole(globalRoleId: number, name: string, permissions: string[]): Promise<Response> {
    return await fetch(`${this.apiBase}/api/global_roles/${globalRoleId}`, {
      ...this._requestConfiguration(),
      method: "PATCH",
      body: JSON.stringify({ name, permissions })
    });
  }

  async deleteGlobalRole(globalRoleId: number): Promise<Response> {
    return await fetch(`${this.apiBase}/api/global_roles/${globalRoleId}`, {
      ...this._requestConfiguration(),
      method: "DELETE"
    });
  }

  async getGlobalRoleMembers(globalRoleId: number): Promise<GlobalRoleMember[]> {
    const response = await fetch(`${this.apiBase}/api/global_roles/${globalRoleId}/members`, this._requestConfiguration());
    if (!response.ok) {
      throw new ApiError(`Failed to list global role members: ${response.statusText}`, {
        data: await response.json().catch(() => ({})),
        status: response.status,
      });
    }
    const result = await response.json() as GlobalRoleMemberResponse[];
    return result.map((item) => ({ id: item.id, email: item.email, isServiceAccount: item.is_service_account }));
  }

  async addGlobalRoleMember(globalRoleId: number, userId: number): Promise<Response> {
    return await fetch(`${this.apiBase}/api/global_roles/${globalRoleId}/members`, {
      ...this._requestConfiguration(),
      method: "POST",
      body: JSON.stringify({ user_id: userId })
    });
  }

  async removeGlobalRoleMember(globalRoleId: number, userId: number): Promise<Response> {
    return await fetch(`${this.apiBase}/api/global_roles/${globalRoleId}/members/${userId}`, {
      ...this._requestConfiguration(),
      method: "DELETE"
    });
  }
}
