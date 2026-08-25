(() => {
  "use strict";

  const track = document.querySelector("#popular-escapes-track");
  const previousButton = document.querySelector("#popular-escapes-previous");
  const nextButton = document.querySelector("#popular-escapes-next");
  const carouselMotionButton = document.querySelector("#popular-escapes-motion");
  const planner = document.querySelector("#recommendation-workspace");
  const form = document.querySelector("#recommendation-form");
  const destinationInput = document.querySelector("#destination-input");
  const hero = document.querySelector("[data-hero-slideshow]");
  const heroMotionButton = document.querySelector("[data-hero-motion-control]");
  const heroCaption = document.querySelector("[data-hero-caption]");
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const intervalMilliseconds = 5000;
  const heroCaptions = [
    "Camps Bay, Cape Town",
    "Cebu, Philippines",
    "Kyoto, Japan",
    "Bali, Indonesia",
    "Istanbul, Türkiye",
    "Budapest, Hungary",
  ];
  let carouselTimer = null;
  let heroTimer = null;
  let heroIndex = 0;
  let carouselPausedByUser = false;
  let heroPausedByUser = false;
  let carouselInteractionPaused = false;

  function scrollBehavior() {
    return reducedMotion.matches ? "auto" : "smooth";
  }

  function moveCarousel(direction) {
    const card = track.querySelector(".escape-card");
    const styles = window.getComputedStyle(track);
    const gap = Number.parseFloat(styles.columnGap || styles.gap) || 0;
    const distance = card ? card.getBoundingClientRect().width + gap : track.clientWidth;
    const atEnd = track.scrollLeft + track.clientWidth >= track.scrollWidth - 2;
    if (direction > 0 && atEnd) {
      track.scrollTo({ left: 0, behavior: scrollBehavior() });
    } else {
      track.scrollBy({ left: direction * distance, behavior: scrollBehavior() });
    }
  }

  function carouselMayRun() {
    return (
      !reducedMotion.matches &&
      !document.hidden &&
      !carouselPausedByUser &&
      !carouselInteractionPaused
    );
  }

  function syncCarouselTimer() {
    window.clearInterval(carouselTimer);
    carouselTimer = null;
    if (carouselMayRun()) {
      carouselTimer = window.setInterval(() => moveCarousel(1), intervalMilliseconds);
    }
  }

  function toggleCarouselMotion() {
    carouselPausedByUser = !carouselPausedByUser;
    carouselMotionButton.setAttribute("aria-pressed", String(carouselPausedByUser));
    carouselMotionButton.setAttribute(
      "aria-label",
      carouselPausedByUser ? "Resume carousel" : "Pause carousel",
    );
    carouselMotionButton.textContent = carouselPausedByUser ? "Play" : "Pause";
    syncCarouselTimer();
  }

  function showHeroSlide(nextIndex) {
    const slides = [...hero.querySelectorAll(".hero-slide")];
    if (slides.length === 0) {
      return;
    }
    heroIndex = (nextIndex + slides.length) % slides.length;
    const activeSlide = slides[heroIndex];
    if (!activeSlide.src && activeSlide.dataset.src) {
      activeSlide.src = activeSlide.dataset.src;
      delete activeSlide.dataset.src;
    }
    slides.forEach((slide, index) => {
      slide.classList.toggle("is-active", index === heroIndex);
      slide.setAttribute("aria-hidden", String(index !== heroIndex));
    });
    heroCaption.textContent = heroCaptions[heroIndex];
    const followingSlide = slides[(heroIndex + 1) % slides.length];
    if (!followingSlide.src && followingSlide.dataset.src) {
      followingSlide.src = followingSlide.dataset.src;
      delete followingSlide.dataset.src;
    }
  }

  function heroMayRun() {
    return !reducedMotion.matches && !document.hidden && !heroPausedByUser;
  }

  function syncHeroTimer() {
    window.clearInterval(heroTimer);
    heroTimer = null;
    if (heroMayRun()) {
      heroTimer = window.setInterval(() => showHeroSlide(heroIndex + 1), intervalMilliseconds);
    }
  }

  function toggleHeroMotion() {
    heroPausedByUser = !heroPausedByUser;
    heroMotionButton.setAttribute("aria-pressed", String(heroPausedByUser));
    heroMotionButton.setAttribute(
      "aria-label",
      heroPausedByUser ? "Resume slideshow" : "Pause slideshow",
    );
    heroMotionButton.textContent = heroPausedByUser ? "Play" : "Pause";
    syncHeroTimer();
  }

  function moveToPlanner() {
    planner.scrollIntoView({ behavior: scrollBehavior(), block: "start" });
    window.requestAnimationFrame(() => destinationInput.focus({ preventScroll: true }));
  }

  if (
    track && previousButton && nextButton && carouselMotionButton && planner &&
    form && destinationInput && hero && heroMotionButton && heroCaption
  ) {
    previousButton.addEventListener("click", () => {
      moveCarousel(-1);
      syncCarouselTimer();
    });
    nextButton.addEventListener("click", () => {
      moveCarousel(1);
      syncCarouselTimer();
    });
    carouselMotionButton.addEventListener("click", toggleCarouselMotion);
    heroMotionButton.addEventListener("click", toggleHeroMotion);

    ["pointerenter", "focusin", "pointerdown"].forEach((eventName) => {
      track.addEventListener(eventName, () => {
        carouselInteractionPaused = true;
        syncCarouselTimer();
      });
    });
    ["pointerleave", "focusout", "pointerup", "pointercancel"].forEach((eventName) => {
      track.addEventListener(eventName, () => {
        carouselInteractionPaused = track.matches(":hover") || track.contains(document.activeElement);
        syncCarouselTimer();
      });
    });

    track.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-escape-destination]");
      if (!button) {
        return;
      }
      form.dispatchEvent(new CustomEvent("solara:add-destination", {
        detail: { query: button.dataset.escapeDestination, kind: "locality" },
      }));
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

    document.addEventListener("visibilitychange", () => {
      syncCarouselTimer();
      syncHeroTimer();
    });
    reducedMotion.addEventListener("change", () => {
      syncCarouselTimer();
      syncHeroTimer();
    });
    showHeroSlide(0);
    syncCarouselTimer();
    syncHeroTimer();
  }
})();
