import { BaseApiClient } from "@/lib/api/base.ts";
import { GroupOption } from "@/lib/types.ts";

export class GroupsApiClient extends BaseApiClient {
  async getGroups(): Promise<GroupOption[]> {
    const response = await fetch(`${this.apiBase}/api/groups`, this._requestConfiguration());
    return (await response.json()) as GroupOption[];
  }
}
