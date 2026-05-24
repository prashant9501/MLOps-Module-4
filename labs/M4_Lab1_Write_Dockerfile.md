# M4 Lab 1: Write a Dockerfile for the Delay Predictor

**Module 4 -- Containerization with Docker | Spine Project: Truck Delay Classification**

> **Just want to ship it end-to-end?** See [M4_Docker_End_to_End_Student_Guide.md](M4_Docker_End_to_End_Student_Guide.md) — single doc covering install → build → push → sanity check across Windows / macOS / Linux. This lab is the deep dive on the Dockerfile itself.

| Detail | Value |
|---|---|
| Duration | 45 minutes |
| Difficulty | Beginner |
| Tools | Docker Desktop (Windows/Mac) or Docker Engine (Linux), VS Code |
| Prerequisite | This repo cloned. The application source already lives at `labs/M4_Lab3_Docker_Compose/app/` — no copying from other repos needed. |
| Builds Toward | Lab 2 (build and run), Lab 4 (push to ECR) |

---

## Learning Objectives

By the end of this lab you will be able to:

1. Explain the purpose of each core Dockerfile instruction (FROM, WORKDIR, COPY, RUN, EXPOSE, HEALTHCHECK, CMD).
2. Choose an appropriate Python base image for an ML application.
3. Order Dockerfile layers to maximise build-cache efficiency.
4. Create a `.dockerignore` file to keep the build context small.
5. Pick a healthcheck strategy that works with the base image you chose.

---

## Business Context

Priya's FreshBasket logistics team in Pune wants to ship the Delivery Delay Predictor to as many environments as possible — Arjun's laptop, the staging EC2, eventually ECS Fargate in M5. Right now every fresh install eats 20+ minutes: install Python, pip-install ML libraries, copy the model `.pkl` files, fight version mismatches. Arjun asked during the standup: *"Can we just package this thing once and run it anywhere?"* That is exactly what Docker does. In this lab you write the recipe (a Dockerfile) that describes how to package the Streamlit app **and its pre-trained model files** into one self-contained container image.

---

## Prerequisites

### Docker Installation

Verify Docker is installed and running on your machine before proceeding.

> **🪟 Windows / 🍎 macOS:** Install [Docker Desktop](https://www.docker.com/products/docker-desktop/). After installation, open Docker Desktop and wait until the whale icon in the system tray shows "Docker Desktop is running".
>
> **🐧 Linux:** Install Docker Engine following the [official docs](https://docs.docker.com/engine/install/). After installation, run `sudo systemctl start docker`.

Open a terminal and confirm:

```bash
docker --version
```

You should see output like `Docker version 27.x.x, build ...`. If you get "command not found", Docker is not installed or not in your PATH.

`[SCREENSHOT: Terminal showing docker --version output]`

### The Application Files

The build context is **already prepared** in this repo at `labs/M4_Lab3_Docker_Compose/app/`. Open that folder in VS Code:

```
labs/M4_Lab3_Docker_Compose/app/
├── app.py              Streamlit dashboard entry point (~200 lines)
├── requirements.txt    Pinned Python dependencies (streamlit, pandas, xgboost, scikit-learn, ...)
├── Dockerfile          The file you'll learn to read + write in this lab
└── artifacts/          4 files (~1 MB) the app loads at startup
    ├── xgboost_model.pkl
    ├── encoder.pkl
    ├── scaler.pkl
    └── model_metadata.json
```

> **Why is there already a Dockerfile?** So you have a reference solution to compare against once you've written your own version. The walkthrough below recreates it from scratch — at the end you can diff your output against the committed one.

---

## Step 1: Understand What You're Containerising

Before writing any Docker instructions, understand what's going inside. Open `app.py` in VS Code and skim it:

```python
import streamlit as st
import pandas as pd
import joblib
import json

# Load 4 pre-trained artifacts from disk
model    = joblib.load('artifacts/xgboost_model.pkl')
encoder  = joblib.load('artifacts/encoder.pkl')
scaler   = joblib.load('artifacts/scaler.pkl')
metadata = json.load(open('artifacts/model_metadata.json'))

# Streamlit form → predict → display
...
```

The application is **deliberately self-contained**:

| File | Purpose | Goes inside the container? |
|---|---|---|
| `app.py` | Streamlit form + prediction logic | **Yes** |
| `requirements.txt` | Pinned Python packages the app needs | **Yes** (installed at build time) |
| `artifacts/xgboost_model.pkl` | The trained XGBoost classifier | **Yes** (loaded at startup) |
| `artifacts/encoder.pkl` | OneHotEncoder fitted on training categoricals | **Yes** |
| `artifacts/scaler.pkl` | StandardScaler fitted on training continuous features | **Yes** |
| `artifacts/model_metadata.json` | Feature names + column groupings the app uses to assemble the input matrix | **Yes** |

**Key insight:** because the artifacts are bundled into the image, the container is **standalone** — no calls out to S3, RDS, or MLflow at startup. Drop this image on any machine with Docker installed and it serves predictions. That's the whole point of a container.

---

## Step 2: Choose a Base Image

Every Dockerfile starts with a `FROM` instruction that specifies the base image — the starting point for your container. For a Python application, the official `python` images on Docker Hub are the standard choice.

There are three common variants. Here is how they compare:

| Base Image | Size (approx.) | Includes | Good For | Drawback |
|---|---|---|---|---|
| `python:3.12` | ~900 MB | Full Debian OS, C compilers, system libraries | Apps that compile C extensions during install | Large image, slow to push/pull |
| `python:3.12-slim` | ~150 MB | Minimal Debian OS, Python only | Most production apps including ML | May need to add system packages manually |
| `python:3.12-alpine` | ~50 MB | Alpine Linux, Python only | Tiny microservices with no C dependencies | Many ML libraries (numpy, scikit-learn, xgboost) fail to install because they expect Debian-based system libraries |

**Our choice: `python:3.12-slim`**

The slim variant is the sweet spot for ML applications. It is small enough to push and pull quickly, yet compatible with every package in our `requirements.txt`. Alpine looks tempting because of its tiny size, but installing numpy, scikit-learn, and xgboost on Alpine often requires compiling from source (adding 10+ minutes to the build and sometimes failing outright). Avoid it for ML workloads.

> **Why 3.12 and not 3.12.10?** Docker Hub tags like `python:3.12-slim` resolve to the latest patch version in the 3.12 series. At the time of writing, that is 3.12.10. If you need to pin the exact patch version, you can use `python:3.12.10-slim`, but `python:3.12-slim` is the more common convention in Dockerfiles.

---

## Step 3: Write the Dockerfile

From a terminal:

```bash
cd labs/M4_Lab3_Docker_Compose/app
```

Open the existing `Dockerfile` in VS Code. It looks like this:

```dockerfile
# FreshBasket Delay Predictor -- Streamlit Dashboard Image
# Loads pre-trained .pkl artifacts directly from ./artifacts/. No DB / S3 / MLflow.
#
# Build:   docker build -t freshbasket-dashboard .
# Run:     docker run -p 8501:8501 freshbasket-dashboard

FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (layer caching: edits to app.py / artifacts don't bust this layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code AND artifacts/ (the .pkl files the app loads at startup)
COPY app.py ./
COPY artifacts/ ./artifacts/

EXPOSE 8501

# Health check uses Python stdlib (python:3.12-slim doesn't ship curl)
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8501/_stcore/health', timeout=3).status == 200 else 1)"

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true", "--browser.gatherUsageStats=false"]
```

`[SCREENSHOT: VS Code showing the complete Dockerfile with syntax highlighting]`

### Instruction-by-Instruction Explanation

Work through the Dockerfile from top to bottom. Each non-comment instruction creates a new **layer** in the image.

**`FROM python:3.12-slim`**
Start with the official Python 3.12 slim image. Think of it as "start with a clean Linux machine that already has Python installed."

**`WORKDIR /app`**
Sets the current directory inside the container to `/app`. All subsequent `COPY`, `RUN`, and `CMD` instructions execute relative to this path. If the directory does not exist, Docker creates it automatically.

**`COPY requirements.txt .`**
Copies the `requirements.txt` file from your local machine (the build context) into the container's `/app` directory. We copy this file **alone**, before copying source code, for a layer-caching reason explained in the discussion below.

**`RUN pip install --no-cache-dir -r requirements.txt`**
Runs `pip install` inside the container during the build. The `--no-cache-dir` flag prevents pip from storing download caches in the image, saving ~150 MB. This is the slowest step (typically 60-90 seconds) because it downloads streamlit, pandas, scikit-learn, xgboost, joblib, and all their sub-dependencies.

**`COPY app.py ./`**
Copies the single Python source file into the container's `/app`.

**`COPY artifacts/ ./artifacts/`**
Copies the entire `artifacts/` folder (4 files, ~1 MB) into `/app/artifacts/`. Without this line, the container would start but immediately crash on `joblib.load('artifacts/xgboost_model.pkl')` — file not found. The container has its own filesystem, isolated from your laptop's, so the artifacts have to be explicitly copied in.

**`EXPOSE 8501`**
Documents that the container listens on port 8501. This does not actually open the port — it is metadata that tells other developers (and tools like docker-compose, Kubernetes, ECS) which port the app uses.

**`HEALTHCHECK --interval=30s ... CMD python -c "..."`**
Tells Docker how to verify the container is healthy. Every 30 seconds, Docker runs the Python one-liner inside the container. It hits Streamlit's built-in `/_stcore/health` endpoint via `urllib.request`. If three consecutive checks fail, Docker marks the container as "unhealthy" — valuable in orchestrators like ECS (M5).

> **Why Python urllib and not curl?** The `python:3.12-slim` base image does **not** include curl. A `HEALTHCHECK CMD curl ...` would error out with "command not found" on every check, and the container would always be marked unhealthy even when it's actually serving fine. You could `RUN apt-get install -y curl` to add it, but that adds ~10 MB to the image. Using Python's stdlib `urllib.request` instead is zero-cost — Python is already in the image.

**`CMD ["streamlit", "run", "app.py", ...]`**
The default command that runs when a container starts. Flags worth knowing:
- `--server.port=8501` — bind to the port we EXPOSE'd
- `--server.address=0.0.0.0` — **critical**. Without it, Streamlit listens only on `localhost` inside the container, which means no traffic from outside can reach it. `0.0.0.0` means "all network interfaces"
- `--server.headless=true` — don't try to open a browser window (there isn't one inside a container)
- `--browser.gatherUsageStats=false` — disable anonymous usage telemetry

---

## Step 4: Create a .dockerignore File

When you run `docker build`, Docker sends the entire directory (the "build context") to the Docker daemon. If your project contains large unused files like `.venv/`, `.git/`, or local Jupyter notebooks, the build context becomes unnecessarily large and the build slows down.

The repo already includes `.dockerignore` at `labs/M4_Lab3_Docker_Compose/.dockerignore`. A typical content:

```
# Virtual environments -- never ship these into a container
.venv/
venv/

# Python bytecode caches
__pycache__/
*.pyc
*.pyo

# Git metadata
.git/
.gitignore

# Editors / IDEs
.vscode/
.idea/
*.swp

# Documentation (not needed inside the container)
*.md
```

**Why this matters:** Without `.dockerignore`, a `.venv` folder alone can add 500+ MB to your build context (you've already pip-installed everything once locally — those 500 MB are sitting in `.venv/`). With it, Docker only sends the files the Dockerfile actually needs.

For our `app/` folder the difference isn't huge (no `.venv/` here), but the habit matters for projects where the dev workspace IS the build context.

---

## Step 5: Verify Your File Structure

Before moving to Lab 2 (where you will build the image), confirm your folder looks exactly like this:

```
labs/M4_Lab3_Docker_Compose/app/
├── Dockerfile              The recipe you walked through in Step 3
├── app.py                  Streamlit dashboard
├── requirements.txt        Python dependencies
└── artifacts/              The 4 files the app loads at startup
    ├── xgboost_model.pkl
    ├── encoder.pkl
    ├── scaler.pkl
    └── model_metadata.json
```

> **🪟 Windows note:** Windows Explorer hides files that start with a dot by default. To see `.dockerignore` (it's one level above, in `labs/M4_Lab3_Docker_Compose/`), open the folder in VS Code's Explorer panel, or enable "Show hidden files" in Windows Explorer (View > Show > Hidden items).

`[SCREENSHOT: VS Code Explorer panel showing the app/ folder with all files visible]`

---

## Discussion: Why Layer Ordering Matters

The order of instructions in your Dockerfile is not arbitrary. Docker caches each layer. When you rebuild the image, Docker reuses cached layers from the top until it hits a layer whose inputs have changed — then it rebuilds that layer and everything below it.

Consider two scenarios:

### Scenario 1: You edited `app.py` (changed a chart title)

```
FROM python:3.12-slim          ✅ cached (unchanged)
WORKDIR /app                   ✅ cached (unchanged)
COPY requirements.txt .        ✅ cached (requirements.txt unchanged)
RUN pip install ...            ✅ cached (same requirements)
COPY app.py ./                 ❌ REBUILD (app.py changed)
COPY artifacts/ ./artifacts/   ❌ rebuild (below changed layer)
EXPOSE 8501                    ❌ rebuild
HEALTHCHECK ...                ❌ rebuild
CMD ...                        ❌ rebuild
```

**Result:** The slow `pip install` step is skipped. Rebuild takes **5-10 seconds**.

### Scenario 2: You added a new package to `requirements.txt`

```
FROM python:3.12-slim          ✅ cached
WORKDIR /app                   ✅ cached
COPY requirements.txt .        ❌ REBUILD (requirements.txt changed)
RUN pip install ...            ❌ REBUILD (must re-install)
COPY app.py ./                 ❌ rebuild
COPY artifacts/ ./artifacts/   ❌ rebuild
EXPOSE 8501                    ❌ rebuild
HEALTHCHECK ...                ❌ rebuild
CMD ...                        ❌ rebuild
```

**Result:** The pip install runs again. Rebuild takes **60-120 seconds**. But this is rare — you change dependencies far less often than source code.

### What if we had copied everything at once?

If the Dockerfile used a single `COPY . .` instead of separating `requirements.txt` from the source files, then **every** source code change would invalidate the pip install cache. You'd wait 60-120 seconds on every single rebuild, even for a one-character typo fix. The two-step copy pattern avoids this.

---

## Checkpoint

Before moving to Lab 2, verify:

- [ ] You can locate the Dockerfile at `labs/M4_Lab3_Docker_Compose/app/Dockerfile`.
- [ ] You can explain why `COPY requirements.txt .` comes **before** `COPY app.py ./`.
- [ ] You can explain why the Dockerfile uses Python `urllib.request` (not curl) for the healthcheck.
- [ ] You can explain what `--server.address=0.0.0.0` does and why it matters.
- [ ] Docker Desktop (or Docker Engine) is running on your machine.

---

## What Comes Next

In **Lab 2** you will build this Dockerfile into an image, run it as a container, test the dashboard in your browser, and explore container inspection commands (`docker logs`, `docker exec`, `docker history`). The Dockerfile you reviewed here is the input — `docker build` is the tool that turns it into a runnable image.

---

*FreshBasket Logistics -- Pune | Module 4, Lab 1 of 4*
