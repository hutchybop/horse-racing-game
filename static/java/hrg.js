window.addEventListener("DOMContentLoaded", function() {
  // Push a new history state so the user starts one step "forward"
  history.pushState(null, "", location.href);

  window.addEventListener("popstate", function () {
    // This fires when the user presses the back button
    const leave = confirm("Going back will destory the race order. Are you sure?");
    if (leave) {
      window.history.back(); // allow navigation
    } else {
      history.pushState(null, "", location.href); // stay on page
    }
  });
});
