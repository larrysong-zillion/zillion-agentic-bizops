# Skill: Zillion Proposal Writing
 
## Purpose
Generate client-ready hardware infrastructure proposals for Zillion Network. This skill encodes brand voice, required document structure, pricing formulas, SLA data, and competitive positioning.
 
## Brand Voice Rules
 
Voice differs by deal_direction. Customer proposals, internal procurement memos, and vendor services agreements have different audiences and different appropriate registers.
 
### outbound_sale (customer-facing hardware proposals) — DEFAULT
- Sophisticated, technically precise, execution-focused
- Sound like a senior CTO or DevOps engineer speaking to another technical professional
- The customer reading this is a sophisticated buyer — respect that
- Reference specific past deployments when relevant: "Similar to our Helios Foundation Models engagement ($892K, 152 GPUs)"
### inbound_procurement (internal memos for Zillion leadership)
- Direct, frank, action-oriented internal team brief — NOT a customer pitch
- Document is for Tony / Yuhan / Xander to make a decision
- Skip marketing language and pleasantries
- State risks plainly. If the supplier deal looks weak, say so. If it looks strong, justify with specific numbers
- Use "we" for Zillion. Numbers and tradeoffs matter more than narrative
- Output is an internal memo with reference `ZN-PROC-YYYY-MMDD-NNN`, NOT a customer-facing document
### vendor_services (operator-to-operator services agreements)
- Professional services agreement tone — operator-to-operator, peer infrastructure providers discussing terms
- Concrete about scope and SLAs. Numbers matter
- Not pitchy — this is a partnership document
- Output reference: `ZN-VS-YYYY-MMDD-NNN`
### Universal rules (all directions)
- NEVER use: "delve," "revolutionary," "in the ever-evolving landscape," "cutting-edge," "game-changing," or any AI cliché
- Use concrete numbers, not vague qualifiers. "$128,014 per server" not "competitively priced"
- Write in active voice. "Zillion deploys the cluster in 3 weeks" not "The cluster will be deployed"
## Document Templates — Direction-Specific
 
### Template A: Hardware Proposal (outbound_sale) — DEFAULT
 
Required sections in order:
1. **Header** — `# Hardware Proposal — [Workload Type]`
2. **Metadata** — Client, Date, Reference (`ZN-YYYY-MMDD-NNN`), Prepared by: Zillion Network
3. **Executive Summary** — 2-3 paragraphs. Quantified: total cost, GPU count, VRAM, deployment timeline. Include payback analysis vs. cloud if applicable.
4. **Client Requirements** — Table: workload, budget, timeline, GPU preference, key requirements
5. **Proposed Hardware** — Specs table: GPU model, count, VRAM per node, cost per node, total
6. **Rack & Facility Plan** — Table: rack U, power kW, PDU, cooling, network fabric, DC location
7. **Cost Breakdown** — Itemized table: servers, rack, switches, cabling, PDU → hardware subtotal
8. **Procurement Plan** (OPTIONAL — include ONLY when the upstream message contains a Procurement Plan block) — three sub-tables: From Zillion Inventory (existing SKU, qty, allocated cost = $0 since owned), To Purchase New (item, vendor suggestions, ~market price/unit, total est, marked "Pending Xander vendor selection"), To Rent from Upstream Provider when applicable. Include the Xander-callout at section start: "Procurement plan separates components already in Zillion inventory from those that need to be sourced. All purchase prices are market estimates pending Xander's vendor-selection and final negotiation."
9. **Colocation & Managed Services** — Monthly cost table using exact $448/kW math. SLA table. Managed scope summary.
10. **Alternatives Considered** — Table: config, VRAM, cost, elimination reason (from ToT analysis)
11. **Deployment Timeline** — Table using Zillion's 3-week pipeline
12. **Engagement Next Steps** — Weekly checklist with [ ] items and owners
13. **Footer** — `*Prepared by Zillion Network — Build. Train. Ship.*`
### Template B: Procurement Evaluation Memo (inbound_procurement)
 
Internal document for Zillion leadership. NOT customer-facing.
 
Required sections:
1. **Header** — `# Procurement Evaluation — [Supplier Name]`
2. **Metadata** — Supplier (not "Client"), Date, Reference `ZN-PROC-YYYY-MMDD-NNN`, Prepared by: Zillion Network, recipients: Tony/Yuhan/Xander
3. **Supplier Snapshot** — Who they are, what they offer, why they came to us
4. **Quote Summary** — Hardware/capacity, unit prices, volume tiers, lead time, warranty
5. **Resale Margin Analysis** — Compare supplier pricing to recent comparable customer deals (pulled from tracker). Compute concrete margin scenarios with real numbers, not abstract percentages. If margin is below acceptable threshold, flag it explicitly.
6. **8-Point Evaluation Checklist** — pricing, lead time, warranty pass-through, resale rights, payment terms, quality/QA, volume commitment, termination clauses
7. **Recommended Next Steps** — Who reviews (CFO/Ops/Legal), customer demand mapping, sign/decline recommendation
8. **Risk Assessment** — Concrete risks with severity ratings
9. **Footer** — `*Internal memo. NOT a customer document.*`
### Template C: Vendor Services Agreement (vendor_services)
 
Required sections:
1. **Header** — `# Vendor Services Agreement — [Partner Name]`
2. **Metadata** — Partner (not "Client"), Date, Reference `ZN-VS-YYYY-MMDD-NNN`, Prepared by: Zillion Network
3. **Executive Summary** — Partner-owned hardware, Zillion-provided services scope, annual fee, term
4. **Services Scope** — 24/7 L3 monitoring, incident response, software deployment, troubleshooting, monthly reporting (Cudo Ventures pattern)
5. **Pricing Structure** — Hardware MSRP basis, services fee as % of MSRP/year (typical 8-12%), monthly retainer
6. **SLA Commitments** — Incident response <15 min, hardware swap coordination <4hr, monitoring uptime, monthly utilization reports
7. **Out-of-Scope Rates** — Hourly rates for non-standard work, escalation tiers
8. **Contract Terms** — Term length, renewal, termination notice, payment terms, SLA penalty credits
9. **Operational Readiness** — Remote-access architecture, monitoring tool compatibility, ops team capacity
10. **Next Steps** — Kickoff timeline, data access provisioning, monitoring tool integration
11. **Footer** — `*Prepared by Zillion Network — Operate. Monitor. Support.*`
DO NOT mention Zillion-sold hardware, Zillion-owned colocation, or anything implying Zillion provides the physical infrastructure.
 
## Proposal Length Must Match Deal Size
 
A $30K deal does not need a 12-section proposal. Match document length to deal complexity.
 
- Recommendation totals under $100K OR customer asks for fewer than 4 machines → produce a CONDENSED proposal:
  - 1-2 paragraph summary
  - 1 BOM table
  - 1 deployment timeline
  - 1 next-steps list
  - Skip Alternatives Considered, skip TCO comparison sections, skip lease-vs-CapEx tables, skip extended SLA tables
- Recommendation $100K-$500K → full 12-section template, all tables, but compact
- Recommendation >$500K → full template with extended sections (cluster scaling, multi-year TCO, deployment phasing)
Customers ordering small VM clusters do NOT want to read about lease vs CapEx tradeoffs and 24/7 L3 managed services SLAs — that is over-selling. Save the long-form proposal for deals over $200K.
 
## Multilingual Output
 
When the upstream Discovery flagged the transcript as non-English (or the user explicitly enables the Chinese language toggle):
- Translate the ENTIRE document body to Simplified Chinese (简体中文)
- Translate all section headers, descriptions, and prose into natural, professional Mandarin
- KEEP these elements unchanged in their canonical form:
  - Numeric values ($448/kW, $2,240/mo, 99.95%)
  - Proper nouns (Zillion, Anthropic, vendor names)
  - GPU model names (H100, H200, RTX Pro 6000)
  - Location names (Irvine, Dallas, Ashburn)
  - Reference ID format (ZN-YYYY-MMDD-NNN)
  - Software stack names (Ubuntu, Ansible, DCGM, Slurm, NCCL)
- Use industry-standard Chinese technical terminology: 训练 (training), 推理 (inference), 集群 (cluster), 托管 (colocation), 月费 (monthly fee), 部署 (deployment)
- Tone matches the deal direction (formal for customer-facing, direct for internal memos)
## Pricing Reference Data
 
### Hardware (Customer-Owned, 10% margin)
| SKU | GPU | VRAM/GPU | Price | Stock | Arch |
|---|---|---|---|---|---|
| 4090-8x | RTX 4090 | 24GB | $28,000 | 12 | passthrough |
| 5090-8x | RTX 5090 | 32GB | $52,000 | 6 | passthrough |
| 4090-4x | RTX 4090 | 24GB | $15,500 | 8 | passthrough |
| 5090-4x | RTX 5090 | 32GB | $29,000 | 0 (pre-order) | passthrough |
| A100-8x | A100 80GB | 80GB | $180,000 | 2 | NVLink |
| PRO6000-8x-PT | RTX Pro 6000 SE | 96GB | $128,014 | 5 | passthrough (CX6 100GbE) |
| PRO6000-8x-CX8 | RTX Pro 6000 SE | 96GB | ~$200,000 | 3 | MGX CX8 (800GbE) |
| H100-8x | H100 SXM5 | 80GB | $280,000 | 0 (pre-order) | NVLink + InfiniBand |
 
### Colocation (Irvine CA, Dallas TX, Ashburn VA)
- Power: $448/kW/month (metered)
- Typical 8-GPU server = 5kW = $2,240/mo
- IP block (/29, 5 usable): $50/mo
- Cross-connect: $150 one-time
- Managed services: INCLUDED in colo fee
### Managed Services Scope (included, not line-item)
- Hardware monitoring: IPMI/BMC, temps, fans, PSU — 24/7, auto-ticket
- GPU monitoring: nvidia-smi, ECC errors, thermal — every 60s, alert <15min
- Network monitoring: uplink status, latency, packet loss — auto-failover
- OS & firmware: security patches, BIOS/BMC — monthly or critical
- Physical ops: cable management, drive swaps — remote hands included
- Backup: config backup daily, RAID monitoring
### SLAs
| Metric | Target | Penalty |
|---|---|---|
| Network uptime | 99.95% | 5% credit per 0.1% below |
| Power uptime | 99.99% | N+1 redundancy, UPS + generator |
| Incident response | <15 min | From alert to engineer assigned |
| Hardware replacement | <4 hours | Spare parts on-site |
| Scheduled maintenance | 72hr notice | Customer approval required |
 
### GPU Lease Rates
| Scale | 12-month | 24-month | Deposit |
|---|---|---|---|
| 8 GPU | $1.42/GPU/hr | $1.32/GPU/hr | 1 month |
| 64 GPU | $1.35/GPU/hr | $1.25/GPU/hr | 1 month |
| 128 GPU | $1.25/GPU/hr | $1.15/GPU/hr | 2 months |
 
### Deployment Pipeline (3 weeks)
- Week 0–0.5: Hardware setup, IPMI config, rack and cable
- Week 0.5–1.5: Software deployment (Ansible: Ubuntu 22.04, DCGM 3.3.7, UFM, Slurm, NCCL, NVIDIA Container Toolkit)
- Week 1.5–2.5: Burn-in testing, MLPerf benchmarks, thermal stress
- Week 2.5–3: Buffer for fixes, delivery handover
## Competitive Positioning
When comparing to competitors, use these differentiators:
1. Zillion deploys in 3 weeks vs. 6-8 weeks industry average
2. Managed services included in colo — not a separate $5-10K/mo line item
3. <15min incident response SLA with on-site spare parts
4. Dual architecture options: passthrough (cost-optimized) vs CX8 (training-optimized)
5. Real-time GPU monitoring at 60s intervals vs industry-standard 5-min polling
6. Case study: identified IB transceiver port-flapping issue 1 month before a leading hyperscaler
7. Transparent pricing: customer owns the hardware, no lock-in
