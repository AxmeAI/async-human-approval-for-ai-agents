"""
Initiator - sends a data export approval request through the AXME pipeline.

Sends an intent to the data analyst agent, then observes the full lifecycle
including the human approval step with reminders and timeout.

Usage:
    export AXME_API_KEY="your-key"
    python initiator.py
"""

from __future__ import annotations

import json
import os
import sys

from axme import AxmeClient, AxmeClientConfig


SAMPLE_EXPORT = {
    "dataset": "customers_q1_2026",
    "destination": "analytics-warehouse",
    "row_count": 145000,
    "requested_by": "analytics-pipeline",
}


def main() -> None:
    api_key = os.environ.get("AXME_API_KEY")
    if not api_key:
        print("Error: AXME_API_KEY environment variable is required", file=sys.stderr)
        sys.exit(1)

    client = AxmeClient(AxmeClientConfig(api_key=api_key))

    print("Sending data export approval intent...")
    intent_id = client.send_intent({
        "intent_type": "intent.data.export_approval.v1",
        "to_agent": "agent://myorg/production/data-analyst",
        "payload": SAMPLE_EXPORT,
    })
    print(f"Intent created: {intent_id}")
    print("Observing lifecycle events...\n")

    for event in client.observe(intent_id):
        event_type = event.get("event_type", "unknown")
        data = event.get("data", {})
        print(f"  [{event_type}] {json.dumps(data, indent=2)[:200]}")

        if event_type in ("intent.completed", "intent.failed", "intent.cancelled"):
            break

        if data.get("status") == "pending_human_approval":
            print("\n  >>> Human approval required.")
            print("  >>> The agent found PII in the dataset.")
            print("  >>> AXME will send a reminder in 5 minutes if no response.")
            print(f"  >>> To approve: axme tasks approve {intent_id}")
            print(f"  >>> To reject:  axme tasks reject {intent_id}")
            print()

    final = client.get_intent(intent_id)
    print(f"\nFinal status: {final.get('status')}")
    print(f"Result: {json.dumps(final.get('result', {}), indent=2)}")


if __name__ == "__main__":
    main()
