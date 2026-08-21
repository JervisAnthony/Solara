(() => {
  "use strict";

  const form = document.querySelector("#recommendation-form");
  const resultsSection = document.querySelector("#recommendation-results");
  const resultsSummary = document.querySelector("#recommendation-results-summary");
  const resultsTitle = document.querySelector("#results-title");
  const recommendationList = document.querySelector("#recommendation-list");
  const emptyState = document.querySelector("#recommendation-empty");
  const emptyTitle = document.querySelector("#recommendation-empty-title");
  const narrationSection = document.querySelector("#recommendation-narration");
  const narrationText = document.querySelector("#recommendation-narration-text");

  function createTextElement(tagName, className, value) {
    const element = document.createElement(tagName);
    if (className) {
      element.className = className;
    }
    element.textContent = String(value);
    return element;
  }

  function humanizeIdentifier(value) {
    const words = String(value).replace(/[_-]+/g, " ").trim();
    return words === "" ? "" : words.charAt(0).toUpperCase() + words.slice(1);
  }

  function appendMetric(metrics, label, value) {
    const metric = document.createElement("div");
    metric.append(
      createTextElement("dt", "metric-label", label),
      createTextElement("dd", "metric-value", value),
    );
    metrics.append(metric);
  }

  function renderScoreComponents(components) {
    const section = document.createElement("section");
    section.className = "component-section";
    section.append(createTextElement("h4", "evidence-heading", "Why it ranked here"));

    const list = document.createElement("ul");
    list.className = "component-list";
    for (const component of components) {
      const item = document.createElement("li");
      item.className = "component-item";
      item.append(
        createTextElement("p", "component-name", humanizeIdentifier(component.name)),
      );

      const metrics = document.createElement("dl");
      metrics.className = "metric-grid metric-grid-compact";
      appendMetric(metrics, "Score", String(component.score));
      appendMetric(metrics, "Weight", String(component.weight));
      appendMetric(
        metrics,
        "Weighted contribution",
        String(component.weighted_contribution),
      );
      item.append(metrics);
      list.append(item);
    }
    section.append(list);
    return section;
  }

  function renderAttractions(attractions) {
    if (!Array.isArray(attractions) || attractions.length === 0) {
      return null;
    }

    const section = document.createElement("section");
    section.className = "evidence-section";
    section.append(createTextElement("h4", "evidence-heading", "Selected attractions"));

    const list = document.createElement("ul");
    list.className = "attraction-list";
    for (const attraction of attractions) {
      const item = document.createElement("li");
      item.append(
        createTextElement("span", "attraction-name", attraction.name),
        createTextElement("span", "attraction-category", attraction.category),
      );
      list.append(item);
    }
    section.append(list);
    return section;
  }

  function renderSeasonalEvidence(seasonalWeather) {
    const section = document.createElement("section");
    section.className = "evidence-section";
    section.append(
      createTextElement("h4", "evidence-heading", "Historical seasonal evidence"),
    );

    const metrics = document.createElement("dl");
    metrics.className = "metric-grid";
    appendMetric(
      metrics,
      "Travel window",
      `${String(seasonalWeather.target_period.start_date)} — ${String(
        seasonalWeather.target_period.end_date,
      )}`,
    );
    appendMetric(
      metrics,
      "Historical years",
      seasonalWeather.historical_years.map(String).join(", "),
    );
    appendMetric(
      metrics,
      "Historical year count",
      String(seasonalWeather.historical_year_count),
    );
    appendMetric(metrics, "Observations", String(seasonalWeather.observation_count));
    appendMetric(
      metrics,
      "Mean temperature",
      `${String(seasonalWeather.mean_temperature_celsius)} °C`,
    );
    appendMetric(
      metrics,
      "Temperature range",
      `${String(seasonalWeather.minimum_temperature_celsius)} °C — ${String(
        seasonalWeather.maximum_temperature_celsius,
      )} °C`,
    );
    appendMetric(
      metrics,
      "Mean relative humidity",
      `${String(seasonalWeather.mean_relative_humidity_percent)} %`,
    );
    appendMetric(
      metrics,
      "Mean daily precipitation",
      `${String(seasonalWeather.mean_daily_precipitation_mm)} mm`,
    );
    section.append(metrics);
    return section;
  }

  function renderTemperatureComfort(temperatureComfort) {
    const section = document.createElement("section");
    section.className = "evidence-section";
    section.append(
      createTextElement("h4", "evidence-heading", "Temperature comfort"),
      createTextElement(
        "p",
        "evidence-note",
        "This range is configured by Solara's deterministic seasonal analysis.",
      ),
    );

    const metrics = document.createElement("dl");
    metrics.className = "metric-grid";
    appendMetric(metrics, "Temperature comfort score", String(temperatureComfort.score));
    appendMetric(
      metrics,
      "Configured comfort range",
      `${String(temperatureComfort.comfort_range.minimum_celsius)} °C — ${String(
        temperatureComfort.comfort_range.maximum_celsius,
      )} °C`,
    );
    appendMetric(
      metrics,
      "Tolerance",
      `${String(temperatureComfort.comfort_range.tolerance_celsius)} °C`,
    );
    appendMetric(
      metrics,
      "Within preferred range fraction",
      String(temperatureComfort.within_preferred_fraction),
    );
    appendMetric(
      metrics,
      "Mean deviation",
      `${String(temperatureComfort.mean_deviation_celsius)} °C`,
    );
    section.append(metrics);
    return section;
  }

  function renderEvidence(evidence) {
    const details = document.createElement("details");
    details.className = "recommendation-evidence";
    details.append(createTextElement("summary", "evidence-summary", "Explore evidence"));

    const content = document.createElement("div");
    content.className = "evidence-content";
    const attractions = renderAttractions(evidence.attractions);
    if (attractions) {
      content.append(attractions);
    }
    content.append(
      renderSeasonalEvidence(evidence.seasonal_weather),
      renderTemperatureComfort(evidence.temperature_comfort),
    );
    details.append(content);
    return details;
  }

  function renderRecommendation(recommendation) {
    const item = document.createElement("li");
    const card = document.createElement("article");
    card.className = "recommendation-card";

    const header = document.createElement("header");
    header.className = "recommendation-card-header";
    const identity = document.createElement("div");
    identity.className = "destination-identity";
    identity.append(
      createTextElement("p", "rank-label", `Rank ${String(recommendation.rank)}`),
      createTextElement("h3", "destination-name", recommendation.destination.name),
      createTextElement("p", "destination-country", recommendation.destination.country),
    );

    const score = document.createElement("dl");
    score.className = "suitability-score";
    appendMetric(score, "Suitability score", String(recommendation.score));
    header.append(identity, score);
    card.append(
      header,
      renderScoreComponents(recommendation.components),
      renderEvidence(recommendation.evidence),
    );
    item.append(card);
    return item;
  }

  function renderNarration(response) {
    if (
      response.has_narration === true &&
      typeof response.narration === "string" &&
      response.narration.trim() !== ""
    ) {
      narrationText.textContent = response.narration;
      narrationSection.hidden = false;
    }
  }

  function clearResults() {
    resultsSection.hidden = true;
    recommendationList.replaceChildren();
    resultsSummary.replaceChildren();
    narrationSection.hidden = true;
    narrationText.replaceChildren();
    emptyState.hidden = true;
  }

  function renderRecommendationResponse(response) {
    clearResults();
    if (response.has_recommendations === false || response.recommendations.length === 0) {
      resultsSection.hidden = false;
      emptyState.hidden = false;
      emptyTitle.focus();
      return;
    }

    const cards = document.createDocumentFragment();
    for (const recommendation of response.recommendations) {
      cards.append(renderRecommendation(recommendation));
    }
    recommendationList.replaceChildren(cards);

    const travelPeriod = response.request?.travel_period;
    const periodText = travelPeriod
      ? ` for ${String(travelPeriod.start_date)} — ${String(travelPeriod.end_date)}`
      : "";
    resultsSummary.textContent =
      `${String(response.recommendation_count)} ranked recommendations${periodText}.`;
    resultsSection.hidden = false;
    renderNarration(response);
    resultsTitle.focus();
  }

  function handleRecommendationReady(event) {
    try {
      renderRecommendationResponse(event.detail);
    } catch {
      clearResults();
    }
  }

  if (
    form &&
    resultsSection &&
    resultsSummary &&
    resultsTitle &&
    recommendationList &&
    emptyState &&
    emptyTitle &&
    narrationSection &&
    narrationText
  ) {
    form.addEventListener("solara:recommendation-request-start", clearResults);
    form.addEventListener("solara:recommendation-ready", handleRecommendationReady);
  }
})();
