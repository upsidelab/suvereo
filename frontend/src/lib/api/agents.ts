import {BaseApiClient} from "@/lib/api/base.ts";
import {Agent, AgentConfig, AgentDetails, ToolConfigSchema, ToolProvidingIntegrationOption} from "@/lib/types.ts";
import {ApiError} from "@/lib/api-error.ts";

export type AgentChoice = {
  key: string;
  name: string;
  agent_args: Record<string, string>;
  prompt_inputs: Record<string, string>;
  tools: Record<string, ToolConfigSchema>;
};

type AvailableAgentsResponse = {
  choices: AgentChoice[];
};

export class AgentsApiClient extends BaseApiClient {
    async getAvailableAgentTypes(): Promise<AgentChoice[]> {
        const response = await this.authenticatedFetch(`${this.apiBase}/api/agents/types`);

        if (!response.ok) {
            throw new Error(`Failed to fetch available agents: ${response.statusText}`);
        }

        const result = await response.json() as AvailableAgentsResponse;
        return result.choices;
    }
    async getDatasetAvailableAgents(dataSetId: number): Promise<Agent[]> {
        const query = new URLSearchParams({ dataset: dataSetId.toString() });
        const response = await this.authenticatedFetch(`${this.apiBase}/api/agents?${query.toString()}`);

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new ApiError(`Failed to fetch available agents: ${response.statusText}`, {
                data: errorData,
                status: response.status
            });
        }

        return await response.json() as Agent[];
    }
    async getToolProvidingIntegrations(dataSetId: number): Promise<ToolProvidingIntegrationOption[]> {
        const query = new URLSearchParams({ dataset: dataSetId.toString() });
        const response = await this.authenticatedFetch(`${this.apiBase}/api/agents/tool-providing-integrations?${query.toString()}`);

        if (!response.ok) {
            throw new ApiError(`Failed to fetch tool-providing integrations: ${response.statusText}`, {
                data: await response.json().catch(() => ({})),
                status: response.status
            });
        }

        return await response.json() as ToolProvidingIntegrationOption[];
    }
    async getAgentById(agentId: number): Promise<AgentDetails> {
        const response = await this.authenticatedFetch(`${this.apiBase}/api/agents/${agentId}`);
        if (!response.ok) {
            throw new Error(`Failed to fetch agent: ${response.statusText}`);
        }
        return await response.json() as AgentDetails;
    }

    async createAgent(data: { name: string; agent_type: string; dataset: number; config: AgentConfig; tool_providing_integrations: number[] }): Promise<AgentDetails> {
        const response = await this.authenticatedFetch(`${this.apiBase}/api/agents`, {
            method: 'POST',
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new ApiError(`Failed to create agent: ${response.statusText}`, {
                data: errorData,
                status: response.status
            });
        }
        return await response.json() as AgentDetails;
    }

    async updateAgent(agentId: number, data: { name: string; agent_type: string; dataset: number; config: AgentConfig; tool_providing_integrations: number[] }): Promise<AgentDetails> {
        const response = await this.authenticatedFetch(`${this.apiBase}/api/agents/${agentId}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new ApiError(`Failed to update agent: ${response.statusText}`, {
                data: errorData,
                status: response.status
            });
        }
        return await response.json() as AgentDetails;

    }

    async deleteAgent(agentId: number): Promise<void> {
        const response = await this.authenticatedFetch(`${this.apiBase}/api/agents/${agentId}`, {
            method: 'DELETE',
        });
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new ApiError(`Failed to delete agent: ${response.statusText}`, {
                data: errorData,
                status: response.status
            });
        }
    }
}
