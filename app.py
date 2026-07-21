from flask import Flask, render_template, request, jsonify
import threading
import os
import uuid
from automation import run_automation

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

MAX_CONCURRENT_RUNS = 3

# Tracks all active/finished jobs by ID:
# { job_id: {"stop_event": Event, "running": bool, "url": str} }
jobs = {}
jobs_lock = threading.Lock()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/run", methods=["POST"])
def run():
    with jobs_lock:
        active_count = sum(1 for j in jobs.values() if j["running"])
        if active_count >= MAX_CONCURRENT_RUNS:
            return jsonify({
                "status": f"⚠️ Maximum of {MAX_CONCURRENT_RUNS} automations already running. "
                           f"Wait for one to finish or stop it first."
            }), 409

    if 'file' not in request.files:
        return jsonify({"status": "Error: No file uploaded"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "Error: No file selected"}), 400

    job_id = uuid.uuid4().hex[:8]

    # Each job gets its own numbers file so concurrent runs don't overwrite each other.
    file_path = os.path.join(UPLOAD_FOLDER, f"numbers_{job_id}.txt")
    file.save(file_path)

    url = request.form.get("url", "https://www.luckywin.com.gh/login")

    stop_event = threading.Event()

    with jobs_lock:
        jobs[job_id] = {"stop_event": stop_event, "running": True, "url": url}

    def run_task():
        try:
            result = run_automation(url, file_path, stop_event)
            print(f"[{job_id}] {result}")
        except Exception as e:
            import traceback
            print(f"❌ [{job_id}] Automation crashed: {e}")
            traceback.print_exc()
        finally:
            with jobs_lock:
                jobs[job_id]["running"] = False

    thread = threading.Thread(target=run_task)
    thread.start()

    return jsonify({
        "status": f"✅ Automation started! Job ID: {job_id}",
        "job_id": job_id
    })


@app.route("/stop", methods=["POST"])
def stop():
    job_id = request.json.get("job_id") if request.is_json else request.form.get("job_id")

    with jobs_lock:
        if not job_id:
            # No job_id given: stop everything currently running.
            if not jobs:
                return jsonify({"status": "No automations are running."})
            for j in jobs.values():
                j["stop_event"].set()
            return jsonify({"status": "🛑 Stop signal sent to all running automations."})

        if job_id not in jobs:
            return jsonify({"status": f"⚠️ No job found with ID {job_id}"}), 404

        jobs[job_id]["stop_event"].set()
        return jsonify({"status": f"🛑 Stop signal sent to job {job_id}."})


@app.route("/status")
def status():
    with jobs_lock:
        active_count = sum(1 for j in jobs.values() if j["running"])
        job_list = [
            {"job_id": jid, "running": j["running"], "url": j["url"]}
            for jid, j in jobs.items()
        ]
    return jsonify({
        "active_count": active_count,
        "max_concurrent": MAX_CONCURRENT_RUNS,
        "jobs": job_list
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)