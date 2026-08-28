
export const PERMISSIONS = {
  DATASET:           { ADD: "dataset.add", CHANGE: "dataset.change", DELETE: "dataset.delete", VIEW: "dataset.view" },
  AGENT:             { ADD: "agent.add", CHANGE: "agent.change", DELETE: "agent.delete", VIEW: "agent.view" },
  INTEGRATION:       { ADD: "integration.add", CHANGE: "integration.change", DELETE: "integration.delete",
                       VIEW: "integration.view", SYNC: "integration.sync" },
  CONVERSATION:      { CONVERSE: "conversation.converse", VIEW_ALL: "conversation.view_all" },
  AGENTIC_EXECUTION: { CREATE: "agentic_execution.create", VIEW_ALL: "agentic_execution.view_all" },
  USER:              { ADD: "user.add", CHANGE: "user.change", VIEW: "user.view" },
  SERVICE_ACCOUNT:   { ADD: "service_account.add", CHANGE: "service_account.change", VIEW: "service_account.view" },
  GLOBAL_ROLE:       { VIEW: "global_role.view", ADD: "global_role.add", CHANGE: "global_role.change",
                       DELETE: "global_role.delete", ASSIGN: "global_role.assign" },
  DATASET_ROLE:      { VIEW: "dataset_role.view", ADD: "dataset_role.add", CHANGE: "dataset_role.change",
                       DELETE: "dataset_role.delete", ASSIGN: "dataset_role.assign" },
  GROUP:             { VIEW: "group.view", ADD: "group.add", CHANGE: "group.change",
                       DELETE: "group.delete", ASSIGN: "group.assign" },
} as const;
