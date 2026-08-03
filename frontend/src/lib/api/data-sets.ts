import { BaseApiClient } from "@/lib/api/base.ts";
import { ApiError } from "@/lib/api-error.ts";
import { DataSet, DataSetAccessGrant } from "@/lib/types.ts";

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

  async createDataSet(dataSet: DataSet, preconfigureAgents: boolean): Promise<number> {
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

    const responseJson = (await response.json()) as DataSetResponse;
    return responseJson.id!;
  }

  async getDataSetAccess(dataSetId: number): Promise<DataSetAccessGrant[]> {
    const response = await fetch(`${this.apiBase}/api/data_sets/${dataSetId}/access`, this._requestConfiguration());
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(`Failed to list data set access: ${response.statusText}`, {
        data: errorData,
        status: response.status,
      });
    }
    const data = await response.json() as {
      target_type: "user" | "group";
      target_id: number;
      target_label: string;
      role: string | null;
    }[];
    return data.map((row) => ({
      targetType: row.target_type,
      targetId: row.target_id,
      targetLabel: row.target_label,
      role: row.role,
    }));
  }

  async grantDataSetAccess(dataSetId: number, targetType: "user" | "group", targetId: number, role: string): Promise<void> {
    await fetch(
      `${this.apiBase}/api/data_sets/${dataSetId}/access`,
      {
        ...this._requestConfiguration(),
        method: "POST",
        body: JSON.stringify({ target_type: targetType, target_id: targetId, role })
      }
    );
  }

  async revokeDataSetAccess(dataSetId: number, targetType: "user" | "group", targetId: number): Promise<void> {
    await fetch(
      `${this.apiBase}/api/data_sets/${dataSetId}/access/${targetType}/${targetId}`,
      {
        ...this._requestConfiguration(),
        method: "DELETE"
      }
    );
  }

  async syncDataSetAllSources(dataSetId: number | undefined): Promise<void> {
    await fetch(
      `${this.apiBase}/api/data_sets/${dataSetId}/sync`,
      {
        ...this._requestConfiguration(),
        method: "POST"
      }
    );
  }

  async syncAllSources(): Promise<void> {
    await fetch(
      `${this.apiBase}/api/sync`,
      {
        ...this._requestConfiguration(),
        method: "POST"
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

    await fetch(`${this.apiBase}/api/data_sets/${dataSetId}`,
      {
        ...this._requestConfiguration(),
        method: 'PATCH',
        body: JSON.stringify(body)
      }
    );
  }
}
