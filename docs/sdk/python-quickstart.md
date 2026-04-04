# Python SDK Quickstart

Get your first AINative agent running in 5 minutes using Python.

Built by AINative Dev Team | Refs #182

---

## Prerequisites

- Python 3.10+
- An AINative API key
- A project ID from the AINative dashboard

---

## Step 1: Install the SDK

```bash
pip install ainative-sdk
# or using poetry
poetry add ainative-sdk
```

---

## Step 2: Configure Authentication

Create a `.env` file:

```env
AINATIVE_API_KEY=your_api_key_here
AINATIVE_PROJECT_ID=proj_your_project_id
AINATIVE_BASE_URL=https://api.ainative.studio/v1/public
```

---

## Step 3: Create Your First Agent

```python
import asyncio
import os
from ainative import AINativeClient

client = AINativeClient(
    api_key=os.environ["AINATIVE_API_KEY"],
    project_id=os.environ["AINATIVE_PROJECT_ID"],
    base_url=os.environ.get("AINATIVE_BASE_URL"),
)

async def main():
    # Create an agent
    agent = await client.agents.create(
        name="my-first-agent",
        did="did:key:z6MkExample123",
        metadata={
            "role": "analyst",
            "capabilities": ["data-analysis", "report-generation"],
        },
    )

    print(f"Agent created: {agent['agent_id']}")
    print(f"Agent DID: {agent['did']}")

asyncio.run(main())
```

---

## Step 4: Submit a Task

```python
# Submit work for the agent
task = await client.tasks.create(
    agent_id=agent["agent_id"],
    description="Analyze quarterly revenue data",
    inputs={
        "dataset": "q4_2025_revenue.csv",
        "output_format": "summary",
    },
)

print(f"Task ID: {task['task_id']}")
print(f"Task status: {task['status']}")
```

---

## Step 5: Store Agent Memory

```python
# Store a memory for the agent
memory = await client.memory.store(
    agent_id=agent["agent_id"],
    content="User prefers concise summaries with bullet points.",
    memory_type="preference",
    metadata={
        "source": "user_interaction",
        "confidence": 0.95,
    },
)

print(f"Memory stored: {memory['memory_id']}")

# Search memory later
results = await client.memory.search(
    agent_id=agent["agent_id"],
    query="output format preferences",
    top_k=5,
)

for r in results:
    print(f"[{r['score']:.2f}] {r['content']}")
```

---

## Step 6: Work with Vectors

```python
# Store a vector embedding
await client.vectors.upsert(
    id="doc-001",
    text="Quarterly revenue increased 23% year-over-year.",
    namespace="financial-docs",
    metadata={
        "quarter": "Q4-2025",
        "type": "revenue",
    },
)

# Semantic search
result = await client.vectors.search(
    query="revenue growth",
    namespace="financial-docs",
    top_k=3,
    filters={"quarter": "Q4-2025"},
)

for r in result["results"]:
    print(f"Match: {r['id']} (score: {r['score']:.3f})")
    print(f"  Content: {r['metadata'].get('content', '')}")
```

---

## Step 7: Upload and Manage Files

```python
# Upload a file
with open("report.pdf", "rb") as f:
    file_result = await client.files.upload(
        file=f,
        filename="report.pdf",
        metadata={"type": "quarterly_report", "quarter": "Q4-2025"},
    )

file_id = file_result["file_id"]
print(f"File uploaded: {file_id}")

# Get a download URL
url_result = await client.files.get_url(file_id=file_id)
print(f"Download URL: {url_result['url']}")
```

---

## Complete Example

```python
import asyncio
import os
from ainative import AINativeClient

client = AINativeClient(
    api_key=os.environ["AINATIVE_API_KEY"],
    project_id=os.environ["AINATIVE_PROJECT_ID"],
)

async def run_agent():
    # 1. Create agent
    agent = await client.agents.create(
        name="financial-analyst",
        did="did:key:z6MkFinAgent",
        metadata={"role": "analyst"},
    )

    # 2. Submit task
    task = await client.tasks.create(
        agent_id=agent["agent_id"],
        description="Analyze portfolio performance",
        inputs={"portfolio_id": "port-001"},
    )

    # 3. Store decision context
    await client.memory.store(
        agent_id=agent["agent_id"],
        content="Portfolio analysis completed. Risk level: medium.",
        metadata={"task_id": task["task_id"]},
    )

    # 4. Embed analysis results
    await client.vectors.upsert(
        id=f"analysis-{task['task_id']}",
        text="Portfolio performance: +12.3% YTD, Sharpe ratio 1.8",
        namespace="analyses",
        metadata={"task_id": task["task_id"]},
    )

    print("Agent run complete!")
    print(f"Agent: {agent['agent_id']}")
    print(f"Task: {task['task_id']}")

asyncio.run(run_agent())
```

---

## Using httpx Directly (No SDK)

If you prefer to use the REST API directly:

```python
import httpx
import os

headers = {
    "X-API-Key": os.environ["AINATIVE_API_KEY"],
    "Content-Type": "application/json",
}

project_id = os.environ["AINATIVE_PROJECT_ID"]
base_url = f"https://api.ainative.studio/v1/public/{project_id}"

async with httpx.AsyncClient() as client:
    # Create an agent
    response = await client.post(
        f"{base_url}/agents",
        headers=headers,
        json={
            "name": "my-agent",
            "did": "did:key:z6MkExample",
            "metadata": {},
        },
    )
    response.raise_for_status()
    agent = response.json()
    print(f"Agent: {agent['agent_id']}")
```

---

## Next Steps

- [TypeScript Quickstart](./typescript-quickstart.md) — same concepts in TypeScript
- [API Reference](./api-reference.md) — complete method signatures
- [Examples](./examples.md) — more code examples
- [Hedera Plugin Guide](./hedera-plugin-guide.md) — add USDC payments via Hedera

Built by AINative Dev Team
