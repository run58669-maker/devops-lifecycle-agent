"""DevOps Lifecycle Agent — Incident response pipeline using ADK multi-agent."""

from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.agents.llm_agent import LlmAgent

from .tools import (
    fetch_cloud_run_logs,
    fetch_monitoring_alerts,
    fetch_recent_deploys,
    create_github_pr,
    generate_alert_rule,
)

MODEL = "gemini-2.5-flash"

# --- Stage 1: Observer — detect and gather incident context ---
observer_agent = LlmAgent(
    name="ObserverAgent",
    model=MODEL,
    instruction="""You are a Cloud Run incident observer.
When the user reports an incident or alert, use your tools to gather context:
1. Call fetch_monitoring_alerts() to get active alerts
2. Call fetch_cloud_run_logs() to get recent error logs
3. Call fetch_recent_deploys() to see what changed recently

Compile all gathered data into a structured incident report with:
- Alert details (severity, timestamp, metric)
- Key error log entries (last 20 relevant lines)
- Recent deployment changes

Output ONLY the structured incident data, no analysis yet.""",
    description="Detects incidents and gathers logs, alerts, and deploy history.",
    tools=[fetch_cloud_run_logs, fetch_monitoring_alerts, fetch_recent_deploys],
    output_key="incident_context",
)

# --- Stage 2: Diagnoser — analyze root cause ---
diagnoser_agent = LlmAgent(
    name="DiagnoserAgent",
    model=MODEL,
    instruction="""You are an expert SRE diagnosing a Cloud Run incident.

**Incident Context:**
{incident_context}

Analyze the logs, alerts, and recent deploys to determine:
1. **Root Cause**: What specifically caused the incident (e.g., OOM due to memory leak in endpoint X, introduced in deploy Y)
2. **Impact**: Which services/endpoints are affected
3. **Evidence**: Cite specific log lines and metrics that support your diagnosis
4. **Severity**: Critical / High / Medium / Low

Be precise and evidence-based. Do not guess — if data is insufficient, say so.
Output a structured diagnosis report.""",
    description="Analyzes incident context to determine root cause.",
    output_key="diagnosis",
)

# --- Stage 3: Fixer — propose fix and create PR ---
fixer_agent = LlmAgent(
    name="FixerAgent",
    model=MODEL,
    instruction="""You are a DevOps engineer proposing a fix for an incident.

**Diagnosis:**
{diagnosis}

Based on the root cause analysis:
1. Propose a specific fix (code change, config change, or rollback)
2. Generate the exact file diff or config change needed
3. Use create_github_pr() to create a pull request with the fix
4. Include rollback instructions if the fix doesn't work

The fix should be minimal and targeted — change only what's necessary.
Output the PR URL and a summary of changes made.""",
    description="Generates fix and creates a GitHub PR for human approval.",
    tools=[create_github_pr],
    output_key="fix_result",
)

# --- Stage 4: Reviewer — write postmortem and prevention rules ---
reviewer_agent = LlmAgent(
    name="ReviewerAgent",
    model=MODEL,
    instruction="""You are an SRE writing a postmortem and prevention plan.

**Incident Context:**
{incident_context}

**Diagnosis:**
{diagnosis}

**Fix Applied:**
{fix_result}

Generate two outputs:

## 1. Postmortem (Markdown)
Follow the standard format:
- **Title**: Incident date + brief description
- **Summary**: 2-3 sentences
- **Timeline**: Key events with timestamps
- **Root Cause**: From diagnosis
- **Resolution**: What was done
- **Impact**: Duration, affected users/services
- **Action Items**: Numbered list with owners and deadlines
- **Lessons Learned**: What went well, what didn't

## 2. Prevention Rules
Use generate_alert_rule() to create a Cloud Monitoring alert that would catch this issue earlier next time.

Output both the complete postmortem markdown and the alert rule configuration.""",
    description="Generates postmortem document and prevention alert rules.",
    tools=[generate_alert_rule],
    output_key="postmortem",
)

# --- Pipeline: Sequential orchestration ---
root_agent = SequentialAgent(
    name="DevOpsLifecycleAgent",
    description="End-to-end incident lifecycle: Observe → Diagnose → Fix → Review",
    sub_agents=[observer_agent, diagnoser_agent, fixer_agent, reviewer_agent],
)
