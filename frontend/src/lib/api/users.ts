import { BaseApiClient } from "@/lib/api/base.ts";
import { PaginatedResult, User } from "@/lib/types.ts";
import { ApiError } from "@/lib/api-error.ts";

export type CreateUserParams = {
  email: string;
  password: string;
  isAdmin: boolean;
  isActive: boolean;
}

export type UpdateUserParams = {
  email: string;
  isAdmin: boolean;
  isActive: boolean;
}

export type CreateUserPayload = {
  email: string;
  password: string;
  is_admin: boolean;
  is_active: boolean;
}

export type UpdateUserPayload = {
  email: string;
  is_admin: boolean;
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
}

export class UsersApiClient extends BaseApiClient {
  async getUsers(page: number): Promise<PaginatedResult<User>> {
    const response = await this.authenticatedFetch(`${this.apiBase}/api/users?page=${page}`);
    if (!response.ok) {
      throw new ApiError(`Failed to list users: ${response.statusText}`, {
        data: await response.json().catch(() => ({})),
        status: response.status,
      });
    }
    const result = await response.json() as PaginatedResult<UserResponse>;

    return {
      count: result.count,
      results: result.results.map((item) => ({
        id: item.id,
        email: item.email,
        isAdmin: item.is_admin,
        isActive: item.is_active
      }))
    };
  }

  async createUser(user: CreateUserParams) {
    const payload: CreateUserPayload = {
      email: user.email,
      password: user.password,
      is_admin: user.isAdmin,
      is_active: user.isActive
    };

    return await this.authenticatedFetch(
      `${this.apiBase}/api/users`,
      {
        method: "POST",
        body: JSON.stringify(payload)
      }
    );
  }

  async updateUser(userId: number, user: UpdateUserParams) {
    const payload: UpdateUserPayload = {
      email: user.email,
      is_admin: user.isAdmin,
      is_active: user.isActive
    };

    return await this.authenticatedFetch(
      `${this.apiBase}/api/users/${userId}`,
      {
        method: "PATCH",
        body: JSON.stringify(payload)
      }
    );
  }

  async setUserAdmin(userId: number, isAdmin: boolean): Promise<Response> {
    return await this.authenticatedFetch(
      `${this.apiBase}/api/users/${userId}`,
      {
        method: "PATCH",
        body: JSON.stringify({ is_admin: isAdmin })
      }
    );
  }

  async updateUserPassword(userId: number, password: string) {
    const payload: UpdateUserPasswordPayload = {
      password: password
    };

    return await this.authenticatedFetch(
      `${this.apiBase}/api/users/${userId}/password`,
      {
        method: "PUT",
        body: JSON.stringify(payload)
      }
    )
  }
}
