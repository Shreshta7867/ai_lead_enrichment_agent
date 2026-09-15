# Autonomous Lead Enrichment Agent

This project builds a lightweight lead enrichment pipeline that crawls public company websites, extracts useful visible text, and sends a cleaned summary to an LLM to recover structured company intelligence.

## What this project does

For each company domain in the configured list, the system:

1. Opens the website homepage.
2. Finds relevant internal pages such as About, Team, Contact, and Pricing.
3. Extracts visible text from those pages.
4. Cleans the text before sending it to the LLM.
5. Calls an OpenAI-compatible model to extract:
   - company overview
   - target audience / ICP
   - public contact points
   - leadership entries
   - confidence score
6. Validates the result using Pydantic.
7. Writes the final results to `output.json`.

## Project structure

- `main.py` – orchestrates the full job and writes output.
- `scraper.py` – Playwright crawler and content harvesting.
- `extractor.py` – LLM extraction and validation logic.
- `models.py` – Pydantic models for structured output.
- `utils.py` – normalization and cleanup helpers.
- `requirements.txt` – Python dependencies.
- `.env.example` – environment variable template.
- `.gitignore` – hides local secrets and environment files.
- `output.json` – generated results for all target domains.

## Prerequisites

- Python 3.11+
- A working OpenAI API key if you want LLM extraction enabled
- A browser runtime available for Playwright

## Set up a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## Install dependencies

```bash
pip install -r requirements.txt
```

## Install Playwright browsers

```bash
playwright install
```

## Configure environment variables

1. Copy `.env.example` to `.env`.
2. Add your OpenAI API key.

Example:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4o-mini
```

## Run the program

```bash
python main.py
```

The script processes the required domains:

- `postman.com`
- `supabase.com`
- `vapi.ai`

## Example output structure

```json
[
  {
    "domain": "postman.com",
    "company_overview": "Postman helps teams build, test, and manage APIs.",
    "target_audience": "Developers, API teams, and engineering organizations.",
    "contact_points": ["hello@postman.com"],
    "leadership": [
      {
        "name": "Abhinav Asthana",
        "role": "Co-founder",
        "linkedin_url": "https://www.linkedin.com/in/abhinavast/"
      }
    ],
    "confidence_score": 0.88,
    "status": "success"
  }
]
```

## Error handling

The project is resilient:

- bad domains or invalid URLs do not crash the run
- page navigation timeouts are logged and skipped
- a failed company does not stop processing the remaining domains
- if the LLM is unavailable or the API key is missing, the script records a failure status instead of crashing

## Notes

- The crawler intentionally stays within the target company's domain.
- It only follows a limited number of relevant internal pages.
- Raw HTML is not sent to the LLM; only cleaned visible text is sent.
