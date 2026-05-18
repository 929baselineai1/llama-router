# Llama Router

A turnkey container for running **multiple AI models** on your own hardware with a **visual control panel**.

Think of it like a personal AI server — no cloud, no subscriptions, runs on your AMD/NVIDIA GPU or CPU.

---

## What does it do?

- **Serve multiple models** via llama.cpp router mode
- **Visual parameter editor** — tweak temperature, top-p, penalties, context size with sliders, no command line
- **Per-model presets** — each model saves its own settings and reloads them on restart
- **Works remotely** — access the control panel from any device on your network

---

## Who is this for?

| Person | Why it works |
|--------|-------------|
| **Strix Halo owners** | ROCm build, 128GB RAM handles multiple large models |
| **NVIDIA GPU users** | CUDA build, drop into any Docker setup |
| **Home lab enthusiasts** | Self-hosted, no cloud dependency |
| **AI developers** | Quick model switching + parameter tuning without CLI |

---

## The three backends

| Tag | Compute | Best for |
|-----|---------|----------|
| `llama-router:rocm` | AMD HIP (ROCm 7.2.3) | Strix Halo, RDNA3/4 AMD GPUs |
| `llama-router:cuda` | NVIDIA CUDA 12.4 | NVIDIA GPUs (4000/5000 series, A100, etc.) |
| `llama-router:cpu` | CPU only | Low-power, small models, no GPU |

---

## Quick Start

### 1. Pull the image

```bash
# AMD GPU (Strix Halo)
docker pull ghcr.io/baselineai/llama-router:rocm

# NVIDIA GPU
docker pull ghcr.io/baselineai/llama-router:cuda

# CPU only
docker pull ghcr.io/baselineai/llama-router:cpu
```

### 2. Create a models directory

```bash
mkdir -p ~/llm-models
# Drop your .gguf model files here
```

### 3. Run it

```bash
docker run -d \
  --name llama-router \
  -v ~/llm-models:/models \
  -p 8080:8080 \
  -p 8090:8090 \
  -p 8099:8099 \
  ghcr.io/baselineai/llama-router:rocm
```

### 4. Open the control panel

```
http://localhost:8099/routerUI.html
```

Or from any device on your network — replace `localhost` with the host IP:

```
http://192.168.x.x:8099/routerUI.html
```

---

## Managing models via INI presets

Each model can have its own default parameters stored in an INI file. Create a file at:

```
/path/to/your/models/llama-presets.ini
```

Example:

```ini
version = 1

[*]
c = 8192
n-gpu-layers = 99
flash-attn = on

[Qwen3.6-35B-A3B-uncensored-heretic-APEX-I-Balanced]
temperature = 0.5
top-p = 0.85
top-k = 25
repeat-penalty = 1.05
presence-penalty = 0
frequency-penalty = 0
c = 131072

[Qwen3.6-35B-A3B-Claude-4.7-Opus-Reasoning-Distilled-APEX-I-Balanced]
temperature = 0.7
c = 131072
```

**Valid preset parameters:**

| What you want | INI key | Notes |
|---------------|---------|-------|
| Temperature | `temperature` | 0.0 – 2.0 |
| Top-P | `top-p` | 0.0 – 1.0 |
| Top-K | `top-k` | 0 – 200 |
| Min-P | `min-p` | 0.0 – 1.0 |
| Repeat penalty | `repeat-penalty` | 1.0 – 2.0 |
| Repeat last-n | `repeat-last-n` | 0 – 256 |
| Presence penalty | `presence-penalty` | -2.0 – 2.0 |
| Frequency penalty | `frequency-penalty` | -2.0 – 2.0 |
| Context size | `c` | 512 – 131072 |
| GPU layers | `n-gpu-layers` | 0 – 999 |
| Flash attention | `flash-attn` | `on` or `off` |

**Not valid in presets** (work per-request but can't persist across restarts): `seed`, `threads`, `min_p` can't be stored in INI on this build. They still work if you set them at request time.

---

## Remote access (outside your network)

The control panel and API are designed to be accessed over LAN. For remote access from anywhere:

**Option 1 — Tailscale (recommended):**
```bash
# Install Tailscale on the host
curl -fsSL https://tailscale.com/install.sh | sh
tailscale up

# Then access via your Tailscale IP (e.g., 100.x.x.x)
# http://100.x.x.x:8099/routerUI.html
```

**Option 2 — Cloudflare Tunnel:**
```bash
cloudflared tunnel --url http://localhost:8099
```

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  llama-router container                             │
│                                                     │
│  ┌──────────────┐   ┌──────────────┐  ┌──────────┐ │
│  │ llama-server │   │ llama-saver  │  │  HTTP    │ │
│  │   :8080      │ ← │   :8090      │→ │  server  │ │
│  │  (router)    │   │  (proxy+INI) │  │  :8099   │ │
│  └──────────────┘   └──────────────┘  └──────────┘ │
│         ↑                                       │   │
│         │         ┌──────────────────────────┐│   │
│         └─────────│ routerUI.html (browser) ──│─┘   │
│                   └──────────────────────────┘     │
└─────────────────────────────────────────────────────┘
         ↑                        ↑
    Models (.gguf)           User browser
    mounted as volume
```

- **llama-server** — the router, serves the OpenAI-compatible API on :8080
- **llama-saver** — Python proxy that handles INI saves + server restarts, adds CORS, on :8090
- **HTTP server** — static file server for the UI on :8099

---

## Building locally

```bash
git clone https://github.com/baselineai/llama-router.git
cd llama-router

# AMD ROCm
podman build -f toolboxes/Dockerfile.rocm -t llama-router:rocm .

# NVIDIA CUDA
podman build -f toolboxes/Dockerfile.cuda -t llama-router:cuda .

# CPU only
podman build -f toolboxes/Dockerfile.cpu -t llama-router:cpu .
```

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_DIR` | `/models` | Where your .gguf files live |
| `NGPU_LAYERS` | `99` | How many layers to offload to GPU |
| `CTX_SIZE` | `131072` | Context window size |
| `BATCH_SIZE` | `512` | Batch size for inference |

---

## Ports

| Port | Service | What it's for |
|------|---------|---------------|
| `8080` | llama-server | Direct API access (OpenAI-compatible) |
| `8090` | llama-saver | UI backend proxy + restart handler |
| `8099` | HTTP server | Control panel UI (routerUI.html) |