(() => {
  "use strict";

  const track = document.querySelector("#popular-escapes-track");
  const previousButton = document.querySelector("#popular-escapes-previous");
  const nextButton = document.querySelector("#popular-escapes-next");
  const planner = document.querySelector("#recommendation-workspace");
  const form = document.querySelector("#recommendation-form");
  const destinationInput = document.querySelector("#destination-input");
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  function scrollBehavior() {
    return reducedMotion.matches ? "auto" : "smooth";
  }

  function moveCarousel(direction) {
    const card = track.querySelector(".escape-card");
    const styles = window.getComputedStyle(track);
    const gap = Number.parseFloat(styles.columnGap || styles.gap) || 0;
    const distance = card ? card.getBoundingClientRect().width + gap : track.clientWidth;
    track.scrollBy({ left: direction * distance, behavior: scrollBehavior() });
  }

  function moveToPlanner() {
    planner.scrollIntoView({ behavior: scrollBehavior(), block: "start" });
    window.requestAnimationFrame(() => destinationInput.focus({ preventScroll: true }));
  }

  if (track && previousButton && nextButton && planner && form && destinationInput) {
    previousButton.addEventListener("click", () => moveCarousel(-1));
    nextButton.addEventListener("click", () => moveCarousel(1));

    track.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-escape-destination]");
      if (!button) {
        return;
      }
      form.dispatchEvent(
        new CustomEvent("solara:add-destination", {
          detail: { query: button.dataset.escapeDestination },
        }),
      );
      moveToPlanner();
    });

    document.querySelectorAll("[data-scroll-target]").forEach((link) => {
      link.addEventListener("click", (event) => {
        const target = document.querySelector(`#${link.dataset.scrollTarget}`);
        if (!target) {
          return;
        }
        event.preventDefault();
        target.scrollIntoView({ behavior: scrollBehavior(), block: "start" });
      });
    });
  }
})();
