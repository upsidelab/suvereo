
export const PERMISSIONS = {
  DATASET:           { ADD: "dataset.add", CHANGE: "dataset.change", DELETE: "dataset.delete", VIEW: "dataset.view" },
  AGENT:             { ADD: "agent.add", CHANGE: "agent.change", DELETE: "agent.delete", VIEW: "agent.view" },
  INTEGRATION:       { ADD: "integration.add", CHANGE: "integration.change", DELETE: "integration.delete",
                       VIEW: "integration.view", SYNC: "integration.sync" },
  CONVERSATION:      { CONVERSE: "conversation.converse", VIEW_ALL: "conversation.view_all" },
  AGENTIC_EXECUTION: { CREATE: "agentic_execution.create", VIEW_ALL: "agentic_execution.view_all" },
  USER:              { ADD: "user.add", CHANGE: "user.change", VIEW: "user.view" },
  SERVICE_ACCOUNT:   { ADD: "service_account.add", CHANGE: "service_account.change", VIEW: "service_account.view" },
  GROUP:             { VIEW: "group.view", ASSIGN: "group.assign" },
  DATASET_ROLE:      { VIEW: "dataset_role.view", ASSIGN: "dataset_role.assign" },
} as const;
