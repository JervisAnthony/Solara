(() => {
  "use strict";

  const form = document.querySelector("#recommendation-form");
  const resultsSection = document.querySelector("#recommendation-results");
  const resultsSummary = document.querySelector("#recommendation-results-summary");
  const resultsTitle = document.querySelector("#results-title");
  const historicalNote = document.querySelector("#recommendation-historical-note");
  const recommendationList = document.querySelector("#recommendation-list");
  const emptyState = document.querySelector("#recommendation-empty");
  const emptyTitle = document.querySelector("#recommendation-empty-title");

  function element(tagName, className, text) {
    const node = document.createElement(tagName);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = String(text);
    return node;
  }

  function percentage(value) {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? `${(numeric * 100).toFixed(1)}%` : "—";
  }

  function destinationNote(response, recommendation) {
    const notes = response.wayfinder?.destination_notes;
    return Array.isArray(notes)
      ? notes.find((note) => note.destination === recommendation.destination.name) ?? null
      : null;
  }

  function seasonalFeel(recommendation) {
    const weather = recommendation.evidence?.seasonal_weather;
    if (!weather) return "Seasonal context is not available for this travel window.";
    const mean = Number(weather.mean_temperature_celsius);
    const rain = Number(weather.mean_daily_precipitation_mm);
    const temperature = mean >= 27
      ? "warmer days and a tropical feel"
      : mean >= 20 ? "mild-to-warm days" : mean >= 12 ? "a cooler, comfortable window" : "crisp, cooler days";
    const moisture = rain >= 4
      ? " Wetter days can be part of the rhythm, so a light waterproof layer may earn its place."
      : " Rainfall tends to be more restrained, leaving more room for unhurried outdoor days.";
    return `Around this time of year, ${recommendation.destination.name} tends to settle into ${temperature}.${moisture}`;
  }

  function goodToKnow(recommendation) {
    const attractions = recommendation.evidence?.attractions;
    if (!Array.isArray(attractions) || attractions.length === 0) return null;
    const names = attractions.slice(0, 3).map((attraction) => attraction.name);
    const joined = names.length === 1
      ? names[0]
      : `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`;
    return `Your validated places shortlist includes ${joined} — useful anchors for a day that still leaves room to wander.`;
  }

  function originLabel(recommendation) {
    const origin = recommendation.origin;
    if (!origin?.requested_scope) return null;
    return origin.was_explicit_locality
      ? `You selected ${origin.requested_scope}`
      : `From your ${origin.requested_scope} search`;
  }

  function geographicContext(recommendation) {
    const regions = recommendation.origin?.administrative_context;
    const context = Array.isArray(regions) ? regions.filter(Boolean) : [];
    return [...context, recommendation.destination.country].join(", ");
  }

  function renderPostcards(recommendation) {
    const section = element("section", "postcards");
    section.setAttribute("aria-label", `Postcards from ${recommendation.destination.name}`);
    section.append(element("p", "card-kicker", "Postcards"));
    const photos = Array.isArray(recommendation.postcards) ? recommendation.postcards : [];
    if (photos.length === 0) {
      const fallback = element("div", "postcard-fallback");
      const mark = document.createElement("img");
      mark.src = "/static/branding/solara-mark-gold.png";
      mark.alt = "";
      mark.width = 1254;
      mark.height = 1254;
      fallback.append(mark, element("strong", "", recommendation.destination.name), element("span", "", recommendation.destination.country));
      section.append(fallback);
      return section;
    }

    const frame = element("div", "postcard-frame");
    const track = element("div", "postcard-track");
    let current = 0;
    const slides = photos.map((photo, index) => {
      const figure = document.createElement("figure");
      figure.className = "postcard-slide";
      figure.hidden = index !== 0;
      const image = document.createElement("img");
      if (index === 0) {
        image.src = photo.image_path;
        image.fetchPriority = recommendation.rank === 1 ? "high" : "auto";
      } else {
        image.dataset.src = photo.image_path;
        image.loading = "lazy";
      }
      image.alt = photo.place_name;
      image.width = photo.width_px;
      image.height = photo.height_px;
      image.decoding = "async";
      const caption = document.createElement("figcaption");
      const source = document.createElement("a");
      source.href = photo.google_maps_uri;
      source.target = "_blank";
      source.rel = "noopener noreferrer";
      source.textContent = "View source photo on Google Maps";
      caption.append(element("span", "postcard-place", photo.place_name), source);
      if (Array.isArray(photo.author_attributions) && photo.author_attributions.length > 0) {
        const credit = element("span", "postcard-credit", "Photo by ");
        photo.author_attributions.forEach((author, authorIndex) => {
          if (authorIndex > 0) credit.append(document.createTextNode(", "));
          if (author.profile_uri) {
            const authorLink = document.createElement("a");
            authorLink.href = author.profile_uri;
            authorLink.target = "_blank";
            authorLink.rel = "noopener noreferrer";
            authorLink.textContent = author.display_name;
            credit.append(authorLink);
          } else {
            credit.append(document.createTextNode(author.display_name));
          }
        });
        caption.append(credit);
      }
      const googleAttribution = element("span", "google-attribution", "Google Maps");
      googleAttribution.setAttribute("translate", "no");
      caption.append(googleAttribution);
      figure.append(image, caption);
      track.append(figure);
      return figure;
    });
    frame.append(track);
    section.append(frame);

    if (slides.length > 1) {
      const controls = element("div", "postcard-controls");
      const previous = element("button", "postcard-arrow", "←");
      previous.type = "button";
      previous.setAttribute("aria-label", "Previous Postcard");
      const status = element("span", "postcard-index", `1 / ${slides.length}`);
      status.setAttribute("aria-live", "polite");
      const next = element("button", "postcard-arrow", "→");
      next.type = "button";
      next.setAttribute("aria-label", "Next Postcard");
      const show = (nextIndex) => {
        current = (nextIndex + slides.length) % slides.length;
        slides.forEach((slide, index) => { slide.hidden = index !== current; });
        const image = slides[current].querySelector("img");
        if (!image.src && image.dataset.src) {
          image.src = image.dataset.src;
          delete image.dataset.src;
        }
        status.textContent = `${current + 1} / ${slides.length}`;
      };
      previous.addEventListener("click", () => show(current - 1));
      next.addEventListener("click", () => show(current + 1));
      let touchStart = null;
      track.addEventListener("touchstart", (event) => { touchStart = event.changedTouches[0]?.clientX ?? null; }, { passive: true });
      track.addEventListener("touchend", (event) => {
        if (touchStart === null) return;
        const distance = (event.changedTouches[0]?.clientX ?? touchStart) - touchStart;
        if (Math.abs(distance) > 40) show(current + (distance < 0 ? 1 : -1));
        touchStart = null;
      }, { passive: true });
      controls.append(previous, status, next);
      section.append(controls);
    }
    return section;
  }

  function renderPlaces(attractions, rank) {
    const section = element("section", "story-section places-section");
    section.append(element("h4", "story-heading", "Places to see"));
    const list = element("ul", "places-list");
    attractions.forEach((attraction, index) => {
      const item = element("li", "", attraction.name);
      item.hidden = index >= 6;
      list.append(item);
    });
    section.append(list);
    if (attractions.length > 6) {
      list.id = `places-${rank}`;
      const toggle = element("button", "places-toggle", "See more places");
      toggle.type = "button";
      toggle.setAttribute("aria-controls", list.id);
      toggle.setAttribute("aria-expanded", "false");
      toggle.addEventListener("click", () => {
        const expanded = toggle.getAttribute("aria-expanded") === "true";
        [...list.children].forEach((item, index) => { item.hidden = expanded && index >= 6; });
        toggle.setAttribute("aria-expanded", String(!expanded));
        toggle.textContent = expanded ? "See more places" : "See fewer places";
      });
      section.append(toggle);
    }
    return section;
  }

  function renderRecommendation(response, recommendation) {
    const item = document.createElement("li");
    const card = document.createElement("article");
    card.className = "destination-story";
    card.id = `destination-story-${recommendation.rank}`;
    card.append(renderPostcards(recommendation));
    const note = destinationNote(response, recommendation);
    const header = element("header", "destination-story-header");
    const identity = element("div", "destination-story-identity");
    identity.append(element("p", "rank-label", `#${recommendation.rank}`), element("h3", "destination-name", recommendation.destination.name), element("p", "destination-country", geographicContext(recommendation)));
    const origin = originLabel(recommendation);
    if (origin) identity.append(element("p", "destination-origin", origin));
    const fit = element("div", "seasonal-fit");
    fit.append(element("span", "", "Seasonal Fit"), element("strong", "", percentage(recommendation.score)));
    header.append(identity, fit);
    card.append(header);
    if (note) {
      const wayfinder = element("section", "wayfinder-section");
      wayfinder.append(element("p", "card-kicker", "The Wayfinder"), element("p", "wayfinder-copy", note.why_it_fits));
      card.append(wayfinder);
    }
    const storyGrid = element("div", "story-grid");
    const seasonal = element("section", "story-section");
    seasonal.append(element("h4", "story-heading", "Seasonal feel"), element("p", "", note?.seasonal_feel ?? seasonalFeel(recommendation)));
    storyGrid.append(seasonal, renderPlaces(recommendation.evidence?.attractions ?? [], recommendation.rank));
    const goodToKnowCopy = note?.good_to_know ?? goodToKnow(recommendation);
    if (goodToKnowCopy) {
      const good = element("section", "story-section good-to-know");
      good.append(element("h4", "story-heading", "Good to know"), element("p", "", goodToKnowCopy));
      storyGrid.append(good);
    }
    card.append(storyGrid);
    const actions = element("div", "destination-story-actions");
    const build = element("button", "build-trip-button", "Build this trip");
    build.type = "button";
    build.addEventListener("click", () => {
      window.dispatchEvent(new CustomEvent("solara:build-trip", {
        detail: { response, recommendations: [recommendation] },
      }));
    });
    actions.append(build);
    card.append(actions);
    item.append(card);
    return item;
  }

  function heading(response) {
    const recommendations = response.recommendations;
    const mode = response.request?.destination_mode;
    if (recommendations.length === 1 && ["explicit_queries", "pre_resolved"].includes(mode)) return `${recommendations[0].destination.name} for your trip`;
    if (mode === "scope_discovery" && response.request?.travel_scope?.display_name) return `Places in ${response.request.travel_scope.display_name} worth considering`;
    if (mode === "mixed_scopes") return "Places across your searches worth considering";
    if (mode === "discovery") return "Places that fit this trip";
    return "Your shortlist";
  }

  function renderOverview(response) {
    if (response.recommendations.length < 2) return null;
    const item = element("li", "shortlist-overview-item");
    const nav = element("nav", "shortlist-overview");
    nav.setAttribute("aria-label", "Shortlist overview");
    nav.append(element("p", "card-kicker", "At a glance"));
    const list = element("ol", "shortlist-links");
    response.recommendations.forEach((recommendation) => {
      const row = document.createElement("li");
      const link = document.createElement("a");
      link.href = `#destination-story-${recommendation.rank}`;
      link.append(element("span", "overview-rank", String(recommendation.rank)), element("strong", "", recommendation.destination.name), element("span", "", percentage(recommendation.score)));
      const note = destinationNote(response, recommendation);
      if (note) link.append(element("small", "", note.why_it_fits));
      const origin = originLabel(recommendation);
      if (origin) link.append(element("small", "overview-origin", origin));
      row.append(link);
      list.append(row);
    });
    nav.append(list);
    if (response.wayfinder?.opening) nav.append(element("p", "wayfinder-opening", response.wayfinder.opening));
    if (response.wayfinder?.comparison_note) nav.append(element("p", "comparison-note", response.wayfinder.comparison_note));
    const buildRoute = element("button", "build-route-button", "Build a multi-stop trip");
    buildRoute.type = "button";
    buildRoute.addEventListener("click", () => {
      window.dispatchEvent(new CustomEvent("solara:build-trip", {
        detail: { response, recommendations: response.recommendations.slice(0, 5) },
      }));
    });
    nav.append(buildRoute);
    item.append(nav);
    return item;
  }

  function clearResults() {
    resultsSection.hidden = true;
    recommendationList.replaceChildren();
    resultsSummary.replaceChildren();
    emptyState.hidden = true;
    historicalNote.hidden = true;
  }

  function renderResponse(response) {
    clearResults();
    resultsTitle.textContent = heading(response);
    if (response.has_recommendations === false || response.recommendations.length === 0) {
      resultsSection.hidden = false;
      emptyState.hidden = false;
      emptyTitle.focus();
      return;
    }
    const fragment = document.createDocumentFragment();
    const overview = renderOverview(response);
    if (overview) fragment.append(overview);
    response.recommendations.forEach((recommendation) => { fragment.append(renderRecommendation(response, recommendation)); });
    recommendationList.replaceChildren(fragment);
    const period = response.request?.travel_period;
    resultsSummary.textContent = period
      ? `${response.recommendation_count} places considered for ${period.start_date} — ${period.end_date}.`
      : `${response.recommendation_count} places considered.`;
    historicalNote.hidden = false;
    resultsSection.hidden = false;
    resultsTitle.focus();
  }

  function handleReady(event) {
    try { renderResponse(event.detail); } catch { clearResults(); }
  }

  emptyState?.querySelectorAll("[data-recovery-target]").forEach((control) => {
    control.addEventListener("click", () => {
      const target = document.querySelector(`#${control.dataset.recoveryTarget}`);
      document.querySelector("#planner")?.scrollIntoView({ behavior: "smooth" });
      target?.focus();
    });
  });

  if (form && resultsSection && resultsSummary && resultsTitle && historicalNote && recommendationList && emptyState && emptyTitle) {
    form.addEventListener("solara:recommendation-request-start", clearResults);
    form.addEventListener("solara:recommendation-ready", handleReady);
  }
})();
