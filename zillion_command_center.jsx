import { useState, useEffect, useRef, useCallback } from "react";

// ═══════════════════════════════════════════════════════════════════════
// MOCK DATA (mirrors Python backend)
// ═══════════════════════════════════════════════════════════════════════

const DUMMY_TRANSCRIPT = `Call with DataForge AI — March 27, 2026
Participants: Raj Mehta (CTO, DataForge), Sandra Liu (ML Lead, DataForge),
              Xander Cole (Zillion), Yuhan Park (Zillion)

Xander: Thanks for jumping on. Walk us through what you're trying to accomplish.

Raj: We're building a multi-modal foundation model — text plus image embeddings, roughly 13B parameters. Right now we're doing full fine-tuning runs on rented A100 boxes through CoreWeave but the costs are brutal, something like $38k/month and the queue times kill our iteration speed.

Sandra: Yeah, our training runs are 4-6 days each. We usually kick off 2-3 concurrent runs with different hyperparameter sweeps. The dataset is about 2.3TB after preprocessing, mostly parquet and image shards.

Yuhan: What's your ideal budget range for owned hardware?

Raj: We've got board approval for somewhere between $400k and $550k. We'd rather be closer to $400k but we can stretch if the perf uplift is there. Our CFO wants a 14-month payback window vs continued cloud spend.

Sandra: One thing — we also need to run inference for our API product. It's maybe 20% of our compute but it's latency-sensitive, sub-200ms p99. We'd love to not need separate inference boxes if possible.

Xander: Timeline?

Raj: We need hardware racked and training by end of May. Aggressive, I know.

Sandra: Oh, and NVLink is non-negotiable. We tried PCIe-only last year and the all-reduce was a bottleneck. Also we need at least 256GB total VRAM across the training cluster for our model to fit with our current sharding strategy.

Raj: Last thing — power and cooling. Our colo facility caps us at 45kW for this deployment. We've got standard 208V/30A circuits.`;

const COT_LINES = [
  { text: "═══ ENGINEER AGENT: Chain-of-Thought Analysis ═══", type: "header" },
  { text: "", type: "blank" },
  { text: "Step 1 — Hard Constraint Filter", type: "step" },
  { text: "  Budget ceiling:  $550,000", type: "data" },
  { text: "  Min VRAM:        256 GB", type: "data" },
  { text: "  Max power:       45 kW", type: "data" },
  { text: "  NVLink required: true", type: "data" },
  { text: "", type: "blank" },
  { text: "  Evaluating: Zillion 4090 Cluster — 8-Node ($52,000/unit)", type: "eval" },
  { text: "    Units: 3x | Cost: $156,000 | VRAM: 576 GB", type: "data" },
  { text: "    Power: 17.4 kW | FP16: 1,982.4 TFLOPS", type: "data" },
  { text: "    NVLink: Partial (bridge pairs)", type: "warn" },
  { text: "    ↑ +10% score: within preferred budget", type: "bonus" },
  { text: "    ↓ -20% penalty: bridge-only NVLink — all-reduce bottleneck", type: "penalty" },
  { text: "    SCORE: 1118.3 | Payback: 4.1 months  ✓ PASSES", type: "score" },
  { text: "", type: "blank" },
  { text: "  Evaluating: Zillion 4090 Cluster — 16-Node ($98,000/unit)", type: "eval" },
  { text: "    Units: 3x | Cost: $294,000 | VRAM: 1,152 GB", type: "data" },
  { text: "    ↓ -20% penalty: bridge-only NVLink", type: "penalty" },
  { text: "    SCORE: 1186.7 | Payback: 7.7 months  ✓ PASSES", type: "score" },
  { text: "", type: "blank" },
  { text: "  Evaluating: Zillion 5090 Cluster — 8-Node ($78,000/unit)", type: "eval" },
  { text: "    Units: 3x | Cost: $234,000 | VRAM: 768 GB", type: "data" },
  { text: "    Power: 21.6 kW | FP16: 2,515.2 TFLOPS", type: "data" },
  { text: "    NVLink: Full mesh (900 GB/s per GPU)", type: "data" },
  { text: "    ↑ +25% bonus: full NVLink mesh (critical for all-reduce)", type: "bonus" },
  { text: "    ↑ +10% bonus: within preferred budget (≤$400K)", type: "bonus" },
  { text: "    ↑ +15% bonus: Blackwell FP4 engine (dual-use train+infer)", type: "bonus" },
  { text: "    SCORE: 1699.6 | Payback: 6.2 months  ✓ PASSES", type: "score" },
  { text: "", type: "blank" },
  { text: "  Evaluating: Zillion 5090 Cluster — 16-Node ($148,000/unit)", type: "eval" },
  { text: "    Units: 3x | Cost: $444,000 | VRAM: 1,536 GB", type: "data" },
  { text: "    ↑ +25% bonus: full NVLink mesh", type: "bonus" },
  { text: "    ↑ +15% bonus: Blackwell FP4 engine", type: "bonus" },
  { text: "    SCORE: 1628.6 | Payback: 11.7 months  ✓ PASSES", type: "score" },
  { text: "", type: "blank" },
  { text: "  Evaluating: Zillion 5090 Cluster — 32-Node ($285,000/unit)", type: "eval" },
  { text: "    ↓ -20% penalty: only 1 unit for 3 concurrent runs", type: "penalty" },
  { text: "    SCORE: 1488.5 | Payback: 7.5 months  ✓ PASSES", type: "score" },
  { text: "", type: "blank" },
  { text: "Step 2 — Ranking", type: "step" },
  { text: "  #1: 5090 8-Node ×3 — Score 1699.6 ($234K) ★ RECOMMENDED", type: "recommend" },
  { text: "  #2: 5090 16-Node ×3 — Score 1628.6 ($444K)", type: "data" },
  { text: "  #3: 5090 32-Node ×1 — Score 1488.5 ($285K)", type: "data" },
  { text: "  #4: 4090 16-Node ×3 — Score 1186.7 ($294K)", type: "data" },
  { text: "  #5: 4090 8-Node ×3 — Score 1118.3 ($156K)", type: "data" },
  { text: "", type: "blank" },
  { text: "Step 3 — Final Recommendation", type: "step" },
  { text: "  Zillion 5090 Cluster — 8-Node ×3", type: "recommend" },
  { text: "  24 GPUs | 768 GB VRAM | 2,515.2 TFLOPS", type: "recommend" },
  { text: "  $234,000 | Payback: 6.2 months", type: "recommend" },
  { text: "  Lead time: 4 weeks", type: "recommend" },
  { text: "", type: "blank" },
  { text: "═══ AWAITING HUMAN APPROVAL (Xander / Yuhan) ═══", type: "header" },
];

const CONSTRAINTS_JSON = {
  client: "DataForge AI",
  project_type: "Multi-modal foundation model (13B params)",
  budget: { min: "$400K", max: "$550K", cloud_spend: "$38K/mo" },
  vram_min: "256 GB",
  power_cap: "45 kW",
  nvlink: "Required (full mesh preferred)",
  concurrent_runs: 3,
  deadline: "End of May 2026",
  inference: "20% compute, sub-200ms p99",
};

const PROPOSAL_MD = `# Hardware Proposal: DataForge AI
**Prepared by:** Zillion Network
**Date:** March 31, 2026
**Status:** DRAFT — Pending approval (Xander Cole / Yuhan Park)

---

## Executive Summary

DataForge AI requires dedicated compute for training a 13B-parameter multi-modal foundation model, replacing a $38K/month cloud spend. We recommend **3× Zillion 5090 Cluster — 8-Node** — a 24-GPU deployment delivering 2,515 TFLOPS of FP16 compute with 768 GB total VRAM at **$234,000**, achieving full payback in **6.2 months** against current cloud costs.

---

## Recommended Configuration

| Spec | Value |
|---|---|
| SKU | ZN-5090-8N |
| Configuration | 3× Zillion 5090 Cluster — 8-Node |
| GPU | NVIDIA RTX 5090 |
| Total GPUs | 24 |
| VRAM (Total) | 768 GB |
| FP16 Throughput | 2,515.2 TFLOPS |
| Interconnect | NVLink 5.0 (full mesh, 900 GB/s per GPU) |
| Network | 200GbE RDMA |
| Storage | 24 TB NVMe |
| Total Power Draw | 21.6 kW |
| Unit Cost | $78,000 /unit |
| **Total Cost** | **$234,000** |
| Lead Time | 4 weeks from PO |

---

## Decision Rationale

1. **VRAM Clearance** — DataForge's 13B model requires ≥256 GB for sharded training. This config provides 768 GB (512 GB headroom for optimizer states and activation checkpoints).

2. **NVLink Topology** — Full-mesh NVLink 5.0 at 900 GB/s per GPU eliminates the all-reduce bottleneck that blocked their previous PCIe-only deployment. Critical for distributed training at 13B scale.

3. **Concurrent Training** — 3 independent cluster units support 3 concurrent hyperparameter sweeps without resource contention.

4. **Inference Co-location** — The RTX 5090 Blackwell architecture includes an FP4 inference engine, enabling sub-200ms p99 latency on dedicated inference partitions without separate hardware.

5. **Power Compliance** — 21.6 kW total draw sits well within the 45 kW facility cap (23.4 kW remaining for networking, cooling, and future expansion).

6. **Budget Fit** — $234,000 falls within the preferred range ($400K–$550K ceiling). Significant budget remaining for future expansion.

---

## Alternatives Considered

| Configuration | GPUs | VRAM | Cost | Reason Not Selected |
|---|---|---|---|---|
| 5090 16-Node ×3 | 48 | 1,536 GB | $444,000 | Over-provisioned for current workload |
| 5090 32-Node ×1 | 32 | 1,024 GB | $285,000 | Single unit can't run 3 concurrent jobs |
| 4090 16-Node ×3 | 48 | 1,152 GB | $294,000 | Bridge-only NVLink — all-reduce bottleneck |
| 4090 8-Node ×3 | 24 | 576 GB | $156,000 | Bridge-only NVLink — all-reduce bottleneck |

---

## Deployment Timeline

| Week | Milestone |
|---|---|
| Week 0 | PO signed, hardware allocated from Zillion inventory |
| Week 1–4 | Hardware staging, burn-in testing, OS imaging |
| Week 5 | Ship to DataForge colo facility |
| Week 6 | Rack, cable, power validation (208V/30A circuits) |
| Week 7 | Network config, NVLink topology verification, NCCL benchmarks |
| Week 8 | Workload onboarding — migrate training scripts, validate data pipeline |
| Week 9 | Full production training begins |

**Target: Production training live by end of May 2026.**

---

## Cost Analysis

| Metric | Value |
|---|---|
| Hardware Investment | $234,000 |
| Current Cloud Spend | $38,000/month |
| Cloud Cost (14 months) | $532,000 |
| **Payback Period** | **6.2 months** |
| **14-Month Savings** | **$298,000** |
| Ongoing Costs (est.) | ~$2,800/month (power, colo, maintenance) |

---

## Next Steps

| Action | Owner | Deadline |
|---|---|---|
| Review and approve this proposal | Xander Cole / Yuhan Park | — |
| Send proposal to DataForge AI | Yuhan Park | — |
| Receive PO and payment terms | DataForge AI | — |
| Begin hardware staging | Zillion Ops | PO + 1 day |
| Schedule colo rack date | DataForge + Zillion | PO + 1 week |

---

*This proposal was generated by the Zillion Network AI Proposal System and is pending human review.*
*Zillion Network — Build. Train. Ship.*`;


// ═══════════════════════════════════════════════════════════════════════
// COMPONENTS
// ═══════════════════════════════════════════════════════════════════════

const StatusBadge = ({ status }) => {
  const styles = {
    idle: "bg-zinc-800 text-zinc-400 border-zinc-700",
    running: "bg-amber-950 text-amber-400 border-amber-800 animate-pulse",
    complete: "bg-emerald-950 text-emerald-400 border-emerald-800",
    awaiting: "bg-violet-950 text-violet-400 border-violet-800",
  };
  const labels = {
    idle: "STANDBY",
    running: "PROCESSING",
    complete: "COMPLETE",
    awaiting: "AWAITING HITL",
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 text-xs font-mono border rounded ${styles[status]}`}>
      {status === "running" && <span className="w-1.5 h-1.5 bg-amber-400 rounded-full mr-1.5 animate-ping" />}
      {status === "complete" && <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full mr-1.5" />}
      {labels[status]}
    </span>
  );
};

const AgentHeader = ({ number, name, subtitle, status }) => (
  <div className="flex items-center justify-between mb-3 pb-2 border-b border-zinc-800">
    <div className="flex items-center gap-2.5">
      <span className="flex items-center justify-center w-6 h-6 rounded bg-zinc-800 text-zinc-300 text-xs font-mono font-bold border border-zinc-700">
        {number}
      </span>
      <div>
        <div className="text-sm font-semibold text-zinc-100 tracking-tight">{name}</div>
        <div className="text-xs text-zinc-500 font-mono">{subtitle}</div>
      </div>
    </div>
    <StatusBadge status={status} />
  </div>
);

const CotLine = ({ line, visible }) => {
  if (!visible) return null;
  const colorMap = {
    header: "text-cyan-400 font-bold",
    step: "text-zinc-100 font-semibold",
    eval: "text-blue-400",
    data: "text-zinc-400",
    bonus: "text-emerald-400",
    penalty: "text-red-400",
    warn: "text-amber-400",
    score: "text-zinc-300",
    recommend: "text-cyan-300 font-semibold",
    blank: "",
  };
  return (
    <div className={`font-mono text-xs leading-relaxed whitespace-pre ${colorMap[line.type] || "text-zinc-500"}`}>
      {line.text || "\u00A0"}
    </div>
  );
};

const ConstraintPill = ({ label, value }) => (
  <div className="flex items-center justify-between py-1.5 px-2.5 rounded bg-zinc-800/50 border border-zinc-800">
    <span className="text-xs text-zinc-500 font-mono uppercase tracking-wider">{label}</span>
    <span className="text-xs text-zinc-200 font-mono font-medium">{value}</span>
  </div>
);

const ProposalRenderer = ({ markdown }) => {
  const lines = markdown.split("\n");
  return (
    <div className="space-y-1">
      {lines.map((line, i) => {
        if (line.startsWith("# "))
          return <h1 key={i} className="text-lg font-bold text-zinc-100 mt-2 mb-1">{line.slice(2)}</h1>;
        if (line.startsWith("## "))
          return <h2 key={i} className="text-sm font-bold text-cyan-400 mt-4 mb-1 uppercase tracking-wider">{line.slice(3)}</h2>;
        if (line.startsWith("| "))
          return (
            <div key={i} className="font-mono text-xs text-zinc-400 leading-relaxed whitespace-pre overflow-x-auto">
              {line.split("|").filter(Boolean).map((cell, j) => {
                const trimmed = cell.trim();
                if (trimmed.startsWith("---")) return null;
                const isBold = trimmed.startsWith("**") && trimmed.endsWith("**");
                return (
                  <span key={j} className={`inline-block min-w-[100px] pr-4 ${isBold ? "text-zinc-100 font-semibold" : ""}`}>
                    {trimmed.replace(/\*\*/g, "")}
                  </span>
                );
              })}
            </div>
          );
        if (line.startsWith("---"))
          return <hr key={i} className="border-zinc-800 my-2" />;
        if (line.startsWith("**"))
          return <p key={i} className="text-xs text-zinc-300 font-medium">{line.replace(/\*\*/g, "")}</p>;
        if (line.startsWith("*"))
          return <p key={i} className="text-xs text-zinc-600 italic">{line.replace(/\*/g, "")}</p>;
        if (/^\d+\./.test(line))
          return <p key={i} className="text-xs text-zinc-300 ml-2 leading-relaxed">{line.replace(/\*\*/g, "")}</p>;
        if (line.trim() === "") return <div key={i} className="h-1" />;
        return <p key={i} className="text-xs text-zinc-400 leading-relaxed">{line.replace(/\*\*/g, "")}</p>;
      })}
    </div>
  );
};


// ═══════════════════════════════════════════════════════════════════════
// MAIN APP
// ═══════════════════════════════════════════════════════════════════════

export default function ZillionCommandCenter() {
  const [transcript, setTranscript] = useState(DUMMY_TRANSCRIPT);
  const [phase, setPhase] = useState("idle"); // idle | listener | engineer | author | done
  const [listenerStatus, setListenerStatus] = useState("idle");
  const [engineerStatus, setEngineerStatus] = useState("idle");
  const [authorStatus, setAuthorStatus] = useState("idle");
  const [constraints, setConstraints] = useState(null);
  const [cotVisible, setCotVisible] = useState(0);
  const [proposal, setProposal] = useState(null);
  const [editMode, setEditMode] = useState(false);
  const [editedProposal, setEditedProposal] = useState("");
  const [approved, setApproved] = useState(false);
  const cotRef = useRef(null);
  const cotInterval = useRef(null);

  const reset = useCallback(() => {
    setPhase("idle");
    setListenerStatus("idle");
    setEngineerStatus("idle");
    setAuthorStatus("idle");
    setConstraints(null);
    setCotVisible(0);
    setProposal(null);
    setEditMode(false);
    setEditedProposal("");
    setApproved(false);
    if (cotInterval.current) clearInterval(cotInterval.current);
  }, []);

  const execute = useCallback(() => {
    reset();

    // Phase 1: Listener
    setTimeout(() => {
      setPhase("listener");
      setListenerStatus("running");
    }, 200);

    setTimeout(() => {
      setListenerStatus("complete");
      setConstraints(CONSTRAINTS_JSON);
    }, 2200);

    // Phase 2: Engineer
    setTimeout(() => {
      setPhase("engineer");
      setEngineerStatus("running");
      let lineIdx = 0;
      cotInterval.current = setInterval(() => {
        lineIdx++;
        setCotVisible(lineIdx);
        if (cotRef.current) {
          cotRef.current.scrollTop = cotRef.current.scrollHeight;
        }
        if (lineIdx >= COT_LINES.length) {
          clearInterval(cotInterval.current);
          setEngineerStatus("awaiting");
        }
      }, 80);
    }, 3000);

    // Phase 3: Author (auto-trigger after engineer completes)
    const engineerDone = 3000 + COT_LINES.length * 80 + 500;
    setTimeout(() => {
      setPhase("author");
      setAuthorStatus("running");
    }, engineerDone);

    setTimeout(() => {
      setAuthorStatus("complete");
      setProposal(PROPOSAL_MD);
      setEditedProposal(PROPOSAL_MD);
      setPhase("done");
    }, engineerDone + 1800);
  }, [reset]);

  const handleApprove = () => setApproved(true);

  const handleRegenerate = () => {
    setProposal(null);
    setAuthorStatus("running");
    setTimeout(() => {
      setAuthorStatus("complete");
      setProposal(editedProposal || PROPOSAL_MD);
    }, 1500);
  };

  return (
    <div style={{ fontFamily: "'JetBrains Mono', 'SF Mono', 'Fira Code', monospace" }}
         className="min-h-screen bg-zinc-950 text-zinc-100 p-4">

      {/* Google Font */}
      <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet" />

      {/* Top Bar */}
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-zinc-800">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded bg-cyan-500 flex items-center justify-center">
            <span style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }} className="text-xs font-extrabold text-zinc-950 tracking-tighter">ZN</span>
          </div>
          <div>
            <h1 style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }} className="text-base font-bold tracking-tight text-zinc-100">
              Zillion Network
            </h1>
            <p className="text-xs text-zinc-600 font-mono">Proposal Command Center — v0.1-sim</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-zinc-900 border border-zinc-800">
            <span className={`w-2 h-2 rounded-full ${phase === "idle" ? "bg-zinc-600" : phase === "done" ? "bg-emerald-500" : "bg-amber-500 animate-pulse"}`} />
            <span className="text-xs text-zinc-400">
              {phase === "idle" ? "Ready" : phase === "done" ? "Pipeline complete" : "Running..."}
            </span>
          </div>
        </div>
      </div>

      {/* 3-Column Layout */}
      <div className="grid grid-cols-3 gap-3" style={{ height: "calc(100vh - 100px)" }}>

        {/* Column 1: ANALYZE */}
        <div className="flex flex-col bg-zinc-900/50 rounded-lg border border-zinc-800 overflow-hidden">
          <AgentHeader number="1" name="The Listener" subtitle="analyze → extract" status={listenerStatus} />
          <div className="flex-1 flex flex-col p-3 pt-0 overflow-hidden">
            <label className="text-xs text-zinc-500 mb-1.5 font-mono uppercase tracking-widest">Meeting Transcript</label>
            <textarea
              value={transcript}
              onChange={(e) => setTranscript(e.target.value)}
              className="flex-1 bg-zinc-950 border border-zinc-800 rounded p-3 text-xs text-zinc-300 font-mono leading-relaxed resize-none focus:outline-none focus:border-zinc-600 transition-colors"
              spellCheck={false}
            />

            {/* Extracted Constraints */}
            {constraints && (
              <div className="mt-3">
                <label className="text-xs text-zinc-500 mb-1.5 font-mono uppercase tracking-widest block">Extracted Constraints</label>
                <div className="space-y-1">
                  <ConstraintPill label="client" value={constraints.client} />
                  <ConstraintPill label="budget" value={`${constraints.budget.min} – ${constraints.budget.max}`} />
                  <ConstraintPill label="cloud spend" value={constraints.budget.cloud_spend} />
                  <ConstraintPill label="vram min" value={constraints.vram_min} />
                  <ConstraintPill label="power cap" value={constraints.power_cap} />
                  <ConstraintPill label="nvlink" value={constraints.nvlink} />
                  <ConstraintPill label="concurrent" value={`${constraints.concurrent_runs} runs`} />
                  <ConstraintPill label="deadline" value={constraints.deadline} />
                  <ConstraintPill label="inference" value={constraints.inference} />
                </div>
              </div>
            )}

            <button
              onClick={phase === "idle" ? execute : reset}
              disabled={phase !== "idle" && phase !== "done"}
              className={`mt-3 w-full py-2.5 rounded text-sm font-semibold tracking-wide transition-all duration-200 ${
                phase === "idle"
                  ? "bg-cyan-500 text-zinc-950 hover:bg-cyan-400 active:scale-[0.98]"
                  : phase === "done"
                  ? "bg-zinc-800 text-zinc-300 hover:bg-zinc-700 border border-zinc-700"
                  : "bg-zinc-800 text-zinc-600 cursor-not-allowed"
              }`}
            >
              {phase === "idle" ? "▶  Execute Workflow" : phase === "done" ? "↻  Reset Pipeline" : "Running..."}
            </button>
          </div>
        </div>

        {/* Column 2: DESIGN */}
        <div className="flex flex-col bg-zinc-900/50 rounded-lg border border-zinc-800 overflow-hidden">
          <AgentHeader number="2" name="The Engineer" subtitle="reason → recommend" status={engineerStatus} />
          <div className="flex-1 flex flex-col p-3 pt-0 overflow-hidden">
            <label className="text-xs text-zinc-500 mb-1.5 font-mono uppercase tracking-widest">Chain-of-Thought Log</label>
            <div
              ref={cotRef}
              className="flex-1 bg-zinc-950 border border-zinc-800 rounded p-3 overflow-y-auto"
              style={{ scrollBehavior: "smooth" }}
            >
              {phase === "idle" ? (
                <div className="flex items-center justify-center h-full">
                  <p className="text-xs text-zinc-700 font-mono">Waiting for transcript analysis...</p>
                </div>
              ) : (
                COT_LINES.map((line, i) => (
                  <CotLine key={i} line={line} visible={i < cotVisible} />
                ))
              )}
            </div>

            {/* HITL Approval */}
            {engineerStatus === "awaiting" && !approved && phase === "done" && (
              <div className="mt-3 p-3 rounded border border-violet-800 bg-violet-950/50">
                <div className="text-xs text-violet-300 font-semibold mb-2">Human-in-the-Loop Review</div>
                <p className="text-xs text-violet-400/80 mb-2">
                  Recommended: 3× ZN-5090-8N ($234,000). Approve to finalize proposal.
                </p>
                <button
                  onClick={handleApprove}
                  className="w-full py-2 rounded bg-violet-600 text-white text-xs font-semibold hover:bg-violet-500 transition-colors active:scale-[0.98]"
                >
                  ✓  Approve Recommendation
                </button>
              </div>
            )}
            {approved && (
              <div className="mt-3 p-2.5 rounded border border-emerald-800 bg-emerald-950/50 text-center">
                <span className="text-xs text-emerald-400 font-semibold">✓ Approved by reviewer</span>
              </div>
            )}
          </div>
        </div>

        {/* Column 3: DRAFT */}
        <div className="flex flex-col bg-zinc-900/50 rounded-lg border border-zinc-800 overflow-hidden">
          <AgentHeader number="3" name="The Author" subtitle="synthesize → draft" status={authorStatus} />
          <div className="flex-1 flex flex-col p-3 pt-0 overflow-hidden">
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs text-zinc-500 font-mono uppercase tracking-widest">Generated Proposal</label>
              {proposal && (
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => setEditMode(!editMode)}
                    className="px-2 py-0.5 text-xs font-mono text-zinc-400 bg-zinc-800 border border-zinc-700 rounded hover:text-zinc-200 hover:border-zinc-600 transition-colors"
                  >
                    {editMode ? "Preview" : "Edit"}
                  </button>
                  <button
                    onClick={handleRegenerate}
                    className="px-2 py-0.5 text-xs font-mono text-amber-400 bg-zinc-800 border border-amber-800/50 rounded hover:bg-amber-950 transition-colors"
                  >
                    Regen
                  </button>
                </div>
              )}
            </div>
            <div className="flex-1 bg-zinc-950 border border-zinc-800 rounded overflow-y-auto">
              {!proposal && phase !== "idle" && authorStatus === "running" ? (
                <div className="flex items-center justify-center h-full">
                  <div className="flex flex-col items-center gap-2">
                    <div className="w-5 h-5 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
                    <p className="text-xs text-zinc-600 font-mono">Generating proposal...</p>
                  </div>
                </div>
              ) : !proposal ? (
                <div className="flex items-center justify-center h-full">
                  <p className="text-xs text-zinc-700 font-mono">Waiting for pipeline...</p>
                </div>
              ) : editMode ? (
                <textarea
                  value={editedProposal}
                  onChange={(e) => setEditedProposal(e.target.value)}
                  className="w-full h-full bg-transparent p-3 text-xs text-zinc-300 font-mono leading-relaxed resize-none focus:outline-none"
                  spellCheck={false}
                />
              ) : (
                <div className="p-3">
                  <ProposalRenderer markdown={editedProposal || proposal} />
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
