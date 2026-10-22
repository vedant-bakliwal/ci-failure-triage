"""Optional LLM step on Amazon Bedrock: a root-cause summary per group, and a second opinion on
low-confidence labels. The model can only choose from the known labels; anything else is ignored."""
from __future__ import annotations

import json
import os
import re

from .classify import LABELS
from .triage import Group

PROMPT = """You triage CI test failures. For the failure group below, reply with only JSON:
{"label": one of product|test|environment|flaky|unknown, "summary": "one or two sentences on the likely root cause and the next step"}
product = the application behaves wrongly; test = the test code or test data is wrong;
environment = infrastructure, network, services or resources; flaky = passes and fails without a code change."""


class BedrockAdvisor:
    def __init__(self, model_id: str | None = None, region: str | None = None, client=None, min_confidence: float = 0.7):
        self.model_id = model_id or os.environ.get("BEDROCK_MODEL_ID", "us.amazon.nova-lite-v1:0")
        self.min_confidence = min_confidence
        if client is None:
            import boto3  # optional dependency
            client = boto3.client("bedrock-runtime", region_name=region or os.environ.get("AWS_REGION", "us-east-1"))
        self.client = client

    def review(self, group: Group) -> None:
        details = (f"Rule label: {group.label} ({group.confidence:.2f}): {group.reason}\n"
                   f"Error: {group.error_type}: {group.message}\nTop frames: {', '.join(group.frames) or 'none'}\n"
                   f"Tests ({len(group.tests)}): {', '.join(group.tests[:10])}")
        response = self.client.converse(
            modelId=self.model_id,
            system=[{"text": PROMPT}],
            messages=[{"role": "user", "content": [{"text": details}]}],
            inferenceConfig={"maxTokens": 300, "temperature": 0.0},
        )
        text = "".join(p.get("text", "") for p in response["output"]["message"]["content"])
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return
        group.summary = str(data.get("summary", "")).strip()
        label = str(data.get("label", "")).lower()
        # Rules win when they are confident; the model only decides the uncertain groups.
        if group.confidence < self.min_confidence and label in LABELS and label != group.label:
            group.label, group.source = label, "llm"
            group.reason = f"LLM review (rule said {group.reason})"
