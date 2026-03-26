"""
Data analyst agent - scans a dataset for PII and requests human approval.

Listens for intents via SSE. When a data export request arrives, the agent
scans the dataset, flags PII findings, and resumes with a report.
The workflow then pauses for human approval before the export proceeds.

Usage:
    export AXME_API_KEY="<agent-key>"
    python agent.py
"""

import os
import sys
import time

sys.stdout.reconfigure(line_buffering=True)

from axme import AxmeClient, AxmeClientConfig


AGENT_ADDRESS = "data-analyst-demo"


def handle_intent(client, intent_id):
    """Scan dataset for PII and resume with findings."""
    intent_data = client.get_intent(intent_id)
    intent = intent_data.get("intent", intent_data)
    payload = intent.get("payload", {})
    if "parent_payload" in payload:
        payload = payload["parent_payload"]

    dataset = payload.get("dataset", "unknown")
    destination = payload.get("destination", "unknown")
    row_count = payload.get("row_count", 0)

    print(f"  Scanning dataset: {dataset} ({row_count} rows)...")
    time.sleep(1)

    print(f"  Checking for PII patterns...")
    time.sleep(1)

    print(f"  Found: 3 columns with PII (email, phone, ssn_last4)")
    time.sleep(1)

    result = {
        "action": "complete",
        "dataset": dataset,
        "destination": destination,
        "row_count": row_count,
        "pii_findings": [
            {"column": "email", "type": "email_address", "rows_affected": row_count},
            {"column": "phone", "type": "phone_number", "rows_affected": 89000},
            {"column": "ssn_last4", "type": "ssn_partial", "rows_affected": 145000},
        ],
        "recommendation": "mask_before_export",
        "scanned_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    client.resume_intent(intent_id, result)
    print(f"  Scan complete. PII found in 3 columns.")
    print(f"  Workflow now waits for data owner approval.")
    print(f"  Reminder in 5 min, timeout in 8 hours.")
    print(f"  To approve: axme tasks approve <intent_id>")


def main():
    api_key = os.environ.get("AXME_API_KEY", "")
    if not api_key:
        print("Error: AXME_API_KEY not set.")
        print("Run the scenario first: axme scenarios apply scenario.json")
        print("Then get the agent key from ~/.config/axme/scenario-agents.json")
        sys.exit(1)

    client = AxmeClient(AxmeClientConfig(api_key=api_key))

    print(f"Agent listening on {AGENT_ADDRESS}...")
    print("Waiting for intents (Ctrl+C to stop)\n")

    for delivery in client.listen(AGENT_ADDRESS):
        intent_id = delivery.get("intent_id", "")
        status = delivery.get("status", "")

        if not intent_id:
            continue

        if status in ("DELIVERED", "CREATED", "IN_PROGRESS"):
            print(f"[{status}] Intent received: {intent_id}")
            try:
                handle_intent(client, intent_id)
            except Exception as e:
                print(f"  Error processing intent: {e}")


if __name__ == "__main__":
    main()
