import { BaseApiClient } from "@/lib/api/base.ts";
import { DataSet, DataSetAccess, DataSetRoleOption } from "@/lib/types.ts";
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

type DataSetAccessResponse = {
  members: {
    id: number;
    user: { id: number; email: string; is_service_account: boolean };
    role: DataSetRoleOption;
  }[];
  groups: {
    id: number;
    group: {
      id: number;
      name: string;
      description: string;
      member_count: number;
      global_role_count: number;
      data_set_role_count: number;
    };
    role: DataSetRoleOption;
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

  async getDataSetAccess(dataSetId: number): Promise<DataSetAccess> {
    const response = await fetch(`${this.apiBase}/api/data_sets/${dataSetId}/roles/`, this._requestConfiguration());
    if (!response.ok) {
      throw new ApiError(`Failed to load data set access: ${response.statusText}`, {
        data: await response.json().catch(() => ({})),
        status: response.status,
      });
    }
    const result = await response.json() as DataSetAccessResponse;
    return {
      members: result.members.map((assignment) => ({
        id: assignment.id,
        role: assignment.role,
        user: {
          id: assignment.user.id,
          email: assignment.user.email,
          isServiceAccount: assignment.user.is_service_account
        }
      })),
      groups: result.groups.map((assignment) => ({
        id: assignment.id,
        role: assignment.role,
        group: {
          id: assignment.group.id,
          name: assignment.group.name,
          description: assignment.group.description,
          memberCount: assignment.group.member_count,
          globalRoleCount: assignment.group.global_role_count,
          dataSetRoleCount: assignment.group.data_set_role_count
        }
      }))
    };
  }

  async grantRoleToMember(dataSetId: number, roleId: number, userId: number): Promise<Response> {
    return await fetch(
      `${this.apiBase}/api/data_sets/${dataSetId}/roles/${roleId}/members`,
      {
        ...this._requestConfiguration(),
        method: "POST",
        body: JSON.stringify({ user_id: userId })
      }
    );
  }

  async grantRoleToGroup(dataSetId: number, roleId: number, groupId: number): Promise<Response> {
    return await fetch(
      `${this.apiBase}/api/data_sets/${dataSetId}/roles/${roleId}/groups`,
      {
        ...this._requestConfiguration(),
        method: "POST",
        body: JSON.stringify({ group_id: groupId })
      }
    );
  }

  async revokeRoleFromMember(dataSetId: number, roleId: number, userId: number): Promise<Response> {
    return await fetch(
      `${this.apiBase}/api/data_sets/${dataSetId}/roles/${roleId}/members/${userId}`,
      {
        ...this._requestConfiguration(),
        method: "DELETE"
      }
    );
  }

  async revokeRoleFromGroup(dataSetId: number, roleId: number, groupId: number): Promise<Response> {
    return await fetch(
      `${this.apiBase}/api/data_sets/${dataSetId}/roles/${roleId}/groups/${groupId}`,
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
