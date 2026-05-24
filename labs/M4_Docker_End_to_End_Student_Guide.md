# Module 4 — Docker End-to-End Student Walkthrough

**Containerise the Module 3 Truck Delay dashboard, push it to ECR, and prove the image runs anywhere.**

> Goal of this doc: a single walkthrough you can follow on your own machine — from installing Docker to having your image in AWS ECR + verified portable. The individual M4 labs ([Lab A](M4_Lab_A_AWS_Provisioning_from_Console.md), [Lab 1](M4_Lab1_Write_Dockerfile.md), [Lab 2](M4_Lab2_Build_Run_Test.md), [Lab 3](M4_Lab3_Push_to_ECR.md)) go deeper on each step; this doc is the "happy-path" tie-everything-together version.

> Format: every OS-specific step is marked **🪟 Windows / 🍎 macOS / 🐧 Linux**. Run the variant that matches your machine and skip the others.

---

## Table of contents

1. [What you'll build (and why)](#1-what-youll-build-and-why)
2. [Prerequisites](#2-prerequisites)
3. [Install Docker Desktop / Docker Engine](#3-install-docker-desktop--docker-engine)
4. [Verify Docker is working](#4-verify-docker-is-working)
5. [Stage the build context](#5-stage-the-build-context)
6. [Write the Dockerfile + .dockerignore](#6-write-the-dockerfile--dockerignore)
7. [Build the image](#7-build-the-image)
8. [Run + test locally](#8-run--test-locally)
9. [Create the ECR repository](#9-create-the-ecr-repository)
10. [Tag + push the image to ECR](#10-tag--push-the-image-to-ecr)
11. [Sanity check — pull from ECR + run](#11-sanity-check--pull-from-ecr--run)
12. [Teardown](#12-teardown)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. What you'll build (and why)

By the end of this walkthrough, you'll have:

- **Docker Desktop running on your laptop** — `docker info` returns a Server block
- **A built image** locally: `truck-delay-app:v1` (~600 MB compressed, runs the self-contained FreshBasket Delay Predictor)
- **The same image in AWS ECR** under a private repository in your account
- **Proof that the image is portable** — you can delete it locally, pull it back from ECR, and the dashboard still runs

This is the **artifact M5 deploys to ECS Fargate.** Everything else in M5 (ALB, CI/CD, autoscaling) assumes this ECR image exists.

### The end-state architecture

```
Your laptop                                         AWS account
─────────────                                       ─────────────
  labs/M4_Lab4_Docker_Compose/app/                  ┌──────────────────┐
    ├── app.py                                      │  ECR repo         │
    ├── artifacts/  (4 pre-trained .pkl + JSON)     │  truck-delay-app  │
    ├── requirements.txt                            │   :v1             │ ── M5 pulls
    └── Dockerfile                                  │   :latest         │
       │                                            │                  │
       ▼                                            └──────────────────┘
  docker build  →  truck-delay-app:v1                      ▲
                          │                                │
                          └────────── docker push ─────────┘
```

---

## 2. Prerequisites

| What | Why | Verify |
|---|---|---|
| This repo cloned | The app + its artifacts + the Dockerfile all live in `labs/M4_Lab4_Docker_Compose/app/` | `ls labs/M4_Lab4_Docker_Compose/app/` shows app.py + Dockerfile + requirements.txt + artifacts/ |
| An AWS account with admin or ECR full-access permissions | Section 9 creates an ECR repo; Section 10 pushes the image | `aws sts get-caller-identity` (after AWS CLI is installed) |
| AWS CLI v2 installed and configured | Sections 9-11 use it | `aws --version` returns 2.x |
| ~10 GB free disk space | Docker images + cache + WSL2 distro can eat space | Self-check |
| Internet connection | Image pulls + ECR push | Self-check |

> **You do NOT need to have completed M3** to do M4. The pre-trained .pkl files in `app/artifacts/` were exported from M3 once and are version-controlled with this repo. Just clone and you're ready.

---

## 3. Install Docker Desktop / Docker Engine

### 🪟 Windows (10 or 11)

Docker Desktop on Windows requires **WSL2** (Windows Subsystem for Linux 2). If you're on Windows Pro/Enterprise, Hyper-V is the alternative — but WSL2 is the default and works on every edition including Home.

**Step 1 — Enable WSL2** (admin PowerShell):

```powershell
# Open PowerShell as Administrator (right-click -> Run as administrator)
wsl --install
# This enables Virtual Machine Platform, enables Windows Subsystem for Linux,
# downloads the WSL2 kernel, sets WSL 2 as default, and installs Ubuntu.

# Reboot when prompted
Restart-Computer
```

After reboot, Ubuntu may auto-launch and ask you to create a username + password. You can set anything (Docker doesn't actually need you to use Ubuntu — it just needs the WSL2 backend installed).

Verify WSL is working:
```powershell
wsl --status
# Expected:
#   Default Distribution: Ubuntu
#   Default Version: 2
```

**Step 2 — Install Docker Desktop:**

1. Download from https://www.docker.com/products/docker-desktop/ → pick **AMD64** (works for both Intel and AMD x64 CPUs; pick ARM64 only if you have a Snapdragon-based Windows laptop).
2. Run the installer. During install, **leave "Use WSL 2 instead of Hyper-V" ticked** (the default).
3. After install completes, launch **Docker Desktop** from the Start Menu.
4. First launch takes ~60 seconds while WSL2 backend provisions.
5. Accept the Docker subscription agreement when prompted. You don't need a Docker Hub account.

System tray whale icon goes solid → Docker Desktop is running.

> **Edge case:** if `wsl --install` complained that the WSL service is "disabled or has no enabled devices" (`Wsl/0x80070422`), the OS-level WSL service is set to `Disabled` start type. Fix from admin PowerShell:
> ```powershell
> Set-Service -Name WSLService -StartupType Manual
> Start-Service -Name WSLService
> wsl --status
> ```
> Then continue with Step 2.

### 🍎 macOS (Intel or Apple Silicon)

Docker Desktop on macOS uses a built-in Linux VM (via Hypervisor.framework) — no manual setup required.

1. Download from https://www.docker.com/products/docker-desktop/ → **pick the right architecture**:
   - **Apple Silicon** (M1/M2/M3/M4): "Docker Desktop for Mac with Apple silicon"
   - **Intel**: "Docker Desktop for Mac with Intel chip"
   - Don't pick the wrong one — installer will refuse to run on the wrong CPU.
   - Check which one you have: Apple menu → About This Mac → look for "Chip" (Apple) or "Processor" (Intel).
2. Open the `.dmg`, drag Docker to Applications.
3. Launch Docker from Launchpad. Accept the agreement.
4. First launch takes ~30 seconds. Whale icon appears in the menu bar.

Alternative (CLI install via Homebrew):
```bash
brew install --cask docker
open /Applications/Docker.app
```

### 🐧 Linux (Ubuntu 22.04 / 24.04 — the common case)

Linux runs Docker Engine **natively** — no Docker Desktop required (though it's available if you prefer the GUI). For server use, Docker Engine is simpler.

**Docker Engine via the official apt repo** (Ubuntu/Debian):

```bash
# Remove any older docker.io / podman-docker that may conflict
sudo apt-get remove docker docker-engine docker.io containerd runc 2>/dev/null

# Install prerequisites
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg

# Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repo
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Run docker without sudo (one-time setup)
sudo usermod -aG docker $USER
newgrp docker     # apply group change to current shell, or log out + back in

# Confirm
docker --version
```

For Fedora / RHEL / other distros, see https://docs.docker.com/engine/install/.

> **Linux Docker is rootless-friendly.** Adding yourself to the `docker` group as above is the most common dev setup. For production, look into [rootless mode](https://docs.docker.com/engine/security/rootless/).

---

## 4. Verify Docker is working

Open a fresh terminal (Linux/macOS) or PowerShell (Windows) and run:

```bash
docker --version
# Expected: Docker version 26.x or newer

docker info | head -20
# Expected: a Client: block AND a Server: block with Server Version, OS, Architecture
```

If `docker info` shows the Client block but no Server block (or an "Cannot connect to the Docker daemon" error), the daemon isn't running. Re-open Docker Desktop and wait for the whale icon to go solid before continuing.

Run the canonical "is docker really working" test:

```bash
docker run --rm hello-world
```

Expected:
```
Hello from Docker!
This message shows that your installation appears to be working correctly.
...
```

If that works, Docker is ready. Move on.

---

## 5. The build context — already staged in this repo

The **build context** is the folder Docker uses as input — every file in it is sent to the Docker daemon when you run `docker build`. For this module, **the build context is already prepared** at:

```
labs/M4_Lab4_Docker_Compose/app/
```

Contents (you'll see this after cloning the repo):

```
labs/M4_Lab4_Docker_Compose/app/
├── app.py              ← FreshBasket Streamlit Delay Predictor (~200 lines)
├── requirements.txt    ← Pinned Python deps (streamlit, pandas, xgboost, ...)
├── Dockerfile          ← (Section 6 walks through what it does)
└── artifacts/          ← 4 files (~1 MB total) the app loads at startup
    ├── xgboost_model.pkl
    ├── encoder.pkl
    ├── scaler.pkl
    └── model_metadata.json
```

> **Why pre-stage?** Earlier versions of this module had students copy 4 files from a different Module 3 lab. The simpler self-contained app makes M4 standalone — clone this repo, `cd` into `app/`, and you're ready to build.

Move into the build context for the rest of the walkthrough:

### 🪟 Windows (PowerShell from the repo root)

```powershell
cd "labs\M4_Lab4_Docker_Compose\app"
Get-ChildItem
```

### 🍎 macOS / 🐧 Linux (bash from the repo root)

```bash
cd labs/M4_Lab4_Docker_Compose/app
ls -la
```

---

## 6. The Dockerfile + .dockerignore

A `Dockerfile` already lives in `app/`. Here's what it looks like + why each line is the way it is. You don't have to write this from scratch — but you should be able to read it.

### `Dockerfile`

```dockerfile
# FreshBasket Delay Predictor -- Streamlit Dashboard Image
# Loads pre-trained .pkl artifacts directly from ./artifacts/. No DB / S3 / MLflow.
#
# Build: docker build -t truck-delay-app:v1 .
# Run:   docker run -d -p 8501:8501 truck-delay-app:v1

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

**Why this Dockerfile is the way it is:**

| Decision | Reason |
|---|---|
| `FROM python:3.12-slim` | "slim" variant = ~75 MB base. Has everything Python needs but excludes docs/dev tools. Don't use `alpine` for ML — numpy/scikit-learn wheels rarely work on Alpine and you'll end up compiling from source. |
| `COPY requirements.txt` BEFORE the source | Docker layer caching. If you edit `app.py` but not requirements, the slow `pip install` layer is reused — rebuilds drop from ~60 s to <5 s. |
| `--no-cache-dir` on pip | Saves ~150 MB in the final image (the pip download cache isn't needed at runtime). |
| `COPY artifacts/ ./artifacts/` | The app calls `joblib.load('artifacts/xgboost_model.pkl')` at startup. Without this line, the container starts then crashes immediately. |
| Python-stdlib healthcheck (not curl) | The `python:slim` base image doesn't include curl. A curl-based healthcheck would always fail silently. `python -c "import urllib.request..."` is always available. |
| `--server.address=0.0.0.0` | Streamlit defaults to `127.0.0.1` (localhost), which is unreachable from outside the container. `0.0.0.0` binds all interfaces so `docker run -p 8501:8501` works. |
| `--server.headless=true` + `--browser.gatherUsageStats=false` | Suppresses the "open a browser?" prompt at startup and disables anonymous telemetry. Both are nice-to-haves for container deployments. |

### `.dockerignore`

```
.venv/
venv/
__pycache__/
*.pyc
.git/
.idea/
.vscode/
*.md
```

**Why each entry:**
- `.venv/` / `venv/` — local Python virtualenvs can be 500+ MB. Don't ship them; the container has its own Python install.
- `__pycache__/` / `*.pyc` — bytecode caches, regenerated on first import.
- `.git/` — your local Git history. Useless inside the image, often hundreds of MB.
- `*.md` — documentation files. Helpful on disk, unnecessary in the image.

---

## 7. Build the image

From inside the `Module 4/build/truck-delay-docker/` folder:

```bash
docker build -t truck-delay-app:v1 .
```

The `-t` flag tags the resulting image with `truck-delay-app:v1`. The trailing `.` means "the build context is the current directory".

### What you'll see (~2-3 minutes total)

```
[+] Building 130.5s (10/10) FINISHED
 => [internal] load build definition from Dockerfile                       0.1s
 => [internal] load metadata for docker.io/library/python:3.12-slim        1.5s
 => [internal] load .dockerignore                                          0.1s
 => CACHED [1/5] FROM python:3.12-slim                                     0.0s
 => [internal] load build context                                          0.2s
 =>   transferring context: 39.4kB                                         0.1s
 => [2/5] WORKDIR /app                                                     0.3s
 => [3/5] COPY requirements.txt .                                          0.1s
 => [4/5] RUN pip install --no-cache-dir -r requirements.txt              65.2s    ← slowest step
 => [5/6] COPY app.py ./                                                   0.1s
 => [6/6] COPY artifacts/ ./artifacts/                                     0.5s
 => exporting to image                                                    37.6s
 => => exporting layers                                                   37.6s
 => => writing image sha256:80e6...                                        0.0s
 => => naming to docker.io/library/truck-delay-app:v1                      0.0s
```

The pip install step pulls Streamlit + pandas + numpy + scikit-learn + xgboost + MLflow + ~70 transitive dependencies. ~65 seconds is typical on a decent connection — first build is the slowest, subsequent ones are dramatically faster because of layer caching.

### Verify the image exists

```bash
docker images truck-delay-app
```

Expected:
```
REPOSITORY        TAG   IMAGE ID       CREATED          SIZE
truck-delay-app   v1    80e6ee996796   2 minutes ago    ~600 MB content / ~2 GB on disk
```

The "size" varies by Docker version — what matters is the IMAGE ID exists.

---

## 8. Run + test locally

Test the image locally before pushing to ECR — quickest feedback loop.

```bash
docker run -d -p 8501:8501 --name td truck-delay-app:v1
```

What the flags mean:
- `-d` — detached (runs in the background; returns the container ID)
- `-p 8501:8501` — map host port 8501 → container port 8501
- `--name td` — short name for the container so you can manage it without typing the ID

(No env vars needed — the app reads everything from `./artifacts/` baked into the image.)

### Wait for Streamlit to bind the port (cold start ~10-15 seconds)

```bash
# Wait
sleep 15      # macOS / Linux
# (PowerShell: Start-Sleep -Seconds 15)

# Check status
docker ps --filter "name=td"
```

Expected:
```
CONTAINER ID   IMAGE                 COMMAND                  STATUS         PORTS                    NAMES
3e23ec8728e6   truck-delay-app:v1    "streamlit run app..."   Up 15 seconds  0.0.0.0:8501->8501/tcp   td
```

### Health-check it from the CLI before opening a browser

```bash
curl -sI http://localhost:8501/_stcore/health
```

Expected:
```
HTTP/1.1 200 OK
Server: TornadoServer/6.5.5
Content-Type: text/html; charset=UTF-8
```

If you see `200 OK`, Streamlit is ready. **Now** open the browser:

**http://localhost:8501**

You should see the FreshBasket Delivery Delay Predictor:
- A form with three columns: 🛣️ Trip & Route Info, 🚛 Driver & Truck Info, 🌤️ Weather Conditions
- A blue **"Predict Delay Risk"** button at the bottom
- Click it with any sample inputs — you'll get a coloured result panel (✅ On Time or ⚠️ At Risk Of Delay) with a probability percentage

> **`ERR_CONNECTION_REFUSED` in the browser?** You opened it before Streamlit finished cold-starting (or the container has already been stopped). Re-run the curl health check first; once it returns 200, hard-refresh the browser with **Ctrl+F5** (or **Cmd+Shift+R** on Mac) since Chrome briefly caches connection refusals.

### Inspect the container logs (debugging tool you'll use often)

```bash
docker logs td

# Or tail in real-time:
docker logs -f td     # Ctrl+C to stop tailing
```

### Stop + remove the test container

When you've eyeballed the dashboard:

```bash
docker stop td
docker rm td
```

The **image** stays on disk — we're about to push it to ECR.

---

## 9. Create the ECR repository

ECR (Elastic Container Registry) is AWS's private Docker registry. Each ECR repository holds all versions of one image, identified by tags.

> **Did you do Lab A ([M4_Lab_A_AWS_Provisioning_from_Console.md](M4_Lab_A_AWS_Provisioning_from_Console.md))?** If yes, the repo already exists — skip to Section 10 with the URI you noted from that lab.

### Verify your AWS CLI is configured

```bash
aws sts get-caller-identity
```

Expected output (your account ID + IAM ARN):
```json
{
  "UserId":  "AIDA...",
  "Account": "<YOUR_AWS_ACCOUNT_ID>",
  "Arn":     "arn:aws:iam::<YOUR_AWS_ACCOUNT_ID>:user/<your-user>"
}
```

If this fails with "Unable to locate credentials", run `aws configure` and enter your access key + secret + region.

### Create the ECR repo

```bash
# Pick a region (same region you'll use in M5 for ECS)
REGION=ap-south-1     # ap-south-1 (Mumbai) is the M3/M5 default

aws ecr create-repository \
    --repository-name truck-delay-app \
    --region $REGION \
    --image-scanning-configuration scanOnPush=true \
    --query "repository.repositoryUri" \
    --output text
```

Expected output (one line — write it down):
```
<YOUR_AWS_ACCOUNT_ID>.dkr.ecr.ap-south-1.amazonaws.com/truck-delay-app
```

That's your **ECR repository URI**. Section 10 needs it.

### Add a lifecycle policy (recommended)

Without this, every push adds another ~600 MB image to ECR forever — your storage bill grows monotonically. The lifecycle policy below keeps only the 5 most recent images and auto-deletes the rest.

```bash
aws ecr put-lifecycle-policy \
    --repository-name truck-delay-app \
    --region $REGION \
    --lifecycle-policy-text '{
      "rules": [{
        "rulePriority": 1,
        "description":  "Keep only the 5 most recent images",
        "selection":    {"tagStatus":"any","countType":"imageCountMoreThan","countNumber":5},
        "action":       {"type":"expire"}
      }]
    }'
```

Lifecycle runs daily — after 5+ images exist, the oldest gets cleaned up automatically.

---

## 10. Tag + push the image to ECR

Three sub-steps: authenticate Docker to ECR, tag the local image with the ECR URI, push.

### Step 10.1 — Docker login to ECR

```bash
REGION=ap-south-1
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)

aws ecr get-login-password --region $REGION \
    | docker login --username AWS --password-stdin \
        $ACCOUNT.dkr.ecr.$REGION.amazonaws.com
```

Expected:
```
Login Succeeded
```

**🪟 PowerShell variant:**
```powershell
$REGION  = "ap-south-1"
$ACCOUNT = aws sts get-caller-identity --query Account --output text

aws ecr get-login-password --region $REGION | `
    docker login --username AWS --password-stdin "$ACCOUNT.dkr.ecr.$REGION.amazonaws.com"
```

The login token is valid for 12 hours. After that, re-run this command.

### Step 10.2 — Tag the local image

Docker images need to be tagged with the full registry URI before they can be pushed:

```bash
ECR_URI=$ACCOUNT.dkr.ecr.$REGION.amazonaws.com/truck-delay-app

docker tag truck-delay-app:v1 $ECR_URI:v1
docker tag truck-delay-app:v1 $ECR_URI:latest

docker images "$ECR_URI"
```

The `latest` tag is convention — many tools default to pulling `:latest` when no tag is specified. The `:v1` tag is the canonical version pin.

> **What `docker tag` actually does:** it creates a second name pointing at the **same image data**. No copying happens. You can see this in `docker images` — both tags have the same IMAGE ID.

### Step 10.3 — Push

```bash
docker push $ECR_URI:v1
docker push $ECR_URI:latest
```

Expected (truncated):
```
The push refers to repository [<account>.dkr.ecr.ap-south-1.amazonaws.com/truck-delay-app]
e6d249f228d6: Pushed
e113665b194b: Pushed
6ee81f006120: Pushed
5b4d6ff92fc4: Pushed
... (a layer per RUN/COPY instruction)
v1: digest: sha256:80e6...d8bd0c size: 856
```

Push time depends on your **upload** bandwidth:
- 100 Mbps: ~50 seconds
- 25 Mbps: ~3-4 minutes
- 10 Mbps: ~8-10 minutes

The `latest` push is **instant** (1-2 seconds) because every layer already exists in ECR from the `v1` push moments earlier.

### Step 10.4 — Verify the image is in ECR

```bash
aws ecr describe-images \
    --repository-name truck-delay-app \
    --region $REGION \
    --query "imageDetails[].{Tags:imageTags, Pushed:imagePushedAt, Size:imageSizeInBytes}" \
    --output table
```

You should see one tagged manifest with both `v1` and `latest`, plus potentially one or two untagged manifests (Docker 26+/buildx attaches OCI provenance attestations — that's normal, not extra storage cost).

Or open the AWS Console:
**https://`<region>`.console.aws.amazon.com/ecr/private-registry/repositories/truck-delay-app**

You'll see your image with both tags, push timestamp, and the image scan results (Amazon Inspector runs automatically because we set `scanOnPush=true`).

---

## 11. Sanity check — pull from ECR + run

This step proves the image is genuinely portable — it can run on any machine with Docker + ECR access.

### Step 11.1 — Delete the local copy

```bash
docker rmi truck-delay-app:v1 $ECR_URI:v1 $ECR_URI:latest
docker images truck-delay-app
# Expected: (empty -- no local copies of this image anymore)
```

### Step 11.2 — Pull from ECR

```bash
docker pull $ECR_URI:v1
```

Expected:
```
v1: Pulling from truck-delay-app
... (downloads each layer)
Status: Downloaded newer image for <account>.dkr.ecr.ap-south-1.amazonaws.com/truck-delay-app:v1
```

Pull time is similar to push time (depends on **download** bandwidth this time).

### Step 11.3 — Run from the pulled image

```bash
docker run -d -p 8501:8501 --name td $ECR_URI:v1

sleep 15
curl -sI http://localhost:8501/_stcore/health
# Expected: HTTP/1.1 200 OK
```

Open `http://localhost:8501` in your browser — same dashboard you saw in Section 8, but this time the bytes came from AWS ECR rather than your local build.

### Step 11.4 — Tear down

```bash
docker stop td
docker rm td
```

---

## 12. Teardown

ECR storage costs ~$0.10/GB/month (~₹8/GB/month) — one image at ~600 MB is ~₹5/month. The lifecycle policy keeps it capped. **Not free, but very cheap.**

If you want to delete everything M4 created:

```bash
REGION=ap-south-1

# 1. Delete the ECR repo (--force lets you delete even if it has images)
aws ecr delete-repository \
    --repository-name truck-delay-app \
    --region $REGION \
    --force

# 2. Remove all local Docker artifacts for this image
docker rmi truck-delay-app:v1 2>/dev/null || true
docker images | grep truck-delay-app | awk '{print $3}' | xargs -r docker rmi 2>/dev/null || true

# 3. Reclaim Docker layer cache (optional, frees significant disk)
docker builder prune --all --force
```

> **Keep the ECR repo for M5.** Module 5 Lab A uses this exact image as the ECS Fargate deployment source. Only run the teardown above if you're stopping after M4 entirely.

---

## 13. Troubleshooting

### Docker installation / startup

| Symptom (any OS) | Cause | Fix |
|---|---|---|
| `docker info` shows Client but no Server | Daemon not running | Start Docker Desktop (Win/Mac) or `sudo systemctl start docker` (Linux) and wait for it to be ready |
| `Cannot connect to the Docker daemon` | Same as above | Same fix |

#### 🪟 Windows-specific

| Symptom | Cause | Fix |
|---|---|---|
| `wsl --install` fails with `Wsl/0x80070422` | WSL service set to Disabled | Admin PowerShell: `Set-Service WSLService -StartupType Manual; Start-Service WSLService` |
| Docker Desktop installer fails: "Cannot create a file when that file already exists" | Leftover files from a previous install | Admin PowerShell: `Remove-Item -Recurse -Force "C:\Program Files\Docker"` and re-run the installer |
| Docker Desktop launches but stays on "Starting..." for >5 min | WSL2 backend stuck | Quit Docker Desktop → `wsl --shutdown` → relaunch |
| `docker run` hangs / "no route to host" inside container | VPN intercepting Docker's virtual network | Disable VPN temporarily, or add Docker's subnets to your VPN's split-tunnel exclusions |

#### 🍎 macOS-specific

| Symptom | Cause | Fix |
|---|---|---|
| Installer refuses to run: "wrong architecture" | Downloaded the wrong installer (Intel vs Apple Silicon) | Re-download the matching one (Apple menu → About This Mac → Chip vs Processor) |
| `docker pull` is very slow / times out | Apple Silicon downloading AMD64 image and emulating | Add `--platform linux/amd64` to your run command, or rebuild on the matching architecture |

#### 🐧 Linux-specific

| Symptom | Cause | Fix |
|---|---|---|
| `docker: permission denied` | User not in `docker` group | `sudo usermod -aG docker $USER` then **log out and log back in** (group changes only apply to new shells) |
| `docker build` fails: "cgroups: cannot find cgroup mount destination: unknown" | Old cgroups v1 vs v2 mismatch (rare on modern distros) | Update Docker: `sudo apt update && sudo apt install --only-upgrade docker-ce` |

### Build issues

| Symptom | Cause | Fix |
|---|---|---|
| Build fails at `pip install`: "could not find a version that satisfies the requirement..." | Wrong Python in base image, or pinned versions incompatible | Confirm the Dockerfile uses `FROM python:3.12-slim` and that `requirements.txt` is the one in `app/` (streamlit 1.32, xgboost 2.0.3, numpy<2.0) |
| Build fails: "no space left on device" | Docker disk quota full | `docker system prune -a -f` reclaims unused images + layers; Docker Desktop also has a "Resources → Disk image size" slider |
| Build is very slow (~10+ minutes for pip install) | Slow upstream PyPI mirror | Add `--index-url https://pypi.org/simple/` explicitly to the `pip install` line, or use Docker BuildKit with a network-cached registry |
| `COPY failed: file not found in build context: app.py` | The 4 source files aren't in the same folder as the Dockerfile | Re-run Section 5 to stage them correctly |

### Container runtime issues

| Symptom | Cause | Fix |
|---|---|---|
| Container exits immediately after start | Streamlit not binding to `0.0.0.0` | Confirm the Dockerfile CMD has `--server.address=0.0.0.0` (Section 6) |
| Browser at `http://localhost:8501` shows "site can't be reached" | Cold start not done yet | Wait 15 s, then `curl -sI http://localhost:8501/_stcore/health` to confirm Streamlit is up |
| Logs show "ModuleNotFoundError" | A package missing from `requirements.txt` | Add it to `requirements.txt`, rebuild |

### ECR issues

| Symptom | Cause | Fix |
|---|---|---|
| `aws ecr create-repository` fails with `AccessDeniedException` | IAM user lacks ECR permissions | Attach `AmazonEC2ContainerRegistryFullAccess` to your IAM user |
| `docker push` fails: "no basic auth credentials" | Login expired (12-hour TTL) | Re-run Step 10.1 (the `aws ecr get-login-password \| docker login` command) |
| `docker push` fails: "denied: User is not authorized to perform: ecr:InitiateLayerUpload" | Login worked but push permission missing | The `AmazonEC2ContainerRegistryFullAccess` policy includes push. Confirm it's attached. PowerUser policy also works. |
| Push completes but image not visible in Console | Wrong region selected in Console | Top-right of Console → switch to the region you pushed to (`ap-south-1` in this guide) |
| `docker push` is extremely slow | Limited upload bandwidth (most home connections cap upload at 10-25 Mbps) | Just wait, or run from a workstation with better upload (datacenter / office connection) |

---

## Quick reference — the whole pipeline in 12 commands

For when you've done this before and just want the muscle memory:

```bash
# The build context is already in this repo
cd labs/M4_Lab4_Docker_Compose/app

# Build + smoke test
docker build -t truck-delay-app:v1 .
docker run -d -p 8501:8501 --name td truck-delay-app:v1
sleep 15 && curl -sI http://localhost:8501/_stcore/health
# Visit http://localhost:8501 to eyeball; then:
docker stop td && docker rm td

# ECR
REGION=ap-south-1
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
ECR_URI=$ACCOUNT.dkr.ecr.$REGION.amazonaws.com/truck-delay-app

aws ecr create-repository --repository-name truck-delay-app --region $REGION
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT.dkr.ecr.$REGION.amazonaws.com
docker tag  truck-delay-app:v1 $ECR_URI:v1
docker push $ECR_URI:v1

# Sanity check
docker rmi truck-delay-app:v1 $ECR_URI:v1
docker pull $ECR_URI:v1
docker run -d -p 8501:8501 --name td2 $ECR_URI:v1
sleep 15 && curl -sI http://localhost:8501/_stcore/health
```

---

## What's next

You now have the M4 ECR image in your account. Three paths forward:

- **Stop here** — you've completed M4. Run the teardown in Section 12 to clean up Docker artifacts locally (keep the ECR repo for M5).
- **Try M4 Lab 4 (Docker Compose)** — see [M4_Lab4_Docker_Compose/README.md](M4_Lab4_Docker_Compose/README.md) for the multi-container local stack (Streamlit + Postgres + MLflow all locally via `docker compose up`).
- **Continue to M5** — [Module 5](../../Module%205/README.md) takes this exact ECR image and deploys it to ECS Fargate behind an Application Load Balancer, with GitHub Actions CI/CD.

The Truck Delay container image is now the **single artifact** that flows through M5, M6, M7, and M8 — same image, different operational layers added at each module.
