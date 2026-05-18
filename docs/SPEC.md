# Llama Router UI — SPEC.md

## 1. Concept & Vision

A lightweight, single-page web UI for managing llama.cpp router mode — switching models, configuring per-model parameters, and monitoring loaded instances. No backend beyond llama-server itself. Feels like a proper pilot's control panel: dense with info, fast to use, zero fluff.

**Design tone:** Dark, utilitarian, professional. Like a mixing console — every control has a purpose.

## 2. Design Language

**Aesthetic:** Dark cockpit UI. Dark backgrounds, sharp contrast, accent colors for status/active states.

**Color palette:**
- Background: `#0d0d0d` (near-black)
- Surface: `#1a1a1a` (panels/cards)
- Border: `#2a2a2a` (subtle dividers)
- Text primary: `#e5e5e5`
- Text muted: `#737373`
- Accent: `#ffffff` (active states, selected model)
- Success: `#22c55e` (model loaded)
- Warning: `#f59e0b` (loading)
- Error: `#ef4444` (crashed/unloaded)

**Typography:**
- Font: `JetBrains Mono` (monospace, fits the dev/tool vibe)
- Fallback: `Consolas, monospace`
- Headings: 14px bold uppercase tracking-wider
- Body/params: 13px
- Labels: 11px muted

**Spatial system:**
- 8px base unit
- Panels: 16px padding
- Gap between panels: 12px
- Compact — no wasted space

**Motion:**
- Minimal. 150ms transitions on hover/active states only.
- Model loading: subtle pulse animation on status indicator

## 3. Layout

```
┌─────────────────────────────────────────────────────────┐
│  LLAMA ROUTER                          [server: online] │
├─────────────────┬───────────────────────────────────────┤
│                 │                                       │
│  MODELS         │  PARAMETERS                           │
│  ─────────────  │  ─────────────                        │
│                 │                                       │
│  ▸ Qwen3-30B    │  Model: Qwen3-30B-Q8_0.gguf           │
│    [loaded]     │  ─────────────────────────────────   │
│                 │                                       │
│  ▸ Mistral-7B   │  temperature    [====◉====] 0.7      │
│    [unloaded]   │  top_p          [========◉=] 0.9      │
│                 │  top_k          [====◉======] 40     │
│  ▸ Gemma-3-4B   │  min_p          [◉==========] 0.05    │
│    [loading]    │  repeat_penalty [===◉======] 1.1     │
│                 │                                       │
│  ▸ Llama-3-8B   │  ctx_size       [████◉██████] 8192    │
│    [unloaded]   │  threads        [██◉████████] 16      │
│                 │  gpu_layers     [████████◉██] 99      │
│                 │                                       │
│                 │  seed           [━━━━━━◉━━━━] -1      │
│                 │                                       │
│                 │  [ ] MTP enabled                      │
│                 │  [ ] speculative dec                 │
│                 │                                       │
│                 │  [SAVE PARAMS]    [RELOAD MODEL]      │
├─────────────────┴───────────────────────────────────────┤
│  Request: POST /v1/chat/completions → ggml-org/Qwen3... │
└─────────────────────────────────────────────────────────┘
```

**Responsive:** Stacks to single-column on narrow screens. Desktop-first.

## 4. Features & Interactions

### 4.1 Model List (left panel)
- Fetches from `GET /models` on load, polls every 10s
- Each entry shows: model name, status badge (loaded/loading/unloaded/error)
- Click model → loads its params into the editor (right panel)
- Loading spinner on models in "loading" state
- Auto-refresh without manual reload

### 4.2 Parameter Editor (right panel)
- **Context fields:**
  - `model` — display only (path to GGUF)
  - Model name header

- **Sliders with number input:**
  | Param | Range | Default | Step | INI key |
  |-------|-------|---------|------|---------|
  | temperature | 0.0 – 2.0 | 0.7 | 0.05 | `temperature` |
  | top_p | 0.0 – 1.0 | 0.9 | 0.05 | `top-p` |
  | top_k | 0 – 200 | 40 | 1 | `top-k` |
  | min_p | 0.0 – 1.0 | 0.05 | 0.01 | `min-p` |
  | repeat_penalty | 0.5 – 2.0 | 1.0 | 0.05 | `repeat-penalty` |
  | repeat_last_n | 0 – 256 | 64 | 1 | `repeat-last-n` |
  | presence_penalty | -2.0 – 2.0 | 0 | 0.05 | `presence-penalty` |
  | frequency_penalty | -2.0 – 2.0 | 0 | 0.05 | `frequency-penalty` |
  | ctx_size | 512 – 131072 | 8192 | 512 | `c` |
  | gpu_layers | 0 – 999 | 99 | 1 | `n-gpu-layers` |

**Note:** Not all llama.cpp params are valid in INI presets. Only params marked as `is_sampling=true` in the llama.cpp arg system (or explicitly whitelisted) can persist via `--models-preset`. Runtime-only params like `seed`, `threads`, `min_p`, etc. work per-request but cannot be saved across restarts on this build.

- **Action buttons:**
  - `SAVE PARAMS` — writes to INI preset file + reloads model
  - `RELOAD MODEL` — sends unload → load to refresh from disk

### 4.3 Config File Format
Writes to `models-preset.ini` in the same directory as `--models-dir`:

```ini
[ggml-org/gemma-3-4b-it-GGUF:Q4_K_M]
model = /path/to/gemma-3-4b-it-Q4_K_M.gguf
temperature = 0.7
top_p = 0.9
top_k = 40
min_p = 0.05
repeat_penalty = 1.1
ctx_size = 8192
threads = 16
gpu_layers = 99
seed = -1
mtp = false
spec_dec = false
```

> Note: Since llama-server runs on the host and the UI is served from there, file writes are straightforward. If serving remotely, ensure the server has write access to the models dir.

### 4.4 Status Bar (bottom)
- Shows last API call: method + endpoint + model
- Server online/offline indicator (polls health)

### 4.5 Error Handling
- Server unreachable: red banner "Server offline — check llama-server is running"
- Model load failure: toast notification with error message
- Invalid param value: inline validation (red border on input)
- Save failure: modal with error detail

### 4.6 Empty States
- No models found: "No GGUF files found in models directory. Drop .gguf files into `./models` and refresh."
- No model selected: right panel shows "← Select a model from the list"

## 5. Component Inventory

### ModelListItem
- States: default, hover, selected, loading, error
- Default: `#1a1a1a` bg, muted text
- Hover: `#252525` bg
- Selected: `#FFB612` left border, slightly lighter bg
- Status badge: colored dot + text (green/yellow/gray/red)

### ParamSlider
- Label (left) + slider track + value readout (right)
- Track: dark gray, thumb: yellow when active
- Input: small number field synced with slider
- Hover: thumb grows slightly

### ActionButton
- Default: dark surface, yellow text
- Hover: yellow bg, dark text
- Active: slightly pressed scale(0.98)
- Disabled: 50% opacity, no pointer

### StatusBadge
- Dot (8px circle) + label
- Colors: loaded=green, loading=yellow+spin, unloaded=gray, error=red

### Toast Notification
- Slides in from top-right
- Auto-dismiss after 4s
- Types: info (blue), success (green), warning (yellow), error (red)

## 6. Technical Approach

**Stack:** Single HTML file — vanilla JS, no build step, no framework.

**File structure:**
```
llama-router-ui/
├── routerUI.html        # everything (HTML + CSS + JS)
├── PRESETS.md       # admin doc for manual INI editing
└── SPEC.md          # this file
```

**API integration:**

| Action | Endpoint | Method |
|--------|----------|--------|
| List models | `/models` | GET |
| Load model | `/models/load` | POST |
| Unload model | `/models/unload` | POST |
| Get model params | `/props` | GET |
| Set model params | `/props` | POST |
| Health check | `/health` | GET |

**Param persistence strategy:**
1. User adjusts sliders → values stored in JS state
2. `SAVE PARAMS` → write INI file to `--models-dir/models-preset.ini`
3. Server picks up on next model load (LRU may auto-unload/load)

> Alternative (if server supports runtime prop updates without reload): hit `POST /props` with updated params + model name. This would be cleaner — verify with testing.

**Serving:**
- `llama-server` serves its own web UI on port 8080
- Custom UI can be served from same port via nginx reverse proxy
- Or: open `routerUI.html` directly in browser (file:// works for static HTML)

**Polling:**
- Model list: `GET /models` every 10s
- Health: `GET /health` every 30s

**Browser compatibility:** Modern browsers only (Chrome/Firefox/Edge). No IE.

## 7. Out of Scope (v1)

- Chat interface (use built-in web UI or API client)
- Multi-user / auth
- Model download from HuggingFace
- Session/history management
- Streaming toggle
- Custom presets beyond what llama-server INI supports

---

**Status:** Built — `routerUI.html` ready
**Status:** Ready for test and feedback