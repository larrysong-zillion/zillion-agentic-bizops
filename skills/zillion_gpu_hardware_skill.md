# Skill: Zillion Hardware Knowledge
 
## Purpose
Provide accurate technical specifications, architecture comparisons, and cluster design rules for Zillion Network's hardware catalogue — GPUs, CPUs, RAM, storage, network, and the procurement-plan output shape. Used by the Architect Agent for Tree-of-Thought hardware recommendations and have/buy/rent BOM splits.
 
Note: this skill covers the full server stack, not GPUs alone. The filename retains `gpu_hardware` for historical compatibility but the scope is broader.
 
## GPU Specifications
 
### RTX 4090 (Ada Lovelace)
- VRAM: 24GB GDDR6X, 384-bit bus
- FP16: 82.6 TFLOPS | FP32: 82.6 TFLOPS | INT8: 660.6 TOPS
- TDP: 450W | PCIe Gen4 x16
- NVLink: Not available — PCIe only
- Best for: Inference, fine-tuning small models (<13B), multi-GPU parallel inference
- Zillion config: 8× per server, passthrough, CX6 NIC
### RTX 5090 (Blackwell)
- VRAM: 32GB GDDR7, 512-bit bus
- FP16: ~105 TFLOPS (est) | FP4: ~3,352 TOPS
- TDP: 575W | PCIe Gen5 x16
- NVLink: Not available — PCIe only
- Best for: Inference at scale, fine-tuning medium models (13B-30B), highest perf/$ for inference
- Zillion config: 8× or 4× per server, passthrough, CX6 NIC
### RTX Pro 6000 Server Edition (Blackwell)
- VRAM: 96GB GDDR7, 512-bit bus
- FP16: ~110 TFLOPS (est) | FP4: ~3,500 TOPS
- TDP: 350W | PCIe Gen5 x16
- NVLink: Not available natively — but MGX CX8 switch board provides direct GPU-to-NIC path
- Best for: Training 30B-70B models, VRAM-intensive workloads, research clusters
- Zillion configs:
  - **Passthrough (CX6)**: 8× GPU per 7U server, dual-port 100GbE, $128,014/server
  - **MGX CX8**: 8× GPU per 4U Supermicro SYS-422GL-NR, 4× CX8 SuperNIC (800GbE each), ~$200K/server
### A100 80GB (Ampere)
- VRAM: 80GB HBM2e, 5TB/s bandwidth
- FP16: 312 TFLOPS (with sparsity) | FP64: 19.5 TFLOPS
- TDP: 400W | NVLink 3.0 (600GB/s bidirectional)
- Best for: Training 70B+ models, HPC/scientific computing, maximum memory bandwidth
- Zillion config: 8× SXM, NVLink fabric, $180,000/server
### H100 SXM5 (Hopper)
- VRAM: 80GB HBM3, 3.35TB/s bandwidth
- FP16: 989 TFLOPS (with sparsity) | FP8: 1,979 TFLOPS
- TDP: 700W | NVLink 4.0 (900GB/s bidirectional) | InfiniBand NDR 400Gb/s
- Best for: Foundation model pre-training (100B+), maximum throughput, multi-node NCCL
- Zillion config: 8× SXM5, InfiniBand HDR200, $280,000/server (pre-order)
## Architecture Comparison: Passthrough vs CX8
 
| Attribute | PCIe Passthrough (CX6) | MGX CX8 Switch Board |
|---|---|---|
| Server platform | Custom 7U (ASRock Rack) | Supermicro SYS-422GL-NR (4U) |
| CPU | 2× AMD EPYC 9J14 (96C) | Intel Xeon 6 6900P |
| GPU interconnect | PCIe Gen5 via CPU root complex | PCIe Gen6 via integrated switch |
| NIC | 1× CX6 Dx dual-port 100GbE | 4× CX8 SuperNIC, 800GbE each |
| NIC-to-GPU ratio | 1:8 (shared) | 1:2 (dedicated) |
| Data path | GPU → PCIe → CPU → PCIe → NIC | GPU → PCIe switch → CX8 (CPU bypassed) |
| RDMA | RoCEv2 over 100GbE | RoCEv2 over 800GbE |
| NCCL bandwidth/GPU | ~25 Gbps effective | ~400 Gbps effective |
| Cluster bandwidth (16 nodes) | 3.2 Tbps | 51.2 Tbps |
| Cost per server | ~$128K | ~$200K |
| Best fit | Inference, fine-tuning, cost-sensitive | Multi-node distributed training |
 
## Cluster Design Rules
 
### When to recommend Passthrough (CX6)
- Budget-sensitive clients (<$200K)
- Inference workloads (latency matters, not all-reduce bandwidth)
- Single-node training (model fits in 8× GPU VRAM)
- Fine-tuning pre-trained models (gradient updates are small)
### When to recommend CX8
- Multi-node distributed training (NCCL all-reduce is the bottleneck)
- Models >30B parameters requiring data parallelism across nodes
- Clients who mentioned "NVLink" or "InfiniBand" as requirements
- Budget >$500K (cost premium is absorbed at scale)
### Scaling Rules
- 128 GPUs passthrough: 4 racks × 4 servers (7U each, 28U per rack)
- 128 GPUs CX8: 2 racks × 8 servers (4U each, 32U per rack)
- Leaf switches: 1 per rack (SN2700 for passthrough, SN5600 for CX8)
- Spine switches: 2 minimum for redundancy
- Power budget: 5kW per 8-GPU passthrough server, 6kW per CX8 server
### NCCL Topology Considerations
- PCIe passthrough: CPU is in the data path. Cross-socket GPU traffic adds xGMI latency.
- CX8: integrated PCIe Gen6 switch bypasses CPU entirely. Each CX8 serves 2 GPUs with dedicated 800GbE.
- For training: always recommend CX8 if client budget allows and workload is multi-node.
- For inference: passthrough is sufficient — latency is dominated by model compute, not NIC bandwidth.
## Network Fabric Components
 
### Passthrough Architecture
| Component | Model | Ports | Price |
|---|---|---|---|
| Leaf switch | Mellanox SN2700 | 32×100GbE | $12,000 |
| Spine switch | Mellanox SN2700 | 32×100GbE | $15,000 |
| Management switch | 1GbE 48-port | 48×1GbE | $800 |
 
### CX8 Architecture
| Component | Model | Ports | Price |
|---|---|---|---|
| Leaf switch | NVIDIA SN5600 | 64×800GbE | $45,000 |
| Spine switch | NVIDIA SN5600 | 64×800GbE | $45,000 |
| Management switch | 1GbE 48-port | 48×1GbE | $800 |
 
## Software Stack (deployed via Ansible)
- OS: Ubuntu 22.04 (Kernel 5.15.0-113)
- GPU Driver: NVIDIA 535.161.08
- DCGM: 3.3.7 (GPU health monitoring)
- UFM: Advanced InfiniBand/Ethernet fabric management
- Slurm: Cluster job scheduler
- NCCL: NVIDIA Collective Communications Library
- NVIDIA Container Toolkit: 1.16.1
- MLNX_OFED: 23.10-2.1.3.1 (RDMA drivers)
- Optional: Kubernetes, Volcano, Docker, PyTorch
## CPU Reference — Zillion's Standard SKUs
 
Match CPU tier to workload. Defaulting to the most powerful option inflates proposal costs and loses deals. Each server has 2 CPUs minimum (one per socket).
 
### ENTRY tier — VM hosts, web serving, lightweight services, dev/test
Use these when the customer asks for small per-machine specs (2-8 cores, 4-16GB RAM) or workloads that don't involve training:
- AMD EPYC 7702, 7542, 7502 (older but plentiful, cheap, perfectly adequate)
- Intel Xeon 8136 (similar tier, often cheaper than EPYC for the same job)
- Intel i9-14900KS — single-socket low-cost desktop builds only, NEVER production VM hosts
### MID tier — mixed AI/CPU workloads, light training, inference, multi-tenant
- AMD EPYC 7763, 75F3
- Intel Xeon 8167M
### HIGH tier — heavy training, large language models, dense GPU clusters
- AMD EPYC 7B13, 9354 (latest generation, premium pricing)
**Critical rule:** if the customer requirements list small per-machine specs (2-8 cores, 4-16GB RAM, web/VM/chat/storage workloads), pick from the ENTRY tier. The high-tier EPYCs are 3-5× the price and add zero value for non-training workloads.
 
## RAM Reference
- Stick sizes: 32GB or 64GB
- Type: DDR4 or DDR5 (match CPU generation — DDR4 for EPYC 7xxx, DDR5 for EPYC 9xxx)
- Minimum 2 sticks per server (one per CPU socket)
- Typical configs:
  - Small VMs / web hosts: 2× 16GB or 2× 32GB
  - Inference / mixed workloads: 8× 32GB = 256GB
  - Training / dense GPU: 8× 64GB = 512GB+
- Vendors: Samsung, SK Hynix, Micron (server-grade ECC RDIMM/LRDIMM)
## Storage Reference
Match storage tier to workload — over-specifying storage inflates BOM cost the same way over-specifying CPUs does.
 
| Tier | Use case | Examples | Sizing |
|---|---|---|---|
| NVMe SSD | Hot data, training scratch, search index | Samsung PM9A3/PM1733, Solidigm D7-P5520, Kioxia CD8/CM7, Micron 7450 | Training: 4TB+ per node. VM hosts: 50-200GB. |
| SATA SSD | Warm data, logs, OS | Samsung PM893, Micron 5400 Pro, Kioxia HK6 | OS + logs: 480GB-1.92TB |
| HDD | Cold / bulk | Seagate Exos, WD Ultrastar, Toshiba MG | Bulk archival only |
 
## Network Reference
 
| Speed | When to use | Vendors |
|---|---|---|
| 10G | VM hosts, web servers, most CPU-only workloads | Intel X710, Mellanox ConnectX-4 Lx, Broadcom NetXtreme |
| 40G | Higher-throughput general compute | Mellanox ConnectX-5, Intel XL710 |
| 100G | Distributed training (Ethernet fabric), inference at scale | Mellanox/NVIDIA ConnectX-6 Dx |
| 200G+ | InfiniBand training fabrics | Mellanox/NVIDIA ConnectX-6 NDR, ConnectX-7 |
| 800G | CX8 MGX architecture | NVIDIA ConnectX-8 SuperNIC |
 
**Critical rule:** do NOT propose 100G+ NICs on web/VM hosts — wasted spend. 10G is enough for VM hosts and most CPU-only workloads.
 
## Multi-Machine BOM Pattern
 
When a customer requests multiple distinct machine types (e.g., "4 small VMs + 1 GPU server"), treat each spec as a separate BOM line with its own CPU/RAM/storage/NIC sized to that machine's job. Do NOT collapse into a single "5 servers" line. Different machines need different components.
 
Real example: customer asked for 4× lightweight VMs (2-4 cores, 4-8GB RAM, 100-200GB SSD, no public IP) + 1× GPU server (2× RTX 4090, 64GB RAM, 24+ core CPU). Correct output: 5 separate procurement_plan entries.
 
## Procurement Plan — Have / Buy / Rent Split
 
Yuhan's operational workflow requires every BOM to be split into three buckets so she can figure out what to ship from where, what to buy, and what to relay to Xander for vendor decisions. The Architect Agent must produce a `procurement_plan` array alongside the paths recommendation.
 
### Schema
```json
{
  "procurement_plan": [
    {
      "item": "e.g. 8-GPU server with 2x AMD EPYC 7763, 512GB DDR4, 4x Samsung PM9A3 NVMe",
      "qty": 2,
      "source": "inventory|purchase|rent",
      "sku_or_vendor": "existing inventory SKU OR suggested vendor",
      "vendor_suggestions": ["Supermicro", "Dell", "ASUS"],
      "market_price_estimate_per_unit": "~$X,XXX",
      "total_estimated_cost": "~$X,XXX",
      "xander_to_confirm": true,
      "notes": "why this line"
    }
  ]
}
```
 
### Source values
- `inventory` — Zillion already owns this. Zero acquisition cost, just allocation. Reference the existing inventory SKU.
- `purchase` — Must be bought new. Include vendor_suggestions (2-3 plausible vendors) and market_price_estimate_per_unit (rough current market range prefixed with `~` to signal estimate). MUST set `xander_to_confirm: true` — Xander makes the final vendor + price decision.
- `rent` — Capacity rented from upstream provider (CoreWeave, Lambda, GCP). Only for GPU capacity deals, not component parts.
### Inventory-first allocation (critical)
Before recommending any "purchase" line, check the inventory snapshot. If a comparable item exists, the procurement_plan entry MUST use `source: "inventory"`. Common cases this catches:
- Customer requested 2× RTX 4090 + Zillion has 4090 chassis in any DC → use `inventory`
- Cross-DC: customer wants Dallas, spare is in LA → still `inventory` with notes "spare available in LA, requires inter-DC shipment — Yuhan to coordinate" — this is a SHIPPING question, not a PURCHASE question
### Inventory gaps — physical movements not in the imported sheet
The imported inventory sheet is updated periodically and may not reflect spare parts, recent inter-DC shipments, or out-of-cycle hardware arrivals. When recommending hardware that would otherwise be a "purchase" line, ALWAYS add a notes field: "Verify with Yuhan whether this is available from spare inventory before procurement." This catches the case where Yuhan has shipped spare GPUs or chassis between DCs without updating the sheet.
 
### Upstream-provider resale pricing
For `source: "rent"` and for small CPU nodes / VM hosts that map to a Lightlayer / SaaS-style provider rather than discrete hardware purchase, the `market_price_estimate_per_unit` is the CUSTOMER-FACING resale price, not Zillion's wholesale cost. Add notes: "resold from upstream provider — Zillion wholesale cost not shown here, captured separately in Hostbill."
 
## Vendor Suggestion Catalog (for purchase lines)
 
| Component | Vendors |
|---|---|
| Server chassis / barebones | Supermicro, Dell PowerEdge, ASUS, Inspur, Wiwynn |
| GPUs | NVIDIA direct, PNY, Penguin Solutions, Exxact, ASBIS (region-dependent) |
| NVMe SSD | Samsung (PM9A3, PM1733), Solidigm (D7-P5520, D5-P5430), Kioxia (CD8, CM7), Micron (7450) |
| SATA SSD | Samsung (PM893), Micron (5400 Pro), Kioxia (HK6) |
| HDD | Seagate Exos, WD Ultrastar, Toshiba MG |
| Network cards | Mellanox/NVIDIA ConnectX, Intel E810/X710, Broadcom NetXtreme |
| Network switches | Arista, Mellanox/NVIDIA Spectrum, Cisco Nexus, Dell PowerSwitch |
| RAM | Samsung, SK Hynix, Micron (server-grade ECC RDIMM/LRDIMM) |
 
