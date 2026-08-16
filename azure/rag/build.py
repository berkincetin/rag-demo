"""Assemble the agent from a built index.

Replaces src/rag/cli.py's build_agent. Two things it deliberately drops:
provider resolution (there is one provider) and the session credential store
(the key comes from a Container Apps secret via the environment).
"""

from azure.rag.agent import Agent
from azure.rag.config import AzureConfig
from azure.rag.embedder import AzureOpenAIEmbedder
from azure.rag.index import load_index
from azure.rag.llm_client import AzureOpenAIClient
from azure.rag.metrics import MetricsStore
from azure.rag.retriever import Retriever
from azure.rag.tools import ToolBox


def build_agent(config: AzureConfig | None = None) -> Agent:
    """Wire retriever, tools and LLM into an agent."""
    config = config or AzureConfig.load()

    embedder = AzureOpenAIEmbedder(config)
    index = load_index(config.storage_dir)
    retriever = Retriever(
        index=index,
        embedder=embedder,
        min_cosine=config.min_cosine,
        min_bm25=config.min_bm25,
    )
    return Agent(
        retriever,
        ToolBox(retriever),
        AzureOpenAIClient(config),
        config.max_tool_turns,
        metrics=MetricsStore(config.storage_dir / "metrics.db"),
    )
