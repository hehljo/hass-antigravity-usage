# Antigravity Pulse

Antigravity Pulse brings Google Antigravity usage into Home Assistant: the
rolling 5-hour window and the weekly limit per model group (Gemini · Claude &
GPT), each with its reset time.

There is no working login flow Home Assistant can run on its own for
Antigravity (Google's redirect only reaches the machine that started the
login, and the old out-of-band code flow was retired in 2022). Paste a
refresh token from a program that signed in as Antigravity — the Antigravity
CLI or tuxevil-rotator — when adding the integration under
**Settings → Devices & services**. The README explains where to find it.
An access token is fetched automatically.
