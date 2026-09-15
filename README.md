# Antigravity Pulse for Home Assistant

[![HACS validation](https://github.com/hehljo/hass-antigravity-usage/actions/workflows/validate.yaml/badge.svg)](https://github.com/hehljo/hass-antigravity-usage/actions/workflows/validate.yaml)
[![Hassfest](https://github.com/hehljo/hass-antigravity-usage/actions/workflows/hassfest.yaml/badge.svg)](https://github.com/hehljo/hass-antigravity-usage/actions/workflows/hassfest.yaml)
[![Tests](https://github.com/hehljo/hass-antigravity-usage/actions/workflows/tests.yaml/badge.svg)](https://github.com/hehljo/hass-antigravity-usage/actions/workflows/tests.yaml)
[![GitHub Release](https://img.shields.io/github/v/release/hehljo/hass-antigravity-usage?display_name=tag)](https://github.com/hehljo/hass-antigravity-usage/releases)
[![License](https://img.shields.io/github/license/hehljo/hass-antigravity-usage)](LICENSE)

![Antigravity Pulse Icon](custom_components/hass_antigravity_usage/brand/icon.png)

Antigravity Pulse brings Google Antigravity usage into Home Assistant: the
rolling 5-hour quota window per model group, the model currently limiting
that window, and its reset time.

## Why token paste instead of a login button

Antigravity's own sign-in redirects back to `http://localhost:<port>` on the
machine that started the login. On a headless Home Assistant host that is
never the machine the user's browser is on, so there is no redirect flow HA
can run by itself — and Google retired the old out-of-band ("enter this code")
flow in 2022, so that is not an option either. Reference tools with the same
problem (CodexBar, openusage) solve it the same way this integration does:
sign in once locally where a browser and the redirect target are the same
machine, then reuse the resulting tokens.

Tokens are stored only in the Home Assistant config entry and are never
logged.

## Install with HACS

1. Open HACS → **⋮** → **Custom repositories**.
2. Add `https://github.com/hehljo/hass-antigravity-usage` and select
   **Integration**.
3. Install **Antigravity Pulse** and restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration**, then choose
   **Antigravity Pulse**.
5. Sign in once locally with the Antigravity CLI/IDE if you have not already,
   open its saved token file (e.g.
   `~/.gemini/antigravity-cli/antigravity-oauth-token` on Linux/macOS), and
   paste the `refresh_token` value into the form. An access token is fetched
   from it automatically.

[![Add repository to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fhehljo%2Fhass-antigravity-usage)

## Sensors

- One usage-percent and one reset-time sensor per quota pool, discovered
  dynamically from the models the account actually reports:
  - **Gemini** — Gemini Flash/Pro model family
  - **Claude & GPT** — Claude and GPT-OSS models served through Antigravity
- Each pool sensor reports the *worst* model in that pool (a shared quota
  window is only as usable as its most exhausted member) and carries the
  limiting model's ID as an attribute.

The default polling interval is five minutes and can be set from 60 to 3,600
seconds. The sample dashboard in `dashboards/antigravity_pulse.yaml` uses
both pools.

## What this integration does not (yet) show

Antigravity's own `/usage` screen shows **two** windows per model group: a
rolling 5-hour window and a weekly window. Only the 5-hour window is
implemented here — it comes from `daily-cloudcode-pa.googleapis.com`'s
`fetchAvailableModels` endpoint, and its values were checked live against
`/usage` (matching exhausted→reset behavior) before being wired up. The
weekly percentage comes from a different, not-yet-identified endpoint. Do
not expect a weekly sensor until that endpoint is found and verified the
same way — a fabricated weekly number would be worse than none.

## Notes

This is an independent Home Assistant integration, not a Google product. The
endpoint it uses is not publicly documented by Google; it was found by
reading the open-source [`tuxevil-rotator`](https://github.com/tuxevil/tuxevil-rotator)
client, which uses it for account rotation. It may change without notice.
