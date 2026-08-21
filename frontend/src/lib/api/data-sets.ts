import { BaseApiClient } from "@/lib/api/base.ts";
import { DataSet, DatasetAccess, DatasetRoleOption, GlobalRoleOption } from "@/lib/types.ts";
import { ApiError } from "@/lib/api-error.ts";

export type DataSetResponse = {
  id: number | undefined;
  name: string;
  language_model_provider: string;
  language_model: string;
  embedding_provider: string;
  embedding_model: string;
  embedding_vector_dimensions: number;
}

export type CreateDataSetPayload = DataSetResponse & {
  preconfigure_agents: boolean;
};

type DatasetAccessResponse = {
  users: {
    id: number;
    user: { id: number; email: string; is_service_account: boolean };
    role: DatasetRoleOption;
  }[];
  global_roles: {
    id: number;
    global_role: GlobalRoleOption;
    role: DatasetRoleOption;
  }[];
}

export type UpdateDataSetPayload = {
  id: number | undefined;
  name: string;
  language_model_provider: string;
  language_model: string;
}

export class DataSetsApiClient extends BaseApiClient {
  async getDataSets(): Promise<DataSet[]> {
    const results: DataSet[] = [];
    let url: string | null = `${this.apiBase}/api/data_sets`;

    while (url) {
      const response: Response = await fetch(url, this._requestConfiguration());
      const data: { results: DataSet[]; next: string | null } = await response.json();
      results.push(...data.results);
      url = data.next;
    }

    return results;
  }

  async createDataSet(dataSet: Omit<DataSet, "id" | "permissions">, preconfigureAgents: boolean): Promise<number> {
    const body: CreateDataSetPayload = {
      id: undefined,
      name: dataSet.name,
      language_model_provider: dataSet.languageModelProvider,
      language_model: dataSet.languageModel,
      embedding_provider: dataSet.embeddingProvider,
      embedding_model: dataSet.embeddingModel,
      embedding_vector_dimensions: dataSet.embeddingVectorSize,
      preconfigure_agents: preconfigureAgents,
    }

    const response = await fetch(`${this.apiBase}/api/data_sets`,
      {
        ...this._requestConfiguration(),
        body: JSON.stringify(body),
        method: 'POST'
      }
    );

    if (!response.ok) {
      throw new ApiError(`Failed to create data set: ${response.statusText}`, {
        data: await response.json().catch(() => ({})),
        status: response.status,
      });
    }

    const responseJson = (await response.json()) as DataSetResponse;
    return responseJson.id!;
  }

  async getDataSetAccess(dataSetId: number): Promise<DatasetAccess> {
    const response = await fetch(`${this.apiBase}/api/data_sets/${dataSetId}/roles/`, this._requestConfiguration());
    if (!response.ok) {
      throw new ApiError(`Failed to load data set access: ${response.statusText}`, {
        data: await response.json().catch(() => ({})),
        status: response.status,
      });
    }
    const result = await response.json() as DatasetAccessResponse;
    return {
      users: result.users.map((assignment) => ({
        id: assignment.id,
        role: assignment.role,
        user: {
          id: assignment.user.id,
          email: assignment.user.email,
          isServiceAccount: assignment.user.is_service_account
        }
      })),
      globalRoles: result.global_roles.map((assignment) => ({
        id: assignment.id,
        role: assignment.role,
        globalRole: assignment.global_role
      }))
    };
  }

  async grantRoleToUser(dataSetId: number, roleId: number, userId: number): Promise<Response> {
    return await fetch(
      `${this.apiBase}/api/data_sets/${dataSetId}/roles/${roleId}/users`,
      {
        ...this._requestConfiguration(),
        method: "POST",
        body: JSON.stringify({ user_id: userId })
      }
    );
  }

  async grantRoleToGlobalRole(dataSetId: number, roleId: number, globalRoleId: number): Promise<Response> {
    return await fetch(
      `${this.apiBase}/api/data_sets/${dataSetId}/roles/${roleId}/global_roles`,
      {
        ...this._requestConfiguration(),
        method: "POST",
        body: JSON.stringify({ global_role_id: globalRoleId })
      }
    );
  }

  async revokeRoleFromUser(dataSetId: number, roleId: number, userId: number): Promise<Response> {
    return await fetch(
      `${this.apiBase}/api/data_sets/${dataSetId}/roles/${roleId}/users/${userId}`,
      {
        ...this._requestConfiguration(),
        method: "DELETE"
      }
    );
  }

  async revokeRoleFromGlobalRole(dataSetId: number, roleId: number, globalRoleId: number): Promise<Response> {
    return await fetch(
      `${this.apiBase}/api/data_sets/${dataSetId}/roles/${roleId}/global_roles/${globalRoleId}`,
      {
        ...this._requestConfiguration(),
        method: "DELETE"
      }
    );
  }

  async getDataSet(dataSetId: number): Promise<DataSet> {
    const response = await fetch(`${this.apiBase}/api/data_sets/${dataSetId}`, this._requestConfiguration());
    const data = await response.json();

    return {
      id: data.id,
      name: data.name,
      languageModelProvider: data.language_model_provider,
      languageModel: data.language_model,
      embeddingProvider: data.embedding_provider,
      embeddingModel: data.embedding_model,
      embeddingVectorSize: data.embedding_vector_dimensions,
      permissions: data.permissions,
    } as DataSet;
  }

  async deleteDataSet(dataSetId: number): Promise<void> {
    const response = await fetch(
      `${this.apiBase}/api/data_sets/${dataSetId}`,
      {
        ...this._requestConfiguration(),
        method: "DELETE",
      }
    );

    if (!response.ok) {
      throw new Error("Failed to delete data set");
    }
  }

  async updateDataSet(dataSetId: number, dataSet: DataSet): Promise<void> {
    const body: UpdateDataSetPayload = {
      id: dataSet.id,
      name: dataSet.name,
      language_model_provider: dataSet.languageModelProvider,
      language_model: dataSet.languageModel,
    }

    const response = await fetch(`${this.apiBase}/api/data_sets/${dataSetId}`,
      {
        ...this._requestConfiguration(),
        method: 'PATCH',
        body: JSON.stringify(body)
      }
    );

    if (!response.ok) {
      throw new ApiError(`Failed to update data set: ${response.statusText}`, {
        data: await response.json().catch(() => ({})),
        status: response.status,
      });
    }
  }
}
