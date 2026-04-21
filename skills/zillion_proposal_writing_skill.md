# Skill: Zillion Proposal Writing

## Purpose
Generate client-ready hardware infrastructure proposals for Zillion Network. This skill encodes brand voice, required document structure, pricing formulas, SLA data, and competitive positioning.

## Brand Voice Rules
- Sophisticated, technically precise, execution-focused
- Sound like a senior CTO or DevOps engineer speaking to another technical professional
- NEVER use: "delve," "revolutionary," "in the ever-evolving landscape," "cutting-edge," "game-changing," or any AI cliché
- Use concrete numbers, not vague qualifiers. "$128,014 per server" not "competitively priced"
- Write in active voice. "Zillion deploys the cluster in 3 weeks" not "The cluster will be deployed"
- Reference specific past deployments when relevant: "Similar to our Helios Foundation Models engagement ($892K, 152 GPUs)"

## Required Proposal Sections (in order)
1. **Header** — `# Hardware Proposal — [Workload Type]`
2. **Metadata** — Client, Date, Reference (ZN-YYYY-MMDD-NNN), Prepared by: Zillion Network
3. **Executive Summary** — 2-3 paragraphs. Quantified: total cost, GPU count, VRAM, deployment timeline. Include payback analysis vs. cloud if applicable.
4. **Client Requirements** — Table: workload, budget, timeline, GPU preference, key requirements
5. **Proposed Hardware** — Specs table: GPU model, count, VRAM per node, cost per node, total
6. **Rack & Facility Plan** — Table: rack U, power kW, PDU, cooling, network fabric, DC location
7. **Cost Breakdown** — Itemized table: servers, rack, switches, cabling, PDU → hardware subtotal
8. **Colocation & Managed Services** — Monthly cost table using exact $448/kW math. SLA table. Managed scope summary.
9. **Alternatives Considered** — Table: config, VRAM, cost, elimination reason (from ToT analysis)
10. **Deployment Timeline** — Table using Zillion's 3-week pipeline
11. **Engagement Next Steps** — Weekly checklist with [ ] items and owners
12. **Footer** — `*Prepared by Zillion Network — Build. Train. Ship.*`

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
