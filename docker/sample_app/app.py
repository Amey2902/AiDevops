import time
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# Leaked memory buffer for memory-leak simulation
LEAK_BUFFER = []

class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global LEAK_BUFFER
        if self.path == "/metrics":
            # Return Prometheus scrape format
            leak_mb = len(LEAK_BUFFER) * 10
            metrics_payload = (
                f"# HELP container_memory_working_set_bytes Simulated memory usage\n"
                f"# TYPE container_memory_working_set_bytes gauge\n"
                f"container_memory_working_set_bytes{{name=\"sample-app\"}} {leak_mb * 1024 * 1024}\n"
                f"# HELP http_requests_total Total HTTP requests\n"
                f"# TYPE http_requests_total counter\n"
                f"http_requests_total{{status=\"200\",service=\"sample-app\"}} 420\n"
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.end_headers()
            self.wfile.write(metrics_payload.encode())
            return

        elif self.path == "/fault/memory-leak":
            # Append 50MB to leak buffer
            LEAK_BUFFER.append(b"A" * (50 * 1024 * 1024))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(f'{{"status":"leak_injected","current_leak_mb":{len(LEAK_BUFFER) * 50}}}'.encode())
            return

        elif self.path == "/fault/cpu-spike":
            def burn():
                start = time.time()
                while time.time() - start < 10:
                    _ = [x**2 for x in range(10000)]
            threading.Thread(target=burn, daemon=True).start()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"cpu_spike_started_10s"}')
            return

        elif self.path == "/healthz":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"service":"sample-app","status":"healthy"}')

def run(port=8080):
    server = HTTPServer(("0.0.0.0", port), MetricsHandler)
    print(f"Sample monitored app listening on port {port}...")
    server.serve_forever()

if __name__ == "__main__":
    run()

