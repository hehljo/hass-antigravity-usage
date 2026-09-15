# Antigravity Pulse

Antigravity Pulse brings Google Antigravity usage into Home Assistant: the
rolling 5-hour quota window per model group (Gemini · Claude & GPT), the
limiting model, and the reset time.

There is no working login flow Home Assistant can run on its own for
Antigravity (Google's redirect only reaches the machine that started the
login, and the old out-of-band code flow was retired in 2022). Sign in once
locally in the Antigravity CLI/IDE, then paste the access and refresh token
from its saved token file when adding the integration under
**Settings → Devices & services**.

Only the 5-hour window is available right now — the weekly window Antigravity's
own `/usage` screen shows comes from a different endpoint that has not been
identified yet.
