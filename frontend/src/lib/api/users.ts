import { BaseApiClient } from "@/lib/api/base.ts";
import { PaginatedResult, User } from "@/lib/types.ts";

export type CreateUserParams = {
  email: string;
  password: string;
  groupIds: number[];
  isActive: boolean;
}

export type UpdateUserParams = {
  email: string;
  groupIds: number[];
  isActive: boolean;
}

export type CreateUserPayload = {
  email: string;
  password: string;
  group_ids: number[];
  is_active: boolean;
}

export type UpdateUserPayload = {
  email: string;
  group_ids: number[];
  is_active: boolean;
}

export type UpdateUserPasswordPayload = {
  password: string;
}

export type UserResponse = {
  id: number;
  email: string;
  is_admin: boolean;
  is_active: boolean;
  group_ids: number[];
}

export class UsersApiClient extends BaseApiClient {
  async getUsers(page: number): Promise<PaginatedResult<User>> {
    const response = await fetch(`${this.apiBase}/api/users?page=${page}`, this._requestConfiguration());
    const result = await response.json() as PaginatedResult<UserResponse>;

    return {
      count: result.count,
      results: result.results.map((item) => ({
        id: item.id,
        email: item.email,
        isAdmin: item.is_admin,
        isActive: item.is_active,
        groupIds: item.group_ids
      }))
    };
  }

  async createUser(user: CreateUserParams) {
    const payload: CreateUserPayload = {
      email: user.email,
      password: user.password,
      group_ids: user.groupIds,
      is_active: user.isActive
    };

    return await fetch(
      `${this.apiBase}/api/users`,
      {
        ...this._requestConfiguration(),
        method: "POST",
        body: JSON.stringify(payload)
      }
    );
  }

  async updateUser(userId: number, user: UpdateUserParams) {
    const payload: UpdateUserPayload = {
      email: user.email,
      group_ids: user.groupIds,
      is_active: user.isActive
    };

    return await fetch(
      `${this.apiBase}/api/users/${userId}`,
      {
        ...this._requestConfiguration(),
        method: "PATCH",
        body: JSON.stringify(payload)
      }
    );
  }

  async updateUserPassword(userId: number, password: string) {
    const payload: UpdateUserPasswordPayload = {
      password: password
    };

    return await fetch(
      `${this.apiBase}/api/users/${userId}/password`,
      {
        ...this._requestConfiguration(),
        method: "PUT",
        body: JSON.stringify(payload)
      }
    )
  }
}
