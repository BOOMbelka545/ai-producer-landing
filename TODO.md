# ProdApp MVP TODO (Этапы + Эпики)

Last update: 2026-02-28
Owner: Leo + Codex

Статусы:
- `[x]` done
- `[~]` in progress
- `[ ]` todo
- `[!]` blocked

## Этап 0: Scope + архитектура (19–21 фев)
- [x] Зафиксировать core MVP фичи.
- [x] Описать API-контракт (OpenAPI v1).
- [x] Описать ERD/схему БД v1.
- [x] Разделить проект на два репозитория (`ai-producer-ios`, `ai-producer-backend`).
- [~] CI/CD и окружения (dev/stage/prod) подняты частично.
- [x] Эпик `codex/epic-backend-auth` завершен.
- [x] Эпик `codex/epic-ios-auth-onboarding` завершен.

## Этап 1: Каркас продукта (22–28 фев)
- [x] Эпик `codex/epic-ios-dashboard-core` завершен.
- [x] Эпик `codex/epic-calendar-reminders` завершен.
- [x] Эпик `codex/epic-backend-analysis-core` закрыт по минимальному API-контракту для iOS.
- [x] Эпик `codex/epic-backend-mvp-usable` завершен.
- [x] Эпик `codex/epic-ios-full-design-implementation` завершен.
- [x] Эпик `codex/epic-ios-full-design-implementation` завершен: основной UI/flow реализован, `MVP_STUB`/`MVP_HARDCODED` промаркированы, build app target green.
- [x] Backend совместим с iOS по endpoints:
- [x] `POST /api/v1/analysis/video`
- [x] `GET /api/v1/analysis/{analysis_id}`
- [x] `GET /api/v1/calendar/posts`
- [x] `POST /api/v1/calendar/posts`
- [x] `PUT /api/v1/calendar/posts/{post_id}`
- [x] Эпик `codex/epic-backend-mvp-usable`: backend stabilized for current iOS flow (`auth/analysis/calendar`), тесты green, OpenAPI/docs актуализированы.
- [~] Временные backend-заглушки явно промаркированы (`MVP_STUB`/`MVP_HARDCODED`) и задокументированы в `ai-producer-backend/docs/backend/mvp-stubs.md`.
- [x] Эпик `codex/epic-backend-domain-completion` завершен.
- [x] Backend: `users/projects/generation jobs/billing placeholders` довести до полного состава этапа.
- [x] Эпик `codex/epic-infra-staging-foundation` завершен.
- [x] Инфра этапа: Postgres/Redis/storage/monitoring на staging.
- [x] `ai-producer-backend`: env templates (`.env.dev.example`, `.env.stage.example`) + расширенные infra переменные.
- [x] `ai-producer-backend`: readiness/metrics/logging/Sentry hook baseline.
- [x] `ai-producer-backend`: reproducible staging stack (`docker-compose.staging.yml`, Postgres/Redis/MinIO/Prometheus/Grafana).
- [x] `ai-producer-backend`: CI staging smoke (config + migrations).
- [x] `ai-producer-backend`: runbook + incident quick checks.
- [x] Финальная валидация `docker compose up` на машине с Docker и закрытие эпика.

## Этап 2: Core value фичи (1–8 мар)
- [ ] AI-генерация контент-идей/сценариев/планов (production-версия).
- [x] Эпик `codex/epic-backend-generation-history` завершен.
- [x] История генераций (backend MVP): сохранение, список, детализация, редактирование.
- [x] Эпик `codex/epic-backend-ai-pipeline-retries` завершен.
- [x] Очереди и ретраи на backend для AI pipeline (mock provider, worker, idempotency, retry policy).
- [ ] Follow-up после `codex/epic-backend-mvp-usable`: заменить `MVP_STUB`/`MVP_HARDCODED` реализации из `ai-producer-backend/docs/backend/mvp-stubs.md`.
- [ ] Отдельная задача (tech debt): `codex/epic-backend-mvp-stubs-replacement`.
- [ ] В рамках `codex/epic-backend-mvp-stubs-replacement`: заменить нереалистичный analysis output на реальный async AI pipeline без ломки текущего iOS-контракта.
- [ ] В рамках `codex/epic-backend-mvp-stubs-replacement`: внедрить social connect flow (provider-backed integrations) и убрать synthetic integration fallback.
- [ ] Follow-up после `codex/epic-backend-generation-history`: вынести `generation-jobs` legacy endpoints в deprecation plan и синхронизировать iOS-клиент на `/api/v1/generations`.
- [ ] Follow-up после `codex/epic-backend-generation-history`: добавить cursor pagination и фильтры (`project_id`, `status`) для истории генераций при росте объема данных.
- [ ] Follow-up после `codex/epic-backend-ai-pipeline-retries`: подключить реальный AI provider за `GenerationProvider` интерфейсом и добавить provider-level auth/secrets rotation.
- [ ] Follow-up после `codex/epic-backend-ai-pipeline-retries`: внедрить DLQ/операторские команды requeue для failed jobs.
- [ ] Follow-up после `codex/epic-backend-ai-pipeline-retries`: добавить расширенные метрики/трейсинг воркера (queue lag, retry cardinality, provider latency/error classes).

## Эпик: backend-ai-pipeline-retries
- [x] Статус: done
- [x] Репозиторий: `ai-producer-backend`
- [x] Ветка: `codex/epic-backend-ai-pipeline-retries`
- [x] Start: 2026-02-24
- [x] End: 2026-02-24
- [x] Реализовано:
- [x] `GenerationProvider` + `MockGenerationProvider` (детерминированный).
- [x] `GenerationJobService` с state machine, retry/backoff и классификацией ошибок.
- [x] Очередь задач (`ResilientGenerationJobQueue`: Redis + fallback in-memory) и worker (`app.workers.generation_jobs_worker`).
- [x] Idempotency key на `POST /api/v1/generation-jobs` + DB unique (`user_id`, `idempotency_key`).
- [x] Unit/integration/regression тесты green, docs/OpenAPI обновлены.

## Эпик: backend-generation-history
- [x] Статус: done
- [x] Репозиторий: `ai-producer-backend`
- [x] Ветка: `codex/epic-backend-generation-history`
- [x] Start: 2026-02-24
- [x] End: 2026-02-24
- [x] Реализовано:
- [x] `POST /api/v1/generations` (save)
- [x] `GET /api/v1/generations` (list + pagination/sorting)
- [x] `GET /api/v1/generations/{generation_id}` (detail)
- [x] `PATCH /api/v1/generations/{generation_id}` (edit)
- [x] Добавлены ownership checks, payload validation, тесты и обновлены docs/OpenAPI.

## Этап 3: Growth + retention (9–14 мар)
- [x] Эпик `codex/epic-analytics-crash` phase 1 (Mixpanel): done.
- [x] Эпик `codex/epic-landing-conversion-page-v1` завершен.
- [x] Mixpanel: внедрен abstraction-first слой (`AnalyticsService` + `Noop/Mixpanel`), MVP funnel schema и typed events в iOS.
- [~] Crash layer: `CrashReporter` оставлен в приложении в режиме `Noop` (Firebase Crashlytics вынесен в отдельный post-release follow-up эпик).
- [x] Проверка live telemetry: dev telemetry подтверждена в Mixpanel Live View (события шли в dev project; проблема была в просмотре prod workspace).
- [ ] Push-уведомления + reminders hardening.
- [ ] Remote Config для быстрых экспериментов.
- [ ] Paywall/подписка (если включаем монетизацию в MVP).

## Эпик: landing-conversion-page-v1
- [x] Статус: done
- [x] Репозиторий: `workspace / landing`
- [x] Ветка: `codex/epic-landing-conversion-page-v1`
- [x] Start: 2026-02-28
- [x] End: 2026-02-28
- [x] Реализовано:
- [x] Conversion-first лендинг в `/landing` с обязательными блоками: Hero, Problem -> Solution, How it works (3 шага), Social proof, Offer/Scarcity, FAQ, Final CTA.
- [x] Lead form: `email + niche + audience_size` + hidden UTM поля.
- [x] `script.js`: захват UTM из URL, сохранение в `localStorage`, гидрация hidden-полей формы.
- [x] `script.js`: клиентская валидация, analytics hooks (`hero_cta_click`, `form_start`, `form_submit_success`, `form_submit_error`) и graceful fallback submit (local queue + mailto fallback).
- [x] `README.md` для локального запуска, управления контентом и подключения реального submit endpoint.
- [ ] Follow-up phase 2: A/B тесты оффера/CTA/соцдоказательства (headline, proof density, CTA copy, form position).
- [ ] Follow-up phase 2: подключить real submit API + server-side валидацию + anti-spam.
- [ ] Follow-up phase 2: включить production analytics (Mixpanel/warehouse) и dashboard по funnel `landing_view -> cta_click -> form_start -> submit_success`.

## Этап 4: Стабилизация + релиз (15–21 мар)
- [ ] Тесты критичных флоу (backend + iOS).
- [ ] Багфикс-спринт.
- [ ] Перф/крэш-оптимизация.
- [ ] TestFlight beta.
- [ ] Release candidate.
- [ ] Отправка в App Store.
- [ ] Буфер review/reject/fix (22–26 мар).

## Эпик: bugfix-sweep-manual-qa
- [x] Статус: done
- [x] BUG-001: Sign Up падает с `The data couldn’t be read because it isn’t in the correct format` после создания аккаунта.
- [x] Статус: done
- [x] Severity: P1
- [x] Репозиторий: `ai-producer-ios`
- [x] Фикс: расширен date decoding в `BackendAPIClient` для ISO8601 с/без fractional seconds; добавлен regression test.
- [x] Доп.фикс: поддержан backend `created_at` без timezone (пример: `2026-02-21T23:19:36.807023`); добавлен regression test.
- [x] Дата фикса: 2026-02-22
- [x] Commit hash: `e93aad5`
- [x] Commit hash (follow-up): `89c1665`

## Эпик: ios-full-design-implementation
- [x] Статус: done
- [x] Репозиторий: `ai-producer-ios`
- [x] Ветка: `codex/epic-ios-full-design-implementation`
- [x] Реализованы основные экраны и состояния:
- [x] onboarding/auth flow (welcome/sign in/sign up/forgot password fallback)
- [x] dashboard (overview/processing/result/error/empty/loading)
- [x] calendar (month/week/list/create/edit)
- [x] profile/settings (account, settings toggles, connected accounts stub)
- [x] paywall screens (UI + routing flow через coordinator/sheet)
- [x] Flow-driven routing усилен:
- [x] `MainFlowCoordinator` управляет tab order + calendar editor route + paywall route
- [x] Порядок табов меняется через `tabOrder` без переписывания feature-экранов
- [x] MVP-заглушки промаркированы в коде (`MVP_STUB`/`MVP_HARDCODED`)
- [x] iOS app target собирается (`xcodebuild build`, simulator iPhone 17 / iOS 26.2)
- [!] Ограничение проверки:
- [!] `xcodebuild test`/`build-for-testing` падает на legacy test-target настройке (`Unable to find module dependency: 'AIProducer'`), не связано с текущими UI-правками и требует отдельного fix эпика для test target configuration.
- [x] Manual smoke для закрытия эпика принят в формате `build + critical flow verification` (детальный full UI pass вынесен в следующий stabilization epic).

## Сервисы по шагам
- [x] OpenAI API (базовая интеграция в плане).
- [x] Mixpanel выбран.
- [x] Firebase выбран.
- [x] Mixpanel подключен в код через `AnalyticsService` abstraction (Noop/Mixpanel + typed events).
- [~] Crashlytics deferred: в коде оставлен `CrashReporter` abstraction, текущая реализация — `NoopCrashReporter`; внедрение после публикации приложения.
- [ ] Adjust (только при старте paid UA).
- [ ] Sentry backend (рекомендуется до staging).

## На сегодня (операционный чеклист)
- [ ] Push backend ветки `codex/chore-backend-api-sync-and-setup-docs` (`efab441`).
- [ ] Push iOS ветки `codex/chore-ios-new-mac-setup-readme` (`88dcdc0`).
- [ ] Создать и смержить PR в обоих репозиториях.
- [ ] Обновить локальные `main` после merge.
- [!] Запустить iOS tests на конкретном simulator runtime в Xcode (в CLI не хватило concrete device).
