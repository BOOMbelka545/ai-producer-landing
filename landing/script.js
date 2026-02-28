const UTM_STORAGE_KEY = "landing_utm_v1";
const PENDING_STORAGE_KEY = "landing_pending_leads_v1";
const UTM_KEYS = ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"];

const EVENTS = {
  HERO_CTA_CLICK: "hero_cta_click",
  FORM_START: "form_start",
  FORM_SUBMIT_SUCCESS: "form_submit_success",
  FORM_SUBMIT_ERROR: "form_submit_error",
};

const form = document.getElementById("lead-form");
const statusNode = document.getElementById("form-status");
const seatsNode = document.getElementById("seats-left");

let formStartTracked = false;

document.body.classList.add("js-enhanced");

function safeParseJSON(raw, fallback) {
  if (!raw) return fallback;
  try {
    return JSON.parse(raw);
  } catch {
    return fallback;
  }
}

function trackEvent(eventName, properties = {}) {
  // TODO: replace this hook with production analytics wiring (e.g. Mixpanel) in phase 2.
  if (window.mixpanel && typeof window.mixpanel.track === "function") {
    window.mixpanel.track(eventName, properties);
    return;
  }

  // TODO: remove console hook when analytics is connected.
  console.info("[analytics TODO]", eventName, properties);
}

function readStoredUtm() {
  return safeParseJSON(localStorage.getItem(UTM_STORAGE_KEY), {});
}

function readUtmFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const parsed = {};

  UTM_KEYS.forEach((key) => {
    const value = params.get(key);
    if (value) parsed[key] = value;
  });

  return parsed;
}

function persistUtm(utmValues) {
  localStorage.setItem(UTM_STORAGE_KEY, JSON.stringify(utmValues));
}

function initUtm() {
  const stored = readStoredUtm();
  const fromUrl = readUtmFromUrl();
  const merged = { ...stored, ...fromUrl };

  if (Object.keys(merged).length > 0) {
    persistUtm(merged);
  }

  return merged;
}

function fillHiddenFields(utmValues) {
  if (!form) return;

  UTM_KEYS.forEach((key) => {
    const input = form.querySelector(`input[name="${key}"]`);
    if (input) input.value = utmValues[key] || "";
  });

  const landingPageField = form.querySelector('input[name="landing_page"]');
  if (landingPageField) landingPageField.value = window.location.href;

  const referrerField = form.querySelector('input[name="referrer"]');
  if (referrerField) referrerField.value = document.referrer || "direct";
}

function updateSeatsCounter() {
  if (!seatsNode) return;
  const seats = 24 + Math.floor(Math.random() * 7);
  seatsNode.textContent = String(seats);
}

function initReveal() {
  const revealItems = document.querySelectorAll(".reveal");

  if (!("IntersectionObserver" in window)) {
    revealItems.forEach((item) => item.classList.add("is-visible"));
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        const delay = Number(entry.target.dataset.delay || 0);
        window.setTimeout(() => entry.target.classList.add("is-visible"), delay);
        observer.unobserve(entry.target);
      });
    },
    { threshold: 0.15 }
  );

  revealItems.forEach((item) => observer.observe(item));
}

function clearFieldErrors() {
  if (!form) return;
  const fields = ["email", "niche", "audience_size"];

  fields.forEach((fieldName) => {
    const input = form.querySelector(`[name="${fieldName}"]`);
    const error = document.getElementById(
      fieldName === "audience_size" ? "audience-error" : `${fieldName}-error`
    );

    if (input) input.setAttribute("aria-invalid", "false");
    if (error) error.textContent = "";
  });
}

function setFieldError(fieldName, message) {
  if (!form) return;

  const input = form.querySelector(`[name="${fieldName}"]`);
  const errorId = fieldName === "audience_size" ? "audience-error" : `${fieldName}-error`;
  const error = document.getElementById(errorId);

  if (input) input.setAttribute("aria-invalid", "true");
  if (error) error.textContent = message;
}

function validatePayload(payload) {
  const errors = {};
  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  if (!payload.email || !emailPattern.test(payload.email)) {
    errors.email = "Введите корректный email.";
  }

  if (!payload.niche) {
    errors.niche = "Выберите нишу.";
  }

  if (!payload.audience_size) {
    errors.audience_size = "Выберите размер аудитории.";
  }

  return errors;
}

function setStatus(message, type = "neutral", allowHtml = false) {
  if (!statusNode) return;

  statusNode.classList.remove("is-success", "is-error");
  if (type === "success") statusNode.classList.add("is-success");
  if (type === "error") statusNode.classList.add("is-error");

  if (allowHtml) {
    statusNode.innerHTML = message;
  } else {
    statusNode.textContent = message;
  }
}

function readPendingLeads() {
  return safeParseJSON(localStorage.getItem(PENDING_STORAGE_KEY), []);
}

function savePendingLeads(items) {
  localStorage.setItem(PENDING_STORAGE_KEY, JSON.stringify(items));
}

function queueLead(payload, reason) {
  const pending = readPendingLeads();
  pending.push({ payload, reason, queued_at: new Date().toISOString() });
  savePendingLeads(pending);
}

function getSubmitEndpoint() {
  if (!form) return "";
  return (form.dataset.endpoint || form.getAttribute("action") || "").trim();
}

async function postLead(endpoint, payload) {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 8000);

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(`http_${response.status}`);
    }
  } finally {
    window.clearTimeout(timeout);
  }
}

async function flushQueuedLeads() {
  const endpoint = getSubmitEndpoint();
  if (!endpoint) return;

  const pending = readPendingLeads();
  if (pending.length === 0) return;

  const stillPending = [];

  // Replay queued leads if endpoint became available.
  for (const entry of pending) {
    try {
      await postLead(endpoint, entry.payload);
    } catch {
      stillPending.push(entry);
    }
  }

  savePendingLeads(stillPending);
}

function buildFallbackMailto(payload) {
  const subject = encodeURIComponent("AI Producer Early Access Lead");
  const body = encodeURIComponent(
    [
      `Email: ${payload.email}`,
      `Niche: ${payload.niche}`,
      `Audience: ${payload.audience_size}`,
      `UTM source: ${payload.utm_source || "-"}`,
      `UTM medium: ${payload.utm_medium || "-"}`,
      `UTM campaign: ${payload.utm_campaign || "-"}`,
    ].join("\n")
  );

  return `mailto:early-access@ai-producer.app?subject=${subject}&body=${body}`;
}

function serializeForm() {
  const formData = new FormData(form);
  const payload = Object.fromEntries(formData.entries());
  payload.submitted_at = new Date().toISOString();
  payload.page_path = window.location.pathname;
  return payload;
}

function bindHeroTracking() {
  const ctaNodes = document.querySelectorAll('[data-track="hero-cta"]');
  ctaNodes.forEach((node) => {
    node.addEventListener("click", () => {
      trackEvent(EVENTS.HERO_CTA_CLICK, {
        placement: node.textContent.trim(),
      });
    });
  });
}

function bindFormStartTracking() {
  if (!form) return;

  const onStart = () => {
    if (formStartTracked) return;
    formStartTracked = true;
    trackEvent(EVENTS.FORM_START, { source: "lead_form" });
  };

  form.addEventListener("focusin", onStart);
  form.addEventListener("input", onStart);
}

function focusFirstInvalidField(errors) {
  const firstInvalidName = Object.keys(errors)[0];
  if (!firstInvalidName || !form) return;

  const field = form.querySelector(`[name="${firstInvalidName}"]`);
  if (field) field.focus();
}

function setSubmitButtonLoading(isLoading) {
  if (!form) return;
  const submitButton = form.querySelector('button[type="submit"]');
  if (!submitButton) return;

  submitButton.disabled = isLoading;
  submitButton.textContent = isLoading ? "Отправляем..." : "Встать в waitlist";
}

async function handleFormSubmit(event) {
  event.preventDefault();

  clearFieldErrors();
  setStatus("");

  const payload = serializeForm();
  const errors = validatePayload(payload);

  if (Object.keys(errors).length > 0) {
    Object.entries(errors).forEach(([fieldName, message]) => setFieldError(fieldName, message));
    focusFirstInvalidField(errors);
    setStatus("Проверьте поля формы и попробуйте снова.", "error");
    trackEvent(EVENTS.FORM_SUBMIT_ERROR, {
      reason: "validation_error",
      fields: Object.keys(errors).join(","),
    });
    return;
  }

  setSubmitButtonLoading(true);

  const endpoint = getSubmitEndpoint();

  try {
    if (!endpoint) {
      throw new Error("endpoint_missing");
    }

    await postLead(endpoint, payload);

    setStatus("Заявка принята. Проверьте email: мы отправим доступ и следующие шаги.", "success");
    trackEvent(EVENTS.FORM_SUBMIT_SUCCESS, {
      niche: payload.niche,
      audience_size: payload.audience_size,
    });

    form.reset();
    fillHiddenFields(initUtm());
  } catch (error) {
    const reason = error instanceof Error ? error.message : "submit_failed";
    queueLead(payload, reason);

    const fallbackLink = buildFallbackMailto(payload);
    const fallbackMessage = `Сервис временно недоступен. Мы сохранили заявку локально. Можно отправить вручную: <a href="${fallbackLink}">через email</a>.`;
    setStatus(fallbackMessage, "error", true);

    trackEvent(EVENTS.FORM_SUBMIT_ERROR, {
      reason,
      fallback: "local_queue+mailto",
    });
  } finally {
    setSubmitButtonLoading(false);
  }
}

function init() {
  initReveal();
  updateSeatsCounter();
  bindHeroTracking();

  if (!form) return;

  fillHiddenFields(initUtm());
  bindFormStartTracking();
  form.addEventListener("submit", handleFormSubmit);
  flushQueuedLeads();
}

init();
