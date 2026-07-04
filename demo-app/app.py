"""Demo Cloud Run app — realistic workload with a hidden memory leak."""
import os
from flask import Flask, jsonify, request

app = Flask(__name__)

# Bug: unbounded cache with no eviction — will OOM under sustained load
_result_cache = {}


@app.route("/")
def health():
    return jsonify(status="ok", cached_items=len(_result_cache))


@app.route("/work")
def work():
    n = int(request.args.get("n", 100000))
    result = sum(range(n))
    # Bug: caches every unique request forever, never evicts
    _result_cache[n] = bytearray(1024 * 1024)  # 1MB per cached entry
    return jsonify(status="ok", result=result, cached=len(_result_cache))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
