import { BaseApiClient } from "@/lib/api/base.ts";
import { GroupDetail, GroupMember, GroupOption, PaginatedResult } from "@/lib/types.ts";
import { ApiError } from "@/lib/api-error.ts";

type GroupMemberResponse = {
  id: number;
  email: string;
  is_service_account: boolean;
};

export class GroupsApiClient extends BaseApiClient {
  async getGroups(): Promise<GroupOption[]> {
    const results: GroupOption[] = [];
    let url: string | null = `${this.apiBase}/api/groups`;

    while (url) {
      const response: Response = await fetch(url, this._requestConfiguration());
      if (!response.ok) {
        throw new ApiError(`Failed to list groups: ${response.statusText}`, {
          data: await response.json().catch(() => ({})),
          status: response.status,
        });
      }
      const page = await response.json() as PaginatedResult<GroupOption>;
      results.push(...page.results);
      url = page.next ?? null;
    }

    return results;
  }

  async createGroup(name: string, permissions: string[] = []): Promise<Response> {
    return await fetch(`${this.apiBase}/api/groups`, {
      ...this._requestConfiguration(),
      method: "POST",
      body: JSON.stringify({ name, permissions })
    });
  }

  async getGroupDetail(groupId: number): Promise<GroupDetail> {
    const response = await fetch(`${this.apiBase}/api/groups/${groupId}`, this._requestConfiguration());
    if (!response.ok) {
      throw new ApiError(`Failed to load group: ${response.statusText}`, {
        data: await response.json().catch(() => ({})),
        status: response.status,
      });
    }
    return await response.json() as GroupDetail;
  }

  async updateGroup(groupId: number, name: string, permissions: string[]): Promise<Response> {
    return await fetch(`${this.apiBase}/api/groups/${groupId}`, {
      ...this._requestConfiguration(),
      method: "PATCH",
      body: JSON.stringify({ name, permissions })
    });
  }

  async deleteGroup(groupId: number): Promise<Response> {
    return await fetch(`${this.apiBase}/api/groups/${groupId}`, {
      ...this._requestConfiguration(),
      method: "DELETE"
    });
  }

  async getGroupMembers(groupId: number): Promise<GroupMember[]> {
    const response = await fetch(`${this.apiBase}/api/groups/${groupId}/members`, this._requestConfiguration());
    if (!response.ok) {
      throw new ApiError(`Failed to list group members: ${response.statusText}`, {
        data: await response.json().catch(() => ({})),
        status: response.status,
      });
    }
    const result = await response.json() as GroupMemberResponse[];
    return result.map((item) => ({ id: item.id, email: item.email, isServiceAccount: item.is_service_account }));
  }

  async addGroupMember(groupId: number, userId: number): Promise<Response> {
    return await fetch(`${this.apiBase}/api/groups/${groupId}/members`, {
      ...this._requestConfiguration(),
      method: "POST",
      body: JSON.stringify({ user_id: userId })
    });
  }

  async removeGroupMember(groupId: number, userId: number): Promise<Response> {
    return await fetch(`${this.apiBase}/api/groups/${groupId}/members/${userId}`, {
      ...this._requestConfiguration(),
      method: "DELETE"
    });
  }
}
