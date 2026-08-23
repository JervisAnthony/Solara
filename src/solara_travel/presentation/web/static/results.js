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

  function formatNumber(value, maximumFractionDigits) {
    const numericValue = Number(value);
    if (!Number.isFinite(numericValue)) {
      return String(value);
    }
    return new Intl.NumberFormat("en", {
      maximumFractionDigits,
      useGrouping: false,
    }).format(numericValue);
  }

  function formatPercentage(value) {
    const numericValue = Number(value);
    if (!Number.isFinite(numericValue)) {
      return String(value);
    }
    const percentage = Math.round((numericValue * 100 + Number.EPSILON) * 10) / 10;
    return `${String(percentage)}%`;
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

      item.append(
        createTextElement(
          "p",
          "component-fit",
          `${formatPercentage(component.score)} seasonal fit`,
        ),
      );
      list.append(item);
    }
    section.append(list);
    return section;
  }

  function renderAttractions(attractions, recommendationRank) {
    if (!Array.isArray(attractions) || attractions.length === 0) {
      return null;
    }

    const section = document.createElement("section");
    section.className = "evidence-section";
    section.append(createTextElement("h4", "evidence-heading", "Selected attractions"));

    const list = document.createElement("ul");
    list.className = "attraction-list";
    for (const [index, attraction] of attractions.entries()) {
      const item = document.createElement("li");
      if (index >= 6) {
        item.hidden = true;
      }
      item.append(
        createTextElement("span", "attraction-name", attraction.name),
        createTextElement("span", "attraction-category", attraction.category),
      );
      list.append(item);
    }
    list.id = `attraction-list-${String(recommendationRank)}`;
    section.append(list);
    if (attractions.length > 6) {
      const toggle = createTextElement("button", "attraction-toggle", "Show all attractions");
      toggle.type = "button";
      toggle.setAttribute("aria-controls", list.id);
      toggle.setAttribute("aria-expanded", "false");
      toggle.addEventListener("click", () => {
        const expanded = toggle.getAttribute("aria-expanded") === "true";
        const nextExpanded = !expanded;
        for (const item of list.children) {
          item.hidden = !nextExpanded && Number(item.dataset.attractionIndex) >= 6;
        }
        toggle.setAttribute("aria-expanded", String(nextExpanded));
        toggle.textContent = nextExpanded ? "Show fewer attractions" : "Show all attractions";
      });
      for (const [index, item] of Array.from(list.children).entries()) {
        item.dataset.attractionIndex = String(index);
      }
      section.append(toggle);
    }
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
      `${formatNumber(seasonalWeather.mean_temperature_celsius, 1)} °C`,
    );
    appendMetric(
      metrics,
      "Temperature range",
      `${formatNumber(seasonalWeather.minimum_temperature_celsius, 1)} °C — ${formatNumber(
        seasonalWeather.maximum_temperature_celsius,
        1,
      )} °C`,
    );
    appendMetric(
      metrics,
      "Mean relative humidity",
      `${formatNumber(seasonalWeather.mean_relative_humidity_percent, 1)}%`,
    );
    appendMetric(
      metrics,
      "Mean daily precipitation",
      `${formatNumber(seasonalWeather.mean_daily_precipitation_mm, 2)} mm`,
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
    appendMetric(metrics, "Seasonal fit", formatPercentage(temperatureComfort.score));
    appendMetric(
      metrics,
      "Configured comfort range",
      `${formatNumber(temperatureComfort.comfort_range.minimum_celsius, 1)} °C — ${formatNumber(
        temperatureComfort.comfort_range.maximum_celsius,
        1,
      )} °C`,
    );
    appendMetric(
      metrics,
      "Tolerance",
      `${formatNumber(temperatureComfort.comfort_range.tolerance_celsius, 1)} °C`,
    );
    appendMetric(
      metrics,
      "Within configured comfort range",
      formatPercentage(temperatureComfort.within_preferred_fraction),
    );
    appendMetric(
      metrics,
      "Mean deviation",
      `${formatNumber(temperatureComfort.mean_deviation_celsius, 1)} °C`,
    );
    section.append(metrics);
    return section;
  }

  function renderEvidence(evidence, recommendationRank) {
    const details = document.createElement("details");
    details.className = "recommendation-evidence";
    details.append(createTextElement("summary", "evidence-summary", "Explore evidence"));

    const content = document.createElement("div");
    content.className = "evidence-content";
    const attractions = renderAttractions(evidence.attractions, recommendationRank);
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
    appendMetric(score, "Seasonal fit", formatPercentage(recommendation.score));
    header.append(identity, score);
    card.append(
      header,
      renderScoreComponents(recommendation.components),
      renderEvidence(recommendation.evidence, recommendation.rank),
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
    const mode = response.request?.destination_mode;
    if (mode === "explicit_queries" && response.request.destination_queries?.length === 1) {
      const destinationName = response.recommendations[0]?.destination?.name;
      resultsTitle.textContent = destinationName
        ? `${String(destinationName)} for your trip`
        : "Destination for your trip";
    } else if (mode === "explicit_queries") {
      resultsTitle.textContent = "Your destination comparison";
    } else {
      resultsTitle.textContent = "Recommended destinations";
    }
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
