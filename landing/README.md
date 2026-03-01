# Landing Conversion Page v1

Локальный конверсионный лендинг для сбора заявок на ранний доступ (lead capture).

## Файлы
- `index.html` — структура страницы и тексты.
- `styles.css` — визуальный стиль, адаптивность, фокус-стейты, анимации reveal/stagger.
- `script.js` — UTM capture, hidden fields, валидация, submit/fallback, tracking hooks.

## Быстрый запуск локально
1. Перейдите в папку:
   ```bash
   cd /Users/leo/Desktop/Production/landing
   ```
2. Запустите landing-сервер с сохранением waitlist:
   ```bash
   python3 server.py
   ```
3. Откройте в браузере:
   - `http://127.0.0.1:8081`

Если нужен только статика-режим (без сохранения email), можно запустить:
   ```bash
   python3 -m http.server 8080
   ```

Можно тестировать UTM так:
- `http://localhost:8080/?utm_source=meta&utm_medium=cpc&utm_campaign=early_access&utm_term=creator&utm_content=ad_a`

## Где менять тексты и CTA
- Hero оффер/подзаголовок: `index.html`, секция `.hero`.
- Primary CTA (верх/низ): `index.html`, кнопки с `data-track="hero-cta"`.
- Problem -> Solution, Steps, Social proof, Offer, FAQ: соответствующие секции `index.html`.
- Scarcity дедлайн/места:
  - текст дедлайна: `#deadline-date` в `index.html`;
  - динамическое число мест: `updateSeatsCounter()` в `script.js`.

## Подключение реального submit endpoint
По умолчанию форма смотрит на `action`/`data-endpoint`:
```html
<form id="lead-form" action="/api/v1/landing/lead" data-endpoint="/api/v1/landing/lead" ...>
```

Чтобы подключить production endpoint:
1. Измените `action` и `data-endpoint` у формы в `index.html`.
2. Убедитесь, что endpoint принимает `POST` JSON с полями:
   - `email`, `niche`, `audience_size`
   - `utm_source`, `utm_medium`, `utm_campaign`, `utm_term`, `utm_content`
   - `landing_page`, `referrer`, `submitted_at`, `page_path`
3. При CORS/ошибках submit включится graceful fallback:
   - lead сохраняется в localStorage (`landing_pending_leads_v1`),
   - пользователю показывается mailto-ссылка для ручной отправки.

## Analytics hooks (минимум v1)
В `script.js` подготовлены события:
- `hero_cta_click`
- `form_start`
- `form_submit_success`
- `form_submit_error`

Сейчас это TODO hooks: при отсутствии Mixpanel/analytics события логируются в `console.info`.
Для production аналитики замените `trackEvent()` на ваш клиент (например Mixpanel SDK).

## Где хранится waitlist (JSON)
- Локальный waitlist сохраняется в:
  - `/Users/leo/Desktop/Production/landing/data/waitlist.json`
- Формат: JSON array (`[{ email, source, submitted_at }, ...]`), можно читать напрямую любым редактором.
