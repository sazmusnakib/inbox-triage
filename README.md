# Inbox Triage Agent

A small Python tool that takes a folder of support emails, runs each one through Claude, and produces a structured triage report: category, urgency, sentiment, a one-line summary, a suggested 2-4 sentence reply, and a flag for "needs human review."

Built as a weekend project to explore how far one well-designed prompt and structured JSON output can take a practical AI workflow. 

## Why I built this

I'm an M.Sc. AI student at FAU Erlangen-Nürnberg and use Claude every day in my study and research workflow. I wanted to move past chat and try plugging one carefully-shaped prompt into a real pipeline, then see what actually breaks when you commit to running it on multiple inputs in a row.

I picked support-email triage because I spent a year as a university lecturer at Asian University of Bangladesh and a lot of that work was triage at university scale: read the email, work out which course it was about, judge urgency, draft a reply that didn't make the student feel stupid. Same loop, different domain.

## What it does

1. Reads emails from `sample_emails/` (one `.txt` per email, so it's easy to drop in real cases).
2. For each email, asks Claude to return a JSON object with:
   - `category`: billing, technical, partnership, feature_request, complaint, general_inquiry, or other
   - `urgency`: low, medium, or high
   - `sentiment`: frustrated, neutral, or positive
   - `summary`: one-line summary of what the sender wants
   - `needs_human_review`: true or false
   - `suggested_response`: 2-4 sentence draft reply that matches the tone of the email
3. Writes one JSON file per email to `output/`, plus a markdown `summary.md` with a category breakdown and the full list of triage results.

## How to run

```bash
git clone https://github.com/sazmusnakib/inbox-triage.git
cd inbox-triage
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Open .env and add your Anthropic API key
python triage.py
```

Then open `output/summary.md`.

## Example output

> # Inbox Triage Report

- **Total emails processed:** 6
- **High urgency:** 2
- **Flagged for human review:** 2

## Category breakdown

- billing: 2
- feature_request: 2
- technical: 1
- partnership: 1

## Details

### 01_billing_refund.txt

- **Category:** billing
- **Urgency:** high
- **Sentiment:** frustrated
- **Summary:** Sarah was double-charged for her subscription and demands an immediate refund or will dispute the charge.
- ⚠️  **Needs human review**

**Suggested response:**

> Hi Sarah, thank you for reaching out, and we sincerely apologize for the duplicate charge and the delay in getting back to you — we completely understand how frustrating this situation must be. We are escalating your case to our billing team as a high priority so they can investigate the double charge and process the appropriate refund as quickly as possible. A member of our team will be in touch with you very shortly with a resolution. We truly appreciate your patience and are sorry for the inconvenience caused.

---


## What I learned

A few things from iterating on the prompt:

- **The first version of the prompt over-flagged emails.** Almost everything ended up with `needs_human_review = true`. The original wording was too broad ("anything outside standard support"). I rewrote it to require specific signals (clear anger, legal or regulatory threats, refund or chargeback disputes, billing errors causing ongoing harm) and added "default to false when unsure." The flag rate dropped to roughly what a person would actually do.

- **Claude is happy to invent facts if the prompt does not tell it not to.** On the API rate-limit sample email, an early draft confidently quoted made-up rate-limit numbers as if they were real. I added an explicit instruction that the model has no access to product documentation, internal systems, pricing, or policies, and should never state specific facts it cannot verify from the email itself. After that the drafts started saying "the relevant team will follow up with the specifics" instead.

- **A separate boolean for `needs_human_review` works much better than embedding that judgment inside the suggested reply.** The boolean is trivial to filter on in the output report. Embedded judgment would make the agent harder to integrate downstream.

- **Tight output enums make structured JSON much more reliable.** Naming the exact category, urgency, and sentiment values inside the prompt almost completely removed free-form variation in the output.

## What I would build next

- Move the category list and "team voice" guidance into a `team_context.yaml` file the prompt loads in, so different teams could configure the agent without editing the prompt directly.
- Wire it to a real inbox (Gmail API or IMAP) so it runs on incoming mail instead of static `.txt` files.
- Add a small feedback loop: a CLI step that asks the user whether the suggested reply was kept, edited, or discarded, and logs the answer. Over time that gives concrete data on where the agent is weakest.

## Stack

- Python 3.10+
- Anthropic Python SDK
- Claude Sonnet 4.5
- No external orchestration tools. Kept intentionally minimal for a weekend project.

## Limitations

- Six hand-written sample emails. Not tested at scale, and the category list is generic, so any real team would need to adjust it.
- No retry logic for API rate limits or JSON parse failures. One bad response will skip that email in the per-email JSON output, though the summary still completes.
- English-only. The prompt would need rework for multilingual inboxes.
- Sentiment is coarse (three buckets). Real production work would benefit from finer scales or per-team customization.
