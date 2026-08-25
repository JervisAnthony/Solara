(() => {
  "use strict";

  function enhanceSelect(root) {
    const trigger = root.querySelector("[role='combobox']");
    const menu = root.querySelector("[role='listbox']");
    const options = [...root.querySelectorAll("[role='option']")];
    const value = root.querySelector("[data-select-value]");
    const label = root.querySelector("[data-select-label]");
    let activeIndex = Math.max(
      0,
      options.findIndex((option) => option.getAttribute("aria-selected") === "true"),
    );

    function setActive(nextIndex) {
      activeIndex = (nextIndex + options.length) % options.length;
      trigger.setAttribute("aria-activedescendant", options[activeIndex].id);
      options.forEach((option, index) => {
        option.classList.toggle("is-active", index === activeIndex);
      });
      options[activeIndex].scrollIntoView({ block: "nearest" });
    }

    function openMenu(preferredIndex = activeIndex) {
      menu.hidden = false;
      trigger.setAttribute("aria-expanded", "true");
      setActive(preferredIndex);
    }

    function closeMenu() {
      menu.hidden = true;
      trigger.setAttribute("aria-expanded", "false");
      trigger.removeAttribute("aria-activedescendant");
      options.forEach((option) => option.classList.remove("is-active"));
    }

    function selectOption(index) {
      const option = options[index];
      value.value = option.dataset.value;
      label.textContent = option.querySelector("strong")?.textContent ?? option.textContent;
      options.forEach((candidate, candidateIndex) => {
        candidate.setAttribute("aria-selected", String(candidateIndex === index));
      });
      activeIndex = index;
      closeMenu();
      value.dispatchEvent(new Event("change", { bubbles: true }));
    }

    trigger.addEventListener("click", () => {
      if (trigger.getAttribute("aria-expanded") === "true") {
        closeMenu();
      } else {
        openMenu();
      }
    });
    trigger.addEventListener("keydown", (event) => {
      const open = trigger.getAttribute("aria-expanded") === "true";
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        const direction = event.key === "ArrowDown" ? 1 : -1;
        if (open) {
          setActive(activeIndex + direction);
        } else {
          openMenu(activeIndex + direction);
        }
      } else if (event.key === "Home" || event.key === "End") {
        event.preventDefault();
        openMenu(event.key === "Home" ? 0 : options.length - 1);
      } else if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        if (open) {
          selectOption(activeIndex);
        } else {
          openMenu();
        }
      } else if (event.key === "Escape" && open) {
        event.preventDefault();
        closeMenu();
      } else if (event.key === "Tab") {
        closeMenu();
      }
    });
    options.forEach((option, index) => {
      option.addEventListener("pointermove", () => setActive(index));
      option.addEventListener("click", () => {
        selectOption(index);
        trigger.focus();
      });
    });
    document.addEventListener("pointerdown", (event) => {
      if (!root.contains(event.target)) {
        closeMenu();
      }
    });
  }

  document.querySelectorAll("[data-premium-select]").forEach(enhanceSelect);

  const composer = document.querySelector("#trip-description");
  document.querySelectorAll("[data-prompt-starter]").forEach((button) => {
    button.addEventListener("click", () => {
      if (composer.value.trim() === "") {
        composer.value = `${button.dataset.promptStarter}. `;
        composer.dispatchEvent(new Event("input", { bubbles: true }));
      }
      composer.focus();
    });
  });
})();
