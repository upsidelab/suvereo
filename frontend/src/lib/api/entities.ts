import { BaseApiClient } from "@/lib/api/base.ts";
import { EntityType, PaginatedResult } from "@/lib/types.ts";

export class EntitiesApiClient extends BaseApiClient {
  async listTypes(): Promise<EntityType[]> {
    const response = await fetch(`${this.apiBase}/api/entities/`, this._requestConfiguration());
    return await response.json() as EntityType[];
  }

  async getRecords(dataSetId: number, slug: string, page: number = 1): Promise<PaginatedResult<Record<string, unknown>>> {
    const params = new URLSearchParams({ page: page.toString() });
    const response = await fetch(
      `${this.apiBase}/api/data_sets/${dataSetId}/${slug}/?${params}`,
      this._requestConfiguration()
    );
    return await response.json() as PaginatedResult<Record<string, unknown>>;
  }
}
