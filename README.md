# Zillion Bizops
 
AI-driven proposal engine that turns customer meeting notes, email chains, and Slack threads into client-ready hardware proposals.
 
---
 
## Highlights
 
- **5–10 minute proposals** instead of 60–90 minutes of manual writing
- **Three-agent pipeline** with human-in-the-loop approval before anything reaches clients
- **Multi-format input**: Granola summaries, email chains, Slack threads, raw notes, Google Doc URLs
- **Tree-of-Thought hardware reasoning** — see exactly why each option won or lost
- **12-section client-ready output** with exact Zillion pricing, SLAs, and 3-week deployment timeline
- **Built-in version history** — every proposal edit is tracked and revertible
- **Confidence scoring** — low-confidence extractions surface yellow warnings before clients see them
- **No build step** — single HTML file, deploys to GitHub Pages in 5 minutes
- **Per-user API keys** for trial, **shared backend** ready when team scales
---
 
## Overview
 
Bizops is an internal tool that eliminates the manual, tedious process of reading customer transcripts and guessing client needs. You paste any kind of customer context — a Granola meeting summary, an email thread, a Slack export, raw notes — and three AI agents work in sequence to produce a structured proposal.
 
The **Discovery Agent** ("The Listener") extracts client constraints: budget, GPU preference, deal stage, follow-up questions for the sales team, and competitive intelligence. The **Architect Agent** ("The Engineer") uses Tree-of-Thought reasoning to evaluate hardware paths from Zillion's catalog and live fleet, then recommends the best fit with full justification. The **Writer Agent** ("The Author") generates a complete Markdown proposal in Zillion's voice with exact pricing, SLAs, and deployment timelines. Every step pauses for human review.
 
### Who built this
 
Engineering by **Larry Song** with sponsorship from CEO **Xander Wu**. Operations review by **Yuhan Ma**. Built using Claude (Anthropic Sonnet 4) as the LLM backbone — model-agnostic by design.
 
### Where it fits in the Zillion stack
 
Bizops sits between the early-stage CRM/notes layer (Granola, Slack, email) and the proposal/SOW layer (Google Docs, signed contracts). It does not replace those tools — it eliminates the writing labor between them. The team continues to capture customer context however they prefer, then runs that context through bizops to produce a draft, reviews it, and exports the final version to wherever proposals live today.
 
The current architecture is a single HTML frontend deployed to GitHub Pages, with an optional FastAPI backend (`server.py`) that becomes useful once the team grows beyond ~5 active users. Both the per-user-key and shared-backend deployment modes are supported by the same codebase — switching between them is a configuration change, not a rewrite.
 
---
 
## Usage Instructions
 
### Setup (2 minutes, one-time)
 
```
1. Get an API key from console.anthropic.com (Zillion Network workspace, ask Xander for invite)
2. Open the bizops site → click ⚙ → paste key → Save
3. Click ⚡ Test Setup → wait for ✓ API Working
```
 
### Generate a proposal (5–10 minutes)
 
```
Home → + New Assessment
  → Pick input tab (Raw / Granola / Email / Google Doc / Slack)
  → Paste customer content
  → Run Discovery Agent →
 
Step 1 (Discovery)  → Review constraints, edit chips if needed → Proceed to Step 2
Step 2 (Architect)  → Run Architect Agent → Review ToT paths → ✓ Approve
Step 3 (Writer)     → Edit proposal inline → 💾 Save / 📋 Copy / 📄 Export PDF / 📧 Send for Review
```
 
### Common actions
 
| What you want to do | How |
|---|---|
| Update an existing customer's proposal | Save again with same client name → choose "update existing" |
| Re-run an agent with feedback | Type into "Reviewer feedback" box → click ↺ Re-run |
| See full proposal history | Click any row in the Proposals tracker → Versions strip |
| Edit Markdown + see preview | Step 3 → Split View toggle |
| Back up everything before closing browser | ⚙ Settings → ⬇ Export All Data |
| Restore from backup | ⚙ Settings → ⬆ Import Data |
| Import fleet inventory from Excel | Hardware Inventory page → 📊 Upload Excel |
| Verify API works without burning a real transcript | Home page → ⚡ Test Setup |
 
### What good input looks like
 
A single Granola meeting summary or email chain works well. Include explicit numbers (`$180-220K budget`, `RTX 5090`, `mid-June timeline`) and verbatim quotes. Don't paraphrase. If the customer mentioned a competitor by name, leave it in — it becomes competitive intel in the output.
 
### What bad input looks like
 
A 50-word vague summary like "customer wants GPUs for AI." The agent will produce a low-confidence extraction with a yellow gaps banner listing what it couldn't determine. That's a feature — go back to the customer and get the missing details.
 
### Troubleshooting
 
| Symptom | Fix |
|---|---|
| "Failed to fetch" | API key invalid or expired — paste a fresh one in ⚙ Settings |
| Agent timed out | Input was too long or too vague — trim it or add specifics |
| Sample data appearing instead of real | Hard refresh (Cmd+Shift+R) to clear cached version |
| Proposals disappeared | Browser data was cleared — restore from backup JSON |
 
---
 
## Feedback Form
 
After every test session, please fill out the **Bizops Feedback Form** (https://docs.google.com/forms/d/e/1FAIpQLSdDzTonEVcnqT1si6dSmoCEYNycbtcM38-I50eKGQugX_Rn1w/viewform?usp=publish-editor). Takes about 5 minutes. Your input directly shapes prompt tuning and UX priorities.
 
Especially helpful: specific failure modes ("the agent kept missing budget when it was mentioned in dollars-per-month form"), not generic "extraction was bad" complaints. The more specific the feedback, the faster we can fix it.
 
For bugs blocking your work, slack Larry directly. 
 
