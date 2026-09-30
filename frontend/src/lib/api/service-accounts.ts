import { BaseApiClient } from "@/lib/api/base.ts";
import { PaginatedResult, ServiceAccount } from "@/lib/types.ts";
import { Token } from "@/lib/api.ts";
import { ApiError } from "@/lib/api-error.ts";

export type ServiceAccountResponse = {
  id: number;
  email: string;
  date_joined: string;
  is_active: boolean;
  is_admin: boolean;
}

export type CreateServiceAccountParams = {
  name: string;
  isActive: boolean;
  isAdmin: boolean;
}

export type UpdateServiceAccountParams = CreateServiceAccountParams;

export type CreateServiceAccountPayload = {
  name: string;
  is_active: boolean;
  is_admin: boolean;
}

export type UpdateServiceAccountPayload = CreateServiceAccountPayload;

export class ServiceAccountsApiClient extends BaseApiClient {
  async getServiceAccounts(page: number): Promise<PaginatedResult<ServiceAccount>> {
    const response = await this.authenticatedFetch(`${this.apiBase}/api/service_accounts?page=${page}`);
    if (!response.ok) {
      throw new ApiError(`Failed to list service accounts: ${response.statusText}`, {
        data: await response.json().catch(() => ({})),
        status: response.status,
      });
    }
    const result = await response.json() as PaginatedResult<ServiceAccountResponse>;

    return {
      count: result.count,
      results: result.results.map((item) => ({
        id: item.id,
        email: item.email,
        dateCreated: item.date_joined,
        isActive: item.is_active,
        isAdmin: item.is_admin
      }))
    };
  }

  async getAllServiceAccounts(): Promise<ServiceAccount[]> {
    const results: ServiceAccount[] = [];
    let url: string | null = `${this.apiBase}/api/service_accounts/`;

    while (url) {
      const response: Response = await this.authenticatedFetch(url);
      if (!response.ok) {
        throw new ApiError(`Failed to list service accounts: ${response.statusText}`, {
          data: await response.json().catch(() => ({})),
          status: response.status,
        });
      }
      const page = await response.json() as PaginatedResult<ServiceAccountResponse>;
      results.push(...page.results.map((item) => ({
        id: item.id,
        email: item.email,
        dateCreated: item.date_joined,
        isActive: item.is_active,
        isAdmin: item.is_admin
      })));
      url = page.next ?? null;
    }

    return results;
  }

  async setServiceAccountAdmin(id: number, isAdmin: boolean): Promise<Response> {
    return await this.authenticatedFetch(`${this.apiBase}/api/service_accounts/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ is_admin: isAdmin })
    });
  }

  async createServiceAccount(serviceAccount: CreateServiceAccountParams): Promise<Token> {
    const payload: CreateServiceAccountPayload = {
      name: serviceAccount.name,
      is_active: serviceAccount.isActive,
      is_admin: serviceAccount.isAdmin
    };

    const response = await this.authenticatedFetch(`${this.apiBase}/api/service_accounts/`, {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      throw new ApiError(`Failed to create service account: ${response.statusText}`, {
        data: await response.json().catch(() => ({})),
        status: response.status,
      });
    }

    return await response.json() as Token;
  }

  async updateServiceAccount(id: number, serviceAccount: UpdateServiceAccountParams): Promise<Response> {
    const payload: UpdateServiceAccountPayload = {
      name: serviceAccount.name,
      is_active: serviceAccount.isActive,
      is_admin: serviceAccount.isAdmin
    };

    return await this.authenticatedFetch(`${this.apiBase}/api/service_accounts/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload)
    });
  }

  async checkServiceNameAvailability(name: string): Promise<boolean> {
    const response = await this.authenticatedFetch(`${this.apiBase}/api/service_accounts/check_name`, {
      method: 'POST',
      body: JSON.stringify({ name })
    });

    const { is_available } = await response.json();
    return is_available;
  }

  async resetServiceAccountToken(id: number): Promise<Token> {
    const response = await this.authenticatedFetch(`${this.apiBase}/api/service_accounts/${id}/reset_token`, {
      method: 'POST'
    });

    if (!response.ok) {
      throw new Error('Failed to revoke service account token');
    }

    return await response.json() as Token;
  }
}
