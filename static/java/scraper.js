(function () {
  const runScraperBtn = document.getElementById("runScraperBtn");
  const runMoveBtn = document.getElementById("runMoveBtn");
  const logOutput = document.getElementById("logOutput");
  const jobStatus = document.getElementById("jobStatus");
  const jobTitle = document.getElementById("jobTitle");
  const readyPanel = document.getElementById("readyPanel");
  const raceCountBadge = document.getElementById("raceCountBadge");
  const cancelJobBtn = document.getElementById("cancelJobBtn");
  const refreshRaceCountBtn = document.getElementById("refreshRaceCountBtn");

  let activeJob = window.scraperPageState.activeJob;
  let logSeq = 0;
  let pollTimer = null;

  function setButtonsDisabled(disabled) {
    runScraperBtn.disabled = disabled;
    runMoveBtn.disabled = disabled;
  }

  function setCancelVisible(visible) {
    if (visible) {
      cancelJobBtn.classList.remove("d-none");
    } else {
      cancelJobBtn.classList.add("d-none");
    }
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
    if (status === "cancelled") {
      jobStatus.classList.add("text-bg-secondary");
      jobStatus.textContent = "Cancelled";
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

  async function refreshRaceCount(redirectIfReady) {
    const res = await fetch("/api/races/count");
    if (!res.ok) {
      return false;
    }
    const data = await res.json();
    raceCountBadge.textContent = `${data.count} / ${data.min_required} races`;
    if (data.enough) {
      readyPanel.classList.remove("d-none");
      if (redirectIfReady) {
        window.location.href = "/";
      }
    } else {
      readyPanel.classList.add("d-none");
    }
    return data.enough;
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
      setCancelVisible(false);
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
    setCancelVisible(activeJob.status === "running" || activeJob.status === "queued");

    const jobName =
      activeJob.job_type === "scrape_races" ? "races_scraper.py" : "move_races.py";
    jobTitle.textContent = `Process Output - ${jobName}`;

    if (activeJob.status === "running" || activeJob.status === "queued") {
      setButtonsDisabled(true);
      return;
    }

    setButtonsDisabled(false);
    setCancelVisible(false);
    stopPolling();
    await refreshRaceCount(true);
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
    setCancelVisible(true);
    startPolling();
  }

  async function cancelActiveJob() {
    if (!activeJob || !activeJob.id) {
      return;
    }

    cancelJobBtn.disabled = true;
    const res = await fetch(`/api/jobs/${activeJob.id}/cancel`, {
      method: "POST",
    });
    const payload = await res.json();
    cancelJobBtn.disabled = false;

    if (!res.ok) {
      if (payload.job) {
        activeJob = payload.job;
      }
      if (logOutput.textContent === "No process output yet.") {
        logOutput.textContent = "";
      }
      logOutput.textContent += `Cancel request failed: ${payload.error || "Unknown error"}\n`;
      return;
    }

    if (logOutput.textContent === "No process output yet.") {
      logOutput.textContent = "";
    }
    logOutput.textContent += "Cancel requested. Waiting for process shutdown...\n";

    activeJob = payload.job;
    setCancelVisible(false);
    startPolling();
  }

  runScraperBtn.addEventListener("click", function () {
    createJob("scrape_races");
  });

  runMoveBtn.addEventListener("click", function () {
    createJob("move_races");
  });

  cancelJobBtn.addEventListener("click", function () {
    cancelActiveJob();
  });

  refreshRaceCountBtn.addEventListener("click", function () {
    refreshRaceCount(true);
  });

  if (activeJob) {
    setButtonsDisabled(true);
    setCancelVisible(true);
    startPolling();
  } else {
    renderStatus("idle");
    setButtonsDisabled(false);
    setCancelVisible(false);
  }

  refreshRaceCount(false);
})();
