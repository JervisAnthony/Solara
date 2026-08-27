(() => {
  "use strict";

  const studio = document.querySelector("#itinerary-studio");
  const closeButton = document.querySelector("#studio-close");
  const partyPresets = document.querySelector("#party-presets");
  const partyCounters = document.querySelector("#party-counters");
  const paceOptions = document.querySelector("#pace-options");
  const requirementOptions = document.querySelector("#requirement-options");
  const route = document.querySelector("#destination-route");
  const routeDuration = document.querySelector("#route-duration");
  const daysContainer = document.querySelector("#itinerary-days");
  const categories = document.querySelector("#activity-categories");
  const activityOptions = document.querySelector("#activity-options");
  const activeDayLabel = document.querySelector("#active-day-label");
  const status = document.querySelector("#studio-status");
  const summary = document.querySelector("#wayfinder-itinerary-copy");
  const title = document.querySelector("#itinerary-studio-title");

  if (!studio || !closeButton || !partyPresets || !partyCounters || !paceOptions ||
      !requirementOptions || !route || !routeDuration || !daysContainer || !categories ||
      !activityOptions || !activeDayLabel || !status || !summary || !title) return;

  const PERIODS = ["morning", "afternoon", "evening"];
  const CAPACITY = { relaxed: 480, balanced: 600, active: 720 };
  const REQUIREMENT_BUFFER = {
    wheelchair_access: 30,
    reduced_walking: 30,
    frequent_breaks: 45,
    stroller: 20,
    slower_transitions: 30,
  };
  const PRESETS = {
    solo: { adults: 1, children: 0, seniors: 0 },
    couple: { adults: 2, children: 0, seniors: 0 },
    family: { adults: 2, children: 2, seniors: 0 },
    group: { adults: 4, children: 0, seniors: 0 },
  };

  let state = null;

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = String(text);
    return node;
  }

  function button(text, className, onClick, label) {
    const node = element("button", className, text);
    node.type = "button";
    if (label) node.setAttribute("aria-label", label);
    node.addEventListener("click", onClick);
    return node;
  }

  function tripDays(response) {
    const period = response.request?.travel_period;
    const start = new Date(`${period.start_date}T00:00:00Z`);
    const end = new Date(`${period.end_date}T00:00:00Z`);
    return Math.max(1, Math.round((end - start) / 86400000) + 1);
  }

  function distributeDays(total, count) {
    const usableCount = Math.min(total, count);
    return Array.from({ length: usableCount }, (_, index) =>
      Math.floor(total / usableCount) + (index < total % usableCount ? 1 : 0));
  }

  function estimate(category) {
    const normalized = String(category).toLowerCase();
    const rules = [
      [["museum", "gallery", "temple", "church", "cultural"], [60, 120]],
      [["beach", "park", "nature", "garden", "hiking"], [120, 180]],
      [["market", "food", "restaurant"], [90, 120]],
      [["night", "entertainment"], [90, 150]],
      [["landmark", "attraction", "viewpoint"], [60, 90]],
    ];
    const match = rules.find(([words]) => words.some((word) => normalized.includes(word)));
    return match ? { minimum: match[1][0], maximum: match[1][1], provenance: "category heuristic" } : null;
  }

  function prepareActivity(attraction, destination, index) {
    const coordinates = attraction.coordinates || {};
    return {
      identity: `${destination.name}-${coordinates.latitude ?? "x"}-${coordinates.longitude ?? index}-${attraction.name}`,
      name: attraction.name,
      category: attraction.category,
      destination: destination.name,
      duration: estimate(attraction.category),
      accessibility: "unknown",
    };
  }

  function openStudio(detail) {
    if (!detail?.response || !Array.isArray(detail.recommendations) || detail.recommendations.length === 0) return;
    const total = tripDays(detail.response);
    const selected = detail.recommendations.slice(0, total);
    const allocations = distributeDays(total, selected.length);
    state = {
      response: detail.response,
      totalDays: total,
      destinations: selected.map((recommendation, index) => ({
        ...recommendation.destination,
        days: allocations[index],
        activities: (recommendation.evidence?.attractions || []).map((activity, activityIndex) =>
          prepareActivity(activity, recommendation.destination, activityIndex)),
      })),
      party: { ...PRESETS.solo },
      pace: "balanced",
      requirements: new Set(),
      selectedActivities: [],
      travelModes: Array.from({ length: Math.max(0, selected.length - 1) }, () => "road"),
      activeDay: 1,
      category: "all",
      replacement: null,
    };
    studio.hidden = false;
    render();
    title.focus();
    studio.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  }

  function dayPlan() {
    const plan = [];
    let number = 1;
    state.destinations.forEach((destination, destinationIndex) => {
      for (let localDay = 0; localDay < destination.days; localDay += 1) {
        plan.push({
          number,
          destination,
          travelMode: destinationIndex > 0 && localDay === 0 ? state.travelModes[destinationIndex - 1] : null,
        });
        number += 1;
      }
    });
    return plan;
  }

  function setPreset(preset) {
    state.party = { ...PRESETS[preset] };
    partyPresets.querySelectorAll("button").forEach((item) => {
      item.setAttribute("aria-pressed", String(item.dataset.party === preset));
    });
    renderPartyCounters();
    renderDays();
  }

  function renderPartyCounters() {
    const fragment = document.createDocumentFragment();
    [["adults", "Adults"], ["children", "Children"], ["seniors", "Seniors"]].forEach(([key, label]) => {
      const row = element("div", "party-counter");
      row.append(element("span", "", label));
      const controls = element("div", "counter-controls");
      controls.append(
        button("−", "counter-button", () => updateParty(key, -1), `Remove one ${label.toLowerCase()}`),
        element("strong", "", state.party[key]),
        button("+", "counter-button", () => updateParty(key, 1), `Add one ${label.toLowerCase()}`),
      );
      row.append(controls);
      fragment.append(row);
    });
    partyCounters.replaceChildren(fragment);
  }

  function updateParty(key, delta) {
    const total = state.party.adults + state.party.children + state.party.seniors;
    const next = state.party[key] + delta;
    if (next < 0 || (delta < 0 && total === 1) || (delta > 0 && total === 20)) return;
    state.party[key] = next;
    partyPresets.querySelectorAll("button").forEach((item) => item.setAttribute("aria-pressed", "false"));
    renderPartyCounters();
    renderDays();
  }

  function updateAllocation(index, delta) {
    if (state.destinations.length < 2) return;
    const receiver = index === state.destinations.length - 1 ? index - 1 : index + 1;
    if (delta > 0 && state.destinations[receiver].days <= 1) return;
    if (delta < 0 && state.destinations[index].days <= 1) return;
    state.destinations[index].days += delta;
    state.destinations[receiver].days -= delta;
    const validDays = new Set(dayPlan().map((day) => `${day.number}:${day.destination.name}`));
    state.selectedActivities = state.selectedActivities.filter((activity) =>
      validDays.has(`${activity.day}:${activity.destination}`));
    state.activeDay = Math.min(state.activeDay, state.totalDays);
    render();
  }

  function moveDestination(index, direction) {
    const target = index + direction;
    if (target < 0 || target >= state.destinations.length) return;
    [state.destinations[index], state.destinations[target]] = [state.destinations[target], state.destinations[index]];
    state.travelModes = Array.from({ length: state.destinations.length - 1 }, (_, modeIndex) => state.travelModes[modeIndex] || "road");
    state.selectedActivities = [];
    state.activeDay = 1;
    announce("Route reordered. Selected activities were cleared so day geography remains valid.");
    render();
  }

  function removeDestination(index) {
    if (state.destinations.length === 1) return;
    const removed = state.destinations[index];
    const receiver = index === state.destinations.length - 1 ? index - 1 : index + 1;
    state.destinations[receiver].days += removed.days;
    state.destinations.splice(index, 1);
    state.travelModes = Array.from({ length: state.destinations.length - 1 }, (_, modeIndex) => state.travelModes[modeIndex] || "road");
    state.selectedActivities = state.selectedActivities.filter((activity) => activity.destination !== removed.name);
    state.activeDay = 1;
    announce(`${removed.name} removed. Its days were reassigned.`);
    render();
  }

  function renderRoute() {
    const fragment = document.createDocumentFragment();
    state.destinations.forEach((destination, index) => {
      const card = element("article", "route-card");
      const header = element("div", "route-card-header");
      header.append(element("span", "route-order", String(index + 1)), element("div", "", undefined));
      header.lastChild.append(element("strong", "", destination.name), element("span", "", destination.country));
      const reorder = element("div", "route-actions");
      reorder.append(
        button("↑", "route-icon", () => moveDestination(index, -1), `Move ${destination.name} earlier`),
        button("↓", "route-icon", () => moveDestination(index, 1), `Move ${destination.name} later`),
        button("×", "route-icon", () => removeDestination(index), `Remove ${destination.name}`),
      );
      header.append(reorder);
      const allocation = element("div", "day-allocation");
      allocation.append(
        button("−", "counter-button", () => updateAllocation(index, -1), `Allocate one fewer day to ${destination.name}`),
        element("strong", "", `${destination.days} ${destination.days === 1 ? "day" : "days"}`),
        button("+", "counter-button", () => updateAllocation(index, 1), `Allocate one more day to ${destination.name}`),
      );
      card.append(header, allocation);
      fragment.append(card);
      if (index < state.destinations.length - 1) fragment.append(renderTravelLeg(index));
    });
    route.replaceChildren(fragment);
    routeDuration.textContent = `${state.totalDays} days · ${state.destinations.length} ${state.destinations.length === 1 ? "destination" : "destinations"}`;
  }

  function renderTravelLeg(index) {
    const leg = element("div", "travel-leg");
    const copy = element("div", "travel-leg-copy");
    copy.append(element("span", "travel-line", ""), element("strong", "", "Travel leg"), element("small", "", "Duration unavailable · hold transfer time before finalising"));
    const modes = element("div", "travel-modes");
    ["flight", "rail", "road", "ferry"].forEach((mode) => {
      const option = button(mode, "", () => {
        state.travelModes[index] = mode;
        render();
      });
      option.setAttribute("aria-pressed", String(state.travelModes[index] === mode));
      modes.append(option);
    });
    leg.append(copy, modes);
    return leg;
  }

  function assessment(day) {
    const selected = state.selectedActivities.filter((activity) => activity.day === day.number);
    let buffer = 90 + Math.max(0, selected.length - 1) * 30;
    if (state.party.children) buffer += 30;
    if (state.party.seniors) buffer += 30;
    state.requirements.forEach((requirement) => { buffer += REQUIREMENT_BUFFER[requirement] || 0; });
    let occupied = buffer + (day.travelMode ? 90 : 0);
    const warnings = [];
    selected.forEach((activity) => {
      if (activity.duration) occupied += Math.ceil((activity.duration.minimum + activity.duration.maximum) / 2);
      else warnings.push(`Duration is unknown for ${activity.name}.`);
    });
    if (day.travelMode) warnings.push("Travel duration is unknown; the day includes only a 90-minute planning hold.");
    const available = CAPACITY[state.pace];
    const ratio = occupied / available;
    const level = ratio <= 0.45 ? "relaxed" : ratio <= 0.70 ? "comfortable" : ratio <= 0.90 ? "full" : "very full";
    if (ratio > 0.90) warnings.push("This day is becoming quite full for your pace and travel needs. Consider moving one activity.");
    return { occupied, available, buffer, level, warnings, impossible: occupied > 1440 };
  }

  function renderDays() {
    const fragment = document.createDocumentFragment();
    dayPlan().forEach((day) => {
      const card = element("article", `itinerary-day${state.activeDay === day.number ? " is-active" : ""}`);
      const heading = element("header", "day-heading");
      const choose = button(`Day ${day.number}`, "day-selector", () => {
        state.activeDay = day.number;
        state.category = "all";
        renderDays();
        renderPalette();
      }, `Choose Day ${day.number}, ${day.destination.name}`);
      choose.setAttribute("aria-pressed", String(state.activeDay === day.number));
      heading.append(choose, element("div", "", undefined));
      heading.lastChild.append(element("strong", "", day.destination.name), element("span", "", day.travelMode ? `Arrival day · ${day.travelMode}` : "A full destination day"));
      const load = assessment(day);
      const meter = element("div", `feasibility feasibility-${load.level.replace(" ", "-")}`);
      meter.append(element("strong", "", load.level), element("span", "", `${load.occupied} of ${load.available} planning minutes`));
      const bar = element("span", "feasibility-track");
      const fill = element("span", "feasibility-fill");
      fill.style.setProperty("--day-load", `${Math.min(100, Math.round(load.occupied / load.available * 100))}%`);
      bar.append(fill);
      meter.append(bar);
      heading.append(meter);
      card.append(heading);

      const periods = element("div", "day-periods");
      PERIODS.forEach((period) => periods.append(renderPeriod(day, period)));
      card.append(periods);
      if (load.warnings.length) {
        const guidance = element("div", "feasibility-guidance");
        guidance.append(element("strong", "", load.impossible ? "Hard timing conflict" : "Planning guidance"));
        load.warnings.forEach((warning) => guidance.append(element("p", "", warning)));
        card.append(guidance);
      }
      fragment.append(card);
    });
    daysContainer.replaceChildren(fragment);
    updateSummary();
  }

  function renderPeriod(day, period) {
    const section = element("section", "day-period");
    section.append(element("h4", "", period));
    const selected = state.selectedActivities
      .filter((activity) => activity.day === day.number && activity.period === period)
      .sort((left, right) => left.order - right.order);
    if (!selected.length) section.append(element("p", "period-empty", "Open space for discovery or rest."));
    selected.forEach((activity, index) => {
      const item = element("div", "planned-activity");
      const copy = element("div", "");
      copy.append(element("strong", "", activity.name), element("span", "", durationLabel(activity.duration)));
      const actions = element("div", "planned-actions");
      actions.append(
        button("↑", "route-icon", () => reorderActivity(activity, -1), `Move ${activity.name} earlier`),
        button("↓", "route-icon", () => reorderActivity(activity, 1), `Move ${activity.name} later`),
        button("Move", "activity-text-button", () => moveActivity(activity), `Move ${activity.name} to another day`),
        button("Replace", "activity-text-button", () => replaceActivity(activity), `Replace ${activity.name}`),
        button("Remove", "activity-text-button", () => removeActivity(activity), `Remove ${activity.name}`),
      );
      item.append(copy, actions);
      section.append(item);
    });
    return section;
  }

  function durationLabel(duration) {
    if (!duration) return "Duration unavailable";
    const format = (minutes) => minutes % 60 ? `${Math.floor(minutes / 60)}½ hr` : `${minutes / 60} hr`;
    return `Est. ${format(duration.minimum)}–${format(duration.maximum)} · ${duration.provenance}`;
  }

  function renderPalette() {
    const day = dayPlan().find((candidate) => candidate.number === state.activeDay) || dayPlan()[0];
    activeDayLabel.textContent = `Adding to Day ${day.number} · ${day.destination.name}`;
    const available = day.destination.activities;
    const uniqueCategories = ["all", ...new Set(available.map((activity) => activity.category))];
    const categoryFragment = document.createDocumentFragment();
    uniqueCategories.forEach((category) => {
      const choice = button(category === "all" ? "All places" : category, "", () => {
        state.category = category;
        renderPalette();
      });
      choice.setAttribute("aria-pressed", String(state.category === category));
      categoryFragment.append(choice);
    });
    categories.replaceChildren(categoryFragment);

    const optionsFragment = document.createDocumentFragment();
    available.filter((activity) => state.category === "all" || activity.category === state.category).forEach((activity) => {
      const card = element("article", "activity-option-card");
      const icon = element("span", "activity-option-mark", "✦");
      const copy = element("div", "activity-option-copy");
      copy.append(element("span", "activity-category", activity.category), element("h4", "", activity.name), element("p", "", durationLabel(activity.duration)), element("small", "", "Accessibility information unavailable"));
      const alreadySelected = state.selectedActivities.some((selected) => selected.identity === activity.identity);
      const add = button(alreadySelected ? "Selected" : state.replacement ? "Use as replacement" : "Add", "activity-add", () => addActivity(activity));
      add.disabled = alreadySelected;
      card.append(icon, copy, add);
      optionsFragment.append(card);
    });
    if (!available.length) optionsFragment.append(element("p", "activity-empty", "No trusted place options were returned for this destination. Your route and day structure remain available."));
    activityOptions.replaceChildren(optionsFragment);
  }

  function addActivity(activity) {
    const day = dayPlan().find((candidate) => candidate.number === state.activeDay);
    if (state.selectedActivities.some((selected) => selected.identity === activity.identity)) return;
    if (state.replacement) {
      const old = state.selectedActivities.find((selected) => selected.identity === state.replacement);
      state.selectedActivities = state.selectedActivities.filter((selected) => selected.identity !== state.replacement);
      state.selectedActivities.push({ ...activity, day: old.day, period: old.period, order: old.order });
      state.replacement = null;
      announce(`${old.name} replaced with ${activity.name}.`);
    } else {
      const selectedForDay = state.selectedActivities.filter((selected) => selected.day === day.number);
      const period = PERIODS[Math.min(2, selectedForDay.length % 3)];
      const order = state.selectedActivities.filter((selected) => selected.day === day.number && selected.period === period).length;
      state.selectedActivities.push({ ...activity, day: day.number, period, order });
      announce(`${activity.name} added to Day ${day.number}.`);
    }
    renderDays();
    renderPalette();
  }

  function removeActivity(activity) {
    state.selectedActivities = state.selectedActivities.filter((selected) => selected.identity !== activity.identity);
    normalizeOrders(activity.day, activity.period);
    announce(`${activity.name} removed.`);
    renderDays();
    renderPalette();
  }

  function replaceActivity(activity) {
    state.replacement = activity.identity;
    state.activeDay = activity.day;
    announce(`Choose a trusted place to replace ${activity.name}.`);
    renderPalette();
    activityOptions.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function moveActivity(activity) {
    const compatible = dayPlan().filter((day) => day.destination.name === activity.destination && day.number !== activity.day);
    if (!compatible.length) {
      announce(`Allocate another day to ${activity.destination} before moving this activity.`);
      return;
    }
    const oldDay = activity.day;
    const oldPeriod = activity.period;
    activity.day = compatible[0].number;
    activity.period = "morning";
    activity.order = state.selectedActivities.filter((selected) => selected.day === activity.day && selected.period === "morning").length;
    normalizeOrders(oldDay, oldPeriod);
    announce(`${activity.name} moved to Day ${activity.day}.`);
    renderDays();
  }

  function reorderActivity(activity, direction) {
    const siblings = state.selectedActivities.filter((selected) => selected.day === activity.day && selected.period === activity.period).sort((left, right) => left.order - right.order);
    const index = siblings.findIndex((selected) => selected.identity === activity.identity);
    const target = index + direction;
    if (target < 0 || target >= siblings.length) return;
    [siblings[index].order, siblings[target].order] = [siblings[target].order, siblings[index].order];
    announce(`${activity.name} reordered.`);
    renderDays();
  }

  function normalizeOrders(day, period) {
    state.selectedActivities.filter((selected) => selected.day === day && selected.period === period).sort((left, right) => left.order - right.order).forEach((selected, index) => { selected.order = index; });
  }

  function announce(message) {
    status.textContent = message;
  }

  function updateSummary() {
    const destinations = state.destinations.map((destination) => destination.name).join(", ");
    const count = state.selectedActivities.length;
    summary.textContent = `A ${state.totalDays}-day route through ${destinations}, with ${count} selected ${count === 1 ? "experience" : "experiences"}. Feasibility remains deterministic; travel durations are unknown until supported by live route evidence.`;
  }

  function render() {
    renderPartyCounters();
    renderRoute();
    renderDays();
    renderPalette();
    paceOptions.querySelectorAll("button").forEach((item) => item.setAttribute("aria-pressed", String(item.dataset.pace === state.pace)));
    requirementOptions.querySelectorAll("button").forEach((item) => item.setAttribute("aria-pressed", String(state.requirements.has(item.dataset.requirement))));
  }

  partyPresets.addEventListener("click", (event) => {
    const preset = event.target.closest("button")?.dataset.party;
    if (preset) setPreset(preset);
  });
  paceOptions.addEventListener("click", (event) => {
    const pace = event.target.closest("button")?.dataset.pace;
    if (!pace || !state) return;
    state.pace = pace;
    render();
  });
  requirementOptions.addEventListener("click", (event) => {
    const requirement = event.target.closest("button")?.dataset.requirement;
    if (!requirement || !state) return;
    if (state.requirements.has(requirement)) state.requirements.delete(requirement);
    else state.requirements.add(requirement);
    render();
  });
  closeButton.addEventListener("click", () => {
    studio.hidden = true;
    document.querySelector("#recommendation-results")?.scrollIntoView();
  });
  window.addEventListener("solara:build-trip", (event) => openStudio(event.detail));
})();
