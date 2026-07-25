const startBtn = document.getElementById("start");
const stopBtn = document.getElementById("stop");
const statusEl = document.getElementById("status");
const progressBar = document.getElementById("progressBar");
const urlInput = document.getElementById("url");
const fileInput = document.getElementById("file");

let isRunning = false;

startBtn.onclick = async function() {
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

    } catch (error) {
        statusEl.textContent = "Error starting automation";
        console.error(error);
    }
};

stopBtn.onclick = function() {
    isRunning = false;
    startBtn.disabled = false;
    statusEl.textContent = "Stopped";
    progressBar.style.width = "0%";
};
let logPollInterval = null;

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
    fetch('/logs/clear', { method: 'POST' });
    logPollInterval = setInterval(pollLogs, 1000);
}

function stopLogPolling() {
    if (logPollInterval) clearInterval(logPollInterval);
}