from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import subprocess

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_web():
    server = HTTPServer(('0.0.0.0', 10000), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_web, daemon=True).start()

subprocess.run(["python", "bot.py"])