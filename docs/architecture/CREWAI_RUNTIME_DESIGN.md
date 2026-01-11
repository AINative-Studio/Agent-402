# CrewAI Runtime Architecture Design
## Issue 72: Implement CrewAI Runtime with 3 Agent Personas

**Document Version:** 1.0
**Date:** 2026-01-11
**Status:** Design Complete - Ready for Implementation

---

## 1. Executive Summary

This document defines the architecture for integrating CrewAI into the AINative Agent-402 platform to deliver autonomous, multi-agent fintech workflows. The design implements PRD Sections 4, 6, and 9 requirements for local-first CrewAI execution with persistent memory, DID-based agent identities, and integration with existing ZeroDB APIs.

### Key Decisions

1. **Local-First Execution**: CrewAI runs entirely locally for determinism and reproducibility
2. **ZeroDB Integration**: Agent profiles and memory leverage existing `/v1/public/{project_id}/agents` and `/v1/public/{project_id}/agent-memory` APIs
3. **Sequential Workflow**: Three agents (Analyst, Compliance, Transaction) execute tasks in strict sequence
4. **Tool Abstraction Ready**: Architecture prepared for Issue 74 tool integration via CrewAI's tool system
5. **Memory Persistence**: All agent decisions stored via agent_memory API for auditability

---

## 2. Requirements Analysis

### 2.1 Functional Requirements (PRD Section 4, 6, 9)

**From PRD Section 5 (Agent Personas):**
- 3 agents: Analyst, Compliance, Transaction
- Each agent has DID, role, goals, backstory
- Persistent memory stored in ZeroDB
- Local CrewAI execution for reproducibility

**From PRD Section 6 (CrewAI Runtime):**
- Agent orchestration via CrewAI
- Task sequencing
- Tool invocation (prepared for Issue 74)
- Structured outputs to ZeroDB

**From PRD Section 7 (ZeroDB Integration):**
- Agent profiles in `agents` collection
- Agent memory in `agent_memory` collection
- Compliance events in `compliance_events` collection
- X402 request ledger support

### 2.2 Non-Functional Requirements

1. **Determinism**: Same inputs produce same outputs
2. **Auditability**: All decisions logged to agent_memory
3. **Reproducibility**: Workflow can be replayed from logs
4. **Performance**: Local execution without external API dependencies
5. **Testability**: CI-compatible smoke tests

---

## 3. Proposed Architecture

### 3.1 System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     CrewAI Runtime Layer                     │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────┐    │
│  │  crew.py   │  │ tasks.py   │  │   run_crew.py      │    │
│  │ (Agents)   │  │ (Workflow) │  │   (Execution)      │    │
│  └─────┬──────┘  └─────┬──────┘  └─────────┬──────────┘    │
└────────┼───────────────┼───────────────────┼────────────────┘
         │               │                   │
         └───────────────┴───────────────────┘
                         │
         ┌───────────────▼────────────────────┐
         │    ZeroDB API Integration Layer     │
         │  ┌──────────────────────────────┐  │
         │  │  /v1/public/{project_id}/    │  │
         │  │    - agents (GET/POST)       │  │
         │  │    - agent-memory (GET/POST) │  │
         │  └──────────────────────────────┘  │
         └───────────────┬────────────────────┘
                         │
         ┌───────────────▼────────────────────┐
         │         ZeroDB Backend              │
         │  ┌─────────────┐  ┌──────────────┐ │
         │  │   agents    │  │agent_memory  │ │
         │  │  (table)    │  │   (table)    │ │
         │  └─────────────┘  └──────────────┘ │
         └─────────────────────────────────────┘
```

### 3.2 Agent Architecture

Each CrewAI agent maps to an agent profile in ZeroDB:

| CrewAI Agent | DID | Role | ZeroDB Profile |
|--------------|-----|------|----------------|
| Analyst Agent | `did:agent:analyst-001` | analyst | Created via POST /agents |
| Compliance Agent | `did:agent:compliance-001` | compliance | Created via POST /agents |
| Transaction Agent | `did:agent:transaction-001` | executor | Created via POST /agents |

### 3.3 Memory Flow

```
CrewAI Task Execution
        │
        ▼
Agent Decision Point
        │
        ▼
Format Memory Record
  - agent_id
  - run_id
  - memory_type (decision/context/result)
  - content
  - metadata
        │
        ▼
POST /v1/public/{project_id}/agent-memory
        │
        ▼
ZeroDB agent_memory Table
```

### 3.4 Data Flow Diagram

```
┌──────────────┐
│ run_crew.py  │
│ - init crew  │
│ - run tasks  │
└──────┬───────┘
       │
       ▼
┌──────────────────────┐
│  Task 1: Analysis    │
│  Agent: Analyst      │──┐
└──────────────────────┘  │
       │                  │
       ▼                  │
┌──────────────────────┐  │  Memory Store
│ Task 2: Compliance   │  ├──► POST /agent-memory
│ Agent: Compliance    │──┤    - decision
└──────────────────────┘  │    - context
       │                  │    - result
       ▼                  │
┌──────────────────────┐  │
│ Task 3: Transaction  │  │
│ Agent: Transaction   │──┘
└──────────────────────┘
       │
       ▼
   Final Output
```

---

## 4. Technology Stack

### 4.1 Dependencies

**Core CrewAI:**
```
crewai>=0.28.0         # Agent orchestration
crewai-tools>=0.1.0    # Tool abstraction (Issue 74)
langchain>=0.1.0       # LLM integration
```

**LLM Provider:**
```
openai>=1.0.0          # For GPT-4 (MVP)
# OR
anthropic>=0.8.0       # For Claude (alternative)
```

**Existing Stack:**
- FastAPI (existing)
- ZeroDB client (existing)
- Pydantic (existing)

### 4.2 Configuration

Environment variables (add to `.env`):
```bash
# CrewAI Configuration
OPENAI_API_KEY=sk-...              # LLM API key
CREWAI_TELEMETRY=false             # Disable telemetry for local-first

# Agent Configuration
DEFAULT_PROJECT_ID=proj_demo_u1_001
DEFAULT_RUN_ID=run_001
```

---

## 5. Implementation Design

### 5.1 File Structure

```
/Users/aideveloper/Agent-402/backend/
├── crew.py                 # Agent definitions
├── tasks.py                # Task definitions
├── run_crew.py             # Execution script
└── crewai_integration/     # (future: modular organization)
    ├── __init__.py
    ├── agents.py
    ├── tasks.py
    ├── tools.py           # Issue 74
    └── config.py
```

### 5.2 Agent Definitions (crew.py)

**Agent 1: Analyst Agent**
```python
Role: "Market Analyst"
Goal: "Analyze market conditions and evaluate transaction viability"
Backstory: "Expert financial analyst specializing in market data interpretation and risk assessment"
DID: "did:agent:analyst-001"
Tools: [] # Will be added in Issue 74
```

**Agent 2: Compliance Agent**
```python
Role: "Compliance Officer"
Goal: "Ensure all transactions meet regulatory requirements and KYC/KYT standards"
Backstory: "Regulatory compliance expert with deep knowledge of financial regulations and AML procedures"
DID: "did:agent:compliance-001"
Tools: [] # Will be added in Issue 74
```

**Agent 3: Transaction Agent**
```python
Role: "Transaction Executor"
Goal: "Execute approved transactions via X402 protocol with proper signatures"
Backstory: "Specialized in secure transaction execution and cryptographic signing using X402 protocol"
DID: "did:agent:transaction-001"
Tools: [] # Will be added in Issue 74 (x402.request tool)
```

### 5.3 Task Workflow (tasks.py)

**Sequential Task Flow:**

1. **Market Analysis Task**
   - Agent: Analyst
   - Input: Transaction request context
   - Output: Market viability assessment
   - Memory: Store analysis decision

2. **Compliance Check Task**
   - Agent: Compliance
   - Input: Analyst's assessment
   - Output: Compliance approval/rejection
   - Memory: Store compliance decision

3. **Transaction Execution Task**
   - Agent: Transaction
   - Input: Compliance approval
   - Output: X402 request result
   - Memory: Store execution result

### 5.4 Integration with agent_memory API

**Memory Storage Pattern:**

```python
async def store_agent_decision(
    agent_id: str,
    run_id: str,
    memory_type: str,
    content: str,
    metadata: dict
):
    """Store agent decision via ZeroDB API."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE}/v1/public/{PROJECT_ID}/agent-memory",
            headers={"X-API-Key": API_KEY},
            json={
                "agent_id": agent_id,
                "run_id": run_id,
                "memory_type": memory_type,
                "content": content,
                "metadata": metadata,
                "namespace": "crewai_runtime"
            }
        )
        return response.json()
```

**Memory Types by Agent:**

- **Analyst**: `memory_type="decision"` for analysis conclusions
- **Compliance**: `memory_type="decision"` for approval/rejection
- **Transaction**: `memory_type="result"` for execution outcome

---

## 6. Execution Flow

### 6.1 Initialization Sequence

```python
# 1. Load environment configuration
load_dotenv()
API_KEY = os.getenv("ZERODB_API_KEY")
PROJECT_ID = os.getenv("DEFAULT_PROJECT_ID")

# 2. Register agents via API (one-time setup)
analyst_profile = create_agent_profile(
    did="did:agent:analyst-001",
    role="analyst",
    name="Market Analyst Agent"
)

# 3. Instantiate CrewAI agents
analyst = Agent(
    role="Market Analyst",
    goal=analyst_profile.goal,
    backstory=analyst_profile.backstory,
    ...
)

# 4. Define tasks with agent assignments
tasks = [analysis_task, compliance_task, execution_task]

# 5. Create Crew
crew = Crew(
    agents=[analyst, compliance_agent, transaction_agent],
    tasks=tasks,
    process=Process.sequential
)
```

### 6.2 Execution Flow

```python
# Generate unique run_id
run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# Execute crew
result = crew.kickoff(inputs={
    "transaction_request": {...},
    "run_id": run_id,
    "project_id": PROJECT_ID
})

# Store final output
store_agent_decision(
    agent_id="transaction_agent",
    run_id=run_id,
    memory_type="result",
    content=result.output,
    metadata={"status": "complete"}
)
```

---

## 7. Quality Assurance

### 7.1 Testing Strategy

**Unit Tests:**
- Agent initialization
- Task configuration
- Memory storage integration

**Integration Tests:**
- Full crew execution
- API communication with ZeroDB
- Memory persistence verification

**Smoke Test (Required):**
```bash
python backend/run_crew.py
```

Expected output:
- 3 agents registered
- 3 tasks executed sequentially
- 3+ memory entries created
- Final result returned

### 7.2 Success Criteria

- [ ] CrewAI crew instantiates without errors
- [ ] 3 agents defined with proper DIDs, roles, goals
- [ ] Tasks execute in sequential order
- [ ] Each agent decision stored in agent_memory
- [ ] `run_crew.py` executes successfully
- [ ] Memory entries retrievable via GET /agent-memory
- [ ] No hardcoded secrets or credentials
- [ ] Execution deterministic (same inputs = same outputs)

---

## 8. Risk Assessment

### 8.1 Technical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM API rate limits | High | Add retry logic, fallback to mock responses for tests |
| CrewAI version changes | Medium | Pin exact versions in requirements.txt |
| Memory API failures | High | Implement graceful degradation, log locally as fallback |
| Non-deterministic LLM outputs | Medium | Use temperature=0, seed parameters where possible |

### 8.2 Integration Challenges

1. **Agent Profile Duplication**: If DID already exists in project
   - Solution: Check existing agents before creation, use GET /agents

2. **Memory Storage Failures**: Network issues, API errors
   - Solution: Retry with exponential backoff, local logging fallback

3. **Tool Integration (Issue 74)**: Tools not yet available
   - Solution: Prepare tool interface, use mock implementations for MVP

---

## 9. Implementation Roadmap

### Phase 1: Foundation (This Issue)
1. Update requirements.txt with CrewAI dependencies
2. Create crew.py with 3 agent definitions
3. Create tasks.py with sequential workflow
4. Create run_crew.py with basic execution
5. Integrate agent_memory API calls
6. Test basic execution flow

### Phase 2: Tool Integration (Issue 74)
1. Implement x402.request tool
2. Implement market data tool
3. Add tools to agents
4. Test tool invocation

### Phase 3: Demo Preparation (Issue 76)
1. Add realistic transaction scenarios
2. Implement replay functionality
3. Create demo script
4. Document for judges

---

## 10. Success Metrics

**Execution Metrics:**
- Crew startup time: < 5 seconds
- Task execution time: < 30 seconds total
- Memory storage latency: < 500ms per call

**Quality Metrics:**
- Code coverage: > 80%
- Test pass rate: 100%
- Documentation completeness: All APIs documented

**Demo Metrics:**
- Demo execution: < 5 minutes end-to-end
- Agent decisions: 100% auditable via API
- Workflow replay: Deterministic output

---

## 11. Open Questions

1. **LLM Provider**: OpenAI (GPT-4) vs Anthropic (Claude) for MVP?
   - **Decision**: Start with OpenAI for CrewAI compatibility, add Anthropic as option

2. **Mock vs Real LLM**: Should initial tests use mock LLM responses?
   - **Decision**: Real LLM for demo, mocks for CI tests

3. **Agent Profile Registration**: Auto-register on first run or manual setup?
   - **Decision**: Auto-register with idempotency check (409 conflict OK)

---

## 12. References

**PRD Sections:**
- Section 4: In-Scope (CrewAI orchestration)
- Section 5: Agent Personas (3 agents with DIDs)
- Section 6: CrewAI Runtime Integration
- Section 7: ZeroDB Integration (agent_memory)
- Section 9: System Architecture

**Existing APIs:**
- `/v1/public/{project_id}/agents` (app/api/agents.py)
- `/v1/public/{project_id}/agent-memory` (app/api/agent_memory.py)

**Related Issues:**
- Issue 74: Tool Integration (x402.request, market data)
- Issue 76: Demo Preparation (workflow showcase)

---

## Appendix A: Agent Configuration Schema

```yaml
agents:
  - id: analyst-001
    did: did:agent:analyst-001
    role: analyst
    name: Market Analyst Agent
    goal: Analyze market conditions and evaluate transaction viability
    backstory: Expert financial analyst specializing in market data interpretation
    tools: []

  - id: compliance-001
    did: did:agent:compliance-001
    role: compliance
    name: Compliance Officer Agent
    goal: Ensure regulatory compliance and KYC/KYT standards
    backstory: Regulatory compliance expert with deep AML knowledge
    tools: []

  - id: transaction-001
    did: did:agent:transaction-001
    role: executor
    name: Transaction Executor Agent
    goal: Execute approved transactions via X402 protocol
    backstory: Specialized in secure cryptographic transaction execution
    tools: []  # Will include x402.request in Issue 74
```

---

**Document Status:** APPROVED - Ready for Implementation
**Next Steps:** Begin Phase 1 implementation starting with requirements.txt update
