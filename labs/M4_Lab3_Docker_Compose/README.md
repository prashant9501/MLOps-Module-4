# M4 Lab 3: Docker Compose

**Module 4 -- Containerisation & Docker | AWS MLOps Master Course**

> **New to M4?** Start with [../M4_Docker_End_to_End_Student_Guide.md](../M4_Docker_End_to_End_Student_Guide.md) — the install → build → push → sanity-check walkthrough. This lab is an **extension** that wraps the Docker work in `docker-compose.yml`.

| Detail          | Value                                       |
|-----------------|---------------------------------------------|
| Duration        | 45 minutes                                  |
| Difficulty      | Beginner-Intermediate                       |
| Prerequisites   | Labs 1 + 2 complete (Docker working)        |
| OS              | Windows / macOS / Linux                     |
| Docker Compose  | v2 (bundled with Docker Desktop / Engine)   |

---

## Learning Objectives

By the end of this lab you will be able to:

1. Read and write a `docker-compose.yml` file (services, build, ports, env vars, healthchecks, restart policies).
2. Bring an application up + down with `docker compose up -d --build` and `docker compose down`.
3. Inspect Compose state (`docker compose ps`, `docker compose logs -f`).
4. **Use an AI model** to generate a `docker-compose.yml` for a new app — see the dedicated KT doc: [M4_KT_Docker_Compose_with_AI.md](../M4_KT_Docker_Compose_with_AI.md).
5. (Stretch) Add multiple services to a Compose file and use Docker networking to let them talk to each other.

---

## The app this lab uses

`app/app.py` is the **self-contained Streamlit predictor** (originally drafted in `Module 3/labs/simple_streamlit_app/`). It loads four artifacts from `app/artifacts/` and serves a manual prediction UI:

- `xgboost_model.pkl` — the trained classifier
- `encoder.pkl` — fitted OneHotEncoder
- `scaler.pkl` — fitted StandardScaler
- `model_metadata.json` — column groupings + feature order

There is **no database, no S3, no MLflow** behind this app. That's deliberate — it makes the Compose file a one-service "hello world" you can actually understand line-by-line.

---

## Folder layout

```
M4_Lab3_Docker_Compose/
├── README.md                  ← you're here
├── docker-compose.yml         ← the single-service Compose file
└── app/
    ├── Dockerfile             ← built from Lab 1's recipe, with a healthcheck
    ├── app.py                 ← the Streamlit predictor
    ├── requirements.txt       ← streamlit + xgboost + scikit-learn + joblib
    └── artifacts/             ← .pkl files + 11 reference plots
        ├── xgboost_model.pkl
        ├── encoder.pkl
        ├── scaler.pkl
        ├── model_metadata.json
        └── ... (PNGs of confusion matrices, ROC curves, feature importances)
```

---

## Quick start

From this folder:

```bash
docker compose up -d --build      # Build the image, start the container
docker compose ps                  # Confirm 'freshbasket-dashboard' is running + healthy
open http://localhost:8501         # macOS; on Windows just visit the URL in a browser
```

Wait ~15-20 s for Streamlit to cold-start. `docker compose ps` should then show `Up 21 seconds (healthy)`. Fill in the form, click **Predict Delay Risk**, see the result.

> **Note on image naming:** Compose auto-names the image it builds as `<project>-<service>:latest` (typically `m4_lab3_docker_compose-dashboard:latest`). That's different from the `truck-delay-app:v1` you produced in Lab 2 by hand. Both work; they're independent. To use the **same** image tag as Lab 2, replace the `build:` block in `docker-compose.yml` with `image: truck-delay-app:v1` — Compose will then skip the build step and use whatever's already in your local Docker.

Stop + clean up:

```bash
docker compose down                # Stop + remove the container; keep the image
docker compose down --rmi all      # Also remove the image (for a true fresh state)
```

---

## What the Compose file does (one-line tour)

| Block | What |
|---|---|
| `services:` | The list of containers Compose manages |
| `dashboard:` | Logical name for this service. Used as a DNS hostname by other services in the same Compose project. |
| `build: context: ./app` | Build the image from `app/Dockerfile`. Alternative: `image: <ECR URI>` to skip building and pull a pre-built image. |
| `ports: 8501:8501` | Map host:container. Same as `docker run -p`. |
| `environment:` | Env vars baked into the container. The simple app reads none — kept here illustratively. |
| `restart: unless-stopped` | If the container crashes, Compose restarts it. Stops respecting this only when you explicitly `docker compose down`. |
| `healthcheck:` | Compose runs this every 30 s and surfaces the result in `docker compose ps`. Same Python urllib check the Dockerfile uses. |

---

## How to generate a `docker-compose.yml` from scratch using AI

The big learning of this lab isn't "how to write YAML" — it's "**how to delegate the YAML to an AI** and get a correct, runnable Compose file every time."

See **[M4_KT_Docker_Compose_with_AI.md](../M4_KT_Docker_Compose_with_AI.md)** for the full walkthrough:

1. Which files to share with the AI as context
2. The prompt template you paste in
3. What to expect in the response
4. How to validate the AI's output before running it
5. Stretch: how to ask for a multi-service variant (Streamlit + Postgres + MLflow)

This is the workflow you'll use in real projects — most teams don't hand-write Compose files; they pattern-match from old examples or generate from a description.

---

## Stretch goal: multi-service Compose

The simple app is one container. Real ML systems are usually 3-5 services minimum (app + DB + cache + monitoring). Once you've got the single-service Compose working, the KT's Section 6 walks you through extending it: ask the AI to add Postgres + MLflow, wire up depends-on / healthchecks / Compose networks, and bring it all up with one `docker compose up`.

The previous version of this lab had a hand-written 3-service Compose. It's deliberately gone — the KT teaches you to generate the same thing in ~3 minutes of prompting instead of memorising YAML.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `docker compose up` says "no such file or directory: Dockerfile" | You're not in the `M4_Lab3_Docker_Compose/` folder. `cd` to it first. |
| Container starts then immediately exits | `docker compose logs dashboard` — usually a Python traceback. Common cause: `artifacts/` not copied into the image (check the Dockerfile `COPY artifacts/ ./artifacts/` line). |
| Browser at `http://localhost:8501` shows `ERR_CONNECTION_REFUSED` | Cold start not done yet. Wait 20 s; check `docker compose ps` — once status is `(healthy)`, Streamlit is ready. |
| `docker compose ps` shows status `(unhealthy)` | Healthcheck failing. `docker compose logs dashboard` for clues. Most common: app crashed at startup. |
| `bind: address already in use` | Port 8501 is taken (another Streamlit running, perhaps from Lab 2). Stop it with `docker ps` → `docker stop <ID>`. |
| Build is very slow | First build pulls the base image + installs all Python deps (~2 min). Subsequent builds use layer caching and are <10 s. |
