"""
Zillion Network — AI-Driven Needs Assessment & Proposal Generation
===================================================================
Backend Simulation: 3-Agent Prompt-Chaining Architecture

Agents:
  1. The Listener  — Extracts constraints from raw meeting transcripts
  2. The Engineer  — CoT reasoning over inventory to recommend hardware
  3. The Author    — Generates formatted Markdown proposal

Usage:
  python zillion_backend.py
"""

import json
import textwrap
from datetime import datetime, timedelta
from typing import Any

# ═══════════════════════════════════════════════════════════════════════
# MOCK DATA
# ═══════════════════════════════════════════════════════════════════════

DUMMY_TRANSCRIPT = """
Call with DataForge AI — March 27, 2026
Participants: Raj Mehta (CTO, DataForge), Sandra Liu (ML Lead, DataForge),
              Xander Cole (Zillion), Yuhan Park (Zillion)

Xander: Thanks for jumping on. Walk us through what you're trying to accomplish.

Raj: We're building a multi-modal foundation model — text plus image embeddings,
roughly 13B parameters. Right now we're doing full fine-tuning runs on rented
A100 boxes through CoreWeave but the costs are brutal, something like $38k/month
and the queue times kill our iteration speed.

Sandra: Yeah, our training runs are 4-6 days each. We usually kick off 2-3
concurrent runs with different hyperparameter sweeps. The dataset is about 2.3TB
after preprocessing, mostly parquet and image shards.

Yuhan: What's your ideal budget range for owned hardware?

Raj: We've got board approval for somewhere between $400k and $550k. We'd rather
be closer to $400k but we can stretch if the perf uplift is there. Our CFO wants
a 14-month payback window vs continued cloud spend.

Sandra: One thing — we also need to run inference for our API product. It's maybe
20% of our compute but it's latency-sensitive, sub-200ms p99. We'd love to not
need separate inference boxes if possible.

Xander: Timeline?

Raj: We need hardware racked and training by end of May. Aggressive, I know.

Sandra: Oh, and NVLink is non-negotiable. We tried PCIe-only last year and the
all-reduce was a bottleneck. Also we need at least 256GB total VRAM across the
training cluster for our model to fit with our current sharding strategy.

Raj: Last thing — power and cooling. Our colo facility caps us at 45kW for this
deployment. We've got standard 208V/30A circuits.
"""

MOCK_INVENTORY = [
    {
        "sku": "ZN-4090-8N",
        "name": "Zillion 4090 Cluster — 8-Node",
        "gpu": "NVIDIA RTX 4090",
        "gpu_count": 8,
        "vram_per_gpu_gb": 24,
        "total_vram_gb": 192,
        "interconnect": "NVLink Bridge (2-way per pair)",
        "fp16_tflops_per_gpu": 82.6,
        "fp16_tflops_cluster": 660.8,
        "tdp_per_gpu_w": 450,
        "total_system_power_kw": 5.8,
        "storage_tb": 8,
        "network": "100GbE RDMA",
        "price_usd": 52_000,
        "lead_time_weeks": 2,
        "in_stock": 14,
        "notes": "Consumer-grade GPU. NVLink limited to 2-way bridge pairs, no full mesh.",
    },
    {
        "sku": "ZN-4090-16N",
        "name": "Zillion 4090 Cluster — 16-Node",
        "gpu": "NVIDIA RTX 4090",
        "gpu_count": 16,
        "vram_per_gpu_gb": 24,
        "total_vram_gb": 384,
        "interconnect": "NVLink Bridge (2-way per pair) + 100GbE fabric",
        "fp16_tflops_per_gpu": 82.6,
        "fp16_tflops_cluster": 1321.6,
        "tdp_per_gpu_w": 450,
        "total_system_power_kw": 11.2,
        "storage_tb": 16,
        "network": "100GbE RDMA",
        "price_usd": 98_000,
        "lead_time_weeks": 3,
        "in_stock": 6,
        "notes": "Good raw FLOPS/$. NVLink topology limits all-reduce at scale.",
    },
    {
        "sku": "ZN-5090-8N",
        "name": "Zillion 5090 Cluster — 8-Node",
        "gpu": "NVIDIA RTX 5090",
        "gpu_count": 8,
        "vram_per_gpu_gb": 32,
        "total_vram_gb": 256,
        "interconnect": "NVLink 5.0 (full mesh, 900 GB/s per GPU)",
        "fp16_tflops_per_gpu": 104.8,
        "fp16_tflops_cluster": 838.4,
        "tdp_per_gpu_w": 575,
        "total_system_power_kw": 7.2,
        "storage_tb": 8,
        "network": "200GbE RDMA",
        "price_usd": 78_000,
        "lead_time_weeks": 4,
        "in_stock": 9,
        "notes": "Blackwell arch. Full NVLink mesh. Strong inference perf with FP4 engine.",
    },
    {
        "sku": "ZN-5090-16N",
        "name": "Zillion 5090 Cluster — 16-Node",
        "gpu": "NVIDIA RTX 5090",
        "gpu_count": 16,
        "vram_per_gpu_gb": 32,
        "total_vram_gb": 512,
        "interconnect": "NVLink 5.0 (full mesh, 900 GB/s per GPU)",
        "fp16_tflops_per_gpu": 104.8,
        "fp16_tflops_cluster": 1676.8,
        "tdp_per_gpu_w": 575,
        "total_system_power_kw": 14.0,
        "storage_tb": 16,
        "network": "200GbE RDMA",
        "price_usd": 148_000,
        "lead_time_weeks": 5,
        "in_stock": 4,
        "notes": "Top-tier consumer GPU cluster. Full NVLink mesh at 16 GPUs.",
    },
    {
        "sku": "ZN-5090-32N",
        "name": "Zillion 5090 Cluster — 32-Node",
        "gpu": "NVIDIA RTX 5090",
        "gpu_count": 32,
        "vram_per_gpu_gb": 32,
        "total_vram_gb": 1024,
        "interconnect": "NVLink 5.0 + NVSwitch fabric",
        "fp16_tflops_per_gpu": 104.8,
        "fp16_tflops_cluster": 3353.6,
        "tdp_per_gpu_w": 575,
        "total_system_power_kw": 27.5,
        "storage_tb": 32,
        "network": "400GbE RDMA",
        "price_usd": 285_000,
        "lead_time_weeks": 6,
        "in_stock": 2,
        "notes": "Enterprise-scale consumer GPU cluster. NVSwitch for full bisection bandwidth.",
    },
]

GOLDEN_PROPOSAL_STYLE = """
# Proposal Structure (Golden Template)
- Executive Summary: 3 sentences max. State the problem, the solution, the payback.
- Recommended Configuration: Table of specs. No filler.
- Decision Rationale: Numbered reasoning steps. Show the math.
- Alternatives Considered: Brief table of what was ruled out and why.
- Deployment Timeline: Week-by-week Gantt-style breakdown.
- Cost Analysis: Total cost, monthly cloud equivalent, payback period.
- Next Steps: Concrete action items with owners.
"""


# ═══════════════════════════════════════════════════════════════════════
# AGENT 1: THE LISTENER
# ═══════════════════════════════════════════════════════════════════════

def listener_agent(transcript: str) -> dict[str, Any]:
    """
    Parses a raw meeting transcript and extracts structured constraints.
    
    In production, this calls Claude API with a structured-extraction prompt.
    For the simulation, we use keyword heuristics as a stand-in.
    """
    # --- Simulated extraction (mocks what the LLM would return) ---
    constraints = {
        "client": "DataForge AI",
        "contacts": [
            {"name": "Raj Mehta", "role": "CTO"},
            {"name": "Sandra Liu", "role": "ML Lead"},
        ],
        "project_type": "Multi-modal foundation model training (13B params, text+image)",
        "workflow_split": {
            "training_pct": 80,
            "inference_pct": 20,
        },
        "budget": {
            "min_usd": 400_000,
            "max_usd": 550_000,
            "preference": "Closer to $400K, will stretch for clear perf gains",
            "payback_window_months": 14,
            "current_cloud_spend_monthly_usd": 38_000,
        },
        "performance_requirements": {
            "concurrent_training_runs": 3,
            "training_run_duration_days": "4-6",
            "dataset_size_tb": 2.3,
            "min_total_vram_gb": 256,
            "inference_latency_p99_ms": 200,
        },
        "hard_constraints": {
            "nvlink_required": True,
            "nvlink_note": "PCIe-only caused all-reduce bottleneck previously",
            "max_power_kw": 45,
            "power_circuits": "208V/30A",
            "deadline": "End of May 2026 — racked and training",
        },
        "nice_to_haves": [
            "Unified training + inference on same hardware",
            "Minimize separate inference boxes",
        ],
        "extracted_at": datetime.now().isoformat(),
    }
    return constraints


# ═══════════════════════════════════════════════════════════════════════
# AGENT 2: THE ENGINEER
# ═══════════════════════════════════════════════════════════════════════

def engineer_agent(
    constraints: dict[str, Any],
    inventory: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Chain-of-Thought hardware recommendation engine.
    
    Evaluates every SKU against extracted constraints, scores them,
    and returns a ranked recommendation with full reasoning trace.
    """
    cot_log: list[str] = []
    budget_max = constraints["budget"]["max_usd"]
    budget_min = constraints["budget"]["min_usd"]
    min_vram = constraints["performance_requirements"]["min_total_vram_gb"]
    max_power = constraints["hard_constraints"]["max_power_kw"]
    nvlink_required = constraints["hard_constraints"]["nvlink_required"]
    concurrent_runs = constraints["performance_requirements"]["concurrent_training_runs"]
    cloud_spend = constraints["budget"]["current_cloud_spend_monthly_usd"]
    payback_months = constraints["budget"]["payback_window_months"]

    cot_log.append("═══ ENGINEER AGENT: Chain-of-Thought Analysis ═══")
    cot_log.append("")
    cot_log.append(f"Step 1 — Hard Constraint Filter")
    cot_log.append(f"  Budget ceiling:  ${budget_max:,}")
    cot_log.append(f"  Min VRAM:        {min_vram} GB")
    cot_log.append(f"  Max power:       {max_power} kW")
    cot_log.append(f"  NVLink required: {nvlink_required}")
    cot_log.append("")

    # We need enough units to support 3 concurrent runs within budget + power.
    # Evaluate multi-unit configs.
    candidates = []

    for sku in inventory:
        cot_log.append(f"  Evaluating: {sku['name']} (${sku['price_usd']:,}/unit)")

        # Determine how many units we can fit
        max_by_budget = budget_max // sku["price_usd"]
        max_by_power = int(max_power // sku["total_system_power_kw"])
        max_by_stock = sku["in_stock"]
        max_units = min(max_by_budget, max_by_power, max_by_stock)

        if max_units < 1:
            reason = []
            if max_by_budget < 1:
                reason.append("exceeds budget")
            if max_by_power < 1:
                reason.append("exceeds power cap")
            if max_by_stock < 1:
                reason.append("out of stock")
            cot_log.append(f"    ✗ ELIMINATED — {', '.join(reason)}")
            cot_log.append("")
            continue

        # Find optimal unit count: enough for concurrent runs
        # Each unit can run 1 training job. Need >= concurrent_runs units for training.
        # Plus headroom for inference.
        ideal_units = concurrent_runs  # 1 unit per concurrent run
        if sku["total_vram_gb"] * ideal_units < min_vram:
            # Need more units to meet VRAM floor
            ideal_units = max(ideal_units, -(-min_vram // sku["total_vram_gb"]))  # ceil div

        chosen_units = min(ideal_units, max_units)
        total_cost = chosen_units * sku["price_usd"]
        total_vram = chosen_units * sku["total_vram_gb"]
        total_power = chosen_units * sku["total_system_power_kw"]
        total_flops = chosen_units * sku["fp16_tflops_cluster"]
        total_lead = sku["lead_time_weeks"]

        # NVLink quality check
        nvlink_full_mesh = "full mesh" in sku["interconnect"].lower() or "nvswitch" in sku["interconnect"].lower()
        nvlink_partial = "nvlink" in sku["interconnect"].lower()

        cot_log.append(f"    Units: {chosen_units}x | Cost: ${total_cost:,} | VRAM: {total_vram} GB")
        cot_log.append(f"    Power: {total_power:.1f} kW | FP16: {total_flops:.1f} TFLOPS")
        cot_log.append(f"    NVLink: {'Full mesh' if nvlink_full_mesh else 'Partial (bridge pairs)' if nvlink_partial else 'None'}")

        # Constraint checks
        passes = True
        flags = []

        if total_vram < min_vram:
            flags.append(f"VRAM short: {total_vram} < {min_vram} GB")
            passes = False
        if total_power > max_power:
            flags.append(f"Power over: {total_power:.1f} > {max_power} kW")
            passes = False
        if total_cost > budget_max:
            flags.append(f"Over budget: ${total_cost:,} > ${budget_max:,}")
            passes = False
        if nvlink_required and not nvlink_partial:
            flags.append("No NVLink")
            passes = False

        # Soft penalties
        penalties = []
        if nvlink_required and not nvlink_full_mesh:
            penalties.append("NVLink is bridge-only, not full mesh — will bottleneck all-reduce on 13B model")
        if chosen_units < concurrent_runs:
            penalties.append(f"Only {chosen_units} units for {concurrent_runs} concurrent runs — must time-share")

        # Deadline check
        delivery_date = datetime.now() + timedelta(weeks=total_lead)
        deadline = datetime(2026, 5, 31)
        if delivery_date > deadline:
            penalties.append(f"Lead time {total_lead}wk — delivery ~{delivery_date.strftime('%b %d')} may miss May deadline")

        if not passes:
            cot_log.append(f"    ✗ ELIMINATED — {'; '.join(flags)}")
            cot_log.append("")
            continue

        # Scoring: FLOPS/$ weighted, with penalty adjustments
        flops_per_dollar = total_flops / total_cost * 1000  # TFLOPS per $1000
        payback_months_actual = total_cost / cloud_spend if cloud_spend > 0 else 999
        score = flops_per_dollar * 100

        # Bonuses
        if nvlink_full_mesh:
            score *= 1.25  # 25% bonus for full mesh NVLink
            cot_log.append(f"    ↑ +25% score bonus: full NVLink mesh (critical for all-reduce)")
        if total_cost <= budget_min:
            score *= 1.10  # 10% bonus for being in preferred budget range
            cot_log.append(f"    ↑ +10% score bonus: within preferred budget (≤${budget_min:,})")
        if sku["gpu"] == "NVIDIA RTX 5090":
            score *= 1.15  # 15% bonus for Blackwell inference capabilities (FP4)
            cot_log.append(f"    ↑ +15% score bonus: Blackwell FP4 engine (dual-use training+inference)")

        # Penalties
        for p in penalties:
            score *= 0.80
            cot_log.append(f"    ↓ -20% score penalty: {p}")

        cot_log.append(f"    SCORE: {score:.1f} | Payback: {payback_months_actual:.1f} months")
        cot_log.append(f"    {'✓ PASSES' if passes else '✗ FAIL'}")
        cot_log.append("")

        candidates.append({
            "sku": sku["sku"],
            "name": sku["name"],
            "units": chosen_units,
            "gpu": sku["gpu"],
            "gpu_count_per_unit": sku["gpu_count"],
            "total_gpus": chosen_units * sku["gpu_count"],
            "total_vram_gb": total_vram,
            "total_flops_tflops": total_flops,
            "total_power_kw": total_power,
            "total_cost_usd": total_cost,
            "interconnect": sku["interconnect"],
            "nvlink_full_mesh": nvlink_full_mesh,
            "network": sku["network"],
            "storage_tb": chosen_units * sku["storage_tb"],
            "lead_time_weeks": total_lead,
            "payback_months": payback_months_actual,
            "score": score,
            "penalties": penalties,
            "notes": sku["notes"],
        })

    # Rank
    candidates.sort(key=lambda c: c["score"], reverse=True)

    cot_log.append("Step 2 — Ranking")
    for i, c in enumerate(candidates):
        marker = "★ RECOMMENDED" if i == 0 else ""
        cot_log.append(f"  #{i+1}: {c['name']} ×{c['units']} — Score {c['score']:.1f} "
                       f"(${c['total_cost_usd']:,}) {marker}")
    cot_log.append("")

    if not candidates:
        cot_log.append("  ⚠ NO VIABLE CANDIDATES — escalate to human review.")
        return {"cot_log": cot_log, "recommendation": None, "alternatives": []}

    recommended = candidates[0]
    alternatives = candidates[1:]

    cot_log.append(f"Step 3 — Final Recommendation")
    cot_log.append(f"  {recommended['name']} ×{recommended['units']}")
    cot_log.append(f"  {recommended['total_gpus']} GPUs | {recommended['total_vram_gb']} GB VRAM | "
                   f"{recommended['total_flops_tflops']:.1f} TFLOPS")
    cot_log.append(f"  ${recommended['total_cost_usd']:,} | Payback: {recommended['payback_months']:.1f}mo")
    cot_log.append(f"  Lead time: {recommended['lead_time_weeks']} weeks")
    if recommended["penalties"]:
        cot_log.append(f"  ⚠ Flags: {'; '.join(recommended['penalties'])}")
    cot_log.append("")
    cot_log.append("═══ AWAITING HUMAN APPROVAL (Xander / Yuhan) ═══")

    return {
        "cot_log": cot_log,
        "recommendation": recommended,
        "alternatives": alternatives,
    }


# ═══════════════════════════════════════════════════════════════════════
# AGENT 3: THE AUTHOR
# ═══════════════════════════════════════════════════════════════════════

def author_agent(
    constraints: dict[str, Any],
    recommendation: dict[str, Any],
    alternatives: list[dict[str, Any]],
) -> str:
    """
    Generates a Markdown proposal from the Engineer's output.
    
    In production, this calls Claude API with the golden template + specs.
    """
    client = constraints["client"]
    rec = recommendation
    budget = constraints["budget"]
    perf = constraints["performance_requirements"]
    deadline = constraints["hard_constraints"]["deadline"]

    alt_rows = ""
    for alt in alternatives[:3]:
        reason = "; ".join(alt["penalties"]) if alt["penalties"] else "Lower composite score"
        alt_rows += (
            f"| {alt['name']} ×{alt['units']} | {alt['total_gpus']} | "
            f"{alt['total_vram_gb']} GB | ${alt['total_cost_usd']:,} | {reason} |\n"
        )
    if not alt_rows:
        alt_rows = "| — | — | — | — | No other viable configurations |\n"

    proposal = textwrap.dedent(f"""\
    # Hardware Proposal: {client}
    **Prepared by:** Zillion Network  
    **Date:** {datetime.now().strftime('%B %d, %Y')}  
    **Status:** DRAFT — Pending approval (Xander Cole / Yuhan Park)

    ---

    ## Executive Summary

    {client} requires dedicated compute for training a 13B-parameter multi-modal foundation model, replacing a $38K/month cloud spend. We recommend **{rec['units']}× {rec['name']}** — a {rec['total_gpus']}-GPU deployment delivering {rec['total_flops_tflops']:.0f} TFLOPS of FP16 compute with {rec['total_vram_gb']} GB total VRAM at **${rec['total_cost_usd']:,}**, achieving full payback in **{rec['payback_months']:.1f} months** against current cloud costs.

    ---

    ## Recommended Configuration

    | Spec | Value |
    |---|---|
    | SKU | {rec['sku']} |
    | Configuration | {rec['units']}× {rec['name']} |
    | GPU | {rec['gpu']} |
    | Total GPUs | {rec['total_gpus']} |
    | VRAM (Total) | {rec['total_vram_gb']} GB |
    | FP16 Throughput | {rec['total_flops_tflops']:.1f} TFLOPS |
    | Interconnect | {rec['interconnect']} |
    | Network | {rec['network']} |
    | Storage | {rec['storage_tb']} TB NVMe |
    | Total Power Draw | {rec['total_power_kw']:.1f} kW |
    | Unit Cost | ${rec['total_cost_usd'] // rec['units']:,} /unit |
    | **Total Cost** | **${rec['total_cost_usd']:,}** |
    | Lead Time | {rec['lead_time_weeks']} weeks from PO |

    ---

    ## Decision Rationale

    1. **VRAM Clearance** — {client}'s 13B model requires ≥{perf['min_total_vram_gb']} GB for sharded training. This config provides {rec['total_vram_gb']} GB ({rec['total_vram_gb'] - perf['min_total_vram_gb']} GB headroom for optimizer states and activation checkpoints).

    2. **NVLink Topology** — {'Full-mesh NVLink 5.0 at 900 GB/s per GPU eliminates the all-reduce bottleneck that blocked their previous PCIe-only deployment. This is critical for distributed training at 13B scale.' if rec['nvlink_full_mesh'] else 'Bridge-pair NVLink. Adequate for this workload but monitor all-reduce performance at scale.'}

    3. **Concurrent Training** — {rec['units']} independent cluster units support {perf['concurrent_training_runs']} concurrent hyperparameter sweeps without resource contention.

    4. **Inference Co-location** — {'The RTX 5090 Blackwell architecture includes an FP4 inference engine, enabling sub-200ms p99 latency on dedicated inference partitions without separate hardware. This addresses the 80/20 training/inference split on a single fleet.' if '5090' in rec['gpu'] else 'The 4090 can serve inference workloads but lacks dedicated low-precision inference engines. Consider reserving 1 unit for inference-only.'}

    5. **Power Compliance** — {rec['total_power_kw']:.1f} kW total draw sits {'well within' if rec['total_power_kw'] < constraints['hard_constraints']['max_power_kw'] * 0.8 else 'within'} the {constraints['hard_constraints']['max_power_kw']} kW facility cap ({constraints['hard_constraints']['max_power_kw'] - rec['total_power_kw']:.1f} kW remaining for networking, cooling overhead, and future expansion).

    6. **Budget Fit** — ${rec['total_cost_usd']:,} falls {'within the preferred range' if rec['total_cost_usd'] <= budget['min_usd'] else 'within the approved ceiling'} (${budget['min_usd']:,}–${budget['max_usd']:,}).

    ---

    ## Alternatives Considered

    | Configuration | GPUs | VRAM | Cost | Reason Not Selected |
    |---|---|---|---|---|
    {alt_rows}
    ---

    ## Deployment Timeline

    | Week | Milestone |
    |---|---|
    | Week 0 | PO signed, hardware allocated from Zillion inventory |
    | Week 1–{rec['lead_time_weeks']} | Hardware staging, burn-in testing, OS imaging |
    | Week {rec['lead_time_weeks']+1} | Ship to {client} colo facility |
    | Week {rec['lead_time_weeks']+2} | Rack, cable, power validation (208V/30A circuits) |
    | Week {rec['lead_time_weeks']+3} | Network config, NVLink topology verification, NCCL benchmarks |
    | Week {rec['lead_time_weeks']+4} | Workload onboarding — migrate training scripts, validate data pipeline |
    | Week {rec['lead_time_weeks']+5} | Full production training begins |

    **Target: Production training live by end of May 2026.**

    ---

    ## Cost Analysis

    | Metric | Value |
    |---|---|
    | Hardware Investment | ${rec['total_cost_usd']:,} |
    | Current Cloud Spend | ${budget['current_cloud_spend_monthly_usd']:,}/month |
    | Cloud Cost (14 months) | ${budget['current_cloud_spend_monthly_usd'] * 14:,} |
    | **Payback Period** | **{rec['payback_months']:.1f} months** |
    | **14-Month Savings** | **${(budget['current_cloud_spend_monthly_usd'] * 14) - rec['total_cost_usd']:,}** |
    | Ongoing Costs (est.) | ~$2,800/month (power, colo, maintenance) |

    ---

    ## Next Steps

    | Action | Owner | Deadline |
    |---|---|---|
    | Review and approve this proposal | Xander Cole / Yuhan Park | — |
    | Send proposal to {client} | Yuhan Park | — |
    | Receive PO and payment terms | {client} | — |
    | Begin hardware staging | Zillion Ops | PO + 1 day |
    | Schedule colo rack date | {client} + Zillion | PO + 1 week |

    ---

    *This proposal was generated by the Zillion Network AI Proposal System and is pending human review.*  
    *Zillion Network — Build. Train. Ship.*
    """)

    return proposal


# ═══════════════════════════════════════════════════════════════════════
# WORKFLOW ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════

def simulate_workflow(transcript: str | None = None) -> dict[str, Any]:
    """
    Runs the full 3-agent pipeline and returns all intermediate + final outputs.
    """
    transcript = transcript or DUMMY_TRANSCRIPT

    print("=" * 72)
    print("  ZILLION NETWORK — AI Proposal Pipeline (Simulation)")
    print("=" * 72)

    # Agent 1
    print("\n▶ AGENT 1: The Listener — Extracting constraints...")
    constraints = listener_agent(transcript)
    print(f"  ✓ Extracted {len(constraints)} constraint fields for {constraints['client']}")
    print(f"  Budget: ${constraints['budget']['min_usd']:,}–${constraints['budget']['max_usd']:,}")
    print(f"  VRAM floor: {constraints['performance_requirements']['min_total_vram_gb']} GB")
    print(f"  Power cap: {constraints['hard_constraints']['max_power_kw']} kW")

    # Agent 2
    print("\n▶ AGENT 2: The Engineer — Running CoT hardware analysis...")
    engineer_result = engineer_agent(constraints, MOCK_INVENTORY)
    for line in engineer_result["cot_log"]:
        print(f"  {line}")

    if not engineer_result["recommendation"]:
        print("\n⚠ Pipeline halted — no viable hardware configuration found.")
        return {
            "constraints": constraints,
            "engineer_result": engineer_result,
            "proposal": None,
        }

    # Human-in-the-loop gate
    print("\n" + "─" * 72)
    print("  ⏸  HUMAN-IN-THE-LOOP: Recommendation ready for review.")
    print(f"     Recommended: {engineer_result['recommendation']['name']} "
          f"×{engineer_result['recommendation']['units']}")
    print(f"     Cost: ${engineer_result['recommendation']['total_cost_usd']:,}")
    print("     (In production, this pauses for Xander/Yuhan approval)")
    print("─" * 72)

    # Agent 3
    print("\n▶ AGENT 3: The Author — Generating proposal...")
    proposal = author_agent(
        constraints,
        engineer_result["recommendation"],
        engineer_result["alternatives"],
    )
    print("  ✓ Proposal generated (Markdown)")
    print(f"  Length: {len(proposal)} characters, {proposal.count(chr(10))} lines")

    print("\n" + "=" * 72)
    print("  PIPELINE COMPLETE")
    print("=" * 72)

    return {
        "constraints": constraints,
        "engineer_result": engineer_result,
        "proposal": proposal,
    }


# ═══════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    result = simulate_workflow()

    print("\n\n" + "=" * 72)
    print("  GENERATED PROPOSAL")
    print("=" * 72 + "\n")
    if result["proposal"]:
        print(result["proposal"])
    else:
        print("No proposal generated.")
