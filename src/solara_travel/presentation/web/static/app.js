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
  const recommendationEndpoint = "/api/v1/recommendations";
  const idleSubmitLabel = "Compare destinations";
  const loadingSubmitLabel = "Comparing…";
  const defaultCooldownSeconds = 60;
  const maximumCooldownSeconds = 86400;
  let requestInFlight = false;
  let cooldownActive = false;
  let cooldownTimer = null;

  const fieldContracts = {
    "travel-start-date": "travel-start-date-error",
    "travel-end-date": "travel-end-date-error",
    interests: "interests-error",
    "preferred-pace": "preferred-pace-error",
    "preferred-climate": "preferred-climate-error",
  };

  class RecommendationRequestError extends Error {
    constructor(
      kind,
      status = null,
      code = null,
      validationErrors = [],
      requestId = null,
      retryAfterSeconds = null,
    ) {
      super("Recommendation request failed.");
      this.name = "RecommendationRequestError";
      this.kind = kind;
      this.status = status;
      this.code = code;
      this.validationErrors = validationErrors;
      this.requestId = requestId;
      this.retryAfterSeconds = retryAfterSeconds;
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
    return {
      travel_period: {
        start_date: targetForm.elements.namedItem("travel-start-date").value,
        end_date: targetForm.elements.namedItem("travel-end-date").value,
      },
      preferences: {
        interests: parseInterests(targetForm.elements.namedItem("interests").value),
        preferred_pace: optionalText(targetForm.elements.namedItem("preferred-pace").value),
        preferred_climate: optionalText(
          targetForm.elements.namedItem("preferred-climate").value,
        ),
      },
      destination: null,
    };
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
      ["preferences.interests", "interests", "Review your interests."],
      ["preferences.preferred_pace", "preferred-pace", "Review your preferred pace."],
      [
        "preferences.preferred_climate",
        "preferred-climate",
        "Review your preferred climate.",
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
    return new RecommendationRequestError(
      "http",
      response.status,
      code,
      validationErrors,
      requestId,
      retryAfterSeconds,
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
    submitButton.textContent = loading ? loadingSubmitLabel : idleSubmitLabel;
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
  }

  function classifyRequestError(error) {
    const knownCodes = {
      recommendation_service_unconfigured: {
        title: "Recommendations aren't available yet",
        message:
          "This Solara preview is running without a configured recommendation service.",
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
      recommendation_rate_limited: {
        title: "Solara is taking a short pause",
        message:
          "This public preview has received several comparison requests. Please wait a little before trying again.",
        retry: true,
      },
      recommendation_budget_exhausted: {
        title: "Solara has reached its current preview allowance",
        message:
          "Recommendation capacity for this public preview is temporarily exhausted. Please try again later.",
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
    const validationErrors = validateForm(form);
    if (validationErrors.length > 0) {
      showValidation(validationErrors);
      return;
    }

    clearRequestError();
    clearRequestReference();
    setLoadingState(true);
    setSubmissionStatus("Comparing destinations.");
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
    requestReferenceValue
  ) {
    form.addEventListener("submit", handleSubmit);
    retryButton.addEventListener("click", () => form.requestSubmit());
  }
})();
