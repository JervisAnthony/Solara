(() => {
  "use strict";

  const input = document.querySelector("#destination-input");
  const listbox = document.querySelector("#destination-suggestions");
  const attribution = document.querySelector("#destination-attribution");
  const status = document.querySelector("#destination-status");
  const endpoint = "/api/v1/travel-scope-suggestions";
  const debounceMilliseconds = 350;
  let debounceTimer = null;
  let activeController = null;
  let requestSequence = 0;
  let activeIndex = -1;
  let suggestions = [];

  function closeSuggestions() {
    suggestions = [];
    activeIndex = -1;
    listbox.replaceChildren();
    listbox.hidden = true;
    attribution.hidden = true;
    input.setAttribute("aria-expanded", "false");
    input.removeAttribute("aria-activedescendant");
  }

  function setActiveIndex(index) {
    const options = [...listbox.querySelectorAll('[role="option"]')];
    if (options.length === 0) {
      return;
    }
    activeIndex = (index + options.length) % options.length;
    options.forEach((option, optionIndex) => {
      const active = optionIndex === activeIndex;
      option.setAttribute("aria-selected", String(active));
      option.classList.toggle("is-active", active);
    });
    input.setAttribute("aria-activedescendant", options[activeIndex].id);
    options[activeIndex].scrollIntoView({ block: "nearest" });
  }

  function chooseSuggestion(index) {
    const suggestion = suggestions[index];
    if (!suggestion) {
      return;
    }
    input.value = suggestion.display_name;
    input.dataset.scopeKind = suggestion.kind;
    input.dispatchEvent(
      new CustomEvent("solara:scope-selected", {
        bubbles: true,
        detail: { query: suggestion.display_name, kind: suggestion.kind },
      }),
    );
    status.textContent = `${suggestion.display_name} selected.`;
    closeSuggestions();
  }

  function renderSuggestions(items) {
    suggestions = items.slice(0, 5);
    activeIndex = -1;
    const fragment = document.createDocumentFragment();
    suggestions.forEach((suggestion, index) => {
      const option = document.createElement("button");
      option.type = "button";
      option.id = `destination-suggestion-${index}`;
      option.className = "destination-suggestion";
      option.setAttribute("role", "option");
      option.setAttribute("aria-selected", "false");
      option.dataset.suggestionIndex = String(index);
      const label = document.createElement("span");
      label.textContent = suggestion.display_name;
      const kind = document.createElement("span");
      kind.className = "destination-suggestion-kind";
      kind.textContent = suggestion.kind;
      option.append(label, kind);
      fragment.append(option);
    });
    listbox.replaceChildren(fragment);
    const hasSuggestions = suggestions.length > 0;
    listbox.hidden = !hasSuggestions;
    attribution.hidden = !hasSuggestions;
    input.setAttribute("aria-expanded", String(hasSuggestions));
    status.textContent = hasSuggestions
      ? `${suggestions.length} destination suggestion${suggestions.length === 1 ? "" : "s"} available.`
      : "No destination suggestions found.";
  }

  async function fetchSuggestions(query, sequence) {
    activeController?.abort();
    activeController = new AbortController();
    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
        signal: activeController.signal,
      });
      if (sequence !== requestSequence) {
        return;
      }
      if (!response.ok) {
        closeSuggestions();
        status.textContent = "Destination suggestions are unavailable; you can still add what you typed.";
        return;
      }
      const payload = await response.json();
      const items = Array.isArray(payload?.suggestions)
        ? payload.suggestions.filter(
            (item) =>
              typeof item?.display_name === "string" &&
              ["locality", "region", "country"].includes(item?.kind),
          )
        : [];
      renderSuggestions(items);
    } catch (error) {
      if (error?.name !== "AbortError" && sequence === requestSequence) {
        closeSuggestions();
        status.textContent = "Destination suggestions are unavailable; you can still add what you typed.";
      }
    }
  }

  function scheduleSuggestions() {
    window.clearTimeout(debounceTimer);
    delete input.dataset.scopeKind;
    const query = input.value.trim();
    requestSequence += 1;
    const sequence = requestSequence;
    if (query.length < 2) {
      activeController?.abort();
      closeSuggestions();
      return;
    }
    debounceTimer = window.setTimeout(
      () => fetchSuggestions(query, sequence),
      debounceMilliseconds,
    );
  }

  if (input && listbox && attribution && status) {
    input.addEventListener("input", scheduleSuggestions);
    input.addEventListener("keydown", (event) => {
      if (listbox.hidden) {
        return;
      }
      if (event.key === "ArrowDown") {
        event.preventDefault();
        setActiveIndex(activeIndex + 1);
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        setActiveIndex(activeIndex - 1);
      } else if (event.key === "Enter" && activeIndex >= 0) {
        event.preventDefault();
        event.stopImmediatePropagation();
        chooseSuggestion(activeIndex);
      } else if (event.key === "Escape") {
        closeSuggestions();
      }
    });
    listbox.addEventListener("pointerdown", (event) => {
      const option = event.target.closest("[data-suggestion-index]");
      if (option) {
        event.preventDefault();
        chooseSuggestion(Number.parseInt(option.dataset.suggestionIndex, 10));
      }
    });
    document.addEventListener("pointerdown", (event) => {
      if (event.target !== input && !listbox.contains(event.target)) {
        closeSuggestions();
      }
    });
  }
})();
