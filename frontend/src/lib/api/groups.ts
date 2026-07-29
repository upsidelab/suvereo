import { BaseApiClient } from "@/lib/api/base.ts";
import { GroupDetail, GroupMember, GroupOption } from "@/lib/types.ts";

type GroupMemberResponse = {
  id: number;
  email: string;
  is_service_account: boolean;
};

export class GroupsApiClient extends BaseApiClient {
  async getGroups(): Promise<GroupOption[]> {
    const response = await fetch(`${this.apiBase}/api/groups`, this._requestConfiguration());
    return (await response.json()) as GroupOption[];
  }

  async createGroup(name: string, permissionIds: number[] = []): Promise<Response> {
    return await fetch(`${this.apiBase}/api/groups`, {
      ...this._requestConfiguration(),
      method: "POST",
      body: JSON.stringify({ name, permission_ids: permissionIds })
    });
  }

  async getGroupDetail(groupId: number): Promise<GroupDetail> {
    const response = await fetch(`${this.apiBase}/api/groups/${groupId}`, this._requestConfiguration());
    const result = await response.json() as { id: number; name: string; permission_ids: number[]; is_system: boolean };
    return { id: result.id, name: result.name, permissionIds: result.permission_ids, isSystem: result.is_system };
  }

  async updateGroup(groupId: number, name: string, permissionIds: number[]): Promise<Response> {
    return await fetch(`${this.apiBase}/api/groups/${groupId}`, {
      ...this._requestConfiguration(),
      method: "PATCH",
      body: JSON.stringify({ name, permission_ids: permissionIds })
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
