from __future__ import annotations

import json
import logging
import os
from typing import Any

from openai import OpenAI
from pydantic import ValidationError

from models import CompanyResult, LeadershipEntry
from utils import clean_text

LOGGER = logging.getLogger(__name__)


class LLMExtractor:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.base_url = os.getenv("OPENAI_BASE_URL")
        self.client = (
            OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
            if self.api_key
            else None
        )

    def extract(self, domain: str, pages: list[dict[str, str]]) -> CompanyResult:
        if not self.client:
            return CompanyResult(
                domain=domain,
                company_overview="",
                target_audience="",
                contact_points=[],
                leadership=[],
                confidence_score=0.0,
                status="failed",
                error="OPENAI_API_KEY is not set. Add it to .env before running the extraction.",
            )

        prompt = self._build_prompt(domain, pages)
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a careful extraction engine. Only use the website content provided. "
                            "Do not invent names, roles, emails, URLs, or company descriptions. "
                            "If information is missing, return empty strings, empty lists, or null values."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            raw_content = response.choices[0].message.content
            if not raw_content:
                raise ValueError("LLM returned an empty response.")

            payload = json.loads(raw_content)
            validated = self._validate_payload(domain, payload)
            return validated
        except (ValidationError, ValueError, json.JSONDecodeError, Exception) as exc:
            LOGGER.exception("LLM extraction failed for %s", domain)
            return CompanyResult(
                domain=domain,
                company_overview="",
                target_audience="",
                contact_points=[],
                leadership=[],
                confidence_score=0.0,
                status="failed",
                error=f"LLM extraction failed: {exc}",
            )

    def _build_prompt(self, domain: str, pages: list[dict[str, str]]) -> str:
        combined = []
        total_chars = 0
        max_chars = 28000

        for page in pages:
            title = page.get("title", "").strip()
            url = page.get("url", "").strip()
            text = clean_text(page.get("text", ""))

            if not text:
                continue

            remaining = max_chars - total_chars

            if remaining <= 0:
                break

            text = text[:remaining]

            combined.append(
                f"SOURCE URL: {url}\n"
                f"TITLE: {title}\n"
                f"CONTENT:\n{text}\n"
                "---\n"
            )

            total_chars += len(text)

        content = "\n".join(combined)

        prompt = f"""
Extract company information for {domain} using ONLY the website content provided below.

IMPORTANT RULES:
- Do not invent or guess any information.
- Only report information explicitly supported by the provided website content.
- Extract ALL relevant public/generic email addresses you can find.
- Extract ALL clearly identifiable leadership/team members that are explicitly named.
- Include a LinkedIn URL only when the exact URL appears in the provided content.
- Do not infer a person's role from context.
- If information is not available, return an empty string or empty list.
- Confidence score must be between 0.0 and 1.0.
- Company overview must be exactly 2 concise sentences.
- Return valid JSON only.

REQUIRED OUTPUT FIELDS:
- domain
- company_overview
- target_audience
- contact_points
- leadership
- confidence_score
- status
- error

LEADERSHIP FORMAT:
Each leadership entry must contain:
- name
- role
- linkedin_url

WEBSITE CONTENT:
{content}
"""

        return prompt

    def _validate_payload(self, domain: str, payload: dict[str, Any]) -> CompanyResult:
        domain_name = payload.get("domain") or domain
        leadership_entries = payload.get("leadership") or []
        normalized_leadership = []
        for raw_person in leadership_entries:
            if not isinstance(raw_person, dict):
                continue
            normalized_leadership.append(
                LeadershipEntry(
                    name=raw_person.get("name") or None,
                    role=raw_person.get("role") or None,
                    linkedin_url=raw_person.get("linkedin_url") or None,
                )
            )

        result = CompanyResult(
            domain=domain_name,
            company_overview=str(payload.get("company_overview") or ""),
            target_audience=str(payload.get("target_audience") or ""),
            contact_points=[str(email) for email in payload.get("contact_points") or [] if isinstance(email, str)],
            leadership=normalized_leadership,
            confidence_score=float(payload.get("confidence_score") or 0.0),
            status=str(payload.get("status") or "success"),
        )

        if not 0.0 <= result.confidence_score <= 1.0:
            result.confidence_score = max(0.0, min(1.0, result.confidence_score))
        return result


def extract_company_profile(domain: str, pages: list[dict[str, str]]) -> CompanyResult:
    extractor = LLMExtractor()
    return extractor.extract(domain, pages)
