"""
Inbox Triage Agent — runs each email in sample_emails/ through Claude
and produces structured triage output plus a markdown summary report.

The model's JSON output is validated against an explicit schema before it is
trusted. If a response is malformed or out of spec, the call is retried once
with a correction; if it still fails, that email is reported as an error.
"""
import json
import os
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

from prompts import TRIAGE_PROMPT

load_dotenv()

MODEL = "claude-sonnet-4-6"

# The schema we require from the model — a single source of truth for
# validation. (These mirror the lists named in prompts.py; a larger project
# would define them once and inject them into both the prompt and this file.)
VALID_CATEGORIES = {
    "billing", "technical", "partnership", "feature_request",
    "complaint", "general_inquiry", "other",
}
VALID_URGENCIES = {"low", "medium", "high"}
VALID_SENTIMENTS = {"frustrated", "neutral", "positive"}
REQUIRED_FIELDS = {
    "category", "urgency", "sentiment",
    "summary", "needs_human_review", "suggested_response",
}


def validate_triage(data: dict) -> list[str]:
    """Check a parsed triage result against the schema.

    Returns a list of human-readable problems; an empty list means valid.
    The model's output is untrusted input, so we never accept it blindly.
    """
    if not isinstance(data, dict):
        return ["response is not a JSON object"]

    problems: list[str] = []

    missing = REQUIRED_FIELDS - data.keys()
    if missing:
        problems.append("missing fields: " + ", ".join(sorted(missing)))

    if data.get("category") not in VALID_CATEGORIES:
        problems.append(f"invalid category: {data.get('category')!r}")
    if data.get("urgency") not in VALID_URGENCIES:
        problems.append(f"invalid urgency: {data.get('urgency')!r}")
    if data.get("sentiment") not in VALID_SENTIMENTS:
        problems.append(f"invalid sentiment: {data.get('sentiment')!r}")
    if not isinstance(data.get("needs_human_review"), bool):
        problems.append("needs_human_review is not true/false")
    if not isinstance(data.get("summary"), str) or not data["summary"].strip():
        problems.append("summary is empty or not text")
    if not isinstance(data.get("suggested_response"), str) or not data["suggested_response"].strip():
        problems.append("suggested_response is empty or not text")

    return problems


def _call_and_parse(client: Anthropic, prompt: str) -> dict:
    """Make one API call and parse a JSON object out of the response."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    # Strip code fences if Claude wrapped the JSON in ```
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)


def triage_email(client: Anthropic, email_text: str) -> dict:
    """Send one email to Claude, parse it, and validate the result.

    LLM output is not guaranteed to match the requested schema, so we retry
    once — telling the model what was wrong — before giving up on the email.
    """
    base_prompt = TRIAGE_PROMPT.format(email=email_text)
    last_problems: list[str] = []

    for attempt in range(2):  # first try, then one corrective retry
        prompt = base_prompt
        if attempt > 0:
            prompt += (
                "\n\nYour previous response was rejected ("
                + "; ".join(last_problems)
                + "). Reply again with ONLY a valid JSON object that has all "
                "required fields and uses only the allowed values."
            )

        try:
            data = _call_and_parse(client, prompt)
        except json.JSONDecodeError as e:
            last_problems = [f"response was not valid JSON ({e})"]
            continue

        last_problems = validate_triage(data)
        if not last_problems:
            return data

    raise ValueError(
        "model output failed validation after retry: " + "; ".join(last_problems)
    )


def write_summary(results: list[dict], path: Path) -> None:
    """Build a human-readable markdown report from all triage results."""
    lines = ["# Inbox Triage Report\n\n"]

    high_urgency = [r for r in results if r.get("urgency") == "high"]
    needs_review = [r for r in results if r.get("needs_human_review")]

    lines.append(f"- **Total emails processed:** {len(results)}\n")
    lines.append(f"- **High urgency:** {len(high_urgency)}\n")
    lines.append(f"- **Flagged for human review:** {len(needs_review)}\n\n")

    # Category breakdown
    categories: dict[str, int] = {}
    for r in results:
        cat = r.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1
    lines.append("## Category breakdown\n\n")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        lines.append(f"- {cat}: {count}\n")
    lines.append("\n")

    # Per-email detail
    lines.append("## Details\n\n")
    for r in results:
        lines.append(f"### {r.get('filename', 'unknown')}\n\n")
        lines.append(f"- **Category:** {r.get('category')}\n")
        lines.append(f"- **Urgency:** {r.get('urgency')}\n")
        lines.append(f"- **Sentiment:** {r.get('sentiment')}\n")
        lines.append(f"- **Summary:** {r.get('summary')}\n")
        if r.get("needs_human_review"):
            lines.append("- ⚠️  **Needs human review**\n")
        lines.append("\n**Suggested response:**\n\n")
        lines.append(f"> {r.get('suggested_response', '')}\n\n")
        lines.append("---\n\n")

    path.write_text("".join(lines), encoding="utf-8")


def main() -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit(
            "ANTHROPIC_API_KEY not set. Copy .env.example to .env and add your key."
        )

    client = Anthropic()
    input_dir = Path("sample_emails")
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    results: list[dict] = []
    for email_file in sorted(input_dir.glob("*.txt")):
        print(f"Processing {email_file.name} ...")
        email_text = email_file.read_text(encoding="utf-8")
        try:
            result = triage_email(client, email_text)
            result["filename"] = email_file.name
            results.append(result)
            (output_dir / f"{email_file.stem}.json").write_text(
                json.dumps(result, indent=2)
            )
        except Exception as e:
            print(f"  Error processing {email_file.name}: {e}")

    write_summary(results, output_dir / "summary.md")
    print(f"\nDone. Processed {len(results)} emails. See output/summary.md")


if __name__ == "__main__":
    main()