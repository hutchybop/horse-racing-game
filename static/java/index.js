(function () {
  const gamesLeftBadge = document.getElementById("gamesLeftBadge");
  const startNewGameBtn = document.getElementById("startNewGameBtn");

  if (!gamesLeftBadge || !startNewGameBtn) {
    return;
  }

  const racesPerGame = 10;
  const minRequired = Number(startNewGameBtn.dataset.minRequired || "10");
  const hasCurrentGame = Number(startNewGameBtn.dataset.gameTracker || "0") !== 0;

  function getBadgeVariant(gamesLeft) {
    if (gamesLeft <= 1) {
      return "danger";
    }
    if (gamesLeft <= 16) {
      return "warning";
    }
    return "success";
  }

  function renderGamesBadge(raceCount) {
    const gamesLeft = Math.max(0, Math.floor(raceCount / racesPerGame));
    const gameLabel = gamesLeft === 1 ? "game" : "games";
    const variant = getBadgeVariant(gamesLeft);

    gamesLeftBadge.textContent = `~${gamesLeft} ${gameLabel}`;
    gamesLeftBadge.className = "badge rounded-pill";
    gamesLeftBadge.classList.add(`text-bg-${variant}`);
  }

  async function refreshCounts() {
    try {
      const res = await fetch("/api/races/count");
      if (!res.ok) {
        return;
      }

      const data = await res.json();
      const raceCount = Number(data.count || 0);
      startNewGameBtn.dataset.raceCount = String(raceCount);
      renderGamesBadge(raceCount);
    } catch (error) {
      return;
    }
  }

  startNewGameBtn.addEventListener("click", function (event) {
    const raceCount = Number(startNewGameBtn.dataset.raceCount || "0");
    if (!hasCurrentGame && raceCount < minRequired) {
      event.preventDefault();
      window.alert(
        `At least ${minRequired} races are required to start a new game. Current races: ${raceCount}.`,
      );
    }
  });

  window.setInterval(refreshCounts, 4000);
  refreshCounts();
})();
