import { getCsrfToken } from "@/lib/csrf.ts";
import { UsersApiClient } from "@/lib/api/users.ts";
import { DataSetsApiClient } from "@/lib/api/data-sets.ts";
import { ConversationsApiClient } from "@/lib/api/conversations.ts";
import { ServiceAccountsApiClient } from "@/lib/api/service-accounts.ts";
import { Account, User } from "@/lib/types.ts";
import { ConfigApiClient } from "@/lib/api/config.ts";
import { AgentsApiClient } from "@/lib/api/agents.ts";
import { AgenticExecutionsApiClient } from "@/lib/api/agentic-executions.ts";
import { IntegrationsApiClient } from "@/lib/api/integrations.ts";
import { EntitiesApiClient } from "@/lib/api/entities.ts";
import { GroupsApiClient } from "@/lib/api/groups.ts";
import { DatasetRolesApiClient } from "@/lib/api/dataset-roles.ts";
import { PermissionsApiClient } from "@/lib/api/permissions.ts";

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

export class ApiClient {
  private readonly apiBase: string;

  constructor() {
    this.apiBase = import.meta.env.VITE_API_BASE;
  }

  async login(email: string, password: string): Promise<void> {
    const response = await fetch(`${this.apiBase}/api/auth/login`, {
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken() ?? ''
      },
      credentials: 'include',
      method: 'POST',
      body: JSON.stringify({ email, password })
    });

    if (response.status !== 200) {
      throw 'Could not sign in';
    }
  }

  async logout(): Promise<void> {
    await fetch(`${this.apiBase}/api/auth/logout`, {
      ...this._requestConfiguration(),
      method: 'POST',
    });
  }

  async getAccount(): Promise<Account> {
    const response = await fetch(`${this.apiBase}/api/account`, this._requestConfiguration());
    const responseJson = await response.json() as AccountResponse;
    return {
      email: responseJson.email,
      isAdmin: responseJson.is_admin,
      permissions: responseJson.permissions
    };
  }

  users(): UsersApiClient {
    return new UsersApiClient(this.apiBase);
  }

  async getAllUsers(): Promise<User[]> {
    const response = await fetch(`${this.apiBase}/api/users?page_size=1000`, this._requestConfiguration());
    return (await response.json()).results as User[];
  }

  serviceAccounts(): ServiceAccountsApiClient {
    return new ServiceAccountsApiClient(this.apiBase);
  }

  dataSets(): DataSetsApiClient {
    return new DataSetsApiClient(this.apiBase);
  }

  groups(): GroupsApiClient {
    return new GroupsApiClient(this.apiBase, this.authenticationProvider);
  }

  datasetRoles(): DatasetRolesApiClient {
    return new DatasetRolesApiClient(this.apiBase, this.authenticationProvider);
  }

  permissions(): PermissionsApiClient {
    return new PermissionsApiClient(this.apiBase, this.authenticationProvider);
  }

  conversations(): ConversationsApiClient {
    return new ConversationsApiClient(this.apiBase);
  }

  config(): ConfigApiClient {
    return new ConfigApiClient(this.apiBase);
  }

  agents(): AgentsApiClient {
    return new AgentsApiClient(this.apiBase);
  }

  agenticExecutions(): AgenticExecutionsApiClient {
    return new AgenticExecutionsApiClient(this.apiBase);
  }

  integrations(): IntegrationsApiClient {
    return new IntegrationsApiClient(this.apiBase);
  }

  entities(): EntitiesApiClient {
    return new EntitiesApiClient(this.apiBase);
  }

  _requestConfiguration(): RequestInit {
    return {
      credentials: 'include',
      headers: {
        'X-CSRFToken': getCsrfToken() ?? '',
        "Content-Type": "application/json"
      }
    }
  }
}
