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
  let feedbackInFlight = false;

  function setLoadingState(loading) {
    feedbackInFlight = loading;
    feedbackSubmit.disabled = loading;
    feedbackSubmit.textContent = loading ? loadingSubmitLabel : idleSubmitLabel;
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
    if (feedbackInFlight) {
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
