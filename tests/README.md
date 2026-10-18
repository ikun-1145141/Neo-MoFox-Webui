# Model test regressions

Run commands from the repository root:

```sh
python -m unittest discover -s tests -v
node --test frontend/tests/model-test.test.mjs
```

Backend requirements: Python 3.11+, `aiohttp`, `pydantic` 2.x, `fastapi`, `openai`, and `httpx`.
Validation used OpenAI SDK 2.33.0, matching the local Neo-MoFox checkout's lockfile.
Frontend requirements: the existing `frontend` dependencies (no extra test framework).

Backend tests isolate the host framework imports and use the real plugin router,
request models, manager and SDK with an in-memory HTTP transport. They never call
an external provider or need real credentials. Frontend tests compile the actual
Vue SFC setup and use Vue's in-memory renderer, stubbing the API boundary.

These tests cover unsaved additions and edits, old name-only requests, invalid
snapshots, no-save/no-reload behavior, errors, timeouts, client cleanup, and the
frontend request payload. They do not replace a live Neo-MoFox/provider smoke test.


# Native request monitor regressions

See `docs/request-monitor.md` for new records API semantics, paired host/WebUI upgrade requirements, deterministic frontend tests and the local-only smoke server. The transport tests use the sibling `Neo-MoFox` source checkout (or the host root specified by `NEO_MOFOX_ROOT`) and never contact a real provider.


Request monitor component/state regressions (after `npm ci` in `frontend`):

```sh
node --test frontend/tests/request-monitor.test.mjs frontend/tests/request-monitor-components.test.mjs
```

The component suite compiles actual SFC templates and tests JSON pagination, pointer escaping,
full-data copy/export, bounded/deep trees, safe text rendering, four-tab state retention,
Embedding/Rerank views and shared Axios error policy. Browser acceptance is a separate manual step.
