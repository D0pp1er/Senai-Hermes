(() => {
  "use strict";
  const chapters = Array.from(document.querySelectorAll(".chapter"));
  const navLinks = Array.from(document.querySelectorAll("#chapter-nav a"));
  const toggle = document.getElementById("present-toggle");
  const controls = document.getElementById("present-controls");
  const previous = document.getElementById("previous-chapter");
  const next = document.getElementById("next-chapter");
  const counter = document.getElementById("chapter-counter");
  const progress = document.getElementById("reading-progress");
  const copyStatus = document.getElementById("copy-status");
  let presenting = false;
  let active = 0;

  function indexFromHash() {
    return chapters.findIndex(chapter => "#" + chapter.id === window.location.hash);
  }

  function updateControls() {
    navLinks.forEach((link, index) => {
      if (index === active) link.setAttribute("aria-current", "location");
      else link.removeAttribute("aria-current");
    });
    previous.disabled = active === 0;
    next.disabled = active === chapters.length - 1;
    counter.textContent = String(active + 1).padStart(2, "0") + " / " + String(chapters.length).padStart(2, "0");
    progress.style.width = ((active + 1) / chapters.length * 100) + "%";
  }

  function reveal(index, { focus = false, updateHash = false } = {}) {
    if (index < 0 || index >= chapters.length) return;
    active = index;
    chapters.forEach((chapter, position) => { chapter.hidden = presenting && position !== active; });
    updateControls();
    if (updateHash) history.replaceState(null, "", "#" + chapters[active].id);
    if (focus) {
      chapters[active].focus({ preventScroll: true });
      chapters[active].scrollIntoView({ block: "start", behavior: "instant" });
    }
  }

  function setPresentation(enabled) {
    presenting = enabled;
    document.body.classList.toggle("is-presenting", presenting);
    controls.hidden = !presenting;
    toggle.textContent = presenting ? "Read guide ↙" : "Present ↗";
    toggle.setAttribute("aria-pressed", String(presenting));
    reveal(active, { focus: true, updateHash: true });
  }

  toggle.hidden = false;
  toggle.setAttribute("aria-pressed", "false");
  toggle.addEventListener("click", () => setPresentation(!presenting));
  previous.addEventListener("click", () => reveal(active - 1, { focus: true, updateHash: true }));
  next.addEventListener("click", () => reveal(active + 1, { focus: true, updateHash: true }));

  document.addEventListener("keydown", event => {
    if (!presenting || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
    if (event.target.closest("input, textarea, select, [contenteditable='true']")) return;
    if (window.getSelection()?.toString()) return;
    const moves = { ArrowRight: 1, ArrowLeft: -1 };
    if (event.key in moves) {
      event.preventDefault();
      reveal(active + moves[event.key], { focus: true, updateHash: true });
    } else if (event.key === "Escape") {
      setPresentation(false);
      toggle.focus();
    }
  });

  // Follow all chapter anchors, including calls to action inside the currently visible chapter.
  document.querySelectorAll('a[href^="#"]').forEach(link => {
    link.addEventListener("click", event => {
      const index = chapters.findIndex(chapter => "#" + chapter.id === link.getAttribute("href"));
      if (index < 0) return;
      event.preventDefault();
      reveal(index, { focus: true, updateHash: true });
    });
  });
  window.addEventListener("hashchange", () => {
    const index = indexFromHash();
    if (index >= 0) reveal(index, { focus: true });
  });

  // Keep the chapter marker in sync while reading the complete guide.
  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(entries => {
      if (presenting) return;
      const visible = entries.filter(entry => entry.isIntersecting)
        .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
      if (visible.length) {
        active = chapters.indexOf(visible[0].target);
        updateControls();
      }
    }, { rootMargin: "-12% 0px -62% 0px", threshold: 0 });
    chapters.forEach(chapter => observer.observe(chapter));
  }

  async function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      try { await navigator.clipboard.writeText(text); return; } catch (_) { /* Try local fallback. */ }
    }
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.cssText = "position:fixed;top:-9999px;left:-9999px";
    const focused = document.activeElement;
    document.body.appendChild(textarea);
    textarea.select();
    let copied = false;
    try { copied = document.execCommand("copy"); }
    finally { textarea.remove(); focused?.focus({ preventScroll: true }); }
    if (!copied) throw new Error("Select and copy the command manually.");
  }

  document.querySelectorAll("[data-copy]").forEach(button => {
    button.hidden = false;
    const target = document.getElementById(button.dataset.copy);
    button.setAttribute("aria-label", "Copy commands: " + button.dataset.copy.replaceAll("-", " "));
    button.addEventListener("click", async () => {
      try {
        await copyText(target.textContent.trim());
        button.textContent = "Copied ✓";
        copyStatus.textContent = "Commands copied to clipboard.";
      } catch (_) {
        button.textContent = "Select text";
        copyStatus.textContent = "Clipboard unavailable. Select and copy the code manually.";
      }
      window.setTimeout(() => { button.textContent = "Copy"; }, 1800);
    });
  });
  reveal(Math.max(0, indexFromHash()));
})();
