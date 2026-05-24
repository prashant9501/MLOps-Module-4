# M4 Lab 1: Write a Dockerfile for the Truck Delay App

**Module 4 -- Containerization with Docker | Spine Project: Truck Delay Classification**

> **Just want to ship it end-to-end?** See [M4_Docker_End_to_End_Student_Guide.md](M4_Docker_End_to_End_Student_Guide.md) — single doc covering install → build → push → sanity check across Windows / macOS / Linux. This lab is the deep dive on the Dockerfile itself.

| Detail | Value |
|---|---|
| Duration | 45 minutes |
| Difficulty | Beginner |
| Tools | Docker Desktop (Windows/Mac) or Docker Engine (Linux), VS Code |
| Prerequisite | The four Streamlit-app files from Module 3 Lab E available on disk (you don't need to have *run* M3; just clone the M3 repo) |
| Builds Toward | Lab 2 (build and run), Lab 3 (push to ECR) |

---

## Learning Objectives

By the end of this lab you will be able to:

1. Explain the purpose of each core Dockerfile instruction (FROM, WORKDIR, COPY, RUN, EXPOSE, CMD).
2. Choose an appropriate Python base image for an ML application.
3. Order Dockerfile layers to maximise build-cache efficiency.
4. Create a `.dockerignore` file to keep the build context small.

---

## Business Context

Priya's FreshBasket logistics team in Pune is happy with the Streamlit dashboard from Module 3 -- it shows truck delay predictions across their fleet. But deployment was painful: every time a new team member or server needed the app, someone spent 20+ minutes installing Python, pip-installing libraries, configuring environment variables, and debugging version mismatches. Arjun asked during the last standup: *"Can we just package this thing once and run it anywhere?"* That is exactly what Docker does. In this lab you will write the recipe (a Dockerfile) that describes how to package the Streamlit app into a container image.

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

### Module 3 Lab E Files

You need the five files from the Module 3 Lab E Streamlit project. **You don't need to have run M3** — just clone the [Module 3 repo](https://github.com/prashant9501/MLOps-Module-3) and copy the files from `labs/M3_Lab_E_Streamlit_Deployment/` into a new working directory for this lab:

```
truck-delay-docker/
    app.py                  # Streamlit dashboard entry point
    config.py               # Centralised configuration (DB, S3, features)
    utils.py                # Helper functions (model loading, demo data)
    batch_score.py          # Batch scoring script (NOT containerised)
    requirements.txt        # Python dependencies
```

> **Missing files?** Clone the [Module 3 repo](https://github.com/prashant9501/MLOps-Module-3) and copy them from `labs/M3_Lab_E_Streamlit_Deployment/`. You don't need to have completed Module 3 — every step in *this* lab uses the files in `DEMO_MODE=true`, so the dashboard runs without any AWS resources.

---

## Step 1: Review the Application You Are Containerising

Before writing any Docker instructions, understand what you are packaging. Open each file in VS Code and remind yourself what it does:

| File | Purpose | Runs Inside Container? |
|---|---|---|
| `app.py` | Streamlit dashboard -- the main entry point users interact with | Yes |
| `config.py` | Reads environment variables for DB host, S3 bucket, feature lists, demo mode flag | Yes |
| `utils.py` | Model loading from S3, database queries, synthetic demo data generation | Yes |
| `requirements.txt` | Lists all Python packages (streamlit, pandas, scikit-learn, xgboost, etc.) | Yes (installed at build time) |
| `batch_score.py` | Standalone batch scoring script run on a schedule -- NOT part of the dashboard | No |

**Key insight:** `batch_score.py` is a separate operational script that runs independently (e.g., via a cron job or Airflow). It does not belong inside the dashboard container. We will leave it out.

The application has a **demo mode** built into `config.py`. When the environment variable `DEMO_MODE` is set to `true`, or when AWS services (RDS, S3) are unreachable, the app generates synthetic data and runs without any cloud dependencies. This means your container will work immediately on your laptop even without AWS credentials -- perfect for local development and testing.

---

## Step 2: Choose a Base Image

Every Dockerfile starts with a `FROM` instruction that specifies the base image -- the starting point for your container. For a Python application, the official `python` images on Docker Hub are the standard choice.

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

Create a new file called `Dockerfile` (no file extension) in your `truck-delay-docker/` directory. Open it in VS Code and add the following content:

```dockerfile
# ── FreshBasket Truck Delay Dashboard ──────────────────────────────
# Module 4, Lab 1 — Containerised Streamlit Application
#
# Build:  docker build -t truck-delay-app:v1 .
# Run:    docker run -d -p 8501:8501 truck-delay-app:v1

FROM python:3.12-slim

# ── 1. Set the working directory inside the container ──────────────
WORKDIR /app

# ── 2. Copy requirements FIRST (layer-caching optimisation) ───────
COPY requirements.txt .

# ── 3. Install Python dependencies ────────────────────────────────
RUN pip install --no-cache-dir -r requirements.txt

# ── 4. Install curl for the health check ──────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# ── 5. Copy application source code ──────────────────────────────
COPY app.py config.py utils.py ./

# ── 6. Expose Streamlit's default port ────────────────────────────
EXPOSE 8501

# ── 7. Health check (optional but recommended) ───────────────────
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# ── 8. Run the Streamlit application ─────────────────────────────
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

`[SCREENSHOT: VS Code showing the complete Dockerfile with syntax highlighting]`

### Instruction-by-Instruction Explanation

Work through the Dockerfile from top to bottom. Each instruction creates a new **layer** in the image.

**`FROM python:3.12-slim`**
This tells Docker to start with the official Python 3.12 slim image. Think of it as "start with a clean Linux machine that already has Python installed."

**`WORKDIR /app`**
Sets the current directory inside the container to `/app`. All subsequent `COPY`, `RUN`, and `CMD` instructions execute relative to this path. If the directory does not exist, Docker creates it automatically.

**`COPY requirements.txt .`**
Copies the `requirements.txt` file from your local machine (the build context) into the container's `/app` directory. We copy this file alone, before copying source code, for a reason explained in Step 5.

**`RUN pip install --no-cache-dir -r requirements.txt`**
Runs the pip install command inside the container during the build. The `--no-cache-dir` flag prevents pip from storing download caches, keeping the layer smaller. This is the slowest step (often 60-120 seconds) because it downloads and installs streamlit, pandas, scikit-learn, xgboost, and all their sub-dependencies.

**`RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf ...`**
Installs the `curl` command-line tool, which the health check uses. The `rm -rf /var/lib/apt/lists/*` at the end removes the package index files to save space.

**`COPY app.py config.py utils.py ./`**
Copies your three application files into the container. Notice that `batch_score.py` is intentionally excluded -- it is not part of the dashboard.

**`EXPOSE 8501`**
Documents that the container listens on port 8501. This does not actually open the port -- it is metadata that tells other developers (and tools like docker-compose) which port the app uses.

**`HEALTHCHECK ...`**
Tells Docker how to verify the container is healthy. Every 30 seconds, Docker runs the `curl` command against Streamlit's built-in health endpoint. If three consecutive checks fail, Docker marks the container as "unhealthy". This is valuable in production orchestrators like ECS (Module 5).

**`CMD ["streamlit", "run", "app.py", ...]`**
The default command that runs when a container starts. The `--server.address=0.0.0.0` flag is critical -- without it, Streamlit only listens on `localhost` inside the container, which means no traffic from outside can reach it.

---

## Step 4: Create a .dockerignore File

When you run `docker build`, Docker sends the entire directory (the "build context") to the Docker daemon. If your project directory contains large files like trained model binaries, CSV datasets, or the `.venv` virtual environment, the build context becomes unnecessarily large and the build slows down.

Create a file called `.dockerignore` (note the leading dot) in the same directory as your Dockerfile:

```
# Virtual environment -- never ship this into a container
.venv/

# Python bytecode caches
__pycache__/
*.pyc

# Git metadata
.git/
.gitignore

# Data files and model artifacts (loaded from S3 at runtime)
*.csv
*.pkl
*.sav
data/
models/

# Environment secrets (should use env vars instead)
.env

# Documentation (not needed inside the container)
*.md

# Batch scoring script (separate operational concern)
batch_score.py

# Jupyter notebook checkpoints
.ipynb_checkpoints/
```

**Why this matters:** Without `.dockerignore`, a `.venv` folder alone can add 500+ MB to your build context. With it, Docker only sends the files the Dockerfile actually needs -- in our case, just the Dockerfile itself, `requirements.txt`, and the three `.py` files. Build context drops from potentially hundreds of megabytes to under 100 KB.

---

## Step 5: Verify Your File Structure

Before moving to Lab 2 (where you will build the image), confirm your directory looks exactly like this:

```
truck-delay-docker/
    Dockerfile              # The recipe you wrote in Step 3
    .dockerignore           # Build context exclusions from Step 4
    app.py                  # Streamlit dashboard (from M3 Lab E)
    config.py               # Configuration file (from M3 Lab E)
    utils.py                # Utility functions (from M3 Lab E)
    batch_score.py          # Batch scorer (excluded from container)
    requirements.txt        # Python dependencies (from M3 Lab E)
```

> **🪟 Windows note:** Windows Explorer hides files that start with a dot by default. To see `.dockerignore`, open the folder in VS Code's Explorer panel, or enable "Show hidden files" in Windows Explorer (View > Show > Hidden items).

`[SCREENSHOT: VS Code Explorer panel showing all files in truck-delay-docker directory]`

---

## Discussion: Why Layer Ordering Matters

The order of instructions in your Dockerfile is not arbitrary. Docker caches each layer. When you rebuild the image, Docker reuses cached layers from the top until it hits a layer whose inputs have changed -- then it rebuilds that layer and everything below it.

Consider two scenarios:

### Scenario 1: You edited `app.py` (changed a chart title)

```
FROM python:3.12-slim          ✅ cached (unchanged)
WORKDIR /app                   ✅ cached (unchanged)
COPY requirements.txt .        ✅ cached (requirements.txt unchanged)
RUN pip install ...            ✅ cached (same requirements)
RUN apt-get install curl ...   ✅ cached (same instruction)
COPY app.py config.py utils.py ❌ REBUILD (app.py changed)
EXPOSE 8501                    ❌ rebuild (below changed layer)
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
RUN apt-get install curl ...   ❌ rebuild
COPY app.py config.py utils.py ❌ rebuild
EXPOSE 8501                    ❌ rebuild
HEALTHCHECK ...                ❌ rebuild
CMD ...                        ❌ rebuild
```

**Result:** The pip install runs again. Rebuild takes **60-120 seconds**. But this is rare -- you change dependencies far less often than source code.

### What if we had copied everything at once?

If the Dockerfile used a single `COPY . .` instead of separating `requirements.txt` from the source files, then every source code change would invalidate the pip install cache. You would wait 60-120 seconds on every single rebuild, even for a one-character typo fix. The two-step copy pattern avoids this.

---

## Checkpoint

Before moving to Lab 2, verify:

- [ ] `Dockerfile` exists in your project directory with all 8 instructions.
- [ ] `.dockerignore` exists and excludes `.venv/`, data files, and `batch_score.py`.
- [ ] You can explain why `COPY requirements.txt .` comes before `COPY app.py config.py utils.py ./`.
- [ ] Docker Desktop (or Docker Engine) is running on your machine.

---

## What Comes Next

In **Lab 2** you will build this Dockerfile into an image, run it as a container, test the Streamlit dashboard in your browser, and explore container inspection commands. The Dockerfile you wrote here is the input -- `docker build` is the tool that turns it into a runnable image.

---

*FreshBasket Logistics -- Pune | Module 4, Lab 1 of 3*
