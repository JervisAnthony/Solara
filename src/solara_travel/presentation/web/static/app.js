(() => {
  "use strict";

  const form = document.querySelector("#recommendation-form");
  const recommendationEndpoint = "/api/v1/recommendations";

  function optionalText(value) {
    const trimmed = value.trim();
    return trimmed === "" ? null : trimmed;
  }

  function parseInterests(value) {
    const trimmed = value.trim();
    return trimmed === "" ? null : trimmed.split(",").map((interest) => interest.trim());
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

  async function submitRecommendationRequest(endpoint, payload) {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error("Recommendation request was not successful.");
    }

    return response.json();
  }

  function setSubmissionStatus(message) {
    document.querySelector("#recommendation-form-status").textContent = message;
  }

  async function handleSubmit(event) {
    event.preventDefault();

    try {
      const responsePayload = await submitRecommendationRequest(
        recommendationEndpoint,
        buildRecommendationRequest(form),
      );
      setSubmissionStatus("Recommendation data received.");
      form.dispatchEvent(
        new CustomEvent("solara:recommendation-ready", { detail: responsePayload }),
      );
    } catch {
      setSubmissionStatus("Solara couldn't complete that request yet.");
    }
  }

  if (form) {
    form.addEventListener("submit", handleSubmit);
  }
})();
