from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from extractor import extract_company_profile
from models import CompanyResult
from scraper import crawl_company_domain
from utils import normalize_domain

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

DOMAINS = ["postman.com", "supabase.com", "vapi.ai"]


def process_domain(domain: str) -> CompanyResult:
    normalized = normalize_domain(domain)
    logging.info("Processing %s", normalized)
    try:
        pages = crawl_company_domain(normalized)
        cleaned_pages = [{"url": page.url, "title": page.title, "text": page.text} for page in pages]
        result = extract_company_profile(normalized, cleaned_pages)
        if result.status == "success" and not result.company_overview and not result.target_audience:
            result.status = "partial"
        return result
    except Exception as exc:
        logging.exception("Unhandled failure for %s", normalized)
        return CompanyResult(
            domain=normalized,
            company_overview="",
            target_audience="",
            contact_points=[],
            leadership=[],
            confidence_score=0.0,
            status="failed",
            error=f"Processing failed: {exc}",
        )


def write_output(results: list[CompanyResult], output_path: Path) -> None:
    payload = [result.model_dump(mode="json") for result in results]
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    logging.info("Saved output to %s", output_path)


def main() -> None:
    load_dotenv()
    results: list[CompanyResult] = []
    for domain in DOMAINS:
        try:
            result = process_domain(domain)
            results.append(result)
        except Exception as exc:
            logging.exception("Unexpected failure while processing domain %s", domain)
            results.append(
                CompanyResult(
                    domain=normalize_domain(domain),
                    company_overview="",
                    target_audience="",
                    contact_points=[],
                    leadership=[],
                    confidence_score=0.0,
                    status="failed",
                    error=str(exc),
                )
            )

    output_path = Path(__file__).resolve().parent / "output.json"
    write_output(results, output_path)
    print(f"Processed {len(results)} companies. Results written to {output_path}")


if __name__ == "__main__":
    main()
