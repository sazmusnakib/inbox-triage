"""
Inbox Triage Agent — runs each email in sample_emails/ through Claude
and produces structured triage output plus a markdown summary report.
"""
import json
import os
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

from prompts import TRIAGE_PROMPT

load_dotenv()

MODEL = "claude-sonnet-4-6"


def triage_email(client: Anthropic, email_text: str) -> dict:
    """Send one email to Claude and parse the structured triage response."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": TRIAGE_PROMPT.format(email=email_text),
            }
        ],
    )
    text = response.content[0].text.strip()
    # Strip code fences if Claude wrapped the JSON
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)


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

    path.write_text("".join(lines))


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
        email_text = email_file.read_text()
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