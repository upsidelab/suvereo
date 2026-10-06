import { FeedbackData, TaskHandle } from "@/lib/api.ts";
import { BaseApiClient } from "@/lib/api/base.ts";
import { Conversation, Message, PaginatedResult } from "@/lib/types.ts";
import { ApiError } from "@/lib/api-error.ts";

export type CreateConversationPayload = {
  agent_id: number;
}

export type CreateMessagePayload = {
  question_message: string;
  data_set_id: number;
  streaming: boolean;
  file_ids?: number[];
}

export type SupportedFileTypes = {
  supported_extensions: string[];
}

export type FileUploadResponse = {
  task_id: string;
}

export type TaskStatusResponse<TResult> = {
  task_id: string;
  status: string;
  result?: TResult;
}

export type FileUploadStatusResponse = TaskStatusResponse<{
  file_id?: number;
  error?: string;
}>

export type MessageTaskStatusResponse = TaskStatusResponse<{
  conversation_id?: number;
  message_id?: number;
  error?: string;
}>

export class ConversationsApiClient extends BaseApiClient {
  async getWebSocketTicket(): Promise<string> {
    const response = await this.authenticatedFetch(`${this.apiBase}/api/auth/ws_ticket`, { method: "POST" });

    if (!response.ok) {
      throw new Error(`Failed to get WebSocket ticket: ${response.statusText}`);
    }

    const { ticket } = await response.json() as { ticket: string };
    return ticket;
  }

  async getConversations(dataSetId: number, page: number = 1): Promise<PaginatedResult<Conversation>> {
    const response = await this.authenticatedFetch(`${this.apiBase}/api/conversations?data_set_id=${dataSetId}&page=${page}`);
    return await response.json() as Promise<PaginatedResult<Conversation>>;
  }

  async createConversation(agentId: number): Promise<number> {
    const requestBody: CreateConversationPayload = {
      agent_id: agentId
    };

    const response = await this.authenticatedFetch(`${this.apiBase}/api/conversations`, {
      method: "POST",
      body: JSON.stringify(requestBody)
    });

    if (!response.ok) {
      throw new Error(`Failed to create conversation: ${response.statusText}`);
    }

    const { id } = await response.json();
    return id;
  }

  async sendMessage(conversationId: number, dataSetId: number, message: string, streaming: boolean, fileIds?: number[]): Promise<TaskHandle> {
    const requestBody: CreateMessagePayload = {
      "question_message": message,
      "data_set_id": dataSetId,
      streaming,
      file_ids: fileIds
    }

    const response = await this.authenticatedFetch(`${this.apiBase}/api/conversations/${conversationId}`, {
      method: "POST",
      body: JSON.stringify(requestBody)
    });

    if (!response.ok) {
      throw new Error(`Failed to enqueue task: ${response.statusText}`);
    }

    return await response.json() as TaskHandle;
  }

  async getTaskStatus(taskHandle: TaskHandle): Promise<MessageTaskStatusResponse> {
    const response = await this.authenticatedFetch(`${this.apiBase}/api/message-push-status/${taskHandle.task_id}`);
    return await response.json() as MessageTaskStatusResponse;
  }

  async fetchResponseMessage(conversationId: number, taskHandle: TaskHandle): Promise<Message | null> {
    const { status: taskStatus } = await this.getTaskStatus(taskHandle);

    if (taskStatus === "SUCCESS" || taskStatus === "FAILURE") {
      const conversation = await this.getConversation(conversationId);
      return conversation.history![conversation.history!.length - 1];
    }

    return null;
  }

  async getConversation(conversation_id: number | null): Promise<Conversation> {
    const response = await this.authenticatedFetch(`${this.apiBase}/api/conversations/${conversation_id}`);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(`Failed to get conversation: ${response.statusText}`, {
        data: errorData,
        status: response.status,
      });
    }

    return await response.json();
  }

  async updateMessageFeedback(messageId: number | null, feedbackData: FeedbackData): Promise<void> {
    const response = await this.authenticatedFetch(`${this.apiBase}/api/messages/${messageId}/feedback/`, {
      method: 'PATCH',
      body: JSON.stringify(feedbackData),
    });

    if (!response.ok) {
      throw new Error(`Could not update feedback for message ID ${messageId}`);
    }

    return await response.json() as Promise<void>;
  }

  async getSupportedFileTypes(): Promise<SupportedFileTypes> {
    try {
      const response = await this.authenticatedFetch(`${this.apiBase}/api/supported-file-types/`, {
        method: 'GET',
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json() as SupportedFileTypes;
    } catch (error) {
      if (error instanceof Error) {
        throw new Error(`Failed to get supported file types: ${error.message}`);
      } else {
        throw new Error("Failed to get supported file types: An unknown error occurred.");
      }
    }
  }

  async uploadFile(conversationId: number, file: File): Promise<FileUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await this.authenticatedFetch(`${this.apiBase}/api/conversations/${conversationId}/upload/`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Failed to start file upload: ${response.status} ${response.statusText}`);
    }

    return await response.json() as FileUploadResponse;
  }

  async getFileUploadStatus(taskId: string): Promise<FileUploadStatusResponse> {
    const response = await this.authenticatedFetch(`${this.apiBase}/api/file-upload-status/${taskId}/`);

    if (!response.ok) {
      throw new Error('Failed to check upload status');
    }

    return await response.json() as FileUploadStatusResponse;
  }
}
