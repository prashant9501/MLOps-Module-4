# M4 Lab 2: Build, Run, and Test Your Container

**Module 4 -- Containerization with Docker | Spine Project: Truck Delay Classification**

> **Just want to ship it end-to-end?** See [M4_Docker_End_to_End_Student_Guide.md](M4_Docker_End_to_End_Student_Guide.md) — single doc covering install → build → push → sanity check across Windows / macOS / Linux. This lab is the deep dive on the `docker build` + `docker run` mechanics.

| Detail | Value |
|---|---|
| Duration | 45 minutes |
| Difficulty | Beginner |
| Tools | Docker Desktop (Windows/Mac) or Docker Engine (Linux), VS Code, browser |
| Prerequisite | Lab 1 complete (Dockerfile and .dockerignore written) |
| Builds Toward | Lab 4 (push to ECR), Module 5 (deploy to ECS) |

---

## Learning Objectives

By the end of this lab you will be able to:

1. Build a Docker image from a Dockerfile using `docker build`.
2. Run a container with port mapping and environment variables.
3. Inspect a running container using `docker logs`, `docker exec`, and `docker history`.
4. Manage the container lifecycle (start, stop, remove).
5. Appreciate the deployment speed advantage of containers over manual setup.

---

## Business Context

In Module 3, the FreshBasket team spent over 20 minutes setting up the Streamlit dashboard on a fresh EC2 instance -- installing Python, transferring files, pip-installing dependencies, fighting version conflicts, copying model `.pkl` files. Every new server required the same tedious process. In Lab 1, you reviewed a Dockerfile that captures the entire setup -- including the pre-trained model artifacts -- as a repeatable recipe. Now you will execute that recipe: build an image once, then start the Streamlit dashboard with a single command in under 5 seconds.

---

## Step 1: Build the Docker Image

Open a terminal, navigate into the build context, and run:

> **🪟 Windows (PowerShell or Command Prompt):**
> ```
> cd labs\M4_Lab3_Docker_Compose\app
> docker build -t truck-delay-app:v1 .
> ```
>
> **🍎 macOS / 🐧 Linux:**
> ```bash
> cd labs/M4_Lab3_Docker_Compose/app
> docker build -t truck-delay-app:v1 .
> ```

**What the flags mean:**

| Flag | Purpose |
|---|---|
| `-t truck-delay-app:v1` | Tags the image with a name (`truck-delay-app`) and version (`v1`). Without a tag, Docker assigns a random ID that is impossible to remember. |
| `.` (the dot at the end) | Tells Docker where to find the Dockerfile and the build context (the set of files Docker can access during the build). The dot means "the current directory". |

### Expected Output

Docker processes each instruction in the Dockerfile as a numbered step. You will see output similar to:

```
[+] Building 87.3s (10/10) FINISHED
 => [1/6] FROM python:3.12-slim@sha256:...                          12.4s
 => [2/6] WORKDIR /app                                               0.1s
 => [3/6] COPY requirements.txt .                                    0.0s
 => [4/6] RUN pip install --no-cache-dir -r requirements.txt        62.8s
 => [5/6] COPY app.py ./                                             0.1s
 => [6/6] COPY artifacts/ ./artifacts/                               0.5s
 => exporting to image                                                3.7s
```

The first build takes 1-3 minutes, depending on your internet speed and machine. The `pip install` step is the slowest because it downloads and installs all ML dependencies. Subsequent builds (after source-code-only changes) will be much faster thanks to layer caching, as you learned in Lab 1.

`[SCREENSHOT: Terminal showing complete docker build output with all steps succeeded]`

> **Build failed?** Check these common issues:
> - "no such file or directory" for `requirements.txt` -- make sure you are running the command from `labs/M4_Lab3_Docker_Compose/app/`.
> - "Cannot connect to the Docker daemon" -- Docker Desktop is not running. Start it and try again.
> - Pip install errors for specific packages -- check that `requirements.txt` is unchanged (streamlit 1.32, xgboost 2.0.3, numpy<2.0).

---

## Step 2: Check Image Size

List your Docker images to see the newly built one:

```bash
docker images truck-delay-app
```

Expected output (sizes vary slightly by Docker version):

```
IMAGE                ID             DISK USAGE   CONTENT SIZE
truck-delay-app:v1   a9ff99743e82       1.79GB          541MB
```

The two numbers measure different things:
- **DISK USAGE** (~1.8 GB) — what the image occupies on your laptop's Docker disk, including unpacked layers
- **CONTENT SIZE** (~540 MB) — compressed size, what gets transferred over the network when you `docker push` to ECR

**Is this size normal?** Yes, for an ML application. The bulk comes from the Python packages: scikit-learn, xgboost, pandas, numpy, and their compiled C libraries (the pip-install layer alone is ~1.1 GB). A simple Flask "Hello World" app would be under 200 MB. There are techniques to reduce this further (multi-stage builds, distroless base images, smaller dependency sets), but 500 MB compressed is typical and acceptable for ML containers.

---

## Step 3: Inspect Image Layers

Every instruction in the Dockerfile created a layer. You can see them with:

```bash
docker history truck-delay-app:v1
```

Expected output (simplified):

```
CREATED BY                                      SIZE
CMD ["streamlit" "run" "app.py" ...]            0B
HEALTHCHECK CMD python -c "..."                 0B
EXPOSE 8501                                     0B
COPY artifacts/ ./artifacts/                    1.09MB
COPY app.py ./                                  16.4kB
RUN pip install --no-cache-dir -r ...           1.12GB    ← biggest layer
COPY requirements.txt .                         12.3kB
WORKDIR /app                                    8.19kB
...                                             (base image layers below)
```

Notice how the `pip install` layer is by far the largest (~1.1 GB). This is the layer you want to keep cached as long as possible -- which is exactly what the two-step COPY pattern from Lab 1 achieves. Edit `app.py` and rebuild → ~5-10 seconds. Edit `requirements.txt` and rebuild → ~60-90 seconds.

`[SCREENSHOT: Terminal showing docker history output with layer sizes]`

---

## Step 4: Run the Container

Now start a container from your image:

```bash
docker run -d -p 8501:8501 --name truck-app truck-delay-app:v1
```

**What the flags mean:**

| Flag | Purpose |
|---|---|
| `-d` | **Detached mode** -- runs the container in the background so you get your terminal back. Without this, Streamlit's log output would take over your terminal. |
| `-p 8501:8501` | **Port mapping** -- maps port 8501 on your host machine (left side) to port 8501 inside the container (right side). This is how traffic from your browser reaches the Streamlit app. |
| `--name truck-app` | Assigns a human-readable name to the container. Without this, Docker assigns a random name like `quirky_ptolemy`. |
| `truck-delay-app:v1` | The image to run (name:tag from the build step). |

Verify the container is running:

```bash
docker ps
```

Expected output (after waiting ~15 seconds for Streamlit + healthcheck):

```
NAMES       STATUS                    PORTS
truck-app   Up 15 seconds (healthy)   0.0.0.0:8501->8501/tcp, [::]:8501->8501/tcp
```

The `STATUS` column should show "Up X seconds (healthy)" — the `(healthy)` suffix means the HEALTHCHECK from the Dockerfile is passing. If you see just "Up X seconds" without `(healthy)`, the healthcheck hasn't fired yet — that's expected during the 15-second `start_period` of the healthcheck. Wait another 30 seconds and re-run `docker ps`.

The `PORTS` column confirms the port mapping is active in both IPv4 (`0.0.0.0:8501->8501/tcp`) and IPv6 (`[::]:8501->8501/tcp`).

`[SCREENSHOT: Terminal showing docker ps output with truck-app container running]`

---

## Step 5: Test in Your Browser

Open your browser and navigate to:

```
http://localhost:8501
```

The FreshBasket Delivery Delay Predictor should load -- a form with three columns (🛣️ Trip & Route Info, 🚛 Driver & Truck Info, 🌤️ Weather Conditions) and a blue "Predict Delay Risk" button at the bottom. Fill in sample values, click the button, and you'll get a colour-coded result panel (✅ On Time or ⚠️ At Risk Of Delay) with a probability percentage.

`[SCREENSHOT: Streamlit Delay Predictor running in the browser from the Docker container, showing the input form and a sample prediction result]`

> **Page not loading?** Give the container 5-10 seconds to start up. Streamlit needs a moment to initialise. If it still does not load after 15 seconds, check the container logs (Step 6).

---

## Step 6: View Container Logs

See what Streamlit is printing inside the container:

```bash
docker logs truck-app
```

You will see Streamlit's startup messages:

```
  You can now view your Streamlit app in your browser.

  URL: http://0.0.0.0:8501
```

To watch logs in real-time (useful for debugging):

```bash
docker logs -f truck-app
```

Press `Ctrl+C` to stop following the logs (this does NOT stop the container -- it only detaches your terminal from the log stream).

---

## Step 7: Execute Commands Inside the Container

You can open a shell session inside the running container to inspect its environment. This is invaluable for debugging:

```bash
docker exec -it truck-app bash
```

**What the flags mean:**

| Flag | Purpose |
|---|---|
| `-i` | Interactive -- keeps STDIN open so you can type commands |
| `-t` | Allocates a pseudo-TTY so the terminal behaves normally |

You are now inside the container. The prompt changes to something like `root@f7a8b2c3d4e5:/app#`. Try these commands:

```bash
# Check the working directory
pwd
# Expected: /app

# List the application files
ls -la
# Expected: app.py  artifacts  requirements.txt

# Look inside artifacts/
ls artifacts/
# Expected: encoder.pkl  model_metadata.json  scaler.pkl  xgboost_model.pkl

# Verify the Python version
python --version
# Expected: Python 3.12.x  (whatever patch version the python:3.12-slim tag resolves to today)

# List installed packages (first 20)
pip list | head -20
# Expected: streamlit, pandas, scikit-learn, xgboost, joblib, etc.

# Exit the container shell
exit
```

`[SCREENSHOT: Terminal inside the container showing pwd, ls, and python --version output]`

> **Important:** When you type `exit`, you leave the container's shell and return to your host machine's terminal. The container itself continues running.

---

## Step 8: Pass Environment Variables (Concept)

Our simple app doesn't read any environment variables — everything it needs (model, encoder, scaler, metadata) is baked into the image at `/app/artifacts/`. But **most production containers do** read env vars at startup for things like database hosts, API keys, log levels. Worth knowing the syntax.

The pattern is `-e KEY=VALUE` (one flag per variable). Stop and recreate the container with one harmless env var:

```bash
docker stop truck-app && docker rm truck-app

docker run -d -p 8501:8501 --name truck-app \
  -e STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
  -e LOG_LEVEL=INFO \
  truck-delay-app:v1
```

> **🪟 Windows Command Prompt:** Replace the `\` line continuations with `^`:
> ```
> docker run -d -p 8501:8501 --name truck-app ^
>   -e STREAMLIT_BROWSER_GATHER_USAGE_STATS=false ^
>   -e LOG_LEVEL=INFO ^
>   truck-delay-app:v1
> ```
>
> **🪟 Windows PowerShell:** Use backtick `` ` `` for line continuation:
> ```powershell
> docker run -d -p 8501:8501 --name truck-app `
>   -e STREAMLIT_BROWSER_GATHER_USAGE_STATS=false `
>   -e LOG_LEVEL=INFO `
>   truck-delay-app:v1
> ```

Verify the variables made it inside the container:

```bash
docker exec truck-app env | grep -E "STREAMLIT|LOG_LEVEL"
# Expected: STREAMLIT_BROWSER_GATHER_USAGE_STATS=false  and  LOG_LEVEL=INFO
```

In M5, the ECS task definition uses this same `-e` pattern to inject DB endpoints, AWS credentials, and feature flags into the running container.

---

## Step 9: Container Lifecycle Management

Containers have a simple lifecycle. Practice these commands:

### Stop a running container

```bash
docker stop truck-app
```

This sends a graceful shutdown signal (SIGTERM). Streamlit has a few seconds to clean up before Docker forcefully terminates it.

### Start a stopped container

```bash
docker start truck-app
```

This restarts the same container with its original configuration (port mapping, environment variables, name). It does not create a new container.

### Remove a stopped container

```bash
docker stop truck-app
docker rm truck-app
```

You must stop a container before removing it. Removing a container deletes it permanently -- its logs and filesystem changes are gone.

### Force-remove a running container (shortcut)

```bash
docker rm -f truck-app
```

This stops and removes in one command. Useful during development but not recommended in production (no graceful shutdown).

### List all containers (including stopped)

```bash
docker ps -a
```

The `-a` flag shows containers in any state. Without it, `docker ps` only shows running containers.

---

## Key Moment: The Speed Comparison

Think back to Module 3 Lab A. Setting up the Real Estate API on a fresh EC2 instance required:

1. SSH into the instance
2. Install Python 3.12 (apt-get update, add repository, install)
3. Create a virtual environment
4. Transfer project files via SCP
5. pip install requirements (and debug any failures)
6. Set environment variables
7. Start the application

**Total time: 20-30 minutes of manual work. Every single time.**

With Docker, on any machine that has Docker installed:

```bash
docker run -d -p 8501:8501 truck-delay-app:v1
```

**Total time: 2 seconds** (after the image is pulled). The entire environment -- OS, Python, libraries, source code, configuration -- is baked into the image. No manual steps. No version mismatches. No "works on my machine" surprises.

This is the core value proposition of containers: **build once, run anywhere, identically**.

---

## Checkpoint

Before moving to Lab 3, verify:

- [ ] `docker images truck-delay-app` shows your `v1` image.
- [ ] `docker run -d -p 8501:8501 --name truck-app truck-delay-app:v1` starts the container.
- [ ] `http://localhost:8501` shows the FreshBasket Delivery Delay Predictor form in your browser, and submitting it returns a prediction.
- [ ] `docker exec -it truck-app bash` lets you inspect the container's filesystem.
- [ ] You can stop, start, and remove the container using the commands from Step 9.

---

## Clean Up

For Lab 3 you will need the `truck-delay-app:v1` image, so do NOT delete it. But remove any stopped containers to keep things tidy:

```bash
docker rm -f truck-app 2>/dev/null
```

---

## What Comes Next

In **Lab 3** you will push your Docker image to Amazon Elastic Container Registry (ECR) -- AWS's private image repository. Once the image is in ECR, any EC2 instance (or ECS cluster in Module 5) can pull and run it without needing your source code or Dockerfile.

---

*FreshBasket Logistics -- Pune | Module 4, Lab 2 of 4*
