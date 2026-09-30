import { BaseApiClient } from "@/lib/api/base.ts";
import { GlobalRoleOption, GroupDetail, GroupMember, GroupOption, PaginatedResult } from "@/lib/types.ts";
import { ApiError } from "@/lib/api-error.ts";

export type GroupResponse = {
  id: number;
  name: string;
  description: string;
  member_count: number;
  global_role_count: number;
  data_set_role_count: number;
};

type GroupDetailResponse = GroupResponse & {
  global_roles: GlobalRoleOption[];
};

type GroupMemberResponse = {
  id: number;
  email: string;
  is_service_account: boolean;
};

export function toGroupOption(group: GroupResponse): GroupOption {
  return {
    id: group.id,
    name: group.name,
    description: group.description,
    memberCount: group.member_count,
    globalRoleCount: group.global_role_count,
    dataSetRoleCount: group.data_set_role_count,
  };
}

export class GroupsApiClient extends BaseApiClient {
  async getGroups(): Promise<GroupOption[]> {
    const results: GroupOption[] = [];
    let url: string | null = `${this.apiBase}/api/groups`;

    while (url) {
      const response: Response = await this.authenticatedFetch(url);
      if (!response.ok) {
        throw new ApiError(`Failed to list groups: ${response.statusText}`, {
          data: await response.json().catch(() => ({})),
          status: response.status,
        });
      }
      const page = await response.json() as PaginatedResult<GroupResponse>;
      results.push(...page.results.map(toGroupOption));
      url = page.next ?? null;
    }

    return results;
  }

  async createGroup(name: string, description: string): Promise<Response> {
    return await this.authenticatedFetch(`${this.apiBase}/api/groups`, {
      method: "POST",
      body: JSON.stringify({ name, description })
    });
  }

  async getGroupDetail(groupId: number): Promise<GroupDetail> {
    const response = await this.authenticatedFetch(`${this.apiBase}/api/groups/${groupId}`);
    if (!response.ok) {
      throw new ApiError(`Failed to load group: ${response.statusText}`, {
        data: await response.json().catch(() => ({})),
        status: response.status,
      });
    }
    const result = await response.json() as GroupDetailResponse;
    return { ...toGroupOption(result), globalRoles: result.global_roles };
  }

  async updateGroup(groupId: number, name: string, description: string): Promise<Response> {
    return await this.authenticatedFetch(`${this.apiBase}/api/groups/${groupId}`, {
      method: "PATCH",
      body: JSON.stringify({ name, description })
    });
  }

  async deleteGroup(groupId: number): Promise<Response> {
    return await this.authenticatedFetch(`${this.apiBase}/api/groups/${groupId}`, {
      method: "DELETE"
    });
  }

  async getGroupMembers(groupId: number): Promise<GroupMember[]> {
    const response = await this.authenticatedFetch(`${this.apiBase}/api/groups/${groupId}/members`);
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
    return await this.authenticatedFetch(`${this.apiBase}/api/groups/${groupId}/members`, {
      method: "POST",
      body: JSON.stringify({ user_id: userId })
    });
  }

  async removeGroupMember(groupId: number, userId: number): Promise<Response> {
    return await this.authenticatedFetch(`${this.apiBase}/api/groups/${groupId}/members/${userId}`, {
      method: "DELETE"
    });
  }

  async grantGlobalRoleToGroup(groupId: number, globalRoleId: number): Promise<Response> {
    return await this.authenticatedFetch(`${this.apiBase}/api/groups/${groupId}/global_roles`, {
      method: "POST",
      body: JSON.stringify({ global_role_id: globalRoleId })
    });
  }

  async revokeGlobalRoleFromGroup(groupId: number, globalRoleId: number): Promise<Response> {
    return await this.authenticatedFetch(`${this.apiBase}/api/groups/${groupId}/global_roles/${globalRoleId}`, {
      method: "DELETE"
    });
  }
}
