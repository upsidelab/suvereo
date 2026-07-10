import { BaseApiClient } from "@/lib/api/base.ts";
import { DataSet, User } from "@/lib/types.ts";

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

  async getDataSetUsers(dataSetId: number): Promise<User[]> {
    const response = await fetch(`${this.apiBase}/api/data_sets/${dataSetId}/users`, this._requestConfiguration());
    return (await response.json()).results as User[];
  }

  async addDataSetUser(dataSetId: number, userId: number): Promise<void> {
    await fetch(
      `${this.apiBase}/api/data_sets/${dataSetId}/users`,
      {
        ...this._requestConfiguration(),
        method: "POST",
        body: JSON.stringify({user_id: userId})
      }
    );
  }

  async removeDataSetUser(dataSetId: number, userId: number): Promise<void> {
    await fetch(
      `${this.apiBase}/api/data_sets/${dataSetId}/users/${userId}`,
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
