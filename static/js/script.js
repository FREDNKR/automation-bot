const startBtn = document.getElementById("start");
const stopBtn = document.getElementById("stop");
const statusEl = document.getElementById("status");
const progressBar = document.getElementById("progressBar");
const urlInput = document.getElementById("url");
const fileInput = document.getElementById("file");

let isRunning = false;
let logPollInterval = null;
let statusPollInterval = null;

startBtn.onclick = async function () {
    if (isRunning) return;
    if (!fileInput.files[0]) {
        alert("Please upload a numbers file first!");
        return;
    }

    const targetUrl = urlInput.value.trim();
    if (!targetUrl) {
        alert("Please enter Target URL");
        return;
    }

    isRunning = true;
    startBtn.disabled = true;
    statusEl.textContent = "Uploading file and starting...";
    progressBar.style.width = "40%";

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);
    formData.append("url", targetUrl);

    try {
        const response = await fetch("/run", {
            method: "POST",
            body: formData
        });

        const result = await response.json();
        statusEl.textContent = result.status || "Running...";
        progressBar.style.width = "80%";

        // 409 means one was already running — don't start polling a fresh run
        if (response.ok) {
            startLogPolling();
            startStatusPolling();
        } else {
            isRunning = false;
            startBtn.disabled = false;
        }

    } catch (error) {
        statusEl.textContent = "Error starting automation";
        console.error(error);
        isRunning = false;
        startBtn.disabled = false;
    }
};

stopBtn.onclick = async function () {
    try {
        const response = await fetch("/stop", { method: "POST" });
        const result = await response.json();
        statusEl.textContent = result.status || "Stopped";
    } catch (error) {
        console.error(error);
    }
    // Note: the automation actually stops after it finishes the current
    // number (see stop_event in app.py) — polling keeps running until
    // /status reports running:false so you still see the final log lines.
};

function pollLogs() {
    fetch('/logs')
        .then(res => res.json())
        .then(lines => {
            const box = document.getElementById('logBox');
            box.textContent = lines.join('\n');
            box.scrollTop = box.scrollHeight;
        })
        .catch(err => console.error('log fetch failed', err));
}

function startLogPolling() {
    logPollInterval = setInterval(pollLogs, 1000);
    pollLogs(); // immediate first fetch instead of waiting 1s
}

function stopLogPolling() {
    if (logPollInterval) clearInterval(logPollInterval);
    logPollInterval = null;
}

function pollStatus() {
    fetch('/status')
        .then(res => res.json())
        .then(data => {
            if (!data.running) {
                // automation finished (or was stopped) on the server
                isRunning = false;
                startBtn.disabled = false;
                progressBar.style.width = "100%";
                stopStatusPolling();
                stopLogPolling();
                pollLogs(); // one last fetch to catch the final log lines
            }
        })
        .catch(err => console.error('status fetch failed', err));
}

function startStatusPolling() {
    statusPollInterval = setInterval(pollStatus, 1500);
}

function stopStatusPolling() {
    if (statusPollInterval) clearInterval(statusPollInterval);
    statusPollInterval = null;
}
