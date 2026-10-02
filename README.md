# Antigravity Pulse for Home Assistant

[![HACS validation](https://github.com/hehljo/hass-antigravity-usage/actions/workflows/validate.yaml/badge.svg)](https://github.com/hehljo/hass-antigravity-usage/actions/workflows/validate.yaml)
[![Hassfest](https://github.com/hehljo/hass-antigravity-usage/actions/workflows/hassfest.yaml/badge.svg)](https://github.com/hehljo/hass-antigravity-usage/actions/workflows/hassfest.yaml)
[![Tests](https://github.com/hehljo/hass-antigravity-usage/actions/workflows/tests.yaml/badge.svg)](https://github.com/hehljo/hass-antigravity-usage/actions/workflows/tests.yaml)
[![GitHub Release](https://img.shields.io/github/v/release/hehljo/hass-antigravity-usage?display_name=tag)](https://github.com/hehljo/hass-antigravity-usage/releases)
[![License](https://img.shields.io/github/license/hehljo/hass-antigravity-usage)](LICENSE)

![Antigravity Pulse Icon](custom_components/hass_antigravity_usage/brand/icon.png)

Antigravity Pulse brings Google Antigravity usage into Home Assistant: both
quota windows per model group — the rolling 5-hour window and the weekly
limit — with their reset times, the same numbers Antigravity's own `/usage`
screen shows.

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
5. Paste your refresh token (see below). The Google Cloud project ID can stay
   empty. An access token is fetched from the refresh token automatically.

[![Add repository to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fhehljo%2Fhass-antigravity-usage)

## Getting your refresh token

The token has to come from a program that signed in **as Antigravity**.
Google binds a refresh token to the OAuth client that issued it, so a token
from a different client is rejected with "invalid token".

**Antigravity CLI (`agy`)** — sign in once, then read the token file. On
Linux it is `~/.gemini/antigravity-cli/antigravity-oauth-token`; the value
sits under `token` → `refresh_token`:

```bash
jq -r .token.refresh_token ~/.gemini/antigravity-cli/antigravity-oauth-token
```

The Linux path is verified. macOS and Windows have not been checked; look
for the same `.gemini/antigravity-cli/` folder in your home directory.

**[tuxevil-rotator](https://github.com/tuxevil/tuxevil-rotator)** — every
account you added with its login has its token in
`~/.tuxevil-rotator/accounts.json`:

```bash
jq -r '.accounts[] | "\(.email)  \(.credentials[0].refreshToken)"' ~/.tuxevil-rotator/accounts.json
```

Add one integration entry per account you want to watch.

**Does not work:** Gemini CLI's `~/.gemini/oauth_creds.json`. It is issued to
Gemini CLI's own OAuth client, which Google does not accept for Antigravity.
Where the Antigravity desktop IDE stores its token has not been verified.

The refresh token grants access to your Antigravity account — treat it like
a password.

## Sensors

Per model group, discovered from what the account actually reports:

| Sensor | Meaning |
|---|---|
| `<group> 5h usage` | Used percentage of the rolling 5-hour window |
| `<group> 5h reset` | When the 5-hour window resets |
| `<group> weekly usage` | Used percentage of the weekly limit |
| `<group> weekly reset` | When the weekly limit resets |

Groups are **Gemini** (Gemini Flash/Pro) and **Claude & GPT** (Claude and
GPT-OSS models served through Antigravity). Each usage sensor carries the
remaining percentage as an attribute.

A reset sensor stays *unknown* while its window is untouched: Google still
reports a reset time for an unused window, but it is just "now + window
length" and moves forward on every poll.

The default polling interval is five minutes and can be set from 60 to 3,600
seconds. The sample dashboard in `dashboards/antigravity_pulse.yaml` shows
both windows for both groups.

### Upgrading from the 5-hour-only version

The 5-hour sensors keep their entity IDs. The weekly sensors are new. The
`limiting_model` attribute is gone: the summary endpoint reports one shared
window per group, not per model.

## Notes

This is an independent Home Assistant integration, not a Google product. It
reads `retrieveUserQuotaSummary` on `daily-cloudcode-pa.googleapis.com`, an
endpoint Google does not document publicly. It was found through
[Antigravity-Manager PR #3185](https://github.com/lbjlaq/Antigravity-Manager/pull/3185)
and checked live on 2026-10-02: its 5-hour values match the per-model quota
of `fetchAvailableModels`, the endpoint earlier versions used. It may change
without notice.
