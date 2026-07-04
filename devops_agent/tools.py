"""Tools for the DevOps Lifecycle Agent — interact with GCP and GitHub."""

import json
import os
import shutil
import subprocess
from datetime import datetime, timezone

_GCLOUD = shutil.which("gcloud.cmd") or shutil.which("gcloud") or "gcloud"


def fetch_cloud_run_logs(
    service_name: str = "demo-app",
    severity: str = "ERROR",
    limit: int = 30,
) -> dict:
    """Fetch recent Cloud Run logs from Cloud Logging.

    Args:
        service_name: Name of the Cloud Run service.
        severity: Minimum log severity (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        limit: Maximum number of log entries to return.

    Returns:
        Dictionary with log entries and metadata.
    """
    project_id = os.environ.get("GCP_PROJECT_ID", "")
    if not project_id:
        return {"error": "GCP_PROJECT_ID not set"}

    filter_str = (
        f'resource.type="cloud_run_revision" '
        f'resource.labels.service_name="{service_name}" '
        f'severity>={severity}'
    )

    cmd = [
        _GCLOUD, "logging", "read", filter_str,
        f"--project={project_id}",
        f"--limit={limit}",
        "--format=json",
        "--freshness=1h",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return {"error": result.stderr.strip(), "logs": []}

        logs = json.loads(result.stdout) if result.stdout.strip() else []
        entries = []
        for log in logs:
            entries.append({
                "timestamp": log.get("timestamp", ""),
                "severity": log.get("severity", ""),
                "message": log.get("textPayload", "")
                    or log.get("jsonPayload", {}).get("message", ""),
            })

        return {
            "service": service_name,
            "project": project_id,
            "count": len(entries),
            "entries": entries,
        }
    except Exception as e:
        return {"error": str(e), "logs": []}


def fetch_monitoring_alerts(project_id: str = "") -> dict:
    """Fetch Cloud Monitoring alert policies for the project.

    Args:
        project_id: GCP project ID. Uses GCP_PROJECT_ID env var if empty.

    Returns:
        Dictionary with alert policies and their conditions.
    """
    project_id = project_id or os.environ.get("GCP_PROJECT_ID", "")
    if not project_id:
        return {"error": "GCP_PROJECT_ID not set"}

    cmd = [
        _GCLOUD, "alpha", "monitoring", "policies", "list",
        f"--project={project_id}",
        "--format=json",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return {"error": result.stderr.strip(), "policies": []}

        policies = json.loads(result.stdout) if result.stdout.strip() else []
        parsed = []
        for p in policies:
            conditions = p.get("conditions", [])
            parsed.append({
                "name": p.get("name", ""),
                "displayName": p.get("displayName", ""),
                "enabled": p.get("enabled", False),
                "conditions": [c.get("displayName", "") for c in conditions],
            })

        return {"project": project_id, "count": len(parsed), "policies": parsed}
    except Exception as e:
        return {"error": str(e), "policies": []}


def fetch_recent_deploys(
    service_name: str = "demo-app",
    limit: int = 5,
) -> dict:
    """Fetch recent Cloud Run deployment revisions.

    Args:
        service_name: Name of the Cloud Run service.
        limit: Maximum number of revisions to return.

    Returns:
        Dictionary with recent deployment revisions.
    """
    project_id = os.environ.get("GCP_PROJECT_ID", "")
    region = os.environ.get("GCP_REGION", "asia-northeast1")

    cmd = [
        _GCLOUD, "run", "revisions", "list",
        f"--service={service_name}",
        f"--project={project_id}",
        f"--region={region}",
        f"--limit={limit}",
        "--format=json",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return {"error": result.stderr.strip(), "revisions": []}

        revisions = json.loads(result.stdout) if result.stdout.strip() else []
        deploys = []
        for rev in revisions:
            metadata = rev.get("metadata", {})
            spec = rev.get("spec", {}).get("containers", [{}])[0]
            deploys.append({
                "name": metadata.get("name", ""),
                "created": metadata.get("creationTimestamp", ""),
                "image": spec.get("image", ""),
                "memory": spec.get("resources", {}).get("limits", {}).get("memory", ""),
            })

        return {
            "service": service_name,
            "region": region,
            "count": len(deploys),
            "revisions": deploys,
        }
    except Exception as e:
        return {"error": str(e), "revisions": []}


def create_github_pr(
    title: str,
    body: str,
    branch_name: str = "",
    file_changes: str = "",
) -> dict:
    """Create a GitHub pull request with proposed fixes.

    Args:
        title: PR title describing the fix.
        body: PR body with detailed description of changes.
        branch_name: Git branch name for the fix. Auto-generated if empty.
        file_changes: JSON string describing file changes, e.g.
            [{"path": "app.py", "content": "new content"}]

    Returns:
        Dictionary with PR URL and status.
    """
    if not branch_name:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        branch_name = f"fix/incident-{ts}"

    repo_dir = os.environ.get("DEMO_REPO_DIR") or os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )

    errors = []

    def _run(cmd):
        r = subprocess.run(cmd, cwd=repo_dir, capture_output=True, text=True)
        if r.returncode != 0:
            errors.append(f"cmd={cmd[0:3]}: {r.stderr.strip()}")
        return r

    try:
        _run(["git", "checkout", "main"])
        _run(["git", "pull", "--rebase"])

        checkout = _run(["git", "checkout", "-b", branch_name])
        if checkout.returncode != 0:
            _run(["git", "checkout", branch_name])

        if file_changes:
            changes = json.loads(file_changes)
            for change in changes:
                filepath = os.path.join(repo_dir, change["path"])
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(change["content"])

        _run(["git", "add", "-A"])
        _run(["git", "commit", "-m", title])
        _run(["git", "push", "-u", "origin", branch_name])

        result = subprocess.run(
            ["gh", "pr", "create", "--title", title, "--body", body],
            cwd=repo_dir, capture_output=True, text=True,
        )

        pr_url = result.stdout.strip() if result.returncode == 0 else ""

        # Always return to main branch
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=repo_dir, capture_output=True, text=True,
        )

        return {
            "status": "created" if pr_url else "failed",
            "pr_url": pr_url,
            "branch": branch_name,
            "errors": errors if errors else [],
        }
    except Exception as e:
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=repo_dir, capture_output=True, text=True,
        )
        return {"error": str(e), "pr_url": ""}


def generate_alert_rule(
    display_name: str,
    metric_type: str,
    threshold_value: float,
    comparison: str = "COMPARISON_GT",
    duration: str = "60s",
) -> dict:
    """Generate a Cloud Monitoring alert policy configuration.

    Args:
        display_name: Human-readable name for the alert.
        metric_type: The metric to monitor, e.g.
            "run.googleapis.com/container/memory/utilizations".
        threshold_value: Threshold value that triggers the alert (0.0-1.0 for ratios).
        comparison: Comparison operator (COMPARISON_GT, COMPARISON_LT, etc.).
        duration: How long the condition must be true before alerting, e.g. "60s".

    Returns:
        Dictionary with the alert policy JSON configuration.
    """
    project_id = os.environ.get("GCP_PROJECT_ID", "")

    policy = {
        "displayName": display_name,
        "combiner": "OR",
        "conditions": [
            {
                "displayName": f"{display_name} - condition",
                "conditionThreshold": {
                    "filter": f'metric.type="{metric_type}" '
                        f'AND resource.type="cloud_run_revision"',
                    "comparison": comparison,
                    "thresholdValue": threshold_value,
                    "duration": duration,
                    "aggregations": [
                        {
                            "alignmentPeriod": "60s",
                            "perSeriesAligner": "ALIGN_MEAN",
                        }
                    ],
                },
            }
        ],
        "alertStrategy": {
            "autoClose": "1800s",
        },
    }

    return {
        "status": "generated",
        "policy": policy,
        "note": f"Apply with: gcloud alpha monitoring policies create "
            f"--policy-from-file=alert.json --project={project_id}",
    }
