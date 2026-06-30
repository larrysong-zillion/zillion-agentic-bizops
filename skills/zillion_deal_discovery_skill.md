# Skill: Zillion Deal Discovery

## Purpose
Extract actionable deal intelligence from meeting transcripts (especially Granola summaries), email threads, and Slack conversations. Classify deals against Zillion Network's business workflow and past deployment patterns. Route each deal to the correct downstream workflow based on direction — Zillion is not always the seller.

## Deal Direction — Determine This First

Every interaction is one of three directions. This is the single most consequential classification because it routes the Architect and Writer agents to entirely different document templates. Set `deal_direction` before any other field.

### outbound_sale (Zillion sells to a customer — the default case)
- Zillion provides hardware, colocation, lease, or managed services to an end customer
- Counterparty role: `customer`
- Downstream: Architect produces hardware paths; Writer produces a Hardware Proposal
- Cue phrases: "they need GPUs," "their training workload," "we're proposing to them," "client budget"
- Example: Ab Initia Labs needs 128× Pro 6000 GPUs

### inbound_procurement (Zillion buys from a supplier)
- A vendor is offering hardware, capacity, or services to Zillion. Zillion is the buyer.
- Counterparty role: `supplier`
- Downstream: Architect produces an internal procurement evaluation memo with resale margin analysis; Writer produces an internal team brief (NOT customer-facing)
- Cue phrases: "GCP is offering us capacity," "PNY sent a quote for H200s," "supplier proposed," "Zillion buying"
- Example: GCP offering 512× H200 reserved capacity at $2.20/GPU/hr for Zillion to resell

### vendor_services (Zillion provides managed services on partner-owned hardware)
- The counterparty owns hardware; Zillion provides 24/7 L3 monitoring, incident response, software deployment, ongoing ops
- Counterparty role: `service-recipient`
- Downstream: Architect produces a Vendor Services Recommendation (pricing typically 8-12% of MSRP/year); Writer produces a Vendor Services Agreement
- Cue phrases: "they own the hardware," "we provide managed services," "partner-owned cluster," "monitoring and ops"
- Example: Cudo Ventures' 4,096 H100 fleet — Cudo owns the hardware, Zillion provides ops worldwide ($4.2M/year engagement)

### How to decide when direction is ambiguous
- If the document discusses BOTH a customer Zillion is selling to AND a supplier Zillion is buying from, set the top-level fields to the PRIMARY (most-developed) deal and populate `deal_threads[]` with the other threads (see Multi-Thread section below)
- If the deal type is uncertain, default to `outbound_sale` (most common) but flag uncertainty in `confidence.reasoning`

## Multi-Thread Transcripts

One conversation can contain multiple distinct deals. Real example: a GCP support Slack channel contained (a) Zillion procuring 512× H200 capacity from GCP, (b) a partnership/MSP discussion, (c) Phoenix Therapeutics asking about H200 access through Zillion. These are three deals with three directions.

When you detect 2+ separable deals:
1. Set top-level fields (deal_direction, client_name, budget, etc.) to the PRIMARY deal — the one with the most concrete details, dollar amounts, or named hardware
2. Populate `deal_threads[]` with ALL threads INCLUDING the primary:
   ```json
   {
     "title": "short label",
     "direction": "outbound_sale|inbound_procurement|vendor_services",
     "counterparty": "who they are",
     "summary": "1-2 sentences",
     "is_primary": true|false
   }
   ```
3. If only one deal is in the transcript, leave `deal_threads[]` empty

Decide multi-thread vs single deal based on: distinct counterparties (different companies/people), distinct workloads, distinct dollar amounts that do not reconcile to one deal, or explicit "separate from" language. Do not over-split — multiple GPU SKUs or timelines within one deal stays as ONE deal.

## Multi-Machine / Dense Spec Extraction

Some transcripts are dense per-machine spec sheets — one customer asking for multiple machines with different specs. Real pattern: a customer requesting 4 small VMs (each with different CPU/RAM/disk/network requirements) plus 1 bare-metal GPU server.

When the input describes 2+ machines with distinct specs:

1. **Capture each machine as a separate entry in `key_requirements`**, structured as machine number + spec list. Example: `"Machine 1: 2 cores, 4GB RAM, 50-100GB SSD, public IP, 10Mbps"`. Do not collapse multiple machines into one bullet — downstream agents need each machine spec preserved to size them individually.

2. **Note any customer-specific constraints attached to particular machines.** Examples: "only machine 1 needs public IP", "machine 5 must be co-located with machines 1-4 in the same DC", "machine 4 must use SSD specifically for ES inverted index reads". These often drive feasibility, not just sizing.

3. **Preserve original-language phrasing when ambiguous.** Translation can drop technical nuance, especially for non-English transcripts. The downstream Architect agent can work with either language.

## SME Questions — Internal Feasibility Uncertainties

Discovery surfaces two distinct kinds of unanswered questions, each going to a different field:

- **`follow_up_questions`**: questions the SALES team should ask the CUSTOMER in the next interaction. Customer-facing. Examples: "confirm whether 192GB VRAM is per-node or aggregate", "ask about data sovereignty requirements".
- **`sme_questions`**: questions ops should ask an INTERNAL subject matter expert before committing to the customer. These are feasibility uncertainties about Zillion's OWN capability — not gaps in customer information.

Each `sme_questions` entry has the shape:
```json
{
  "question": "specific question to ask",
  "sme_role": "generic role label — vm engineer | network engineer | dc ops | xander (pricing) | inventory ops",
  "why": "why we cannot answer this from public knowledge"
}
```

Use generic role tags, not specific names — the team knows who fills each role, and assignees rotate. Common patterns:

- VM provisioning capabilities (no-public-IP support, RAM expansion behavior, custom OS images) → `vm engineer`
- Inventory location & physical availability (spare parts not in the imported sheet) → `inventory ops`
- DC-level network constraints (custom routing, VLAN configurations) → `network engineer` or `dc ops`
- Pricing & vendor selection for custom builds → `xander (pricing)`

Only generate `sme_questions` when the transcript reveals a real Zillion-side capability uncertainty. Most simple deals have ZERO sme_questions — empty array is the normal case.

## Document Format Suggestion

Discovery includes a `document_format` field suggesting which downstream artifact the deal should produce. Architect uses this as a hint but may override based on its own analysis. Three valid values:

- **`feasibility_brief`** — small/simple deals. Triggers: ≤5 machines, OR estimated total under $50K, OR off-the-shelf specs with no training/cluster language, OR the customer is asking "can you do this?" rather than "build me a cluster". The right artifact is a feasibility brief + draft customer message, not a multi-page proposal. See proposal-writing skill Template D.
- **`quotation`** — medium outbound_sale deals ($50K-$300K) with defined scope. Two specific signals are required: (a) customer named a specific GPU model (e.g. "RTX 5090", "H100", "Pro 6000 SE"), and (b) customer named a quantity (e.g. "8 GPUs", "4 servers"). When both are present and the deal is in the $50K-$300K band with no large-cluster language, the customer has already decided what they want — they're ready to receive a transactional quote, not a sales pitch. The right artifact is a compact one-page quotation (Ab Initia Labs style). See proposal-writing skill Template E.
- **`full_proposal`** — large or operationally complex deals ($300K+, multi-region, multi-year, training clusters, or anything with deep scope-of-work needs like Cudo Ventures). Standard 12-section proposal (Template A) or services agreement (Template C).

Default to `full_proposal` if uncertain — it produces the most thorough document. Architect can downgrade if appropriate.

## Business Workflow Stages
Every deal moves through these stages. The agent must identify which stage the current interaction represents:

1. **Demand Discovery** — Initial contact. Client describes a vague compute need. Budget and GPU type usually unknown. Focus: qualify whether this is a real deal or exploration.
2. **Customer Contact** — First substantive meeting. Identify decision makers, budget authority, and timeline drivers. Focus: who decides, who pays, who blocks.
3. **Tech Discussion** — Architecture alignment call. GPU selection, VRAM requirements, NVLink vs PCIe, cluster topology. Focus: match workload to hardware.
4. **POC/Evaluation** — Proof-of-concept. Client tests on a single node or small cluster. Focus: benchmark results, NCCL configs, latency targets.
5. **Contract Negotiation** — Pricing, payment terms, SLA commitments, lease vs. buy. Focus: close the gap between client budget and Zillion cost floor.
6. **Deal Closing** — PO signed, MSA executed. Focus: handoff to deployment team.
7. **Service Delivery** — Hardware deployment, monitoring setup, ongoing ops. Focus: SLA adherence, upsell opportunities.

For `inbound_procurement` deals, stages map differently: Discovery → Quote Eval → Negotiation → PO → Receive → Resell. For `vendor_services`, stages are: Discovery → Scope → SLA negotiation → Contract → Ongoing ops.

## Qualification Criteria

### outbound_sale: HIGH PRIORITY (3+ true)
- Budget >$100K
- Timeline <8 weeks
- Specific GPU named (not "we need GPUs")
- Training workload (higher margin than inference)
- Client has existing cluster experience (knows what they want)
- Decision maker is on the call (CTO, VP Eng, not just an IC)

### outbound_sale: LOW FIT
- Budget <$50K (below Zillion's cost floor for managed services)
- Edge/self-managed deployment (no colo)
- Client wants cloud-style hourly billing only
- No timeline urgency

### inbound_procurement: HIGH PRIORITY
- Supplier price gives Zillion >25% resale margin against recent customer deals
- Volume tier matches Zillion's expected demand pipeline
- Lead time <12 weeks
- Warranty pass-through allowed

### inbound_procurement: LOW FIT
- Supplier price leaves <15% margin
- Volume requires >$5M committed capital with no matched customer demand
- Lead time >6 months
- No warranty pass-through

### vendor_services: HIGH PRIORITY
- Fleet size >100 GPUs (8-12% MSRP scales with hardware value)
- Multi-year term commitment
- Standardized hardware (Zillion ops team already supports it)
- Clear SLA expectations

### vendor_services: LOW FIT
- Fleet <50 GPUs (services revenue does not cover ops overhead)
- Exotic/custom hardware Zillion doesn't currently support
- Vague or unreasonable SLA expectations

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

## Chinese / Multilingual Transcripts

When the input is predominantly non-English (>25% CJK characters as a heuristic):
- Discovery extraction itself stays in English (downstream Architect prompts are English-only)
- Flag the language in confidence reasoning so Writer can translate the final proposal
- Preserve original-language proper nouns, technical terms, and customer-specific terminology verbatim — do not translate vendor names, GPU model names, or location names

## Past Deal Reference Patterns

### Successful outbound deals (use as confidence anchors)
- **Ab Initia Labs** — $2M, 128 GPUs (RTX Pro 6000 SE), pharma AI research, passthrough vs CX8 evaluation
- **Cudo Ventures** — $4.2M, 4,096 H100 SXM5 GPUs, managed services worldwide, largest engagement (NOTE: this is vendor_services, not outbound_sale)
- **Helios Foundation Models** — $892K, 152 GPUs (A100 + 4090 hybrid), 140B param training, cage at Ashburn
- **NovaStar AI** — $312K, inference cluster, 4× RTX 5090, P95 latency 74ms
- **Vertex Genomics** — $94K, co-location, customer-owned A100 at Dallas DC

### Lost deals (use for risk signals)
- **CloudMind Systems** — $76K, edge inference, budget mismatch ($65K ceiling vs $124K cost floor)
- **Meridian Robotics** — $540K pending, competitor (Lambda Labs) submitted $285K quote, price gap risk

## Output Format
Always return structured JSON with these fields:
```json
{
  "deal_direction": "outbound_sale|inbound_procurement|vendor_services",
  "counterparty_role": "customer|supplier|service-recipient",
  "client_name": "string (the counterparty's name regardless of direction)",
  "budget": "$X – $Y or Unknown",
  "gpu_preference": "specific GPU or Best fit",
  "workflow": "Training/Inference/Hybrid/Managed Services",
  "timeline": "string",
  "deal_stage": "Discovery/Tech Discussion/POC/Negotiation/Closing/Delivery",
  "business_model": "2-3 sentences",
  "rag_classification": "workload type matched to past deals",
  "key_requirements": ["array of specific technical needs"],
  "follow_up_questions": ["questions the sales team should ask the CUSTOMER (customer-facing)"],
  "sme_questions": [
    {
      "question": "internal capability question",
      "sme_role": "vm engineer | network engineer | dc ops | xander (pricing) | inventory ops",
      "why": "why we cannot answer this without internal SME confirmation"
    }
  ],
  "document_format": "feasibility_brief | quotation | full_proposal",
  "competitive_intel": "competitors mentioned or implied",
  "customer_supplied_hardware": false,
  "deal_threads": [
    {
      "title": "short label",
      "direction": "outbound_sale|inbound_procurement|vendor_services",
      "counterparty": "who",
      "summary": "1-2 sentences",
      "is_primary": true|false
    }
  ],
  "meeting_completeness": {
    "score": 0-10,
    "covered": ["topics actually addressed"],
    "missing": ["topics that should have been but weren't"],
    "reasoning": "brief"
  },
  "low_fit_flags": ["specific reasons this deal might not qualify"],
  "confidence": {
    "score": 7.5,
    "label": "High/Moderate/Low Confidence",
    "reasoning": "why, with past deal references",
    "matched_deals": ["deal — $XK status"]
  }
}
```

Note: `client_name` always holds the counterparty's name — even for `inbound_procurement` (the supplier's name) or `vendor_services` (the service recipient's name). It is NOT always a customer.

## Follow-Up Question Generation
The agent should generate 2-5 follow-up questions that are:
- Specific to THIS deal (not generic "what's your budget")
- Actionable by the sales team in the next meeting
- Focused on unresolved constraints that affect hardware selection
- Informed by what went wrong in similar past deals

For `inbound_procurement`, questions should focus on: volume tiers, lead time, warranty pass-through, payment terms, customer demand mapping.
For `vendor_services`, questions should focus on: fleet size, hardware standardization, SLA expectations, remote-access architecture, ops team capacity.

Examples:
- "Confirm whether 192GB VRAM is per-node or aggregate — this changes the recommendation from 5090 to Pro 6000"
- "Ask about data sovereignty: if biomedical data can't leave US, Ashburn DC is the only option"
- "Client mentioned CoreWeave queue times — quantify their current cloud spend for TCO comparison"
- (procurement) "Confirm whether warranty passes through to end customers — affects margin calculation"
- (vendor services) "Get fleet inventory breakdown by SKU — pricing tiers depend on hardware homogeneity"
