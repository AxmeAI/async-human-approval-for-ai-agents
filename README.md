# Async Human Approval for AI Agents

Stop losing hours to blocked agents. AXME adds async human approvals with reminders, escalation, and timeout to any AI agent.

Your AI agent asks a question. The human is at lunch. Other solutions: agent blocks forever. AXME: agent waits patiently. Reminder in 5 min. Escalation in 30 min. Human answers from phone 2 hours later. Agent continues automatically.

> **Alpha** - Built with [AXME](https://github.com/AxmeAI/axme) (AXP Intent Protocol).
> [cloud.axme.ai](https://cloud.axme.ai) - [hello@axme.ai](mailto:hello@axme.ai)

---

## The Problem

Every AI agent framework has the same blind spot: what happens when the agent needs a human and the human isn't there?

```
Agent: "Should I delete the staging database?"
Human: (at lunch)
Agent: (blocks)
Agent: (still blocking)
Agent: (30 minutes later, still blocking)
Agent: (timeout, session lost, start over)
```

What breaks:
- **Agents block forever** - no timeout, no fallback, just frozen
- **No reminders** - human forgets, agent waits indefinitely
- **No escalation** - if person A doesn't respond, nobody else gets notified
- **Session dies** - connection drops, approval state is lost
- **Only yes/no** - no structured responses, forms, or review workflows
- **Framework lock-in** - every framework implements HITL differently (or not at all)

---

## The Solution: Async Approval with Lifecycle

```
Agent -> send_intent("needs_approval", remind=5min, timeout=8h)

5 min later:  AXME sends reminder (Slack push / email)
30 min later: AXME escalates to backup reviewer
2 hours later: Human approves from phone

Agent <- resumes with approval result
```

The agent doesn't poll. The agent doesn't block. The agent suspends durably and resumes when the human responds - whether that's 5 seconds or 5 hours later.

---

## Quick Start

```bash
pip install axme
export AXME_API_KEY="your-key"   # Get one: axme login
```

```python
from axme import AxmeClient, AxmeClientConfig
import os

client = AxmeClient(AxmeClientConfig(api_key=os.environ["AXME_API_KEY"]))

# Agent requests async approval - with reminder and timeout
intent_id = client.send_intent({
    "intent_type": "intent.data.export_approval.v1",
    "to_agent": "agent://myorg/production/data-analyst",
    "payload": {
        "dataset": "customers_q1_2026",
        "destination": "analytics-warehouse",
        "pii_detected": True,
        "columns_flagged": ["email", "phone", "ssn_last4"],
    },
})

print(f"Approval requested: {intent_id}")

# Agent suspends durably. No polling. No blocking.
# AXME handles: reminder in 5 min, escalation in 30 min, timeout in 8 hours.
result = client.wait_for(intent_id)
print(f"Decision: {result['status']}")
```

---

## Before / After

### Before: DIY Async Approval (200+ lines)

```python
# 1. Send notification
def request_approval(reviewer, context):
    token = secrets.token_urlsafe(32)
    db.insert("approvals", token=token, status="pending", reviewer=reviewer)
    send_slack_message(reviewer, f"Approval needed: {context}\n{approve_url(token)}")
    schedule_reminder(token, delay=300)      # custom reminder scheduler
    schedule_escalation(token, delay=1800)   # custom escalation logic
    schedule_timeout(token, delay=28800)     # custom timeout handler
    return token

# 2. Reminder scheduler (runs on cron or background thread)
def reminder_job():
    for row in db.query("SELECT * FROM approvals WHERE status='pending' AND remind_at < now()"):
        send_slack_message(row.reviewer, f"Reminder: approval still pending")
        db.update("approvals", row.id, remind_at=now() + timedelta(minutes=30))

# 3. Escalation handler
def escalation_job():
    for row in db.query("SELECT * FROM approvals WHERE status='pending' AND escalate_at < now()"):
        backup = get_backup_reviewer(row.reviewer)
        send_slack_message(backup, f"Escalation: {row.reviewer} hasn't responded")

# 4. Webhook callback
@app.post("/webhooks/approval")
async def handle_approval(req):
    verify_token(req.json["token"])
    db.update("approvals", req.json["token"], status=req.json["decision"])

# 5. Polling loop in the agent
async def wait_for_approval(token, timeout=28800):
    for _ in range(timeout // 5):
        row = db.get("approvals", token)
        if row["status"] != "pending":
            return row
        await asyncio.sleep(5)  # 5,760 polls per 8 hours
    raise TimeoutError()

# Plus: token expiry, audit logging, retry on Slack failure,
# DB cleanup, orphan detection, backup reviewer config...
```

### After: AXME Async Approval (4 lines)

```python
intent_id = client.send_intent({
    "intent_type": "intent.data.export_approval.v1",
    "to_agent": "agent://myorg/production/data-analyst",
    "payload": {"dataset": "customers_q1_2026", "pii_detected": True},
})
result = client.wait_for(intent_id)
```

No reminder scheduler. No escalation handler. No webhook endpoint. No polling loop. No token management. No DB tables.

AXME handles reminders, escalation, timeout, delivery guarantees, and audit trail.

---

## What Makes This Different from Sync Approval

| | Sync (block and wait) | Async (AXME) |
|---|---|---|
| Human at lunch | Agent blocks forever | Reminder in 5 min |
| Human doesn't respond | Timeout, session lost | Escalation to backup |
| Connection drops | Approval state lost | State durable in DB |
| Response time | Must respond NOW | Hours or days later |
| Reminder | None | Configurable: 5 min, 30 min, custom |
| Escalation | None | Chain: person A -> person B -> team |
| Timeout | Hard kill | Graceful: fallback action or cancel |
| Task types | Yes/No only | 8 types: approval, review, form, override, ... |
| Audit trail | None | Full: who, when, decision, context |

---

## 8 Human Task Types

Not every approval is a yes/no button. AXME supports 8 structured task types:

| Type | Purpose | Example |
|------|---------|---------|
| `approval` | Binary yes/no gate | "Deploy to production?" |
| `review` | Content review with comments | "Review this PR summary" |
| `form` | Structured data collection | "Fill in budget justification" |
| `manual_action` | Out-of-band physical action | "Flip the DNS switch" |
| `override` | Manual override of automated decision | "Override rate limit for VIP" |
| `confirmation` | Acknowledge receipt / verify fact | "Confirm backup completed" |
| `assignment` | Route work to specific person | "Assign to security team" |
| `clarification` | Request missing information | "Which region should I deploy to?" |

---

## How It Works

```
+-----------+  send_intent()   +----------------+   notify      +-----------+
|           | ---------------> |                | ------------> |           |
|   Agent   |                  |   AXME Cloud   |               |   Human   |
|           | <- wait_for() -- |   (platform)   | <- approve/   | (reviewer)|
| suspends  |  resumes when    |                |    reject     |           |
| durably   |  human responds  |  - remind 5m   |               | responds  |
|           |                  |  - escalate 30m|               | hours     |
| continues |                  |  - timeout 8h  |               | later     |
+-----------+                  +----------------+               +-----------+
```

1. Agent sends an **approval intent** with context and deadline
2. Platform **notifies** the reviewer (Slack, email, CLI)
3. Agent **suspends durably** - zero resources consumed while waiting
4. **5 minutes** pass with no response - AXME sends a **reminder**
5. **30 minutes** pass - AXME **escalates** to backup reviewer
6. Human **approves** from phone 2 hours later
7. Agent **resumes** instantly with the decision

---

## Works With Any Agent Framework

AXME is not an agent framework. It's the coordination layer underneath.

| Framework | How to Add Async Approval |
|-----------|--------------------------|
| **LangGraph** | `send_intent()` between graph nodes |
| **CrewAI** | Pause crew tasks for async sign-off |
| **AutoGen** | Insert approval checkpoints in multi-agent chat |
| **OpenAI Agents SDK** | Gate tool calls behind approval |
| **Google ADK** | Replace `LongRunningFunctionTool` with AXME |
| **Pydantic AI** | Add HITL where Pydantic AI has none |
| **Any Python code** | `send_intent()` + `wait_for()` anywhere |

---

## Run the Full Example

### Prerequisites

```bash
# Install CLI (one-time)
curl -fsSL https://raw.githubusercontent.com/AxmeAI/axme-cli/main/install.sh | sh
# Open a new terminal, or run the "source" command shown by the installer

# Log in
axme login

# Install Python SDK
pip install axme
```

### Terminal 1 - submit the scenario

```bash
axme scenarios apply scenario.json
# Note the intent_id in the output
```

### Terminal 2 - start the agent

Get the agent key after scenario apply:

```bash
# macOS
cat ~/Library/Application\ Support/axme/scenario-agents.json | grep -A2 data-analyst-demo

# Linux
cat ~/.config/axme/scenario-agents.json | grep -A2 data-analyst-demo
```

Run the agent:

```bash
AXME_API_KEY=<agent-key> python agent.py
```

### Terminal 1 - approve (after agent completes its scan)

```bash
# Intent will be in WAITING status after agent step
axme tasks approve <intent_id>
```

### Verify

```bash
axme intents get <intent_id>
# lifecycle_status: COMPLETED
```

---

## Related

- [AXME](https://github.com/AxmeAI/axme) - project overview
- [AXP Spec](https://github.com/AxmeAI/axme-spec) - open Intent Protocol specification
- [AXME Examples](https://github.com/AxmeAI/axme-examples) - 20+ runnable examples across 5 languages
- [AXME CLI](https://github.com/AxmeAI/axme-cli) - manage intents, agents, scenarios from the terminal
- [Agent Workflow with Human Approval](https://github.com/AxmeAI/agent-workflow-with-human-approval) - basic approval gate example
- [AI Agent Checkpoint and Resume](https://github.com/AxmeAI/ai-agent-checkpoint-and-resume) - durable state without checkpoint code

---

Built with [AXME](https://github.com/AxmeAI/axme) (AXP Intent Protocol).
