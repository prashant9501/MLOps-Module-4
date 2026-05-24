# M4 KT — Generating Dockerfile + `docker-compose.yml` Using an AI Model

**Module 4 | Knowledge Transfer | "Hand the Docker work to an AI" pattern**

> **Audience:** anyone with a Python app (a `.py` file + a `requirements.txt`) who wants it containerised + composed — without memorising Dockerfile syntax or Compose v2 spec.
>
> **End state:** working `Dockerfile`, working `docker-compose.yml`, a running container serving the app on `http://localhost:<port>`. ~10 minutes once you've done it once.
>
> **AI model:** any modern one — Claude (Sonnet / Opus), ChatGPT (4o / 5), Gemini 2.5 Pro, etc. The prompts work across all of them.

---

## Why this KT exists

Three friction points when containerising a project by hand:

1. **Dockerfile syntax is a moving target.** Layer caching tricks (`COPY requirements.txt` before source code), the right base image (`python:3.12-slim` vs `alpine` vs full `python:3.12`), healthchecks, non-root users, multi-stage builds — easy to forget one and produce a 2 GB image that takes 5 minutes to rebuild.
2. **YAML is unforgiving.** One bad indent in `docker-compose.yml` and the whole file is invalid.
3. **The 80% case is templated.** Most Python web apps need the same blocks. Hand-writing them every time is wasted effort.

An AI handles all three. You describe your app, the AI returns a working Dockerfile + Compose file, you validate + run.

This KT teaches you **how to prompt well** so the output is correct on the first try.

---

## The 6-step workflow

```
1. Inventory   →  list the files the AI needs to "see"
2. Context     →  paste those files into the chat
3. Stage 1     →  ask the AI to generate the Dockerfile
4. Stage 2     →  ask the AI to generate the docker-compose.yml
5. Validate    →  eyeball both outputs against the checklist
6. Build + run →  docker compose up -d --build; visit the URL
```

We'll work the M4 Lab 4 self-contained Streamlit predictor as the example. The same flow works for Flask APIs, FastAPI services, batch scripts, Jupyter notebooks served via voila, etc.

---

## Step 1 — Inventory: what files does the AI need?

For the **Dockerfile** stage, the AI needs to know:
- **What the app does** — to pick the right base image, the right CMD, the right port
- **What it depends on** — to know what to install

So for our simple Streamlit app, share these two files:

| File | Why |
|---|---|
| `app.py` | The AI reads `import streamlit`, sees `joblib.load('artifacts/...')`, and infers: "Python app, Streamlit framework, needs the artifacts/ folder at runtime, default port 8501." |
| `requirements.txt` | Pinned Python deps. The AI picks the Python version compatible with those packages (e.g., `streamlit==1.32` works on Python 3.10-3.12 → it picks 3.12-slim). |

**Optionally** share:
- A short text description of any **runtime data** the app needs at startup. Our app reads `artifacts/*.pkl`, so we mention "the app loads .pkl files from an `artifacts/` directory alongside `app.py`" — that tells the AI to add a `COPY artifacts/ ./artifacts/` line.
- Any **non-default port** the app binds to. Streamlit defaults to 8501 so we don't need this. Flask defaults to 5000, FastAPI to 8000. Mention it if different.

Don't share the whole repo — irrelevant files dilute the context and increase hallucination risk. Two files + one sentence of context is the sweet spot.

---

## Step 2 — Set up the context block

Paste this at the top of the AI chat. Wording matters — being explicit about what you're sharing helps the AI not invent things.

```
I'm containerising a Python application. I need both a Dockerfile AND a
docker-compose.yml for it, in that order. I'll ask for them in two separate
prompts so I can review each.

Below are the two relevant files. Read them carefully before you respond.

The app also reads pre-trained .pkl files from an `artifacts/` folder
that sits alongside app.py. The container needs to include that folder.

==========================
FILE 1: app.py
==========================
<paste the full contents of app.py here>

==========================
FILE 2: requirements.txt
==========================
<paste requirements.txt here>
```

> **Tip:** paste files inline rather than uploading attachments. Inline pasting works on every AI model (no upload feature needed), produces deterministic results, and is easy to debug if the output is wrong.

---

## Step 3 — Stage 1: Ask the AI to generate the Dockerfile

Paste this **after** your context block:

```
STAGE 1 OF 2 -- Generate the Dockerfile.

Requirements:
- Base image: python:3.12-slim (good balance of size + ML-package compatibility)
- WORKDIR /app
- Order matters for layer caching: COPY requirements.txt and pip install
  it BEFORE copying any source code, so source edits don't bust the pip cache
- COPY app.py AND the artifacts/ folder (the app reads .pkl files from
  artifacts/ at startup, so the folder must be inside the image)
- EXPOSE the port the app listens on
- HEALTHCHECK that uses Python stdlib urllib (the slim base image
  does NOT ship curl, so don't write a curl-based healthcheck)
- CMD that starts the app with --server.address=0.0.0.0 so it binds
  all interfaces (otherwise `docker run -p` won't route traffic in)
- Add a 1-line comment above each instruction explaining what it does

Output: ONLY the Dockerfile, in a fenced code block. No prose.
```

A good AI returns something like:

```dockerfile
# Use the slim Python 3.12 image -- ~75 MB base, fully compatible with ML packages
FROM python:3.12-slim

# All subsequent commands run inside /app, matches where we'll COPY the source
WORKDIR /app

# Copy requirements FIRST so the heavy pip-install layer caches across source edits
COPY requirements.txt .

# --no-cache-dir saves ~150 MB vs the default behavior
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code and the pre-trained artifacts the app loads at startup
COPY app.py ./
COPY artifacts/ ./artifacts/

# Streamlit's default port
EXPOSE 8501

# Health check using Python stdlib (slim base image doesn't ship curl)
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8501/_stcore/health', timeout=3).status == 200 else 1)"

# Bind to 0.0.0.0 so docker -p can map the port in from the host
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true", "--browser.gatherUsageStats=false"]
```

Save this to your project folder as `Dockerfile` (no extension). Compare against the one already in `labs/M4_Lab4_Docker_Compose/app/Dockerfile` — should be close to identical.

---

## Step 4 — Stage 2: Ask the AI to generate the docker-compose.yml

In the **same chat** (don't start a new conversation — the AI already has your app's context loaded), paste:

```
STAGE 2 OF 2 -- Generate the docker-compose.yml using the Dockerfile from Stage 1.

Requirements:
- Use Docker Compose v2 syntax (NO `version:` field at the top -- that's
  deprecated)
- Single service named "dashboard"
- Build the image from ./app (the folder containing the Dockerfile + app.py
  + requirements.txt + artifacts/)
- Map host port 8501 to container port 8501
- Include the SAME healthcheck as the Dockerfile (Python urllib hitting
  /_stcore/health -- expressed in Compose array form)
- Restart policy: unless-stopped
- Add inline comments explaining what each block does, written for someone
  who has never used Compose before
- After the YAML, add a 3-line "How to run" block:
    docker compose up -d --build
    docker compose ps
    docker compose down

Output: YAML in a fenced code block, then the 3-line how-to-run. No
prose between or around.
```

Expected output:

```yaml
services:
  dashboard:
    # Build the image from ./app (Dockerfile + app.py + artifacts/ live there)
    build:
      context: ./app
      dockerfile: Dockerfile
    container_name: freshbasket-dashboard

    # Map HOST:CONTAINER. 8501 is Streamlit's default port.
    ports:
      - "8501:8501"

    # If the container crashes, Compose restarts it. Stops respecting this
    # only when you explicitly run `docker compose down`.
    restart: unless-stopped

    # Hit Streamlit's built-in health endpoint via Python stdlib (no curl in
    # python:slim base images). Array form is required by Compose v2.
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

Save this to your project folder as `docker-compose.yml` (one level above `./app`).

> **Folder structure at this point:**
> ```
> your-project/
> ├── docker-compose.yml           ← Stage 2 output
> └── app/
>     ├── Dockerfile               ← Stage 1 output
>     ├── app.py
>     ├── requirements.txt
>     └── artifacts/               ← .pkl files
> ```

---

## Step 5 — Validate both outputs before running

Eyeball the Dockerfile and the Compose file for these red flags:

### Dockerfile checklist

| Check | What to look for | If wrong... |
|---|---|---|
| `FROM` uses `python:3.x-slim` | Should match Python version your deps need. Avoid `alpine` for ML packages (compilation hell for numpy/scikit-learn). | Reprompt: "Use python:3.12-slim, not alpine." |
| `COPY requirements.txt` BEFORE `COPY app.py` | This is the layer-caching trick. If reversed, every source edit forces a re-pip-install. | Edit + retry. |
| `--no-cache-dir` on `pip install` | Saves ~150 MB in the final image. | Add it. |
| `COPY artifacts/` is present | App needs `.pkl` files at runtime. Without this, the container starts then crashes. | Reprompt: "Add a COPY for the artifacts folder." |
| `EXPOSE 8501` (or the app's actual port) | EXPOSE is documentation; the actual mapping happens in Compose. Still good to have. | Add. |
| Healthcheck uses Python stdlib (NOT curl) | `python:slim` images don't ship curl. Curl-based healthcheck fails silently. | Reprompt: "Don't use curl; use Python urllib." |
| `CMD` includes `--server.address=0.0.0.0` (for Streamlit / Flask binding) | Without this, the app binds 127.0.0.1, unreachable from outside the container. | Add. |

### docker-compose.yml checklist

| Check | What to look for | If wrong... |
|---|---|---|
| **No `version:` field at the top** | Compose v2 ignores it; older AI training data may still include it. | Delete the `version: '3.x'` line. |
| `build.context: ./app` matches your folder layout | The AI sometimes guesses `.` or `./src`. | Edit to match where your Dockerfile lives. |
| `ports:` is `HOST:CONTAINER` | `"8501:8501"` is fine. AI sometimes flips this. | Swap if reversed. |
| `healthcheck.test:` uses **array form** | `["CMD", "python", "-c", "..."]` or `["CMD-SHELL", "..."]`. NOT a bare string. | Reformat as array. |
| Healthcheck command doesn't use curl | Should mirror the Dockerfile (Python urllib). | Reject + reprompt. |
| No invented services | AI sometimes adds `db:` or `redis:` unprompted. | Delete if you didn't ask. |
| No invented volumes / bind mounts | Same — only include volumes if your app needs persistence. | Remove unprompted blocks. |

Then validate Compose syntax:

```bash
docker compose config
# Prints the parsed config if valid; errors out with line numbers if not.
```

If `docker compose config` errors, copy the error message back to the AI: "This Compose file errored with `<paste error>`. Fix it."

---

## Step 6 — Build + run

From the folder containing `docker-compose.yml`:

```bash
docker compose up -d --build      # Build the image + start the container
docker compose ps                  # Should show 'running (healthy)' after ~20 s
docker compose logs -f dashboard   # Follow logs (Ctrl-C to stop following)

# Visit the URL in your browser
open http://localhost:8501          # macOS
# Or just paste http://localhost:8501 in any browser

docker compose down                # Tear down when done
```

If `docker compose ps` shows `(unhealthy)` for more than 2 minutes:

```bash
docker compose logs dashboard
# Look for the Python traceback. Most common at this stage:
#   - artifacts/ not in the image (Dockerfile missing COPY)
#   - port mismatch (Dockerfile EXPOSEs one port, app binds another)
#   - Python version too old for some pip package
```

Fix the Dockerfile, run `docker compose up -d --build` again.

---

## 7. Stretch — multi-service (Postgres + MLflow)

Once you've got the single-service version working, extend it. **Add this to the same chat** (the AI still has your app's context):

```
STRETCH -- extend the docker-compose.yml above with two more services:

1. PostgreSQL 15 named "db":
   - Image: postgres:15-alpine
   - DB: predictions_db
   - User: app_user
   - Password: read from env var DB_PASSWORD (default "changeme_in_prod")
   - Persist data with a named volume "pgdata"
   - Healthcheck using pg_isready

2. MLflow tracking server named "mlflow":
   - Base: python:3.12-slim
   - Install mlflow + psycopg2-binary on startup (via `command:`)
   - Run `mlflow server --host 0.0.0.0 --port 5000` with the Postgres
     above as backend store URI
   - Wait for `db` to be healthy before starting (depends_on with condition)

3. Update dashboard service:
   - depends_on db with condition: service_healthy
   - Pass DB_HOST=db, DB_PORT=5432, MLFLOW_TRACKING_URI=http://mlflow:5000
     into the dashboard's environment

4. All three services on a custom bridge network "freshbasket-net" so they
   resolve each other by service name.

Output rules: same as before -- YAML only, no prose, plus run/stop commands at the end.
```

Apply the same validation checks. Now you'll have top-level `volumes:` and `networks:` blocks, which is expected for multi-service setups.

---

## Common AI mistakes — what to spot

### Dockerfile mistakes

| Mistake | Why it happens | How to spot it |
|---|---|---|
| Uses `python:3.x` (full, ~1 GB) instead of `python:3.x-slim` | AI defaults to "safe" full image | Image size > 1 GB after build |
| Uses `python:3.x-alpine` for ML workloads | Alpine is "small" so AI suggests it; ML wheels rarely work on Alpine | Build fails compiling numpy/sklearn from source |
| Forgets `--no-cache-dir` on pip | Not in the AI's "must-have" list | `du -sh /root/.cache/pip` inside container shows ~150 MB |
| `COPY . .` instead of explicit `COPY app.py artifacts/ ./` | Less precise — copies in test files, .git/, .venv/ if not gitignored | Image suddenly much larger than expected |
| Curl-based healthcheck on slim image | Curl is on every AI's "obvious" list; doesn't notice slim doesn't have it | Healthcheck always returns "starting" then "unhealthy" |
| Missing `--server.address=0.0.0.0` (Streamlit) or `--host 0.0.0.0` (FastAPI) | AI uses framework defaults | Browser can't connect even though container is running |

### docker-compose.yml mistakes

| Mistake | Why it happens | How to spot it |
|---|---|---|
| Adds `version: '3.x'` at the top | Stale training data — pre-2023 Compose docs included it | First line of the YAML |
| `healthcheck.test` as a bare string instead of array | Older Compose syntax allowed bare strings | `docker compose config` may show warnings |
| Uses `links:` instead of `networks:` | `links:` was deprecated in Compose v2 | Top-level `links:` block |
| Bind-mounts `./app` into the container | Useful for live-reload dev but defeats the "image is portable" point | `volumes:` block under the service mounting source code |
| Service names in CamelCase | Should be lowercase + hyphens / underscores | `services:` block |
| Forgets `depends_on.condition: service_healthy` | Without it, depends_on only waits for the dependency to START, not be healthy | Multi-service stacks only — dashboard starts before db is ready |

If you spot any, reprompt with a one-liner like "Remove the `version:` field" or "Use Python urllib in the healthcheck, not curl". The AI fixes and re-emits.

---

## When NOT to use AI for Docker

The AI is great for **structure**. It's not great for:

- **Picking image version pins for production** — the AI may suggest `postgres:latest` (no version pin) or pin to a version that's been EOL'd. Always check Docker Hub for current stable tags.
- **Tuning resource limits** — `mem_limit`, `cpus`, etc. depend on your actual workload. AI defaults are guesses.
- **Security hardening** — non-root users, read-only filesystems, `cap_drop`, secret management. AI knows these exist but rarely applies them. For production, treat AI output as a starting draft.
- **Multi-stage builds for compiled languages (Go, Rust)** — AI can do these but often gets the layer copy wrong. Worth hand-reviewing.

For a class lab or a dev environment? AI-generated is more than fine. For a production deploy, hand-review every line.

---

## Quick-reference combined prompt

Once you're comfortable with both stages, you can ask for both files in one prompt. Useful for repeat use:

```
Containerise this Python app. Generate:
1. A Dockerfile (FROM python:3.12-slim, WORKDIR /app, requirements before
   source, --no-cache-dir, COPY app.py + artifacts/, EXPOSE 8501, Python-
   stdlib healthcheck on /_stcore/health, CMD streamlit run app.py
   --server.address=0.0.0.0).
2. A docker-compose.yml (v2 syntax, no version field, build from ./app,
   port 8501, restart unless-stopped, healthcheck mirroring Dockerfile,
   inline comments).

After both, add the docker compose up/ps/down commands.

==========================
app.py:
<paste>

requirements.txt:
<paste>
```

That's the whole KT in one prompt for when you've internalised the pattern.

---

## Recap

The deliverable of this KT is **two files** you didn't hand-write:

1. `Dockerfile` — generated in Stage 1 from `app.py + requirements.txt + a sentence about runtime files`
2. `docker-compose.yml` — generated in Stage 2 using the Dockerfile from Stage 1 as additional context

Both checked against the Dockerfile + Compose validation tables above before running. End state: `docker compose up -d --build` brings the app up at `http://localhost:8501`.

This is the workflow you'll use on real projects — most teams don't hand-write Docker tooling anymore; they generate from a description and pattern-match from prior examples.
