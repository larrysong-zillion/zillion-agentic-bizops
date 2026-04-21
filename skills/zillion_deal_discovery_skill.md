# Skill: Zillion Deal Discovery

## Purpose
Extract actionable deal intelligence from meeting transcripts (especially Granola summaries), email threads, and Slack conversations. Classify deals against Zillion Network's business workflow and past deployment patterns.

## Business Workflow Stages
Every deal moves through these stages. The agent must identify which stage the current interaction represents:

1. **Demand Discovery** — Initial contact. Client describes a vague compute need. Budget and GPU type usually unknown. Focus: qualify whether this is a real deal or exploration.
2. **Customer Contact** — First substantive meeting. Identify decision makers, budget authority, and timeline drivers. Focus: who decides, who pays, who blocks.
3. **Tech Discussion** — Architecture alignment call. GPU selection, VRAM requirements, NVLink vs PCIe, cluster topology. Focus: match workload to hardware.
4. **POC/Evaluation** — Proof-of-concept. Client tests on a single node or small cluster. Focus: benchmark results, NCCL configs, latency targets.
5. **Contract Negotiation** — Pricing, payment terms, SLA commitments, lease vs. buy. Focus: close the gap between client budget and Zillion cost floor.
6. **Deal Closing** — PO signed, MSA executed. Focus: handoff to deployment team.
7. **Service Delivery** — Hardware deployment, monitoring setup, ongoing ops. Focus: SLA adherence, upsell opportunities.

## Qualification Criteria
Flag a deal as HIGH PRIORITY if any 3+ of these are true:
- Budget >$100K
- Timeline <8 weeks
- Specific GPU named (not "we need GPUs")
- Training workload (higher margin than inference)
- Client has existing cluster experience (knows what they want)
- Decision maker is on the call (CTO, VP Eng, not just an IC)

Flag a deal as LOW FIT if:
- Budget <$50K (below Zillion's cost floor for managed services)
- Edge/self-managed deployment (no colo)
- Client wants cloud-style hourly billing only
- No timeline urgency

## Granola-Specific Processing
Granola AI summaries have known limitations:
- Often paraphrases technical details, losing precision (e.g., "they need lots of GPU memory" instead of "192GB VRAM per node")
- May merge multiple speakers into one summary, losing attribution
- Action items are usually accurate but may miss implicit commitments
- Meeting tone/urgency is often flattened

When processing Granola input:
1. Extract explicit constraints first (budget numbers, GPU names, dates)
2. Infer implicit constraints from context ("our contract with Pfizer starts July 1st" → hard deadline)
3. Flag anything ambiguous as a follow-up question
4. Look for competitive signals ("we tried Lambda Labs", "CoreWeave queue times")
5. Identify the decision maker from attendee list + speaking patterns

## Past Deal Reference Patterns

### Successful Deals (use as confidence anchors)
- **Ab Initia Labs** — $2M, 128 GPUs (RTX Pro 6000 SE), pharma AI research, passthrough vs CX8 evaluation
- **Cudo Ventures** — $4.2M, 4,096 H100 SXM5 GPUs, managed services worldwide, largest engagement
- **Helios Foundation Models** — $892K, 152 GPUs (A100 + 4090 hybrid), 140B param training, cage at Ashburn
- **NovaStar AI** — $312K, inference cluster, 4× RTX 5090, P95 latency 74ms
- **Vertex Genomics** — $94K, co-location, customer-owned A100 at Dallas DC

### Lost Deals (use for risk signals)
- **CloudMind Systems** — $76K, edge inference, budget mismatch ($65K ceiling vs $124K cost floor)
- **Meridian Robotics** — $540K pending, competitor (Lambda Labs) submitted $285K quote, price gap risk

## Output Format
Always return structured JSON with these fields:
```json
{
  "client_name": "string",
  "budget": "$X – $Y or Unknown",
  "gpu_preference": "specific GPU or Best fit",
  "workflow": "Training/Inference/Hybrid/Managed Services",
  "timeline": "string",
  "deal_stage": "Discovery/Tech Discussion/POC/Negotiation/Closing/Delivery",
  "business_model": "2-3 sentences",
  "rag_classification": "workload type matched to past deals",
  "key_requirements": ["array of specific technical needs"],
  "follow_up_questions": ["questions the sales team should ask"],
  "competitive_intel": "competitors mentioned or implied",
  "confidence": {
    "score": 7.5,
    "label": "High/Moderate/Low Confidence",
    "reasoning": "why, with past deal references",
    "matched_deals": ["deal — $XK status"]
  }
}
```

## Follow-Up Question Generation
The agent should generate 2-5 follow-up questions that are:
- Specific to THIS deal (not generic "what's your budget")
- Actionable by the sales team in the next meeting
- Focused on unresolved constraints that affect hardware selection
- Informed by what went wrong in similar past deals

Examples:
- "Confirm whether 192GB VRAM is per-node or aggregate — this changes the recommendation from 5090 to Pro 6000"
- "Ask about data sovereignty: if biomedical data can't leave US, Ashburn DC is the only option"
- "Client mentioned CoreWeave queue times — quantify their current cloud spend for TCO comparison"
