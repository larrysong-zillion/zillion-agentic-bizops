# Skill: GPU Hardware Knowledge

## Purpose
Provide accurate technical specifications, architecture comparisons, and cluster design rules for Zillion Network's GPU hardware catalogue. Used by the Architect Agent for Tree-of-Thought hardware recommendations.

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
