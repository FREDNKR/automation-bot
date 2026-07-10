from flask import Flask, render_template, request, jsonify
import threading
import os
from automation import run_automation

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/run", methods=["POST"])
def run():
    if 'file' not in request.files:
        return jsonify({"status": "Error: No file uploaded"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "Error: No file selected"}), 400

    # Save uploaded file as numbers.txt (accepts any original name)
    file_path = os.path.join(UPLOAD_FOLDER, "numbers.txt")
    file.save(file_path)

    url = request.form.get("url", "https://www.luckywin.com.gh/login")

    def run_task():
        try:
            result = run_automation(url, file_path)
            print(result)
        except Exception as e:
            import traceback
            print(f"❌ Automation crashed: {e}")
            traceback.print_exc()

    thread = threading.Thread(target=run_task)
    thread.start()

    return jsonify({"status": "✅ Automation started using uploaded file!"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)