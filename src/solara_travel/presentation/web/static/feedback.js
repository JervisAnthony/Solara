(() => {
  "use strict";

  const feedbackForm = document.querySelector("#tester-feedback-form");
  const recommendationForm = document.querySelector("#recommendation-form");
  const feedbackSubmit = document.querySelector("#feedback-submit");
  const feedbackStatus = document.querySelector("#feedback-status");
  const feedbackComment = document.querySelector("#feedback-comment");
  const feedbackEndpoint = "/api/v1/feedback";
  const idleSubmitLabel = "Send feedback";
  const loadingSubmitLabel = "Sending…";
  const successMessage = "Thanks — your feedback was received.";
  const failureMessage = "Solara couldn't send your feedback. Please try again.";
  const rateLimitMessage =
    "Solara is receiving a lot of feedback right now. Please wait a little and try again.";
  const defaultCooldownSeconds = 60;
  const maximumCooldownSeconds = 86400;
  let feedbackInFlight = false;
  let cooldownActive = false;
  let cooldownTimer = null;

  function setLoadingState(loading) {
    feedbackInFlight = loading;
    feedbackSubmit.disabled = loading || cooldownActive;
    feedbackSubmit.textContent = loading ? loadingSubmitLabel : idleSubmitLabel;
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

  function startCooldown(retryAfterSeconds) {
    const seconds = retryAfterSeconds ?? defaultCooldownSeconds;
    cooldownActive = true;
    feedbackSubmit.disabled = true;
    window.clearTimeout(cooldownTimer);
    cooldownTimer = window.setTimeout(() => {
      cooldownActive = false;
      feedbackSubmit.disabled = feedbackInFlight;
    }, seconds * 1000);
    return seconds;
  }

  function selectedRating() {
    return feedbackForm.querySelector('input[name="rating"]:checked');
  }

  function buildPayload(rating) {
    const trimmedComment = feedbackComment.value.trim();
    return {
      recommendation_request_id:
        recommendationForm.dataset.recommendationRequestId || null,
      rating: rating.value,
      comment: trimmedComment === "" ? null : trimmedComment,
    };
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (feedbackInFlight || cooldownActive) {
      return;
    }

    const rating = selectedRating();
    if (!rating) {
      feedbackStatus.textContent = "Choose a feedback rating before sending.";
      feedbackForm.querySelector('input[name="rating"]').focus();
      return;
    }

    feedbackStatus.replaceChildren();
    setLoadingState(true);
    try {
      const response = await fetch(feedbackEndpoint, {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify(buildPayload(rating)),
      });
      if (response.status === 429) {
        const seconds = startCooldown(parseRetryAfter(response));
        feedbackStatus.textContent =
          `${rateLimitMessage} You can try again in about ${seconds} seconds.`;
        return;
      }
      if (!response.ok || response.status !== 202) {
        feedbackStatus.textContent = failureMessage;
        return;
      }
      feedbackForm.reset();
      feedbackStatus.textContent = successMessage;
    } catch {
      feedbackStatus.textContent = failureMessage;
    } finally {
      setLoadingState(false);
    }
  }

  if (
    feedbackForm &&
    recommendationForm &&
    feedbackSubmit &&
    feedbackStatus &&
    feedbackComment
  ) {
    feedbackForm.addEventListener("submit", handleSubmit);
  }
})();
