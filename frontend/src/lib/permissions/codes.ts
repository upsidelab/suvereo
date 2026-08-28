
export const PERMISSIONS = {
  DATA_SET:          { ADD: "data_set.add", CHANGE: "data_set.change", DELETE: "data_set.delete",
                       VIEW: "data_set.view" },
  AGENT:             { ADD: "agent.add", CHANGE: "agent.change", DELETE: "agent.delete", VIEW: "agent.view" },
  INTEGRATION:       { ADD: "integration.add", CHANGE: "integration.change", DELETE: "integration.delete",
                       VIEW: "integration.view", SYNC: "integration.sync" },
  CONVERSATION:      { CONVERSE: "conversation.converse", VIEW_ALL: "conversation.view_all" },
  AGENTIC_EXECUTION: { CREATE: "agentic_execution.create", VIEW_ALL: "agentic_execution.view_all" },
  USER:              { ADD: "user.add", CHANGE: "user.change", VIEW: "user.view" },
  SERVICE_ACCOUNT:   { ADD: "service_account.add", CHANGE: "service_account.change", VIEW: "service_account.view" },
  GLOBAL_ROLE:       { VIEW: "global_role.view", ADD: "global_role.add", CHANGE: "global_role.change",
                       DELETE: "global_role.delete", ASSIGN: "global_role.assign" },
  DATA_SET_ROLE:     { VIEW: "data_set_role.view", ADD: "data_set_role.add", CHANGE: "data_set_role.change",
                       DELETE: "data_set_role.delete", ASSIGN: "data_set_role.assign" },
  GROUP:             { VIEW: "group.view", ADD: "group.add", CHANGE: "group.change",
                       DELETE: "group.delete", ASSIGN: "group.assign" },
} as const;
