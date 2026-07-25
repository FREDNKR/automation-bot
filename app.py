from flask import Flask, render_template, request, jsonify
import threading
import os
import sys
from automation import run_automation

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Signals the running automation to stop between numbers.
stop_event = threading.Event()

# Tracks whether an automation run is currently in progress, so a second
# run can't be started on top of it (running two Chrome browsers at once
# competes for the same CPU/RAM and can crash both).
is_running = False
run_lock = threading.Lock()

# --- Live log capture -------------------------------------------------
# Every print() call inside run_automation() gets mirrored into this list
# so the frontend can poll /logs and show live output.
log_lines = []
log_lock = threading.Lock()


class LogCapture:
    """Wraps stdout so every printed line is (a) still printed normally
    and (b) appended to log_lines for the /logs endpoint to serve."""

    def __init__(self, original_stream):
        self.original_stream = original_stream
        self.buffer = ""

    def write(self, message):
        self.original_stream.write(message)
        self.buffer += message
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            if line.strip():
                with log_lock:
                    log_lines.append(line)

    def flush(self):
        self.original_stream.flush()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/run", methods=["POST"])
def run():
    global is_running

    with run_lock:
        if is_running:
            return jsonify({
                "status": "⚠️ An automation is already running. Please wait for it to finish or stop it first."
            }), 409
        is_running = True

    if 'file' not in request.files:
        is_running = False
        return jsonify({"status": "Error: No file uploaded"}), 400

    file = request.files['file']
    if file.filename == '':
        is_running = False
        return jsonify({"status": "Error: No file selected"}), 400

    # Save uploaded file as numbers.txt (accepts any original name)
    file_path = os.path.join(UPLOAD_FOLDER, "numbers.txt")
    file.save(file_path)

    url = request.form.get("url", "https://www.luckywin.com.gh/login")

    stop_event.clear()  # reset in case a previous run was stopped

    # clear old logs so this run starts with a fresh log box
    with log_lock:
        log_lines.clear()

    def run_task():
        global is_running
        original_stdout = sys.stdout
        sys.stdout = LogCapture(original_stdout)
        try:
            result = run_automation(url, file_path, stop_event)
            print(result)
        except Exception as e:
            import traceback
            print(f"❌ Automation crashed: {e}")
            traceback.print_exc()
        finally:
            sys.stdout = original_stdout
            is_running = False

    thread = threading.Thread(target=run_task)
    thread.start()

    return jsonify({"status": "✅ Automation started using uploaded file!"})


@app.route("/stop", methods=["POST"])
def stop():
    stop_event.set()
    return jsonify({"status": "🛑 Stop signal sent. It will stop after the current number finishes."})


@app.route("/status")
def status():
    return jsonify({"running": is_running})


@app.route("/logs")
def get_logs():
    with log_lock:
        return jsonify(log_lines)


@app.route("/logs/clear", methods=["POST"])
def clear_logs():
    with log_lock:
        log_lines.clear()
    return jsonify({"status": "cleared"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
