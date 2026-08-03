export interface PaginatedResult<T> {
  results: T[];
  count: number;
  next?: string | null;
  previous?: string | null;
}

export type EntityType = {
  slug: string;
  label: string;
  fields: { name: string; label: string }[];
};

export type IntegrationType = {
  type: string;
  name: string;
  integration_type_name: string;
  syncable: boolean;
  config_schema: unknown;
};

export type Integration = {
  id: number;
  dataset: number;
  type: string;
  name: string;
  integration_type_name: string | null;
  syncable: boolean;
  configurable: boolean;
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type DataSet = {
  id: number | undefined;
  name: string;
  languageModelProvider: string;
  languageModel: string;
  embeddingProvider: string;
  embeddingModel: string;
  embeddingVectorSize: number;
}

export type Product = {
  id: number;
  name: string;
  sku: string;
  slug: string;
  description: string;
  categories: string;
  properties: string;
  price: number;
}

export type Document = {
  id: number;
  url: string;
  title: string;
  content: string;
  isIndexed: boolean;
}

export type Account = {
  email: string;
  isAdmin: boolean;
  permissions: string[];
}

export type User = {
  id: number;
  email: string;
  isActive: boolean;
  isAdmin: boolean;
  groupIds: number[];
}

export type DataSetAccessGrant = {
  targetType: "user" | "group";
  targetId: number;
  targetLabel: string;
  role: string | null;
};

export type DatasetRoleOption = {
  id: number;
  name: string;
  isSystem: boolean;
};

export type GroupOption = {
  id: number;
  name: string;
};

export type GroupMember = {
  id: number;
  email: string;
  isServiceAccount: boolean;
};

export type PermissionOption = {
  id: number;
  codename: string;
  name: string;
  description: string;
};

export type GroupDetail = {
  id: number;
  name: string;
  permissionIds: number[];
  isSystem: boolean;
};

export type DatasetRoleDetail = {
  id: number;
  name: string;
  permissionIds: number[];
  isSystem: boolean;
};

export type Agent = {
  id: number;
  name: string;
  description: string;
  agent_type: string;
  created_at: string;
  updated_at: string;
  deleted_at: string;
  corrupted: boolean;
};

export type Conversation = {
  id: number;
  started_at: Date;
  model: string;
  dimensions: number;
  data_set: string;
  summary?: string;
  agent: Agent;
  history?: Message[];
  is_execution_conversation: boolean;
  user_email: string;
}

export type Message = {
  id: number;
  type: string;
  text: string;
}

export type ServiceAccount = {
  id: number;
  email: string;
  isActive: boolean;
  isAdmin: boolean;
  dateCreated: string;
  dataSetIds: number[];
  groupIds: number[];
};

export type ProvidersConfig = {
  languageModelProviders: string[];
  embeddingProviders: string[];
}

export type EmbeddingModelsConfig = {
  models: string[];
  vectorSizeConstraints: Record<string, number[]>;
}

export type TypeInfo = {
  container: string | null;
  inner_type?: string;
  key_type?: string;
  value_type?: string;
  nullable?: boolean;
};

export type ExtraArgDetail = {
  type: TypeInfo;
  description?: string | null;
  title?: string | null;
};

export type AgentConfig = {
  agent_args?: Record<string, ExtraArgDetail>;
  prompt_input?: Record<string, ExtraArgDetail>;
  prompt_extension?: Record<string, ExtraArgDetail>;
  tools?: Array<Record<string, ExtraArgDetail>>;
};

export type ConversationFile = {
  id: number;
  filename: string;
  file_url: string;
  content_type: string;
};

export type AgenticExecution = {
  id: number;
  agent: number;
  execution_key: string;
  conversation: number;
  status: 'pending' | 'in_progress' | 'finished' | 'failed';
  input: Record<string, unknown>;
  result: Record<string, unknown> | null;
  failure_code: string | null;
  failure_explanation: string | null;
  celery_task_id: string | null;
  started_at: string;
  finished_at: string | null;
  duration_seconds: number | null;
};

export type AgenticExecutionDetail = AgenticExecution & {
  files: ConversationFile[];
};

export type ExecutionDefinition = {
  key: string;
  name: string;
  description: string | null;
  input_schema: Record<string, unknown>;
};

export type AgentDetails = {
  id: number;
  name: string;
  description: string;
  file_upload: boolean;
  config: AgentConfig;
  dataset: number;
  agent_type: string;
  created_at: string;
  updated_at: string;
};
