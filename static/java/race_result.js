document.getElementById("calculateBtn").addEventListener("click", function() {
    const betInput = document.getElementById("betAmount");
    const returnsBox = document.getElementById("returnsBox");
    const returnsAmount = document.getElementById("returnsAmount");

    const bet = parseFloat(betInput.value);
    if (isNaN(bet) || bet <= 0) {
        alert("Please enter a valid bet amount.");
        return;
    }

    const odds = parseFloat(this.dataset.odds);
    const returns = Math.round((bet * odds) + bet);

    returnsAmount.textContent = "£" + returns.toFixed(2);
    returnsBox.style.display = "block";
});