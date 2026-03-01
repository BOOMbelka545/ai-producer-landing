const anchors = document.querySelectorAll('a[href^="#"]');
const openModalButtons = document.querySelectorAll('[data-open-beta-modal="true"]');
const modal = document.getElementById("beta-modal");
const closeModalButtons = document.querySelectorAll('[data-close-beta-modal="true"]');
const emailForm = document.getElementById("beta-email-form");
const emailInput = document.getElementById("beta-email");
const modalStatus = document.getElementById("beta-modal-status");
const WAITLIST_ENDPOINT = "/api/waitlist";
const ANALYTICS_DEBUG_ENDPOINT = "/api/analytics-debug";

const systemSection = document.querySelector(".system");
const trendPath = document.querySelector(".trend-line__path");
const trendDot = document.querySelector(".trend-dot");
const trendGlow = document.querySelector(".trend-glow");

const TOKENS = {
  dev: (document.querySelector('meta[name="mixpanel-token-dev"]')?.content || "").trim(),
  stage: (document.querySelector('meta[name="mixpanel-token-stage"]')?.content || "").trim(),
  prod: (document.querySelector('meta[name="mixpanel-token-prod"]')?.content || "").trim(),
};

const SESSION_KEY = "landing_session_id_v1";
const UTM_KEY = "landing_utm_v1";
const SECTION_OBSERVED = ["hero", "problem", "how-it-works", "reviews", "final-cta"];
const SCROLL_DEPTH_STEPS = [25, 50, 75, 100];

const analyticsState = {
  pageStartTs: Date.now(),
  sessionId: getSessionId(),
  utm: getUtmData(),
  country: "unknown",
  sentDepth: new Set(),
  sentSections: new Set(),
  engagedTimerDone: false,
  engagedScrollDone: false,
  engagedSentStates: new Set(),
  mixpanelReady: false,
  pendingEvents: [],
  modalOpenTs: null,
  lastCtaId: "unknown",
};

function resolveMixpanelToken() {
  const host = window.location.hostname.toLowerCase();

  if (host === "localhost" || host === "127.0.0.1" || host.endsWith(".local")) {
    return TOKENS.stage || TOKENS.dev;
  }

  if (host.includes("stage") || host.includes("staging")) {
    return TOKENS.stage || TOKENS.dev;
  }

  return TOKENS.prod || TOKENS.stage || TOKENS.dev;
}

initMixpanelWithRetry();
fetchGeoCountry();
trackEvent("landing_view", {});
setupSectionTracking();
setupScrollDepthTracking();
setupEngagedVisitTracking();
setupScrollTrend();
setupCtaTracking();
setupFooterLinkTracking();

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function getDeviceType() {
  const width = window.innerWidth;
  if (width < 768) return "mobile";
  if (width < 1024) return "tablet";
  return "desktop";
}

function createSessionId() {
  if (window.crypto && crypto.randomUUID) {
    return crypto.randomUUID();
  }

  return `sess_${Date.now()}_${Math.random().toString(36).slice(2, 12)}`;
}

function getSessionId() {
  const existing = localStorage.getItem(SESSION_KEY);
  if (existing) return existing;

  const sessionId = createSessionId();
  localStorage.setItem(SESSION_KEY, sessionId);
  return sessionId;
}

function parseUtmFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return {
    utm_source: params.get("utm_source") || "",
    utm_medium: params.get("utm_medium") || "",
    utm_campaign: params.get("utm_campaign") || "",
    utm_term: params.get("utm_term") || "",
    utm_content: params.get("utm_content") || "",
  };
}

function getUtmData() {
  const parsed = parseUtmFromUrl();
  const hasUtm = Object.values(parsed).some(Boolean);

  if (hasUtm) {
    localStorage.setItem(UTM_KEY, JSON.stringify(parsed));
    return parsed;
  }

  try {
    const stored = JSON.parse(localStorage.getItem(UTM_KEY) || "{}");
    return {
      utm_source: stored.utm_source || "",
      utm_medium: stored.utm_medium || "",
      utm_campaign: stored.utm_campaign || "",
      utm_term: stored.utm_term || "",
      utm_content: stored.utm_content || "",
    };
  } catch {
    return parsed;
  }
}

function initMixpanel() {
  const mixpanelToken = resolveMixpanelToken();

  if (!mixpanelToken || !window.mixpanel || typeof window.mixpanel.init !== "function") {
    return false;
  }

  window.mixpanel.init(mixpanelToken, {
    track_pageview: false,
    persistence: "localStorage",
  });

  analyticsState.mixpanelReady = true;
  flushPendingEvents();
  console.info("[analytics] mixpanel initialized", { host: window.location.hostname, token: mixpanelToken.slice(0, 6) + "***" });
  return true;
}

function initMixpanelWithRetry() {
  const maxAttempts = 20;
  let attempts = 0;

  const tryInit = () => {
    attempts += 1;
    const ready = initMixpanel();
    if (ready) return;

    if (attempts < maxAttempts) {
      window.setTimeout(tryInit, 250);
    } else {
      console.warn("[analytics] mixpanel init failed after retries; events will stay in console only");
    }
  };

  tryInit();
}

function flushPendingEvents() {
  if (!analyticsState.mixpanelReady || !window.mixpanel || typeof window.mixpanel.track !== "function") {
    return;
  }

  while (analyticsState.pendingEvents.length > 0) {
    const queued = analyticsState.pendingEvents.shift();
    if (!queued) break;
    window.mixpanel.track(queued.eventName, queued.props);
  }
}

function getCommonProps() {
  const timeOnPageSec = Math.round((Date.now() - analyticsState.pageStartTs) / 1000);

  return {
    session_id: analyticsState.sessionId,
    page_url: window.location.href,
    page_path: window.location.pathname,
    referrer: document.referrer || "direct",
    device_type: getDeviceType(),
    viewport_w: window.innerWidth,
    viewport_h: window.innerHeight,
    time_on_page_sec: timeOnPageSec,
    country: analyticsState.country,
    ...analyticsState.utm,
  };
}

async function fetchGeoCountry() {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), 2500);

  try {
    const response = await fetch("https://ipapi.co/json/", {
      method: "GET",
      signal: controller.signal,
    });
    if (!response.ok) return;

    const payload = await response.json();
    const code = String(payload.country_code || payload.country || "").trim();
    if (code) analyticsState.country = code.toUpperCase();
  } catch {
    // Keep "unknown" fallback.
  } finally {
    window.clearTimeout(timeoutId);
  }
}

function trackEvent(eventName, payload) {
  const props = {
    ...getCommonProps(),
    ...payload,
  };

  if (analyticsState.mixpanelReady && window.mixpanel && typeof window.mixpanel.track === "function") {
    window.mixpanel.track(eventName, props);
  } else {
    analyticsState.pendingEvents.push({ eventName, props });
  }

  sendAnalyticsDebug(eventName, props);

  // Keep local visibility during implementation.
  console.info("[track]", eventName, props);
}

function sendAnalyticsDebug(eventName, props) {
  const body = JSON.stringify({
    event_name: eventName,
    props,
  });

  fetch(ANALYTICS_DEBUG_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
    keepalive: true,
  }).catch(() => {
    // Ignore debug endpoint errors to avoid impacting user flow.
  });
}

function setupCtaTracking() {
  openModalButtons.forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();

      const ctaId = button.dataset.ctaId || "unknown";
      const section = button.dataset.ctaSection || "unknown";
      analyticsState.lastCtaId = ctaId;

      trackEvent("cta_click", {
        cta_id: ctaId,
        cta_text: button.textContent.trim(),
        section,
        scroll_depth_pct: getCurrentScrollDepth(),
      });

      analyticsState.modalOpenTs = Date.now();
      trackEvent("waitlist_modal_open", {
        source_cta_id: ctaId,
        section,
        scroll_depth_pct: getCurrentScrollDepth(),
      });

      openModal();
    });
  });
}

function setupFooterLinkTracking() {
  document.querySelectorAll("[data-link-name]").forEach((link) => {
    link.addEventListener("click", () => {
      trackEvent("external_link_click", {
        link_name: link.dataset.linkName,
      });
    });
  });
}

function setupSectionTracking() {
  if (!("IntersectionObserver" in window)) return;

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;

        const sectionId = entry.target.id;
        if (!sectionId || analyticsState.sentSections.has(sectionId)) return;

        analyticsState.sentSections.add(sectionId);
        trackEvent("section_view", { section_id: sectionId });
      });
    },
    { threshold: 0.35 }
  );

  SECTION_OBSERVED.forEach((id) => {
    const section = document.getElementById(id);
    if (section) observer.observe(section);
  });
}

function getCurrentScrollDepth() {
  const doc = document.documentElement;
  const scrollTop = window.scrollY || doc.scrollTop;
  const scrollHeight = doc.scrollHeight - window.innerHeight;
  if (scrollHeight <= 0) return 100;

  return Math.round((scrollTop / scrollHeight) * 100);
}

function setupScrollDepthTracking() {
  const handleScroll = () => {
    const depth = getCurrentScrollDepth();

    SCROLL_DEPTH_STEPS.forEach((step) => {
      if (depth >= step && !analyticsState.sentDepth.has(step)) {
        analyticsState.sentDepth.add(step);
        trackEvent("scroll_depth_reached", { depth: String(step) });

        if (step >= 75) {
          analyticsState.engagedScrollDone = true;
          emitEngagedVisit();
        }
      }
    });
  };

  window.addEventListener("scroll", handleScroll, { passive: true });
  handleScroll();
}

function setupEngagedVisitTracking() {
  window.setTimeout(() => {
    analyticsState.engagedTimerDone = true;
    emitEngagedVisit();
  }, 30000);
}

function emitEngagedVisit() {
  const timer = analyticsState.engagedTimerDone;
  const scroll = analyticsState.engagedScrollDone;

  if (!timer && !scroll) return;

  let state = "";
  if (timer && scroll) state = "both";
  else if (timer) state = "time_30s";
  else state = "scroll_75";

  if (analyticsState.engagedSentStates.has(state)) return;
  analyticsState.engagedSentStates.add(state);

  trackEvent("engaged_visit", { engagement_type: state });
}

function openModal() {
  if (!modal) return;
  modal.hidden = false;
  document.body.classList.add("modal-open");

  if (emailInput) {
    window.setTimeout(() => emailInput.focus(), 0);
  }
}

function closeModal() {
  if (!modal) return;
  modal.hidden = true;
  document.body.classList.remove("modal-open");

  if (emailForm) {
    emailForm.reset();
  }

  if (modalStatus) {
    modalStatus.textContent = "";
  }
}

anchors.forEach((anchor) => {
  anchor.addEventListener("click", (event) => {
    const href = anchor.getAttribute("href");
    if (!href || href === "#") return;

    const target = document.querySelector(href);
    if (!target) return;

    event.preventDefault();
    target.scrollIntoView({ behavior: "smooth", block: "start" });
  });
});

closeModalButtons.forEach((button) => {
  button.addEventListener("click", closeModal);
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && modal && !modal.hidden) {
    closeModal();
  }
});

async function sha256(input) {
  const enc = new TextEncoder();
  const data = enc.encode(input);
  const hash = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(hash)).map((b) => b.toString(16).padStart(2, "0")).join("");
}

function getEmailDomain(email) {
  const parts = email.split("@");
  return parts.length === 2 ? parts[1].toLowerCase() : "";
}

if (emailForm && emailInput && modalStatus) {
  emailForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = emailInput.value.trim();
    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    const sourceCtaId = analyticsState.lastCtaId || "unknown";

    trackEvent("waitlist_email_submit_attempt", {
      source_cta_id: sourceCtaId,
      email,
      email_domain: getEmailDomain(email),
      time_from_modal_open_sec: analyticsState.modalOpenTs
        ? Math.round((Date.now() - analyticsState.modalOpenTs) / 1000)
        : null,
    });

    if (!emailPattern.test(email)) {
      modalStatus.textContent = "Please enter a valid email address.";
      modalStatus.style.color = "#ff9aab";
      emailInput.focus();

      trackEvent("waitlist_email_submit_error", {
        source_cta_id: sourceCtaId,
        email,
        error_type: "validation",
        error_message: "invalid_email",
      });
      return;
    }

    try {
      const response = await fetch(WAITLIST_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email,
          source: "landing_modal",
          submitted_at: new Date().toISOString(),
        }),
      });

      if (!response.ok) {
        trackEvent("waitlist_email_submit_error", {
          source_cta_id: sourceCtaId,
          email,
          error_type: "server",
          http_status: response.status,
          error_message: "request_failed",
        });
        throw new Error("request_failed");
      }

      const emailHash = await sha256(email.toLowerCase());
      const leadId = emailHash.slice(0, 16);

      if (analyticsState.mixpanelReady && window.mixpanel && typeof window.mixpanel.identify === "function") {
        window.mixpanel.identify(emailHash);
      }

      trackEvent("waitlist_email_submit_success", {
        source_cta_id: sourceCtaId,
        email,
        email_domain: getEmailDomain(email),
        submit_method: "api",
        lead_id: leadId,
      });

      modalStatus.textContent = "Thanks. You're on the waitlist. We'll notify you as soon as the App Store release is live.";
      modalStatus.style.color = "#98fdbe";
      emailForm.reset();
    } catch {
      modalStatus.textContent = "Save failed. Please try again in a moment.";
      modalStatus.style.color = "#ff9aab";

      trackEvent("waitlist_email_submit_error", {
        source_cta_id: sourceCtaId,
        email,
        error_type: "network",
        error_message: "network_or_runtime_error",
      });
    }
  });
}

function setupScrollTrend() {
  if (!systemSection || !trendPath || !trendDot || !trendGlow) return;

  const svg = trendPath.ownerSVGElement;
  if (!svg || !svg.viewBox || !svg.viewBox.baseVal) return;

  const totalLength = trendPath.getTotalLength();
  const viewBox = svg.viewBox.baseVal;

  trendPath.style.strokeDasharray = `${totalLength}`;

  const updateByProgress = (progress) => {
    const safeProgress = clamp(progress, 0, 1);
    const drawLength = totalLength * safeProgress;
    trendPath.style.strokeDashoffset = `${totalLength - drawLength}`;

    const point = trendPath.getPointAtLength(drawLength);
    const xPercent = (point.x / viewBox.width) * 100;
    const yPercent = (point.y / viewBox.height) * 100;

    trendDot.style.left = `${xPercent}%`;
    trendDot.style.top = `${yPercent}%`;
    trendGlow.style.left = `${xPercent}%`;
    trendGlow.style.top = `${yPercent}%`;

    trendDot.style.opacity = safeProgress < 0.05 ? "0" : "1";
    trendGlow.style.opacity = safeProgress < 0.05 ? "0" : `${0.32 + safeProgress * 0.45}`;
  };

  let ticking = false;

  const onScroll = () => {
    if (ticking) return;
    ticking = true;

    window.requestAnimationFrame(() => {
      const rect = systemSection.getBoundingClientRect();
      const start = window.innerHeight * 0.9;
      const end = window.innerHeight * 0.2;
      const rawProgress = (start - rect.top) / (start - end);
      updateByProgress(clamp(rawProgress, 0, 1));
      ticking = false;
    });
  };

  updateByProgress(0);
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll);
  onScroll();
}
