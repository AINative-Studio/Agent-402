# SDK Examples

Working code examples for common AINative Agent-402 use cases.

Built by AINative Dev Team | Refs #182

---

## Example 1: Create an Agent

```python
# Python
import asyncio
import httpx
import os

API_KEY = os.environ["AINATIVE_API_KEY"]
PROJECT_ID = os.environ["AINATIVE_PROJECT_ID"]
BASE_URL = f"https://api.ainative.studio/v1/public/{PROJECT_ID}"
HEADERS = {"X-API-Key": API_KEY}

async def create_agent():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/agents",
            headers=HEADERS,
            json={
                "name": "compliance-agent",
                "did": "did:key:z6MkComplianceAgent",
                "metadata": {
                    "role": "compliance",
                    "version": "1.0.0",
                },
            },
        )
        response.raise_for_status()
        agent = response.json()
        print(f"Created agent: {agent['agent_id']}")
        return agent

asyncio.run(create_agent())
```

```typescript
// TypeScript
import axios from 'axios';

const API_KEY = process.env.AINATIVE_API_KEY!;
const PROJECT_ID = process.env.AINATIVE_PROJECT_ID!;
const BASE_URL = `https://api.ainative.studio/v1/public/${PROJECT_ID}`;
const headers = { 'X-API-Key': API_KEY };

async function createAgent() {
  const response = await axios.post(
    `${BASE_URL}/agents`,
    {
      name: 'compliance-agent',
      did: 'did:key:z6MkComplianceAgent',
      metadata: { role: 'compliance', version: '1.0.0' },
    },
    { headers }
  );

  const agent = response.data;
  console.log(`Created agent: ${agent.agent_id}`);
  return agent;
}

createAgent().catch(console.error);
```

---

## Example 2: Submit a Task

```python
# Python
async def submit_task(agent_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/agents/{agent_id}/tasks",
            headers=HEADERS,
            json={
                "description": "Review transaction #TX-2026-001 for compliance",
                "inputs": {
                    "transaction_id": "TX-2026-001",
                    "amount": "50000",
                    "currency": "USD",
                    "counterparty": "Acme Corp",
                },
                "priority": "high",
            },
        )
        response.raise_for_status()
        task = response.json()
        print(f"Task submitted: {task['task_id']}, status: {task['status']}")
        return task
```

---

## Example 3: Store and Search Memory

```python
# Python — Store decision context in agent memory
async def store_and_search_memory(agent_id: str):
    async with httpx.AsyncClient() as client:

        # Store memory
        store_response = await client.post(
            f"{BASE_URL}/agent-memory",
            headers=HEADERS,
            json={
                "agent_id": agent_id,
                "content": (
                    "Transaction TX-2026-001 flagged for review. "
                    "Counterparty Acme Corp has no prior risk events. "
                    "Amount $50,000 exceeds standard threshold of $10,000."
                ),
                "memory_type": "decision",
                "metadata": {
                    "transaction_id": "TX-2026-001",
                    "risk_level": "medium",
                },
            },
        )
        store_response.raise_for_status()
        memory = store_response.json()
        print(f"Memory stored: {memory['memory_id']}")

        # Search memory
        search_response = await client.post(
            f"{BASE_URL}/agent-memory/search",
            headers=HEADERS,
            json={
                "agent_id": agent_id,
                "query": "high value transaction risk",
                "top_k": 5,
            },
        )
        search_response.raise_for_status()
        results = search_response.json()

        print(f"\nFound {results['total']} related memories:")
        for r in results["results"]:
            print(f"  [{r['score']:.2f}] {r['content'][:80]}...")
```

---

## Example 4: Vector Embeddings

```python
# Python — Embed documents and search semantically
async def vector_search_example():
    async with httpx.AsyncClient() as client:

        # Batch upsert documents
        documents = [
            {
                "id": "policy-001",
                "text": "All transactions above $10,000 require dual approval.",
                "namespace": "compliance-policies",
                "metadata": {"category": "approval", "effective_date": "2026-01-01"},
            },
            {
                "id": "policy-002",
                "text": "Counterparties in high-risk jurisdictions require enhanced due diligence.",
                "namespace": "compliance-policies",
                "metadata": {"category": "due-diligence", "effective_date": "2026-01-01"},
            },
            {
                "id": "policy-003",
                "text": "Unusual transaction patterns must be reported within 24 hours.",
                "namespace": "compliance-policies",
                "metadata": {"category": "reporting", "effective_date": "2026-01-01"},
            },
        ]

        for doc in documents:
            resp = await client.post(
                f"{BASE_URL}/vectors/upsert",
                headers=HEADERS,
                json=doc,
            )
            resp.raise_for_status()
            print(f"Upserted: {doc['id']}")

        # Semantic search
        search_resp = await client.post(
            f"{BASE_URL}/vectors/search",
            headers=HEADERS,
            json={
                "query": "large payment approval requirements",
                "namespace": "compliance-policies",
                "top_k": 3,
                "min_score": 0.6,
            },
        )
        search_resp.raise_for_status()
        results = search_resp.json()

        print("\nRelevant policies:")
        for r in results["results"]:
            print(f"  [{r['score']:.3f}] {r['id']}: {r['metadata'].get('content', '')[:60]}...")
```

---

## Example 5: File Upload and Download

```python
# Python — Upload a compliance report PDF
import io

async def file_operations():
    async with httpx.AsyncClient() as client:

        # Upload file
        pdf_content = b"%PDF-1.4 fake pdf content for example"
        files = {"file": ("compliance_report.pdf", io.BytesIO(pdf_content), "application/pdf")}
        data = {
            "filename": "compliance_report.pdf",
            "metadata": '{"report_type": "quarterly", "quarter": "Q1-2026"}',
        }

        upload_resp = await client.post(
            f"{BASE_URL}/files",
            headers={"X-API-Key": API_KEY},  # No Content-Type — multipart handles it
            files=files,
            data=data,
        )
        upload_resp.raise_for_status()
        file_info = upload_resp.json()
        file_id = file_info["file_id"]
        print(f"Uploaded: {file_id}")

        # Get download URL
        url_resp = await client.get(
            f"{BASE_URL}/files/{file_id}/url",
            headers=HEADERS,
        )
        url_resp.raise_for_status()
        url_info = url_resp.json()
        print(f"Download URL: {url_info['url']}")
        print(f"Expires: {url_info['expires_at']}")
```

---

## Example 6: Hedera USDC Payment

```python
# Python — Pay an agent for completing a task via Hedera HTS
async def pay_agent_via_hedera(agent_id: str, task_id: str, recipient_account: str):
    async with httpx.AsyncClient() as client:

        # Step 1: Create Hedera wallet for the agent
        wallet_resp = await client.post(
            f"{BASE_URL}/hedera/wallets",
            headers=HEADERS,
            json={"agent_id": agent_id, "initial_balance": 10},
        )
        wallet_resp.raise_for_status()
        wallet = wallet_resp.json()
        account_id = wallet["account_id"]
        print(f"Wallet created: {account_id}")

        # Step 2: Associate USDC token (REQUIRED before receiving HTS tokens)
        assoc_resp = await client.post(
            f"{BASE_URL}/hedera/wallets/{account_id}/associate-usdc",
            headers=HEADERS,
        )
        assoc_resp.raise_for_status()
        print(f"USDC token associated: {assoc_resp.json()['status']}")

        # Step 3: Send payment (5 USDC = 5,000,000 smallest units)
        payment_resp = await client.post(
            f"{BASE_URL}/hedera/payments",
            headers=HEADERS,
            json={
                "agent_id": agent_id,
                "amount": 5_000_000,  # 5 USDC
                "recipient": recipient_account,
                "task_id": task_id,
                "memo": f"Payment for task {task_id}",
            },
        )
        payment_resp.raise_for_status()
        payment = payment_resp.json()
        print(f"Payment sent: {payment['payment_id']}")
        print(f"Transaction: {payment['transaction_id']}")

        # Step 4: Verify settlement (Hedera targets sub-3 second finality)
        verify_resp = await client.post(
            f"{BASE_URL}/hedera/payments/verify",
            headers=HEADERS,
            json={"transaction_id": payment["transaction_id"]},
        )
        verify_resp.raise_for_status()
        verification = verify_resp.json()

        if verification["settled"]:
            print(f"Payment settled at: {verification['consensus_timestamp']}")
        else:
            print(f"Payment pending: {verification['status']}")

        # Step 5: Get full receipt
        receipt_resp = await client.get(
            f"{BASE_URL}/hedera/payments/{payment['payment_id']}/receipt",
            headers=HEADERS,
        )
        receipt_resp.raise_for_status()
        receipt = receipt_resp.json()
        print(f"Receipt hash: {receipt['hash']}")
```

---

## Example 7: Full Agent Workflow

```python
# Python — Complete agent lifecycle: create, work, pay
async def full_agent_workflow():
    print("=== AINative Agent-402 Full Workflow ===\n")

    async with httpx.AsyncClient() as client:

        # 1. Create agent
        print("1. Creating agent...")
        agent_resp = await client.post(
            f"{BASE_URL}/agents",
            headers=HEADERS,
            json={
                "name": "invoice-processor",
                "did": "did:key:z6MkInvoiceAgent",
                "metadata": {"role": "finance", "capabilities": ["invoice-processing"]},
            },
        )
        agent = agent_resp.json()
        agent_id = agent["agent_id"]
        print(f"   Agent: {agent_id}\n")

        # 2. Submit task
        print("2. Submitting task...")
        task_resp = await client.post(
            f"{BASE_URL}/agents/{agent_id}/tasks",
            headers=HEADERS,
            json={
                "description": "Process invoice INV-2026-042",
                "inputs": {"invoice_id": "INV-2026-042", "amount": "12500.00"},
            },
        )
        task = task_resp.json()
        task_id = task["task_id"]
        print(f"   Task: {task_id}\n")

        # 3. Store processing memory
        print("3. Storing decision memory...")
        await client.post(
            f"{BASE_URL}/agent-memory",
            headers=HEADERS,
            json={
                "agent_id": agent_id,
                "content": "Invoice INV-2026-042 processed. Vendor verified, amount approved.",
                "metadata": {"task_id": task_id, "invoice_id": "INV-2026-042"},
            },
        )
        print("   Memory stored\n")

        # 4. Search compliance policies
        print("4. Checking compliance policies...")
        search_resp = await client.post(
            f"{BASE_URL}/vectors/search",
            headers=HEADERS,
            json={
                "query": "invoice approval requirements",
                "namespace": "compliance-policies",
                "top_k": 2,
            },
        )
        results = search_resp.json().get("results", [])
        print(f"   Found {len(results)} relevant policies\n")

        # 5. Create Hedera wallet and pay
        print("5. Setting up Hedera wallet...")
        wallet_resp = await client.post(
            f"{BASE_URL}/hedera/wallets",
            headers=HEADERS,
            json={"agent_id": agent_id, "initial_balance": 10},
        )
        wallet = wallet_resp.json()
        account_id = wallet["account_id"]

        # Associate USDC
        await client.post(
            f"{BASE_URL}/hedera/wallets/{account_id}/associate-usdc",
            headers=HEADERS,
        )
        print(f"   Wallet ready: {account_id}\n")

        # Pay for the task (12.50 USDC = 12,500,000 smallest units)
        print("6. Sending USDC payment...")
        pay_resp = await client.post(
            f"{BASE_URL}/hedera/payments",
            headers=HEADERS,
            json={
                "agent_id": agent_id,
                "amount": 12_500_000,
                "recipient": "0.0.99999",
                "task_id": task_id,
                "memo": f"Invoice {task_id} payment",
            },
        )
        payment = pay_resp.json()
        print(f"   Payment: {payment['payment_id']}")
        print(f"   Status: {payment['status']}")
        print(f"   TX: {payment['transaction_id']}\n")

        print("=== Workflow Complete ===")

asyncio.run(full_agent_workflow())
```

Built by AINative Dev Team
