import { AuthenticationProvider, TokenPair } from "./authentication-provider.ts";
import { BaseApiClient } from "@/lib/api/base.ts";
import { UsersApiClient } from "@/lib/api/users.ts";
import { DataSetsApiClient } from "@/lib/api/data-sets.ts";
import { ConversationsApiClient } from "@/lib/api/conversations.ts";
import { ServiceAccountsApiClient } from "@/lib/api/service-accounts.ts";
import { Account, GlobalRoleMember, PaginatedResult, User } from "@/lib/types.ts";
import { ConfigApiClient } from "@/lib/api/config.ts";
import { AgentsApiClient } from "@/lib/api/agents.ts";
import { AgenticExecutionsApiClient } from "@/lib/api/agentic-executions.ts";
import { IntegrationsApiClient } from "@/lib/api/integrations.ts";
import { EntitiesApiClient } from "@/lib/api/entities.ts";
import { GlobalRolesApiClient } from "@/lib/api/global-roles.ts";
import { GroupsApiClient } from "@/lib/api/groups.ts";
import { DataSetRolesApiClient } from "@/lib/api/data-set-roles.ts";
import { PermissionsApiClient } from "@/lib/api/permissions.ts";
import { UserResponse } from "@/lib/api/users.ts";
import { ApiError } from "@/lib/api-error.ts";

export type Token = {
  token: string;
}

type AccountResponse = {
  email: string;
  is_admin: boolean;
  permissions: string[];
}

export type FeedbackData = {
  rating: number | null;
  feedback: string;
}

export type TaskHandle = {
  task_id: string;
  streaming: boolean;
}

export class ApiClient extends BaseApiClient {
  constructor(authenticationProvider: AuthenticationProvider) {
    super(import.meta.env.VITE_API_BASE, authenticationProvider);
  }

  async login(email: string, password: string): Promise<TokenPair> {
    const response = await fetch(`${this.apiBase}/api/auth/login`, {
      headers: {
        'Content-Type': 'application/json'
      },
      method: 'POST',
      body: JSON.stringify({ email, password })
    });

    if (response.status !== 200) {
      throw 'Could not sign in';
    }

    return await response.json() as TokenPair;
  }

  async logout(): Promise<void> {
    const refresh = this.authenticationProvider.refreshToken;
    if (refresh === null) {
      return;
    }

    try {
      await fetch(`${this.apiBase}/api/auth/logout`, {
        headers: {
          'Content-Type': 'application/json'
        },
        method: 'POST',
        body: JSON.stringify({ refresh })
      });
    } catch {
      // The refresh token expires on its own.
    }
  }

  async getAccount(): Promise<Account> {
    const response = await this.authenticatedFetch(`${this.apiBase}/api/account`);
    const responseJson = await response.json() as AccountResponse;
    return {
      email: responseJson.email,
      isAdmin: responseJson.is_admin,
      permissions: responseJson.permissions
    };
  }

  users(): UsersApiClient {
    return new UsersApiClient(this.apiBase, this.authenticationProvider);
  }

  async getAllUsers(): Promise<User[]> {
    const results: User[] = [];
    let url: string | null = `${this.apiBase}/api/users`;

    while (url) {
      const response: Response = await this.authenticatedFetch(url);
      if (!response.ok) {
        throw new ApiError(`Failed to list users: ${response.statusText}`, {
          data: await response.json().catch(() => ({})),
          status: response.status,
        });
      }
      const page = await response.json() as PaginatedResult<UserResponse>;
      results.push(...page.results.map((item) => ({
        id: item.id,
        email: item.email,
        isAdmin: item.is_admin,
        isActive: item.is_active
      })));
      url = page.next ?? null;
    }

    return results;
  }

  async getAdmins(): Promise<GlobalRoleMember[]> {
    const response = await this.authenticatedFetch(`${this.apiBase}/api/admins`);
    if (!response.ok) {
      throw new ApiError(`Failed to list admins: ${response.statusText}`, {
        data: await response.json().catch(() => ({})),
        status: response.status,
      });
    }
    const result = await response.json() as { id: number; email: string; is_service_account: boolean }[];
    return result.map((item) => ({ id: item.id, email: item.email, isServiceAccount: item.is_service_account }));
  }

  serviceAccounts(): ServiceAccountsApiClient {
    return new ServiceAccountsApiClient(this.apiBase, this.authenticationProvider);
  }

  dataSets(): DataSetsApiClient {
    return new DataSetsApiClient(this.apiBase, this.authenticationProvider);
  }

  globalRoles(): GlobalRolesApiClient {
    return new GlobalRolesApiClient(this.apiBase, this.authenticationProvider);
  }

  groups(): GroupsApiClient {
    return new GroupsApiClient(this.apiBase, this.authenticationProvider);
  }

  dataSetRoles(): DataSetRolesApiClient {
    return new DataSetRolesApiClient(this.apiBase, this.authenticationProvider);
  }

  permissions(): PermissionsApiClient {
    return new PermissionsApiClient(this.apiBase, this.authenticationProvider);
  }

  conversations(): ConversationsApiClient {
    return new ConversationsApiClient(this.apiBase, this.authenticationProvider);
  }

  config(): ConfigApiClient {
    return new ConfigApiClient(this.apiBase, this.authenticationProvider);
  }

  agents(): AgentsApiClient {
    return new AgentsApiClient(this.apiBase, this.authenticationProvider);
  }

  agenticExecutions(): AgenticExecutionsApiClient {
    return new AgenticExecutionsApiClient(this.apiBase, this.authenticationProvider);
  }

  integrations(): IntegrationsApiClient {
    return new IntegrationsApiClient(this.apiBase, this.authenticationProvider);
  }

  entities(): EntitiesApiClient {
    return new EntitiesApiClient(this.apiBase, this.authenticationProvider);
  }
}
