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
  const ACTIVITY_ENDPOINT = "/api/v1/itinerary-activities";
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
  let activityRequest = null;

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

  function canonicalDestination(destination) {
    return `${destination.name}, ${destination.country}`;
  }

  function destinationLabel(destination) {
    return state.destinations.filter((item) => item.name === destination.name).length > 1
      ? canonicalDestination(destination) : destination.name;
  }

  function cancelActivityRequest() {
    if (!activityRequest) return;
    activityRequest.controller.abort();
    if (state?.activityCache.get(activityRequest.key)?.status === "loading") {
      state.activityCache.delete(activityRequest.key);
    }
    activityRequest = null;
  }

  function openStudio(detail) {
    if (!detail?.response || !Array.isArray(detail.recommendations) || detail.recommendations.length === 0) return;
    cancelActivityRequest();
    const total = tripDays(detail.response);
    const selected = detail.recommendations.slice(0, total);
    const allocations = distributeDays(total, selected.length);
    state = {
      response: detail.response,
      totalDays: total,
      destinations: selected.map((recommendation, index) => ({
        ...recommendation.destination,
        days: allocations[index],
      })),
      party: { ...PRESETS.solo },
      pace: "balanced",
      requirements: new Set(),
      selectedActivities: [],
      travelLegs: Array.from({ length: Math.max(0, selected.length - 1) }, (_, index) => ({
        origin: selected[index].destination,
        destination: selected[index + 1].destination,
        options: [],
        selectedIdentity: null,
      })),
      activityCache: new Map(),
      activeDay: 1,
      category: "all",
      replacement: null,
    };
    document.querySelector('input[name="handoff-requirements"][value="exclude"]').checked = true;
    document.querySelector("#handoff-status").textContent = "";
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
          travelLeg: destinationIndex > 0 && localDay === 0 ? state.travelLegs[destinationIndex - 1] : null,
        });
        number += 1;
      }
    });
    return plan;
  }

  function dateForDay(offset) {
    const value = new Date(`${state.response.request.travel_period.start_date}T00:00:00Z`);
    value.setUTCDate(value.getUTCDate() + offset);
    return value.toISOString().slice(0, 10);
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
    reconcileActivities();
    state.activeDay = Math.min(state.activeDay, state.totalDays);
    render();
  }

  function moveDestination(index, direction) {
    const target = index + direction;
    if (target < 0 || target >= state.destinations.length) return;
    [state.destinations[index], state.destinations[target]] = [state.destinations[target], state.destinations[index]];
    rebuildUnknownTravelLegs();
    reconcileActivities();
    state.activeDay = 1;
    announce("Route reordered. Selected activities stayed with their destinations; review the new day loads.");
    render();
  }

  function removeDestination(index) {
    if (state.destinations.length === 1) return;
    const removed = state.destinations[index];
    const receiver = index === state.destinations.length - 1 ? index - 1 : index + 1;
    state.destinations[receiver].days += removed.days;
    state.destinations.splice(index, 1);
    rebuildUnknownTravelLegs();
    reconcileActivities();
    state.activeDay = 1;
    announce(`${removed.name} removed. Its days were reassigned.`);
    render();
  }

  function rebuildUnknownTravelLegs() {
    state.travelLegs = Array.from({ length: Math.max(0, state.destinations.length - 1) }, (_, index) => ({
      origin: state.destinations[index],
      destination: state.destinations[index + 1],
      options: [],
      selectedIdentity: null,
    }));
  }

  function reconcileActivities() {
    const days = dayPlan();
    state.selectedActivities = state.selectedActivities.filter((activity) => {
      const compatible = days.filter((day) => canonicalDestination(day.destination) === activity.destinationKey);
      const target = compatible.find((day) => day.number === activity.day) || compatible[0];
      if (!target) return false;
      activity.day = target.number;
      return true;
    });
    days.forEach((day) => PERIODS.forEach((period) => normalizeOrders(day.number, period)));
  }

  function renderRoute() {
    const fragment = document.createDocumentFragment();
    let offset = 0;
    state.destinations.forEach((destination, index) => {
      const label = destinationLabel(destination);
      const card = element("article", "route-card");
      const header = element("div", "route-card-header");
      header.append(element("span", "route-order", String(index + 1)), element("div", "", undefined));
      header.lastChild.append(element("strong", "", destination.name), element("span", "", destination.country));
      const reorder = element("div", "route-actions");
      reorder.append(
        button("↑", "route-icon", () => moveDestination(index, -1), `Move ${label} earlier`),
        button("↓", "route-icon", () => moveDestination(index, 1), `Move ${label} later`),
        button("×", "route-icon", () => removeDestination(index), `Remove ${label}`),
      );
      header.append(reorder);
      const allocation = element("div", "day-allocation");
      allocation.append(
        button("−", "counter-button", () => updateAllocation(index, -1), `Allocate one fewer day to ${label}`),
        element("strong", "", `${destination.days} ${destination.days === 1 ? "day" : "days"}`),
        button("+", "counter-button", () => updateAllocation(index, 1), `Allocate one more day to ${label}`),
      );
      const dates = element("p", "route-dates", `${dateForDay(offset)} → ${dateForDay(offset + destination.days)} · departure boundary`);
      offset += destination.days;
      card.append(header, dates, allocation);
      fragment.append(card);
      if (index < state.destinations.length - 1) fragment.append(renderTravelLeg(index));
    });
    route.replaceChildren(fragment);
    routeDuration.textContent = `${state.totalDays} days · ${state.destinations.length} ${state.destinations.length === 1 ? "destination" : "destinations"}`;
  }

  function renderTravelLeg(index) {
    const evidence = state.travelLegs[index];
    const verifiedOptions = evidence.options.filter((option) => option.verified === true);
    const leg = element("div", "travel-leg");
    const copy = element("div", "travel-leg-copy");
    copy.append(
      element("span", "travel-line", ""),
      element("strong", "", `Travel between ${evidence.origin.name} and ${evidence.destination.name}`),
      element(
        "small",
        "",
        verifiedOptions.length
          ? "Verified planning options only · no live schedule or booking availability"
          : "Route options are not yet verified. Travel time is needed before arrival-day feasibility can be assessed.",
      ),
    );
    const modes = element("div", "travel-modes");
    verifiedOptions.forEach((routeOption) => {
      const option = button(routeOption.mode, "", () => {
        evidence.selectedIdentity = routeOption.identity;
        render();
      });
      option.setAttribute("aria-pressed", String(evidence.selectedIdentity === routeOption.identity));
      option.append(element("span", "travel-option-duration", durationLabel(routeOption.duration)));
      modes.append(option);
    });
    if (!verifiedOptions.length) modes.append(element("span", "route-unverified", "Travel time needed"));
    leg.append(copy, modes);
    return leg;
  }

  function assessment(day, requirements = state.requirements) {
    const selected = state.selectedActivities.filter((activity) => activity.day === day.number);
    let buffer = 90 + Math.max(0, selected.length - 1) * 30;
    if (state.party.children) buffer += 30;
    if (state.party.seniors) buffer += 30;
    requirements.forEach((requirement) => { buffer += REQUIREMENT_BUFFER[requirement] || 0; });
    let occupied = buffer;
    let travelMinutes = 0;
    let unresolvedTravel = false;
    const warnings = [];
    selected.forEach((activity) => {
      if (activity.duration) occupied += activity.duration.typical_minutes;
      else warnings.push(`Duration is unknown for ${activity.name}.`);
    });
    if (day.travelLeg) {
      const routeOption = day.travelLeg.options.find((option) =>
        option.verified === true && option.identity === day.travelLeg.selectedIdentity);
      if (!routeOption?.duration) {
        unresolvedTravel = true;
        warnings.push("Travel time is needed before Solara can fully assess this arrival day.");
      } else {
        travelMinutes = routeOption.duration.maximum_minutes + (routeOption.planning_buffer_minutes || 0);
        occupied += travelMinutes;
      }
    }
    const available = CAPACITY[state.pace];
    const ratio = occupied / available;
    const level = unresolvedTravel ? "travel time needed" : ratio <= 0.45 ? "relaxed" : ratio <= 0.70 ? "comfortable" : ratio <= 0.90 ? "full" : "very full";
    if (!unresolvedTravel && ratio > 0.90) warnings.push("This day is becoming quite full for your pace and travel needs. Consider moving one activity.");
    const impossible = !unresolvedTravel && day.travelLeg &&
      (travelMinutes >= available || occupied > available);
    return { occupied, available, buffer, level, warnings, impossible, unresolvedTravel };
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
      heading.lastChild.append(
        element("strong", "", day.destination.name),
        element("span", "day-date", dateForDay(day.number - 1)),
        element("span", "", day.travelLeg ? "Arrival day · route evidence pending" : "A full destination day"),
      );
      if (day.travelLeg) heading.lastChild.append(element("span", "journey-day-route", `${day.travelLeg.origin.name} → ${day.travelLeg.destination.name}`));
      const load = assessment(day);
      const meter = element("div", `feasibility feasibility-${load.level.replace(" ", "-")}`);
      meter.append(
        element("strong", "", load.level),
        element("span", "", load.unresolvedTravel
          ? `${load.occupied} known planning minutes · transfer excluded`
          : `${load.occupied} of ${load.available} planning minutes`),
      );
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
        guidance.append(element("strong", "", load.impossible ? "Hard timing conflict" : load.unresolvedTravel ? "Feasibility pending" : "Planning guidance"));
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
      item.dataset.activityIdentity = activity.identity;
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
    const provenance = duration.provenance.replaceAll("_", " ");
    return `Est. ${format(duration.minimum_minutes)}–${format(duration.maximum_minutes)} · ${provenance} · ${duration.confidence} confidence`;
  }

  function renderPalette() {
    const day = dayPlan().find((candidate) => candidate.number === state.activeDay) || dayPlan()[0];
    const key = canonicalDestination(day.destination);
    activeDayLabel.textContent = `Adding to Day ${day.number} · ${day.destination.name}`;
    const cached = state.activityCache.get(key);
    if (!cached) {
      categories.replaceChildren();
      activityOptions.replaceChildren(
        element("div", "activity-loading", "Gathering trusted activity ideas…"),
        element("div", "activity-loading-card", ""),
        element("div", "activity-loading-card", ""),
      );
      void loadActivityPalette(day.destination);
      return;
    }
    if (cached.status === "loading") {
      categories.replaceChildren();
      activityOptions.replaceChildren(
        element("div", "activity-loading", "Gathering trusted activity ideas…"),
        element("div", "activity-loading-card", ""),
        element("div", "activity-loading-card", ""),
      );
      return;
    }
    if (cached.status === "unavailable") {
      categories.replaceChildren();
      activityOptions.replaceChildren(element("p", "activity-empty", "Activity ideas are temporarily unavailable for this destination. Your itinerary is still here."));
      return;
    }
    const available = cached.activities;
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
      card.dataset.activityIdentity = activity.identity;
      const icon = element("span", "activity-option-mark", "✦");
      const copy = element("div", "activity-option-copy");
      const accessibility = {
        confirmed: "Accessibility confirmed by trusted data",
        unavailable: "Accessibility unavailable",
        unknown: "Accessibility information unavailable",
      }[activity.accessibility];
      copy.append(element("span", "activity-category", activity.category), element("h4", "", activity.name), element("p", "", durationLabel(activity.duration)), element("small", "", accessibility));
      const alreadySelected = state.selectedActivities.some((selected) => selected.identity === activity.identity);
      const add = button(alreadySelected ? "Selected" : state.replacement ? "Use as replacement" : "Add", "activity-add", () => addActivity(activity));
      add.disabled = alreadySelected;
      card.append(icon, copy, add);
      optionsFragment.append(card);
    });
    if (!available.length) optionsFragment.append(element("p", "activity-empty", "No trusted activity suggestions are available for this destination yet. Your route and day structure remain available."));
    activityOptions.replaceChildren(optionsFragment);
  }

  async function loadActivityPalette(destination) {
    const key = canonicalDestination(destination);
    if (state.activityCache.has(key)) return;
    cancelActivityRequest();
    const controller = new AbortController();
    const requestIdentity = Symbol(key);
    activityRequest = { key, controller, identity: requestIdentity };
    state.activityCache.set(key, { status: "loading", activities: [] });
    renderPalette();
    try {
      const response = await fetch(ACTIVITY_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ destination_query: key }),
        signal: controller.signal,
      });
      if (!response.ok) throw new Error("activity discovery unavailable");
      const payload = await response.json();
      if (!Array.isArray(payload.activities)) throw new Error("invalid activity palette");
      const activities = payload.activities.slice(0, 12).map((activity) => ({
        identity: activity.identity,
        name: activity.name,
        category: activity.category,
        destination: destination.name,
        destinationKey: key,
        coordinates: activity.coordinates,
        duration: activity.duration,
        accessibility: activity.accessibility,
      }));
      if (activityRequest?.identity !== requestIdentity) return;
      state.activityCache.set(key, {
        status: activities.length ? "success" : "empty",
        activities,
      });
    } catch (error) {
      if (error.name === "AbortError" || activityRequest?.identity !== requestIdentity) return;
      state.activityCache.set(key, { status: "unavailable", activities: [] });
    } finally {
      if (activityRequest?.identity === requestIdentity) activityRequest = null;
    }
    const activeDestination = dayPlan().find((day) => day.number === state.activeDay)?.destination;
    if (activeDestination && canonicalDestination(activeDestination) === key) renderPalette();
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
    const compatible = dayPlan().filter((day) => canonicalDestination(day.destination) === activity.destinationKey && day.number !== activity.day);
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
    summary.textContent = `A ${state.totalDays}-day route through ${destinations}, with ${count} selected ${count === 1 ? "experience" : "experiences"}. Arrival-day feasibility remains pending until trusted route evidence supplies travel time.`;
  }

  function render() {
    renderPartyCounters();
    renderRoute();
    renderDays();
    renderPalette();
    paceOptions.querySelectorAll("button").forEach((item) => item.setAttribute("aria-pressed", String(item.dataset.pace === state.pace)));
    requirementOptions.querySelectorAll("button").forEach((item) => item.setAttribute("aria-pressed", String(state.requirements.has(item.dataset.requirement))));
  }

  function exportDestination(destination) {
    return { name: destination.name, country: destination.country, coordinates: {
      latitude: destination.coordinates.latitude, longitude: destination.coordinates.longitude,
    } };
  }

  function exportLeg(leg) {
    if (!leg) return null;
    const option = leg.options.find((item) => item.verified === true && item.identity === leg.selectedIdentity);
    return {
      origin: exportDestination(leg.origin), destination: exportDestination(leg.destination),
      mode: option?.mode || null, duration: exportDuration(option?.duration),
      planning_buffer_minutes: option?.planning_buffer_minutes || 0,
      evidence_provenance: option?.evidence_provenance || null,
      distance_kilometers: option?.distance_kilometers || null, verified: Boolean(option),
    };
  }

  function exportDuration(duration) {
    return duration ? {
      minimum_minutes: duration.minimum_minutes, maximum_minutes: duration.maximum_minutes,
      provenance: duration.provenance, confidence: duration.confidence,
    } : null;
  }

  function tripSnapshot(includeRequirements) {
    return {
      schema_version: 1, requirements_included: includeRequirements,
      itinerary: {
        start_date: state.response.request.travel_period.start_date,
        end_date: state.response.request.travel_period.end_date,
        traveller_profile: {
          party: { ...state.party, young_adults: 0, infants: 0 }, pace: state.pace,
          requirements: includeRequirements ? Array.from(state.requirements).sort() : [],
        },
        stays: state.destinations.map((destination) => ({ destination: exportDestination(destination), days: destination.days })),
        days: dayPlan().map((day) => ({
          number: day.number, destination: exportDestination(day.destination),
          inbound_travel_leg: exportLeg(day.travelLeg),
          activities: state.selectedActivities.filter((activity) => activity.day === day.number)
            .sort((left, right) => PERIODS.indexOf(left.period) - PERIODS.indexOf(right.period) || left.order - right.order)
            .map((activity) => ({
              identity: activity.identity, name: activity.name, destination: exportDestination(day.destination),
              category: activity.category, coordinates: activity.coordinates || null,
              duration: exportDuration(activity.duration), day_number: day.number,
              period: activity.period, order: activity.order, accessibility: activity.accessibility,
            })),
        })),
      },
    };
  }

  function tripText(snapshot) {
    const trip = snapshot.itinerary;
    const lines = ["SOLARA · TRIP HANDOFF", "Planning summary · not booked or submitted",
      `${trip.start_date} to ${trip.end_date} · ${trip.traveller_profile.pace} pace`,
      `Travellers: ${Object.values(trip.traveller_profile.party).reduce((sum, count) => sum + count, 0)}`,
      "Stay departure dates below are exclusive allocation boundaries, not reservations."];
    let offset = 0;
    trip.stays.forEach((stay) => {
      lines.push(`${stay.destination.name}, ${stay.destination.country}: ${dateForDay(offset)} to ${dateForDay(offset + stay.days)} · ${stay.days} days`);
      offset += stay.days;
    });
    lines.push(snapshot.requirements_included
      ? `Travel requirements: ${trip.traveller_profile.requirements.map((item) => item.replaceAll("_", " ")).join(", ")}`
      : "Travel requirements: excluded by traveller");
    trip.days.forEach((day) => {
      lines.push(`Day ${day.number} · ${dateForDay(day.number - 1)} · ${day.destination.name}`);
      const leg = day.inbound_travel_leg;
      if (leg) {
        lines.push(`Journey: ${leg.origin.name} → ${leg.destination.name} · ${leg.duration ? "verified_planning" : "unresolved"}`);
        lines.push(leg.duration
          ? `Verified planning estimate: ${leg.duration.minimum_minutes}–${leg.duration.maximum_minutes} minutes · ${leg.evidence_provenance}`
          : "Travel time needed; arrival-day feasibility unresolved");
      }
      if (snapshot.requirements_included) {
        const load = assessment(dayPlan()[day.number - 1]);
        lines.push(`Feasibility: ${load.unresolvedTravel ? "unresolved" : load.level.replaceAll(" ", "_")}`);
      } else {
        lines.push("Day load: review in Solara with your full travel requirements.");
      }
      day.activities.forEach((activity) => lines.push(`  ${activity.period}: ${activity.name} · ${activity.duration ? `${activity.duration.minimum_minutes}–${activity.duration.maximum_minutes} minutes (${activity.duration.provenance})` : "duration unknown"}`));
    });
    return `${lines.join("\n")}\n`;
  }

  function canonicalJson(value) {
    return JSON.stringify(value, (_key, item) => item && typeof item === "object" && !Array.isArray(item)
      ? Object.fromEntries(Object.keys(item).sort().map((key) => [key, item[key]])) : item);
  }

  function downloadTrip(format) {
    if (!state) return;
    const feedback = document.querySelector("#handoff-status");
    try {
      const include = document.querySelector('input[name="handoff-requirements"]:checked').value === "include";
      const snapshot = tripSnapshot(include);
      const json = canonicalJson(snapshot);
      if (new Blob([json]).size > 1000000) throw new Error("size");
      const content = format === "json" ? json : tripText(snapshot);
      const blob = new Blob([content], { type: format === "json" ? "application/json" : "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `solara-trip-${snapshot.itinerary.start_date}.${format === "json" ? "json" : "txt"}`;
      document.body.append(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      feedback.textContent = `Your trip ${format === "json" ? "JSON" : "summary"} is ready. Travel requirements ${include ? "included" : "kept private"}. Nothing was submitted.`;
    } catch (_error) {
      feedback.textContent = "Export could not be prepared. Your plan is still here; try again.";
    }
  }

  document.querySelector("#export-trip-text").addEventListener("click", () => downloadTrip("text"));
  document.querySelector("#export-trip-json").addEventListener("click", () => downloadTrip("json"));

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
    cancelActivityRequest();
    studio.hidden = true;
    document.querySelector("#recommendation-results")?.scrollIntoView();
  });
  window.addEventListener("solara:build-trip", (event) => openStudio(event.detail));
})();
