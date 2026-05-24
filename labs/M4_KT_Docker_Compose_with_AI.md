# M4 KT — Generating a `docker-compose.yml` Using an AI Model

**Module 4 | Knowledge Transfer | The "delegate the YAML to an AI" pattern**

> **Audience:** anyone who has the Module 3 simple Streamlit predictor (or a similar single-app project) and wants Docker Compose for it — but doesn't want to memorise Compose v2 syntax.
>
> **Length of this doc:** ~10 minutes to read. ~3-5 minutes to actually do once you understand the flow.
>
> **AI model:** any modern one will do — Claude (Sonnet / Opus), ChatGPT (4o / 5), Gemini 2.5 Pro, etc. Examples below use a generic "AI" — the prompts work across all of them.

---

## Why this KT exists

Writing a Docker Compose file by hand has three problems:

1. **YAML is unforgiving** — one wrong indent and the whole file is invalid. Easy to lose 20 minutes to "I forgot to indent `volumes:`".
2. **The spec evolves** — Compose v1 (`docker-compose`, hyphenated) vs v2 (`docker compose`, space). The two have different syntax for the same concepts (`version:` field, healthchecks, depends_on conditions). Old StackOverflow answers often use v1; current Docker Desktop uses v2.
3. **The 80% case is templated** — most apps need the same blocks (build, ports, env, volumes, healthcheck, restart). Hand-writing them from scratch every time is wasted effort.

An AI model handles all three. You describe what you have + what you want, the AI returns a working YAML, you validate + run.

This KT teaches you **how to prompt well** so the output is correct on the first try.

---

## The 5-step workflow

```
1. Inventory  →  list the files the AI needs to "see"
2. Context    →  paste those files into the chat
3. Prompt     →  paste the prompt template, fill in the blanks
4. Validate   →  inspect the output before running it
5. Run        →  docker compose up -d --build
```

We'll work the simple Streamlit predictor as the example.

---

## Step 1 — Inventory: what files does the AI need?

The AI needs enough context to know:
- **What** runs inside the container (the app code + its deps)
- **How** it starts (the Dockerfile, if one exists; otherwise, the entry-point command)
- **What** it needs at runtime (env vars, files, ports, dependent services)

For our simple app, that's three files:

| File | Why the AI needs it |
|---|---|
| `app/app.py` | To understand what the app does + what it loads. The AI reads it once, sees `joblib.load('artifacts/...')` + `streamlit run`, and infers: "needs Python + xgboost + the artifacts folder + port 8501". |
| `app/requirements.txt` | The pinned Python deps. The AI bakes these into the Dockerfile / base image choice. Also helps it pick the right `FROM python:3.12-slim` (vs `python:3.8`, etc.). |
| `app/Dockerfile` | If you already have one, paste it so the AI knows the build context shape (does it copy `artifacts/`? expose port 8501? have a healthcheck?). If you don't have one yet, ask the AI to generate it too. |

**That's it.** Don't dump the entire repo — irrelevant files dilute the context and increase the chance the AI hallucinates something. Three files is the sweet spot for a single-service Compose.

If you're doing a multi-service Compose (see Section 6), add:
- A short description of each service ("Postgres 15 for storing prediction logs, MLflow 2.10 backed by Postgres")
- The model metadata file if the AI needs to understand the schema (`artifacts/model_metadata.json`)

---

## Step 2 — Set up the context block

Paste this at the top of your chat with the AI, **before** the prompt. The wording matters — being explicit about what's pasted helps the AI not invent things.

```
I have a single-service Streamlit application I want to wrap in Docker Compose.

Below are the three relevant files. Read them carefully before you respond.

==========================
FILE 1: app/app.py
==========================
<paste the full contents of app.py here>

==========================
FILE 2: app/requirements.txt
==========================
<paste requirements.txt here>

==========================
FILE 3: app/Dockerfile
==========================
<paste the Dockerfile here>
```

> **Why paste them inline?** Because pasting files directly is the most reliable way to give an AI context. File attachments and URL references work too, but inline pasting works on every AI (no upload feature needed) and produces deterministic results.

---

## Step 3 — The prompt

Paste this after your context block. Adjust the bracketed fields for your project.

```
Goal: generate a `docker-compose.yml` for the app above.

Requirements:
- Use Docker Compose v2 syntax (no `version:` field at the top — that's deprecated).
- Single service named "dashboard".
- Build the image from ./app (uses the Dockerfile pasted above).
- Map host port 8501 to container port 8501.
- Include a healthcheck that hits Streamlit's /_stcore/health endpoint using
  Python's urllib (not curl — the base image doesn't ship curl).
- Set the restart policy to `unless-stopped`.
- Add inline comments explaining what each block does, written for someone
  who has never used Compose before.

Constraints:
- Output ONLY the YAML, in a fenced code block.
- No prose explanation alongside the YAML — I want to copy-paste cleanly.
- After the YAML, add a 3-line "How to run" block (`docker compose up -d --build`,
  `docker compose ps`, `docker compose down`).
```

Send this. A good AI returns valid YAML in 5-10 seconds.

---

## Step 4 — Validate the output

Before running anything, eyeball the YAML for these red flags:

| Check | What to look for | If wrong... |
|---|---|---|
| **No `version:` field at the top** | Compose v2 ignores it; older AI training data may still include it. | Delete the `version: '3.x'` line if present. Harmless but obsolete. |
| **`build.context` matches your folder** | Should be `./app`, not `.` or `./dashboard`. | Edit to match where your Dockerfile actually lives. |
| **Port mapping is `HOST:CONTAINER`** | `"8501:8501"` is right. AI sometimes flips this. | Swap if reversed. |
| **Healthcheck `test:` uses an array form** | `["CMD", "python", "-c", "..."]` or `["CMD-SHELL", "..."]`. NOT a bare string. | Reformat as array. |
| **Healthcheck command doesn't use curl** | Should use Python urllib (curl isn't in `python:*-slim` base images). | Reject + reprompt: "Don't use curl; use Python urllib." |
| **No invented services** | The AI may add a `db:` or `redis:` service unprompted. | If you didn't ask for it, delete it. |
| **No invented volumes** | Same — only include volumes if your app actually needs persistence. | Remove unprompted `volumes:` blocks. |

If the YAML passes these checks, save it as `docker-compose.yml` in the parent folder of your `app/` directory.

**Sanity-validate the YAML syntax**:

```bash
docker compose config
# Prints the parsed config if valid; errors out with line numbers if not.
```

If `docker compose config` errors, copy the error back to the AI and ask it to fix.

---

## Step 5 — Run it

From the folder containing `docker-compose.yml`:

```bash
docker compose up -d --build
docker compose ps
# Expected: dashboard service shown as "running" then "running (healthy)" after ~20 s

# Visit http://localhost:8501 in a browser
# Fill in the form, click "Predict Delay Risk"

docker compose down       # Tear down when done
```

If `ps` shows status `(unhealthy)` after a couple of minutes:

```bash
docker compose logs dashboard
```

Find the Python traceback. Most common at this stage: the Dockerfile didn't `COPY artifacts/` into the image, so `app.py` errors out at startup. Fix the Dockerfile and rerun `docker compose up -d --build`.

---

## A complete worked example

For the M4 Lab 4 single-service Compose, here's what the AI returned with the prompt above (your output may vary slightly):

```yaml
services:
  dashboard:
    # Build the image from the Dockerfile in ./app
    # (Compose passes ./app as the build context, so paths like 'artifacts/'
    # in the Dockerfile resolve relative to that folder.)
    build:
      context: ./app
      dockerfile: Dockerfile
    container_name: freshbasket-dashboard

    # Map host port 8501 -> container port 8501 (Streamlit's default)
    ports:
      - "8501:8501"

    # The simple app doesn't read any env vars; the line below just disables
    # Streamlit's anonymous usage telemetry (a nice-to-have).
    environment:
      - STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

    # If the container crashes, Compose restarts it. Stays off only when you
    # explicitly run `docker compose down`.
    restart: unless-stopped

    # Hit Streamlit's built-in health endpoint to confirm the app is ready.
    # We use Python's urllib because the python:3.12-slim base image doesn't
    # include curl.
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8501/_stcore/health', timeout=3).status == 200 else 1)"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 15s
```

How to run:
```bash
docker compose up -d --build
docker compose ps
docker compose down
```

That's exactly what's in `docker-compose.yml` in this folder.

---

## 6. Stretch: ask the AI for a multi-service variant

Once you've got the single-service Compose working, here's how to extend it. **Add this to the chat** (don't start a new conversation — the AI already has the app's context loaded from Steps 2-3):

```
Now extend the docker-compose.yml above with two more services:

1. A PostgreSQL 15 database named "db":
   - Use image postgres:15-alpine
   - Database: predictions_db
   - User: app_user
   - Password: read from env var DB_PASSWORD (default to "changeme_in_prod" if unset)
   - Persist data with a named volume "pgdata"
   - Add a healthcheck using pg_isready

2. An MLflow tracking server named "mlflow":
   - Use python:3.12-slim as the base image
   - Install mlflow + psycopg2-binary on container startup (via `command:`)
   - Run `mlflow server --host 0.0.0.0 --port 5000` with the PostgreSQL
     above as the backend store URI
   - Depend on `db` being healthy before starting

3. Update the dashboard service:
   - Wait for db to be healthy before starting (depends_on with condition: service_healthy)
   - Pass DB_HOST=db, DB_PORT=5432, MLFLOW_TRACKING_URI=http://mlflow:5000
     into the dashboard's environment (the app may not read these yet, but
     plumbing them is useful for the next iteration)

4. Put all three services on a custom bridge network named "freshbasket-net"
   so they resolve each other by service name.

Output rules: same as before -- YAML only, no prose, plus the run/stop commands at the end.
```

The AI will return a 3-service Compose. Apply the same validation checks from Step 4 (note: now you'll have `volumes:` and `networks:` top-level blocks, which is expected for multi-service setups).

---

## Common AI mistakes to watch for

| Mistake | Why it happens | How to spot it |
|---|---|---|
| Adds `version: '3.x'` at the top | Stale training data — pre-2023 Compose docs included `version:` | First line of the YAML |
| Uses curl in healthcheck | Curl is on every AI's "obvious" list; doesn't notice slim base image doesn't have it | Look at `test:` array |
| Uses `links:` instead of `networks:` | `links:` was deprecated in Compose v2 | Look for top-level `links:` block — should be `networks:` |
| Bind-mounts `./app` into the container | Useful for live-reload dev but defeats the "image is portable" lesson | `volumes:` block under the service mounting source code |
| Names services in CamelCase | Service names should be lowercase + hyphens / underscores | Look at `services:` block — should be all lowercase |
| Forgets `depends_on.condition` for v2 | v2 needs explicit `condition: service_healthy`; just `depends_on: [db]` doesn't wait for healthy | Multi-service stacks only |

If you spot any of these, reprompt with a one-liner: "Remove the `version:` field" or "Use Python urllib in the healthcheck, not curl". The AI fixes and re-emits.

---

## When NOT to use AI for Compose

The AI is great for **structure**. It's not great for:

- **Picking image versions for production** — the AI may suggest `postgres:latest` (no version pin) or pin to a version that's been EOL'd. Always check official Docker Hub for current stable tags.
- **Tuning resource limits** — `mem_limit`, `cpus`, etc. depend on your actual workload. AI defaults are wild guesses.
- **Security hardening** — non-root users, read-only filesystems, `cap_drop`. AI knows these exist but rarely applies them by default. For production, treat AI output as a starting draft.

For a class lab? AI-generated Compose is more than fine. For a production prod-ops deploy, hand-review every line.

---

## Quick-reference prompt (copy-paste-ready)

For when you've done this before and just want the magic words:

```
Generate a docker-compose.yml (v2 syntax, no version field) for the app I'm
about to paste. Use the Dockerfile in ./app for the build context. Map port
8501. Python urllib healthcheck on /_stcore/health (no curl). Restart
unless-stopped. Output YAML only, inside a fenced code block. Add inline
comments. After the YAML, add the docker compose up/ps/down commands.

==========================
app.py:
<paste>

requirements.txt:
<paste>

Dockerfile:
<paste>
```

That's the whole KT in one prompt.
