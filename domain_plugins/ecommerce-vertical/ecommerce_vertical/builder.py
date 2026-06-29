from agent.core.builder import AgentBuilder
from ecommerce_vertical.injector import EcommerceInjector


class EcommerceAgentBuilder(AgentBuilder):
    """AgentBuilder that wires an EcommerceInjector with product and document retrievers."""

    def _build_injector(self) -> EcommerceInjector:
        chat_history = self._build_chat_history()
        memory_compactor = self._build_memory_compactor(chat_history)
        return EcommerceInjector(
            repositories=self._repositories,
            chat_history=chat_history,
            memory_compactor=memory_compactor,
            tool_scratchpad=self._tool_scratchpad,
            data_set_id=self._data_set_id,
        )
