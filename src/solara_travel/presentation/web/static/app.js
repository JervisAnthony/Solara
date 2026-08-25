(() => {
  "use strict";

  const form = document.querySelector("#recommendation-form");
  const submitButton = document.querySelector("#recommendation-submit");
  const statusRegion = document.querySelector("#recommendation-form-status");
  const validationSummary = document.querySelector("#recommendation-validation-summary");
  const validationList = document.querySelector("#recommendation-validation-list");
  const requestError = document.querySelector("#recommendation-request-error");
  const requestErrorTitle = document.querySelector("#recommendation-request-error-title");
  const requestErrorMessage = document.querySelector(
    "#recommendation-request-error-message",
  );
  const retryButton = document.querySelector("#recommendation-request-retry");
  const requestReference = document.querySelector("#recommendation-request-reference");
  const requestReferenceValue = document.querySelector(
    "#recommendation-request-reference-value",
  );
  const destinationInput = document.querySelector("#destination-input");
  const destinationAddButton = document.querySelector("#destination-add");
  const destinationChips = document.querySelector("#destination-chips");
  const destinationStatus = document.querySelector("#destination-status");
  const tripDescription = document.querySelector("#trip-description");
  const tripDescriptionCount = document.querySelector("#trip-description-count");
  const recommendationEndpoint = "/api/v1/recommendations";
  const loadingSubmitLabel = "Comparing…";
  const maximumDestinations = 5;
  const coldStartThresholdMilliseconds = 10000;
  const defaultCooldownSeconds = 60;
  const maximumCooldownSeconds = 86400;
  let requestInFlight = false;
  let cooldownActive = false;
  let cooldownTimer = null;
  let coldStartTimer = null;
  const destinationQueries = [];

  const fieldContracts = {
    "destination-input": "destination-error",
    "travel-start-date": "travel-start-date-error",
    "travel-end-date": "travel-end-date-error",
    interests: "interests-error",
    "preferred-pace": "preferred-pace-error",
    "preferred-climate": "preferred-climate-error",
    "trip-description": "trip-description-error",
  };

  function shortenedDestination(value) {
    const name = value.split(",", 1)[0].trim();
    return name.length <= 24 ? name : `${name.slice(0, 23).trimEnd()}…`;
  }

  function idleSubmitLabel() {
    if (destinationQueries.length === 0) {
      return "FIND DESTINATIONS →";
    }
    if (destinationQueries.length === 1) {
      return `EXPLORE ${shortenedDestination(destinationQueries[0].query).toUpperCase()} →`;
    }
    return "COMPARE DESTINATIONS →";
  }

  function updateSubmitLabel() {
    if (!requestInFlight) {
      submitButton.textContent = idleSubmitLabel();
    }
  }

  class RecommendationRequestError extends Error {
    constructor(
      kind,
      status = null,
      code = null,
      validationErrors = [],
      requestId = null,
      retryAfterSeconds = null,
      responseMessage = null,
      suggestions = [],
    ) {
      super("Recommendation request failed.");
      this.name = "RecommendationRequestError";
      this.kind = kind;
      this.status = status;
      this.code = code;
      this.validationErrors = validationErrors;
      this.requestId = requestId;
      this.retryAfterSeconds = retryAfterSeconds;
      this.responseMessage = responseMessage;
      this.suggestions = suggestions;
    }
  }

  function parseRetryAfter(response) {
    const rawValue = response.headers.get("Retry-After");
    if (typeof rawValue !== "string" || !/^\d+$/.test(rawValue)) {
      return null;
    }
    const seconds = Number.parseInt(rawValue, 10);
    if (!Number.isSafeInteger(seconds) || seconds <= 0) {
      return null;
    }
    return Math.min(seconds, maximumCooldownSeconds);
  }

  function optionalText(value) {
    const trimmed = value.trim();
    return trimmed === "" ? null : trimmed;
  }

  function parseInterests(value) {
    const trimmed = value.trim();
    return trimmed === "" ? null : trimmed.split(",").map((interest) => interest.trim());
  }

  function selectedInterests(targetForm) {
    const interests = [
      ...targetForm.querySelectorAll('input[name="guided-interest"]:checked'),
    ].map((control) => control.value);
    const custom = parseInterests(targetForm.elements.namedItem("interests").value) ?? [];
    const seen = new Set(interests.map((interest) => interest.toLowerCase()));
    custom.forEach((interest) => {
      if (!seen.has(interest.toLowerCase())) {
        interests.push(interest);
        seen.add(interest.toLowerCase());
      }
    });
    return interests.length === 0 ? null : interests;
  }

  function validationError(fieldId, message) {
    return { fieldId, errorId: fieldContracts[fieldId], message };
  }

  function clearValidation() {
    validationSummary.hidden = true;
    validationList.replaceChildren();
    for (const [fieldId, errorId] of Object.entries(fieldContracts)) {
      const field = document.querySelector(`#${fieldId}`);
      const error = document.querySelector(`#${errorId}`);
      field.removeAttribute("aria-invalid");
      error.replaceChildren();
      error.hidden = true;
    }
  }

  function showDestinationValidation(message) {
    const error = document.querySelector("#destination-error");
    destinationInput.setAttribute("aria-invalid", "true");
    error.textContent = message;
    error.hidden = false;
    destinationStatus.textContent = message;
  }

  function clearDestinationValidation() {
    const error = document.querySelector("#destination-error");
    destinationInput.removeAttribute("aria-invalid");
    error.replaceChildren();
    error.hidden = true;
    destinationStatus.replaceChildren();
  }

  function renderDestinationChips() {
    const fragment = document.createDocumentFragment();
    destinationQueries.forEach(({ query, kind }, index) => {
      const item = document.createElement("li");
      item.className = "destination-chip";
      const label = document.createElement("span");
      label.textContent = query;
      if (kind === "country" || kind === "region") {
        const kindLabel = document.createElement("small");
        kindLabel.textContent = kind;
        label.append(" ", kindLabel);
      }
      const remove = document.createElement("button");
      remove.type = "button";
      remove.dataset.destinationIndex = String(index);
      remove.setAttribute("aria-label", `Remove ${query}`);
      remove.textContent = "×";
      item.append(label, remove);
      fragment.append(item);
    });
    destinationChips.replaceChildren(fragment);
    updateSubmitLabel();
  }

  function addDestinationQuery(query, kind = null) {
    const normalizedQuery = query.trim();
    clearDestinationValidation();
    if (normalizedQuery === "") {
      showDestinationValidation("Enter a destination to add.");
      return false;
    }
    if (destinationQueries.length >= maximumDestinations) {
      showDestinationValidation("You can compare up to five destinations.");
      return false;
    }
    if (
      destinationQueries.some(
        (value) => value.query.toLowerCase() === normalizedQuery.toLowerCase(),
      )
    ) {
      showDestinationValidation("That destination is already included.");
      return false;
    }
    const broadScope = kind === "country" || kind === "region";
    const alreadyBroad = destinationQueries.some(
      (value) => value.kind === "country" || value.kind === "region",
    );
    if ((broadScope && destinationQueries.length > 0) || alreadyBroad) {
      showDestinationValidation(
        "Choose one country or region by itself, or compare individual cities.",
      );
      return false;
    }
    destinationQueries.push({ query: normalizedQuery, kind });
    destinationInput.value = "";
    delete destinationInput.dataset.scopeKind;
    destinationStatus.textContent = `${normalizedQuery} added.`;
    renderDestinationChips();
    return true;
  }

  function commitPendingDestination({ allowBlank = false } = {}) {
    const query = destinationInput.value.trim();
    clearDestinationValidation();
    if (query === "") {
      if (!allowBlank) {
        showDestinationValidation("Enter a destination to add.");
        return false;
      }
      return true;
    }
    return addDestinationQuery(query, destinationInput.dataset.scopeKind ?? null);
  }

  function showValidation(errors) {
    clearValidation();
    const summaryItems = document.createDocumentFragment();
    for (const error of errors) {
      const field = document.querySelector(`#${error.fieldId}`);
      const fieldError = document.querySelector(`#${error.errorId}`);
      field.setAttribute("aria-invalid", "true");
      fieldError.textContent = error.message;
      fieldError.hidden = false;

      const item = document.createElement("li");
      const link = document.createElement("a");
      link.setAttribute("href", `#${error.fieldId}`);
      link.textContent = error.message;
      item.append(link);
      summaryItems.append(item);
    }
    validationList.replaceChildren(summaryItems);
    validationSummary.hidden = false;
    setSubmissionStatus("Please check the highlighted trip details.");
    validationSummary.focus();
  }

  function validateForm(targetForm) {
    const errors = [];
    const startDate = targetForm.elements.namedItem("travel-start-date").value;
    const endDate = targetForm.elements.namedItem("travel-end-date").value;
    const interestValue = targetForm.elements.namedItem("interests").value;

    if (startDate === "") {
      errors.push(validationError("travel-start-date", "Choose a start date."));
    }
    if (endDate === "") {
      errors.push(validationError("travel-end-date", "Choose an end date."));
    } else if (startDate !== "" && endDate < startDate) {
      errors.push(
        validationError(
          "travel-end-date",
          "End date must be the same as or after the start date.",
        ),
      );
    }

    if (interestValue.trim() !== "") {
      const interests = interestValue.split(",").map((interest) => interest.trim());
      if (interests.some((interest) => interest === "")) {
        errors.push(
          validationError("interests", "Remove empty interests between commas."),
        );
      } else {
        const normalizedInterests = new Set();
        const duplicateFound = interests.some((interest) => {
          const normalized = interest.toLowerCase();
          if (normalizedInterests.has(normalized)) {
            return true;
          }
          normalizedInterests.add(normalized);
          return false;
        });
        if (duplicateFound) {
          errors.push(validationError("interests", "Remove duplicate interests."));
        }
      }
    }
    return errors;
  }

  function buildRecommendationRequest(targetForm) {
    const request = {
      travel_period: {
        start_date: targetForm.elements.namedItem("travel-start-date").value,
        end_date: targetForm.elements.namedItem("travel-end-date").value,
      },
      preferences: {
        interests: selectedInterests(targetForm),
        preferred_pace: optionalText(targetForm.elements.namedItem("preferred-pace").value),
        preferred_climate: optionalText(
          targetForm.elements.namedItem("preferred-climate").value,
        ),
        trip_description: optionalText(
          targetForm.elements.namedItem("trip-description").value,
        ),
      },
      destination: null,
    };
    if (destinationQueries.length > 0) {
      request.destination_queries = destinationQueries.map(({ query }) => query);
    }
    return request;
  }

  function structuralValidationErrors(detail) {
    if (!Array.isArray(detail)) {
      return [];
    }
    const errors = [];
    const seenFields = new Set();
    const mappings = [
      ["travel_period.start_date", "travel-start-date", "Enter a valid start date."],
      ["travel_period.end_date", "travel-end-date", "Enter a valid end date."],
      ["destination_queries", "destination-input", "Review your destinations."],
      ["preferences.interests", "interests", "Review your interests."],
      ["preferences.preferred_pace", "preferred-pace", "Review your preferred pace."],
      [
        "preferences.preferred_climate",
        "preferred-climate",
        "Review your preferred climate.",
      ],
      [
        "preferences.trip_description",
        "trip-description",
        "Review your trip description.",
      ],
    ];
    for (const issue of detail) {
      const location = Array.isArray(issue?.loc) ? issue.loc.join(".") : "";
      const mapping = mappings.find(([path]) => location.endsWith(path));
      if (mapping && !seenFields.has(mapping[1])) {
        errors.push(validationError(mapping[1], mapping[2]));
        seenFields.add(mapping[1]);
      }
    }
    return errors;
  }

  function domainValidationErrors(detail) {
    if (
      typeof detail !== "object" ||
      detail === null ||
      detail.code !== "invalid_recommendation_request" ||
      typeof detail.message !== "string"
    ) {
      return [];
    }
    if (detail.message.includes("end date must not be before start date")) {
      return [
        validationError(
          "travel-end-date",
          "End date must be the same as or after the start date.",
        ),
      ];
    }
    if (detail.message.includes("interests must not be blank")) {
      return [validationError("interests", "Remove empty interests between commas.")];
    }
    if (detail.message.includes("interests must not contain duplicates")) {
      return [validationError("interests", "Remove duplicate interests.")];
    }
    if (detail.message.includes("preferred pace must not be blank")) {
      return [validationError("preferred-pace", "Enter a preferred pace or leave it blank.")];
    }
    if (detail.message.includes("preferred climate must not be blank")) {
      return [
        validationError(
          "preferred-climate",
          "Enter a preferred climate or leave it blank.",
        ),
      ];
    }
    if (detail.message.includes("trip description")) {
      return [
        validationError(
          "trip-description",
          "Keep the trip description under 1,000 characters and remove control characters.",
        ),
      ];
    }
    if (detail.message.includes("destination_queries")) {
      return [validationError("destination-input", "Review your destinations.")];
    }
    return [];
  }

  async function readErrorResponse(response, requestId) {
    const retryAfterSeconds = parseRetryAfter(response);
    let payload = null;
    try {
      payload = await response.json();
    } catch {
      return new RecommendationRequestError(
        "http",
        response.status,
        null,
        [],
        requestId,
        retryAfterSeconds,
      );
    }
    const detail = payload?.detail;
    const code =
      typeof detail === "object" && detail !== null && typeof detail.code === "string"
        ? detail.code
        : null;
    const validationErrors = [
      ...domainValidationErrors(detail),
      ...structuralValidationErrors(detail),
    ];
    const responseMessage =
      code === "destination_not_found" && typeof detail.message === "string"
        ? detail.message
        : null;
    const suggestions =
      code === "destination_not_found" && Array.isArray(detail?.suggestions)
        ? detail.suggestions.filter((value) => typeof value === "string").slice(0, 5)
        : [];
    return new RecommendationRequestError(
      "http",
      response.status,
      code,
      validationErrors,
      requestId,
      retryAfterSeconds,
      responseMessage,
      suggestions,
    );
  }

  async function submitRecommendationRequest(endpoint, payload) {
    let response;
    try {
      response = await fetch(endpoint, {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
    } catch {
      throw new RecommendationRequestError("network");
    }

    const requestId = response.headers.get("X-Request-ID");

    if (!response.ok) {
      throw await readErrorResponse(response, requestId);
    }

    let responsePayload;
    try {
      responsePayload = await response.json();
    } catch {
      throw new RecommendationRequestError("response", response.status, null, [], requestId);
    }
    if (
      typeof responsePayload !== "object" ||
      responsePayload === null ||
      !Array.isArray(responsePayload.recommendations)
    ) {
      throw new RecommendationRequestError("response", response.status, null, [], requestId);
    }
    return { payload: responsePayload, requestId };
  }

  function clearRequestReference() {
    requestReference.hidden = true;
    requestReferenceValue.replaceChildren();
    delete form.dataset.recommendationRequestId;
  }

  function showRequestReference(requestId) {
    if (!requestId) {
      return;
    }
    requestReferenceValue.textContent = requestId;
    requestReference.hidden = false;
    form.dataset.recommendationRequestId = requestId;
  }

  function setSubmissionStatus(message) {
    statusRegion.textContent = message;
  }

  function setLoadingState(loading) {
    requestInFlight = loading;
    submitButton.disabled = loading || cooldownActive;
    submitButton.textContent = loading ? loadingSubmitLabel : idleSubmitLabel();
    destinationAddButton.disabled = loading;
    form.querySelectorAll("input, select, textarea").forEach((control) => {
      control.disabled = loading;
    });
    if (loading) {
      form.setAttribute("aria-busy", "true");
    } else {
      form.removeAttribute("aria-busy");
    }
  }

  function startCooldown(retryAfterSeconds) {
    const seconds = retryAfterSeconds ?? defaultCooldownSeconds;
    cooldownActive = true;
    submitButton.disabled = true;
    retryButton.disabled = true;
    window.clearTimeout(cooldownTimer);
    cooldownTimer = window.setTimeout(() => {
      cooldownActive = false;
      submitButton.disabled = requestInFlight;
      retryButton.disabled = false;
    }, seconds * 1000);
  }

  function clearRequestError() {
    requestError.hidden = true;
    requestErrorTitle.replaceChildren();
    requestErrorMessage.replaceChildren();
    retryButton.hidden = true;
    requestError.querySelector(".destination-corrections")?.remove();
  }

  function classifyRequestError(error) {
    const knownCodes = {
      recommendation_service_unconfigured: {
        title: "Recommendations aren't available yet",
        message:
          "This Solara public alpha is running without a configured recommendation service.",
        retry: false,
      },
      provider_authentication_failed: {
        title: "Travel data is temporarily unavailable",
        message:
          "Solara can't access the travel data needed for this comparison right now.",
        retry: false,
      },
      provider_rate_limited: {
        title: "Travel data is busy right now",
        message:
          "The travel-data service is temporarily busy. Please wait a moment and try again.",
        retry: true,
      },
      provider_invalid_response: {
        title: "Solara couldn't use the travel data",
        message:
          "Travel data was returned, but Solara couldn't safely prepare recommendations from it. Please try again.",
        retry: true,
      },
      provider_unavailable: {
        title: "Travel data is temporarily unavailable",
        message:
          "Solara couldn't reach the travel data needed for this comparison. Please try again shortly.",
        retry: true,
      },
      provider_error: {
        title: "Travel data couldn't be prepared",
        message:
          "Solara couldn't complete the travel-data step for this request. Please try again.",
        retry: true,
      },
      invalid_recommendation_request: {
        title: "Check your trip details",
        message:
          "Some trip details could not be accepted. Review the form and try again.",
        retry: false,
      },
      destination_not_found: {
        title: "Destination not found",
        message:
          "Solara couldn't find one of those destinations. Review your destination and try again.",
        retry: false,
      },
      broad_scope_combination_not_supported: {
        title: "Choose one discovery approach",
        message: "Use one country or region by itself, or compare individual cities.",
        retry: false,
      },
      destination_discovery_unavailable: {
        title: "Destination discovery is temporarily unavailable",
        message:
          "Solara couldn't prepare a discovery shortlist right now. Please try again shortly.",
        retry: true,
      },
      recommendation_rate_limited: {
        title: "Solara is taking a short pause",
        message:
          "This public alpha has received several comparison requests. Please wait a little before trying again.",
        retry: true,
      },
      recommendation_budget_exhausted: {
        title: "Solara has reached its current public-alpha allowance",
        message:
          "Recommendation capacity for this public alpha is temporarily exhausted. Please try again later.",
        retry: true,
      },
      recommendation_capacity_reached: {
        title: "Solara is busy right now",
        message:
          "Other recommendations are currently being prepared. Please wait a moment and try again.",
        retry: true,
      },
    };
    if (error.code && knownCodes[error.code]) {
      if (error.code === "destination_not_found" && error.responseMessage) {
        return { ...knownCodes.destination_not_found, message: error.responseMessage };
      }
      return knownCodes[error.code];
    }
    if (error.kind === "network") {
      return {
        title: "Can't reach Solara right now",
        message: "Check your connection and try the recommendation again.",
        retry: true,
      };
    }
    if (error.kind === "response") {
      return {
        title: "Solara couldn't read the recommendation response",
        message:
          "The recommendation response wasn't in the expected format. Please try again.",
        retry: true,
      };
    }
    if (error.status === 422) {
      return knownCodes.invalid_recommendation_request;
    }
    if (error.status === 500) {
      return {
        title: "Something went wrong",
        message: "Solara couldn't prepare recommendations this time. Please try again.",
        retry: true,
      };
    }
    if (error.status === 429) {
      return {
        title: "Solara needs a short pause",
        message: "Please wait a little before trying this recommendation request again.",
        retry: true,
      };
    }
    return {
      title: "Solara couldn't complete the request",
      message: "The recommendation request didn't complete successfully. Please try again.",
      retry: error.status >= 500,
    };
  }

  function showRequestError(error) {
    if (error.status === 422 && error.validationErrors.length > 0) {
      showValidation(error.validationErrors);
      return;
    }
    const presentation = classifyRequestError(error);
    requestErrorTitle.textContent = presentation.title;
    requestErrorMessage.textContent = presentation.message;
    if (error.suggestions.length > 0) {
      const choices = document.createElement("div");
      choices.className = "destination-corrections";
      const prompt = document.createElement("p");
      prompt.textContent = "Did you mean:";
      choices.append(prompt);
      error.suggestions.forEach((suggestion) => {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = suggestion;
        button.addEventListener("click", () => {
          const unresolvedIndex = destinationQueries.findIndex(({ query }) =>
            error.responseMessage?.includes(`"${query}"`),
          );
          if (unresolvedIndex >= 0) {
            destinationQueries[unresolvedIndex] = { query: suggestion, kind: null };
            destinationInput.value = "";
            destinationStatus.textContent = `${suggestion} selected. Review your trip, then submit when ready.`;
            renderDestinationChips();
          } else {
            destinationInput.value = suggestion;
          }
          clearRequestError();
          destinationInput.focus();
        });
        choices.append(button);
      });
      requestErrorMessage.after(choices);
    }
    retryButton.hidden = !presentation.retry;
    requestError.hidden = false;
    if (error.status === 429) {
      startCooldown(error.retryAfterSeconds);
      const seconds = error.retryAfterSeconds ?? defaultCooldownSeconds;
      setSubmissionStatus(`You can try again in about ${seconds} seconds.`);
    } else {
      setSubmissionStatus("Solara couldn't complete the recommendation request.");
      requestError.focus();
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (requestInFlight || cooldownActive) {
      return;
    }

    clearValidation();
    if (!commitPendingDestination({ allowBlank: true })) {
      destinationInput.focus();
      return;
    }
    const validationErrors = validateForm(form);
    if (validationErrors.length > 0) {
      showValidation(validationErrors);
      return;
    }

    clearRequestError();
    clearRequestReference();
    setLoadingState(true);
    setSubmissionStatus("Comparing destinations.");
    window.clearTimeout(coldStartTimer);
    coldStartTimer = window.setTimeout(() => {
      setSubmissionStatus(
        "Solara may be waking up. The public alpha can take up to a minute after being idle.",
      );
    }, coldStartThresholdMilliseconds);
    form.dispatchEvent(new CustomEvent("solara:recommendation-request-start"));

    let responseResult;
    try {
      responseResult = await submitRecommendationRequest(
        recommendationEndpoint,
        buildRecommendationRequest(form),
      );
    } catch (error) {
      const controlledError =
        error instanceof RecommendationRequestError
          ? error
          : new RecommendationRequestError("response");
      showRequestReference(controlledError.requestId);
      showRequestError(controlledError);
      return;
    } finally {
      window.clearTimeout(coldStartTimer);
      setLoadingState(false);
    }

    const responsePayload = responseResult.payload;
    showRequestReference(responseResult.requestId);

    const hasRecommendations =
      responsePayload.has_recommendations === true &&
      responsePayload.recommendations.length > 0;
    setSubmissionStatus(
      hasRecommendations
        ? "Recommendations ready."
        : "No recommendations were returned for this request.",
    );
    form.dispatchEvent(
      new CustomEvent("solara:recommendation-ready", { detail: responsePayload }),
    );
  }

  if (
    form &&
    submitButton &&
    statusRegion &&
    validationSummary &&
    validationList &&
    requestError &&
    requestErrorTitle &&
    requestErrorMessage &&
    retryButton &&
    requestReference &&
    requestReferenceValue &&
    destinationInput &&
    destinationAddButton &&
    destinationChips &&
    destinationStatus &&
    tripDescription &&
    tripDescriptionCount
  ) {
    renderDestinationChips();
    form.addEventListener("submit", handleSubmit);
    retryButton.addEventListener("click", () => form.requestSubmit());
    form.addEventListener("solara:add-destination", (event) => {
      const query = event.detail?.query;
      if (!requestInFlight && typeof query === "string") {
        addDestinationQuery(query, event.detail?.kind ?? null);
      }
    });
    destinationAddButton.addEventListener("click", () => {
      if (!requestInFlight && commitPendingDestination()) {
        destinationInput.focus();
      }
    });
    destinationInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.isComposing) {
        event.preventDefault();
        if (!requestInFlight && commitPendingDestination()) {
          destinationInput.focus();
        }
      }
    });
    destinationChips.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-destination-index]");
      if (!button || requestInFlight) {
        return;
      }
      const index = Number.parseInt(button.dataset.destinationIndex, 10);
      if (Number.isInteger(index) && index >= 0 && index < destinationQueries.length) {
        const [removed] = destinationQueries.splice(index, 1);
        destinationStatus.textContent = `${removed.query} removed.`;
        renderDestinationChips();
        destinationInput.focus();
      }
    });
    form.addEventListener("solara:scope-selected", () => clearDestinationValidation());
    tripDescription.addEventListener("input", () => {
      tripDescriptionCount.textContent = String(tripDescription.value.length);
    });
  }
})();
