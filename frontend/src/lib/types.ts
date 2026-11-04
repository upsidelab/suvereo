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
  supports_oauth: boolean;
  oauth_field: string;
  oauth_refresh_field: string;
  config_schema: unknown;
};

export type Integration = {
  id: number;
  dataset: number;
  needs_reconnect?: boolean;
  type: string;
  name: string;
  integration_type_name: string | null;
  syncable: boolean;
  configurable: boolean;
  config: Record<string, unknown>;
  config_schema: unknown;
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
  permissions: string[];
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
}

export type Agent = {
  id: number;
  name: string;
  description: string;
  agent_type: string;
  agent_type_name: string;
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
};

export type GlobalRoleOption = {
  id: number;
  name: string;
  description: string;
};

export type GlobalRoleDetail = {
  id: number;
  name: string;
  description: string;
  permissions: string[];
};

export type GlobalRoleMember = {
  id: number;
  email: string;
  isServiceAccount: boolean;
};

export type GroupOption = {
  id: number;
  name: string;
  description: string;
  memberCount: number;
  globalRoleCount: number;
  dataSetRoleCount: number;
};

export type GroupDetail = GroupOption & {
  globalRoles: GlobalRoleOption[];
};

export type GroupMember = GlobalRoleMember;

export type DataSetRoleOption = {
  id: number;
  name: string;
  description: string;
};

export type DataSetRoleDetail = {
  id: number;
  name: string;
  description: string;
  permissions: string[];
};

export type DataSetMemberRoleAssignment = {
  id: number;
  role: DataSetRoleOption;
  user: GlobalRoleMember;
};

export type DataSetGroupRoleAssignment = {
  id: number;
  role: DataSetRoleOption;
  group: GroupOption;
};

export type DataSetAccess = {
  members: DataSetMemberRoleAssignment[];
  groups: DataSetGroupRoleAssignment[];
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
  required?: boolean;
};

export type ToolConfigSchema = {
  title: string;
  used_by: string[];
  fields: Record<string, ExtraArgDetail>;
};

export type AgentConfig = {
  agent_args?: Record<string, ExtraArgDetail>;
  prompt_input?: Record<string, ExtraArgDetail>;
  tools?: Record<string, Record<string, unknown>>;
};

export type AgentConfigSchema = {
  agent_args?: Record<string, ExtraArgDetail>;
  prompt_input?: Record<string, ExtraArgDetail>;
  tools?: Record<string, ToolConfigSchema>;
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
  user_email: string;
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

export type ToolProvidingIntegrationOption = {
  id: number;
  name: string;
};

export type AgentDetails = {
  id: number;
  name: string;
  description: string;
  file_upload: boolean;
  tool_providing_integrations: number[];
  config: AgentConfig;
  config_schema: AgentConfigSchema;
  dataset: number;
  agent_type: string;
  agent_type_name: string;
  created_at: string;
  updated_at: string;
};
