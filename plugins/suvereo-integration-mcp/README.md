# Suvereo Integration MCP

This Suvereo plugin lets a dataset connect to one or more MCP (Model Context Protocol)
servers over the network (SSE or streamable HTTP). Once a server is connected, each of the
dataset's agents can select it under **Tool sources** — any agent that selects it and can
answer asynchronously picks up its tools, and agents with no server selected are unaffected.
