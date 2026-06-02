# Inbox Triage Agent

A small Python tool that takes a folder of support emails, runs each one through Claude, and produces a structured triage report: category, urgency, sentiment, a one-line summary, a suggested 2–4 sentence reply, and a flag for "needs human review."

Built as a weekend project to explore how far one well-designed prompt and structured JSON output can take a practical AI workflow.

## Why I built this

> [FILL IN — pick the angle that's true for you. Options:
>
> 1. *"I spent a year as a university lecturer fielding student support emails and noticed how much of triage is repetitive: classify, judge urgency, write a draft reply. I wanted to see how much of that loop Claude could handle if the structure was right."*
>
> 2. *"I use Claude every day for study work and wanted to move beyond chat: take one well-shaped prompt, plug it into a real workflow, and see what the failure modes are when you commit to running it on real data."*
>
> 3. *Write your own — 2-3 sentences, your real motivation.*]

## What it does

1. Reads emails from `sample_emails/` (one `.txt` per email — easy to drop in real cases).
2. For each email, asks Claude to return a JSON object with:
   - `category` — billing, technical, partnership, feature_request, complaint, general_inquiry, other
   - `urgency` — low, medium, high
   - `sentiment` — frustrated, neutral, positive
   - `summary` — one-line summary of what the sender wants
   - `needs_human_review` — true/false flag
   - `suggested_response` — 2–4 sentence draft reply that matches tone
3. Writes per-email JSON files to `output/` plus a markdown `summary.md` with category breakdown and the full list.

## How to run

```bash
git clone https://github.com/sazmusnakib/inbox-triage.git
cd inbox-triage
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your Anthropic API key
python triage.py
```

Then open `output/summary.md`.

## Example output

> [INCLUDE 5–10 LINES FROM YOUR ACTUAL `output/summary.md` HERE.
> Paste a category breakdown table and one full per-email block so a reader can see the format without running it themselves.]

## What I learned

> [FILL IN — be honest and specific. Some ideas that will probably be true after you run this:
>
> - Structured JSON output is much more reliable when the prompt names exact field names and value enums; without that Claude wanders.
> - Sentiment on terse emails is noisy — "thanks" can be sincere or sarcastic without context.
> - Asking for `needs_human_review` as a separate boolean is much more useful than asking Claude to embed that judgment inside the response text.
> - Setting `max_tokens` to ~1024 keeps responses tight and reduces drift.
> - Errors and JSON parsing failures need to be handled per-email or one bad email kills the whole run.
> - Write your own discoveries.]

## What I would build next

> [FILL IN — pick 2–3 honestly:
>
> - Move the category list and team-specific context into a `team_context.yaml` so different teams can configure the agent without editing the prompt.
> - Wire it to a real inbox (IMAP or Gmail API) so it runs on incoming mail instead of static files.
> - Add a feedback loop: a small CLI prompt asking the human whether the suggested reply was kept, edited, or rejected, logged so we can see which categories the agent is weakest on.
> - Replace the single prompt with two passes (classify first, then draft response with the classification as context) to see whether reliability improves.]

## Stack

- Python 3.10+
- Anthropic Python SDK
- Claude Sonnet 4.5
- No external orchestration tools — kept intentionally minimal for a weekend project.

## Limitations

> [Add honest limitations. E.g.:
> - 6 hand-written sample emails; not tested at scale.
> - No retry logic on rate limits.
> - English-only; the prompt would need adapting for multilingual support inboxes.
> - Sentiment categories are coarse — production would benefit from a finer scale or per-team customization.]
