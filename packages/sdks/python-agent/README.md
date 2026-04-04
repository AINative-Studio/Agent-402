# ainative-agent

Python SDK for the AINative platform. Provides async access to agent, memory, vector, and file operations.

Built by AINative Dev Team.

## Installation

```bash
pip install ainative-agent
```

## Quick Start

```python
import asyncio
from ainative_agent import AINativeSDK

async def main():
    async with AINativeSDK(api_key="your-api-key") as sdk:
        # Create an agent
        agent = await sdk.agents.create({
            "name": "my-agent",
            "role": "assistant",
            "description": "A helpful assistant"
        })

        # Store a memory
        memory = await sdk.memory.remember("Important context", namespace="default")

        # Recall memories
        results = await sdk.memory.recall("context", limit=10)

        # Upsert a vector
        vector = await sdk.vectors.upsert(
            embedding=[0.1] * 384,
            metadata={"document": "sample text", "model": "BAAI/bge-small-en-v1.5"}
        )

asyncio.run(main())
```

## Authentication

```python
# API key authentication
sdk = AINativeSDK(api_key="sk-...")

# JWT authentication
sdk = AINativeSDK(jwt="eyJ...")
```

## Agents

```python
agent = await sdk.agents.create({"name": "agent1", "role": "researcher"})
agent = await sdk.agents.get("agent_id")
agents = await sdk.agents.list()
agent = await sdk.agents.update("agent_id", {"name": "updated-name"})
await sdk.agents.delete("agent_id")
```

## Tasks

```python
task = await sdk.tasks.create(
    description="Research topic X",
    agent_types=["researcher"],
    config={"max_steps": 10}
)
task = await sdk.tasks.get("task_id")
tasks = await sdk.tasks.list(status="pending")
```

## Memory

```python
memory = await sdk.memory.remember("content", namespace="default")
results = await sdk.memory.recall("query", limit=5)
await sdk.memory.forget("mem_id")
reflection = await sdk.memory.reflect("entity_id")

# Graph operations
await sdk.memory.graph.add_entity({"id": "e1", "type": "person", "name": "Alice"})
await sdk.memory.graph.add_edge({"source": "e1", "target": "e2", "relation": "knows"})
path = await sdk.memory.graph.traverse("e1", depth=2)
results = await sdk.memory.graph.graphrag("Who knows Alice?")
```

## Vectors

```python
vector = await sdk.vectors.upsert(
    embedding=[0.1] * 384,
    metadata={"document": "text", "model": "BAAI/bge-small-en-v1.5"}
)
results = await sdk.vectors.search("query text", limit=10)
await sdk.vectors.delete("vec_id")
```

## Files

```python
file = await sdk.files.upload(b"file content", filename="data.txt")
content = await sdk.files.download("file_id")
files = await sdk.files.list(limit=20)
```
