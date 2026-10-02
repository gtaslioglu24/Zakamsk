(() => {
  document.documentElement.classList.add("js");
  const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;

  // In-page links scroll smoothly without writing #section into the URL,
  // so a reload or language switch always starts at the top of the page.
  // A hash arriving from another page (e.g. legal page -> "../#plan") is honoured once, then removed.
  const scrollToEl = (el, smooth) => {
    el.scrollIntoView({ behavior: smooth && !reduceMotion ? "smooth" : "instant" });
    if (el.id === "main") {           // skip link: move keyboard focus too
      el.setAttribute("tabindex", "-1");
      el.focus({ preventScroll: true });
    }
  };
  if (location.hash) {
    const target = document.getElementById(location.hash.slice(1));
    history.replaceState(null, "", location.pathname + location.search);
    if (target) addEventListener("load", () => scrollToEl(target, false), { once: true });
    else window.scrollTo(0, 0);
  }
  document.addEventListener("click", (e) => {
    const a = e.target.closest('a[href^="#"]');
    if (!a) return;
    const id = a.getAttribute("href").slice(1);
    const target = id ? document.getElementById(id) : null;
    if (!target) return;
    e.preventDefault();
    closeNav();
    scrollToEl(target, true);
  });

  // Reveal on scroll
  const items = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.12 });
    items.forEach((el) => {
      const sib = el.parentElement ? [...el.parentElement.children].filter((c) => c.classList.contains("reveal")) : [];
      el.style.setProperty("--d", `${Math.min(sib.indexOf(el), 5) * 70}ms`);
      io.observe(el);
    });
  } else {
    items.forEach((el) => el.classList.add("in"));
  }

  // Mobile navigation
  const toggle = document.querySelector(".nav__toggle");
  const nav = document.getElementById("site-nav");
  function closeNav() {
    if (!toggle || toggle.getAttribute("aria-expanded") !== "true") return;
    toggle.setAttribute("aria-expanded", "false");
    toggle.setAttribute("aria-label", toggle.dataset.openLabel);
    toggle.querySelector("i").className = "ph ph-list";
    document.body.classList.remove("nav-open");
  }
  if (toggle && nav) {
    toggle.addEventListener("click", () => {
      if (toggle.getAttribute("aria-expanded") === "true") return closeNav();
      toggle.setAttribute("aria-expanded", "true");
      toggle.setAttribute("aria-label", toggle.dataset.closeLabel);
      toggle.querySelector("i").className = "ph ph-x";
      document.body.classList.add("nav-open");
      nav.querySelector("a")?.focus();
    });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && document.body.classList.contains("nav-open")) { closeNav(); toggle.focus(); } });
    matchMedia("(min-width: 1081px)").addEventListener("change", closeNav);
  }

  // Language menu: custom dropdown that always opens below the button
  const lang = document.querySelector("[data-lang]");
  if (lang) {
    const btn = lang.querySelector(".lang__btn");
    const menu = lang.querySelector(".lang__menu");
    const links = [...menu.querySelectorAll("a")];
    const setOpen = (open) => {
      btn.setAttribute("aria-expanded", String(open));
      menu.hidden = !open;
      if (open) { closeNav(); (menu.querySelector("[aria-current]") || links[0]).focus(); }
    };
    btn.addEventListener("click", () => setOpen(menu.hidden));
    document.addEventListener("click", (e) => { if (!lang.contains(e.target)) setOpen(false); });
    lang.addEventListener("keydown", (e) => {
      if (e.key === "Escape") { setOpen(false); btn.focus(); }
      if (menu.hidden || !["ArrowDown", "ArrowUp"].includes(e.key)) return;
      e.preventDefault();
      const i = links.indexOf(document.activeElement);
      links[(i + (e.key === "ArrowDown" ? 1 : -1) + links.length) % links.length].focus();
    });
    links.forEach((a) => a.addEventListener("click", (e) => {
      e.preventDefault();
      try { localStorage.setItem("lang", a.dataset.code); } catch (_) {}
      location.href = a.getAttribute("href");
    }));
  }

  // Map: OpenStreetMap is loaded only after the visitor clicks (no third-party request before consent)
  document.querySelectorAll("[data-map-src]").forEach((box) => {
    box.querySelector("button")?.addEventListener("click", () => {
      const f = document.createElement("iframe");
      f.src = box.dataset.mapSrc;
      f.title = box.dataset.mapTitle;
      f.loading = "lazy";
      box.replaceChildren(f);
    });
  });

  // Investor pack form.
  // With data-endpoint set (config.json "form_endpoint", e.g. a Formspree URL) it posts JSON;
  // without it, it falls back to opening the visitor's mail client.
  const form = document.getElementById("pack-form");
  if (!form) return;
  const d = form.dataset;
  const status = form.querySelector(".form__status");
  const submitBtn = form.querySelector('button[type="submit"]');
  const setErr = (input, msg) => {
    const field = input.closest(".field");
    field.classList.toggle("invalid", !!msg);
    field.querySelector(".err").textContent = msg || "";
    input.setAttribute("aria-invalid", msg ? "true" : "false");
  };
  const setStatus = (msg, kind) => {
    status.textContent = msg;
    status.dataset.kind = kind || "";
  };
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const f = form.elements;
    let ok = true;
    const name = f.name.value.trim();
    const email = f.email.value.trim();
    setErr(f.name, name ? "" : d.errRequired); ok = ok && !!name;
    const emailOk = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    setErr(f.email, !email ? d.errRequired : emailOk ? "" : d.errEmail); ok = ok && emailOk;
    setErr(f.consent, f.consent.checked ? "" : d.errConsent); ok = ok && f.consent.checked;
    if (!ok) { form.querySelector(".invalid input")?.focus(); return; }
    if (f.website.value) return; // honeypot filled: silently drop bots

    const data = {
      name,
      company: f.company.value.trim(),
      email,
      country: f.country.value.trim(),
      ticket: f.range.value,
      message: f.message.value.trim(),
      language: document.documentElement.lang,
      _subject: d.subject,
    };

    if (!d.endpoint) {
      const body = [
        `Name: ${data.name}`, `Company: ${data.company}`, `Email: ${data.email}`,
        `Country: ${data.country}`, `Ticket: ${data.ticket}`, "", data.message, "", `Language: ${data.language}`,
      ].join("\n");
      location.href = `mailto:${d.email}?subject=${encodeURIComponent(d.subject)}&body=${encodeURIComponent(body)}`;
      setStatus(d.ok, "ok");
      return;
    }

    submitBtn.disabled = true;
    setStatus(d.sending, "busy");
    try {
      const res = await fetch(d.endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(data),
      });
      if (!res.ok) throw new Error(String(res.status));
      form.reset();
      setStatus(d.sent, "ok");
    } catch (_) {
      setStatus(d.error, "error");
    } finally {
      submitBtn.disabled = false;
    }
  });
})();
