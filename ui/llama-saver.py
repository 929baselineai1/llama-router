#!/usr/bin/env python3
"""Llama Router UI backend — saves params to INI, kills & restarts llama-server."""
import http.server, json, os, signal, subprocess, sys, threading, time
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError

PORT = 8090
PRESETS = os.environ.get("PRESETS", "/models/llama-presets.ini")
PID_FILE = "/tmp/llama-server.pid"
LOG_FILE = "/tmp/llama-server.log"
RESTART_SCRIPT = "/tmp/llama-server-restart.sh"
API = "http://127.0.0.1:8080"

# Only these params are valid in llama-server INI presets
# https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md#model-presets
VALID_INI_PARAMS = {
    'temperature',
    'top-p', 'top-k', 'min-p',
    'repeat-penalty', 'repeat-last-n',
    'presence-penalty', 'frequency-penalty',
    'mirostat', 'mirostat_tau', 'mirostat_eta',
    'c',
    'n-gpu-layers', 'flash-attn',
}

class ReuseAddrTCPServer(http.server.HTTPServer):
    allow_reuse_address = True
    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        super().server_bind()

import socket

def get_pid():
    try: return int(Path(PID_FILE).read_text().strip())
    except: return None

def read_ini():
    sections, cur = {}, None
    for line in Path(PRESETS).read_text().splitlines():
        line = line.rstrip()
        if not line or line.startswith(';'): continue
        if line.startswith('[') and line.endswith(']'):
            cur = line[1:-1]; sections[cur] = {}
        elif '=' in line and cur:
            k, v = line.split('=', 1); sections[cur][k.strip()] = v.strip()
    return sections

def write_ini(sections):
    lines = ["version = 1", ""]
    for sec, params in sections.items():
        lines.append(f"[{sec}]")
        for k, v in params.items(): lines.append(f"{k} = {v}")
        lines.append("")
    Path(PRESETS).write_text("\n".join(lines))

def do_restart_async(result_dict):
    pid = get_pid()
    if pid:
        try: os.kill(pid, signal.SIGTERM)
        except: pass
    time.sleep(2)
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(f"\n--- restart at {time.strftime('%H:%M:%S')} ---\n")
            f.flush()
            p = subprocess.Popen(["/bin/bash", RESTART_SCRIPT], stdout=f, stderr=subprocess.STDOUT)
        Path(PID_FILE).write_text(str(p.pid))
        for i in range(30):
            try:
                urlopen(API + "/props", timeout=3)
                result_dict['ok'] = True
                return
            except: time.sleep(1)
        result_dict['ok'] = False
    except Exception as e:
        result_dict['ok'] = False
        result_dict['msg'] = str(e)

class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"; timeout = 10

    def do_POST(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        if parsed.path == "/save":
            model = qs.get("model", [""])[0]
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length).decode()) if length else {}
            sections = read_ini()
            if not sections: sections = {"[*]": {"c": "8192", "n-gpu-layers": "99", "flash-attn": "on"}}
            # Convert underscore keys to hyphen for INI
            PENALTY_MAP = {
                'top_p': 'top-p',
                'top_k': 'top-k',
                'min_p': 'min-p',
                'repeat_penalty': 'repeat-penalty',
                'repeat_last_n': 'repeat-last-n',
                'presence_penalty': 'presence-penalty',
                'frequency_penalty': 'frequency-penalty',
                'n_ctx': 'c',
            }
            if model:
                sections[model] = {}
                for k, v in body.items():
                    k = PENALTY_MAP.get(k, k)
                    if k not in VALID_INI_PARAMS: continue
                    if v is None or str(v) in ("", "undefined", "null", "NaN"): continue
                    sections[model][k] = str(v)
            write_ini(sections)
            threading.Thread(target=do_restart_async, args=({'ok': False},)).start()
            response_data = json.dumps({"success": True, "restarting": True}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_data)))
            self.send_header("Connection", "close")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(response_data)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else None
            url = f"http://127.0.0.1:8080{self.path}"
            req = Request(url, data=body, method="POST")
            for h in ["Content-Type", "Authorization"]:
                if h in self.headers: req.add_header(h, self.headers[h])
            with urlopen(req, timeout=30) as r:
                data = r.read()
                self.send_response(r.status)
                for k, v in r.headers.items():
                    if k.lower() not in ("transfer-encoding", "connection"): self.send_header(k, v)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(data)
        except HTTPError as e:
            self.send_response(e.code); self.send_header("Access-Control-Allow-Origin", "*"); self.end_headers(); self.wfile.write(e.read())
        except Exception as e:
            self.send_response(502); self.end_headers(); self.wfile.write(json.dumps({"error": str(e)}).encode())

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Access-Control-Allow-Origin", "*"); self.end_headers(); self.wfile.write(json.dumps({"pid": get_pid(), "ok": True}).encode()); return
        try:
            with urlopen(f"http://127.0.0.1:8080{self.path}", timeout=15) as r:
                data = r.read(); self.send_response(r.status)
                for k, v in r.headers.items():
                    if k.lower() not in ("transfer-encoding", "connection"): self.send_header(k, v)
                self.send_header("Access-Control-Allow-Origin", "*"); self.end_headers(); self.wfile.write(data)
        except HTTPError as e:
            self.send_response(e.code); self.send_header("Access-Control-Allow-Origin", "*"); self.end_headers()
        except: self.send_response(502); self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200); self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type"); self.end_headers()

    def log_message(self, fmt, *args): sys.stderr.write(fmt % args + "\n")

if __name__ == "__main__":
    srv = ReuseAddrTCPServer(("0.0.0.0", PORT), Handler)
    sys.stderr.write(f"Saver listening on http://0.0.0.0:{PORT}\n")
    srv.serve_forever()
