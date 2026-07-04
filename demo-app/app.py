"""Demo Cloud Run app with intentional OOM trigger for hackathon demo."""
import os
from flask import Flask, jsonify

app = Flask(__name__)

_leak = []

@app.route("/")
def health():
    return jsonify(status="ok", memory_items=len(_leak))

@app.route("/work")
def normal_work():
    result = sum(range(100000))
    return jsonify(status="ok", result=result)

@app.route("/leak")
def trigger_leak():
    chunk = bytearray(50 * 1024 * 1024)  # 50MB per call
    _leak.append(chunk)
    return jsonify(
        status="leaking",
        chunks=len(_leak),
        total_mb=len(_leak) * 50,
    )

@app.route("/oom")
def trigger_oom():
    blocks = []
    while True:
        blocks.append(bytearray(100 * 1024 * 1024))  # 100MB chunks

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
