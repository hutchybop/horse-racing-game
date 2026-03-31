(function () {
  const runScraperBtn = document.getElementById("runScraperBtn");
  const runMoveBtn = document.getElementById("runMoveBtn");
  const logOutput = document.getElementById("logOutput");
  const jobStatus = document.getElementById("jobStatus");
  const jobTitle = document.getElementById("jobTitle");
  const readyPanel = document.getElementById("readyPanel");
  const raceCountBadge = document.getElementById("raceCountBadge");

  let activeJob = window.scraperPageState.activeJob;
  let logSeq = 0;
  let pollTimer = null;

  function setButtonsDisabled(disabled) {
    runScraperBtn.disabled = disabled;
    runMoveBtn.disabled = disabled;
  }

  function renderStatus(status) {
    jobStatus.className = "badge";
    if (status === "running" || status === "queued") {
      jobStatus.classList.add("text-bg-warning");
      jobStatus.textContent = status === "running" ? "Running" : "Queued";
      return;
    }
    if (status === "succeeded") {
      jobStatus.classList.add("text-bg-success");
      jobStatus.textContent = "Succeeded";
      return;
    }
    if (status === "failed") {
      jobStatus.classList.add("text-bg-danger");
      jobStatus.textContent = "Failed";
      return;
    }
    jobStatus.classList.add("text-bg-secondary");
    jobStatus.textContent = "Idle";
  }

  function appendLogs(lines) {
    if (!lines || lines.length === 0) {
      return;
    }
    if (logOutput.textContent === "No process output yet.") {
      logOutput.textContent = "";
    }
    lines.forEach((entry) => {
      logOutput.textContent += `[${entry.seq}] ${entry.line}\n`;
      logSeq = entry.seq;
    });
    logOutput.scrollTop = logOutput.scrollHeight;
  }

  async function refreshRaceCount() {
    const res = await fetch("/api/races/count");
    const data = await res.json();
    raceCountBadge.textContent = `${data.count} / ${data.min_required} races`;
    if (data.enough) {
      readyPanel.classList.remove("d-none");
    } else {
      readyPanel.classList.add("d-none");
    }
  }

  function stopPolling() {
    if (pollTimer) {
      window.clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  async function pollActiveJob() {
    if (!activeJob) {
      stopPolling();
      renderStatus("idle");
      setButtonsDisabled(false);
      return;
    }

    const res = await fetch(`/api/jobs/${activeJob.id}/logs?after_seq=${logSeq}`);
    if (!res.ok) {
      stopPolling();
      setButtonsDisabled(false);
      renderStatus("failed");
      return;
    }

    const payload = await res.json();
    activeJob = payload.job;
    appendLogs(payload.lines);
    renderStatus(activeJob.status);

    const jobName = activeJob.job_type === "scrape_races" ? "races_scraper.py" : "move_races.py";
    jobTitle.textContent = `Process Output - ${jobName}`;

    if (activeJob.status === "running" || activeJob.status === "queued") {
      setButtonsDisabled(true);
      return;
    }

    setButtonsDisabled(false);
    stopPolling();
    await refreshRaceCount();
  }

  function startPolling() {
    stopPolling();
    pollTimer = window.setInterval(pollActiveJob, 1500);
    pollActiveJob();
  }

  async function createJob(jobType) {
    const res = await fetch("/api/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_type: jobType }),
    });

    const payload = await res.json();

    if (res.status === 409 && payload.active_job) {
      activeJob = payload.active_job;
      if (logOutput.textContent === "No process output yet.") {
        logOutput.textContent = "";
      }
      logOutput.textContent += "Another job is already active. Following existing job output.\n";
      startPolling();
      return;
    }

    if (!res.ok) {
      if (logOutput.textContent === "No process output yet.") {
        logOutput.textContent = "";
      }
      logOutput.textContent += `Failed to start job: ${payload.error || "Unknown error"}\n`;
      renderStatus("failed");
      return;
    }

    activeJob = payload.job;
    logSeq = 0;
    logOutput.textContent = "";
    readyPanel.classList.add("d-none");
    startPolling();
  }

  runScraperBtn.addEventListener("click", function () {
    createJob("scrape_races");
  });

  runMoveBtn.addEventListener("click", function () {
    createJob("move_races");
  });

  if (activeJob) {
    setButtonsDisabled(true);
    startPolling();
  } else {
    renderStatus("idle");
    setButtonsDisabled(false);
  }

  refreshRaceCount();
})();
