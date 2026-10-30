# Prompts

The system prompt defines an [agent's](/docs/concepts#agent) role and behavior: what it does, which [tools](/docs/concepts#tool) it uses and how it answers.

## Configuration

The agent system prompt is a plain string declared as the `SYSTEM_PROMPT` class variable of the agent, which is required. The framework passes it on as `AgentConfig.system_prompt`, see [Agent Configuration](/docs/agents/agent-config):

```python
# prompt.py (conventional location)
ARTICLES_SYSTEM_PROMPT = """
Answer from the articles you find with search_articles.
"""
```

```python
# agent.py
class ArticlesAgent(BaseToolCallingAgent):
    NAME = "Articles"
    AGENT_KEY = "articles-agent"
    SYSTEM_PROMPT = ARTICLES_SYSTEM_PROMPT
    TOOLS = [LLMToolConfig(tool_class=SearchArticlesTool)]
```

An [agentic execution](/docs/concepts#agentic-execution) can use a different prompt by declaring its own `SYSTEM_PROMPT` on its definition, see [Agentic Execution](/docs/agents/agentic-execution#execution-configuration).

## Template Variables

The system prompt can contain `{variable}` placeholders. `_get_system_prompt_variables()` returns the variables that fill them, and it is called each time the prompt is built.

By default it returns the fields of the agent's `PROMPT_INPUT` by name, filled with the values entered in the UI, see [Agent Classes](/docs/agents/agent-classes#class-variables). With this `PROMPT_INPUT` and prompt, `{output_format}` needs no override:

```python
class PromptInputSchema(RequiredFieldsModel):
    output_format: str = Field(title="Output Format", description="Expected response format")

SYSTEM_PROMPT = """
You answer questions about articles. Format every answer as {output_format}.
"""
```

To rename variables or compute others, override the method in the agent class and call `super()` to keep the defaults:

```python
SYSTEM_PROMPT = """
You answer questions about articles. Today is {today}. Format every answer as {output_format}.
"""

class ArticlesAgent(BaseToolCallingAgent):
    def _get_system_prompt_variables(self) -> dict:
        return {**super()._get_system_prompt_variables(), "today": date.today().isoformat()}
```

Agents with a static prompt and no `PROMPT_INPUT` fields need no override.
