# MLOps Module 4 — Containerization with Docker & ECR

**Take the Truck Delay model from M3, package it as a Docker image, push it to AWS ECR, and learn to use AI to generate `docker-compose.yml`.**

> **Just want to ship it?** Read **[labs/M4_Docker_End_to_End_Student_Guide.md](labs/M4_Docker_End_to_End_Student_Guide.md)** — single doc covering install → build → push → sanity check across Windows / macOS / Linux. ~30 minutes end-to-end.

> **Want to learn the AI-assisted Compose pattern?** Read **[labs/M4_KT_Docker_Compose_with_AI.md](labs/M4_KT_Docker_Compose_with_AI.md)** — how to prompt any AI model to generate a working `docker-compose.yml` for your project, with validation steps.

---

## What this module teaches

By the end you'll have:

- **Docker Desktop / Engine running** on your laptop (Windows + WSL2 / macOS / Linux)
- **A working Docker image** of the FreshBasket Delay Predictor — `truck-delay-app:v1` (~600 MB)
- **The same image in your AWS ECR** under a private repository
- **A `docker-compose.yml`** for the simpler self-contained app — generated via an AI prompt rather than hand-written
- **Conceptual exposure** to a separate Flask + SBERT containerised search service via the branch take-home

This is **spine phase 2**: the Truck Delay app went from notebook (M3) → **containerised (M4)** → production-deployed (M5) → drift-monitored (M6) → feature-store-driven (M7) → fully automated (M8).

---

## Repo map

```
.
├── README.md                                            ← you're here
│
└── labs/
    ├── M4_Docker_End_to_End_Student_Guide.md            ⭐ Single-doc walkthrough (start here)
    ├── M4_KT_Docker_Compose_with_AI.md                  ⭐ AI prompt + workflow for generating Compose files
    │
    ├── M4_Lab_A_AWS_Provisioning_from_Console.md        Console clicks to create the ECR repository
    ├── M4_Lab1_Write_Dockerfile.md                      Deep dive on the Dockerfile (FROM, COPY, RUN, CMD, layer caching)
    ├── M4_Lab2_Build_Run_Test.md                        Deep dive on docker build / run / logs / exec / lifecycle
    ├── M4_Lab3_Push_to_ECR.md                           Deep dive on docker login / tag / push to ECR
    │
    ├── M4_Lab4_Docker_Compose/                          The Compose lab
    │   ├── README.md                                       Compose lab walkthrough
    │   ├── docker-compose.yml                              Single-service Compose example
    │   └── app/
    │       ├── app.py                                      Self-contained Streamlit predictor
    │       ├── Dockerfile                                  Image recipe (layer-cached, healthcheck included)
    │       ├── requirements.txt                            Pinned Python deps
    │       └── artifacts/                                  Pre-trained .pkl files + 11 reference plots
    │
    └── M4_Branch_SBERT_Search/                          Take-home branch project (NLP / Flask + SBERT)
        ├── M4_Branch_Briefing_SBERT.md
        ├── solution/                                        Full reference implementation
        └── starter/                                         Scaffolding for students to fill in
```

---

## How to use this repo

### Path 1 — Quick (you just want a working image in ECR)

Read **[labs/M4_Docker_End_to_End_Student_Guide.md](labs/M4_Docker_End_to_End_Student_Guide.md)** and follow it. ~30 minutes including install. End state: `<your-account>.dkr.ecr.<region>.amazonaws.com/truck-delay-app:v1` exists and you've verified it's pullable from anywhere.

### Path 2 — Comprehensive (you want to understand every layer)

Work through Lab A → Lab 1 → Lab 2 → Lab 3 → Lab 4 in order. ~5 hours. Each lab goes deep on one piece. The Student Guide is the speedrun version of the same content.

### Path 3 — Just the AI Compose pattern (you know Docker, want the workflow)

Skip straight to **[labs/M4_KT_Docker_Compose_with_AI.md](labs/M4_KT_Docker_Compose_with_AI.md)**. Pair it with the app + Dockerfile in `labs/M4_Lab4_Docker_Compose/app/` to practice the prompt → validate → run loop on a real project.

---

## Prerequisites

You need three things from **outside** this repo:

1. **The M3 Streamlit app files** — `app.py`, `config.py`, `utils.py`, `requirements.txt`. Clone https://github.com/prashant9501/MLOps-Module-3 and pull them from `labs/M3_Lab_E_Streamlit_Deployment/`. **You don't need to have run M3** — the app supports `DEMO_MODE=true` with synthetic data, so M4 Labs 1-2-4 work without any AWS deployment from M3.

   > Lab 4 (the Compose lab) uses a **simpler self-contained app** that's already in this repo at `labs/M4_Lab4_Docker_Compose/app/` — no M3 dependency for that one.

2. **An AWS account** with permissions for ECR + IAM (only needed for Lab 3 push to ECR).

3. **A laptop with Docker Desktop or Docker Engine.** Install instructions for all 3 OSes are in §3 of the Student Guide.

---

## AWS services this module uses

Just one — **Amazon ECR** (Elastic Container Registry). Created hands-on in Lab A (Console) or via the CLI in the Student Guide.

> **Note on IaC:** Earlier course planning had AWS CDK pre-provisioning ECR. M4 now uses Console / CLI hands-on instead — ECR is the first AWS service M4 introduces, so doing it manually is the learning moment. CDK / Terraform exposure lives in M5 onwards (M5 branch project uses Terraform; M3 + M8 use CDK).

---

## Teardown

```bash
# Delete the ECR repo (--force lets it delete even with images present)
aws ecr delete-repository --repository-name truck-delay-app --region <your-region> --force

# Local Docker cleanup
docker rmi truck-delay-app:v1 2>/dev/null || true
docker system prune --all --force        # reclaim build cache (optional)
```

> **Keep the ECR repo for M5.** Module 5 Lab A uses this exact image as the ECS Fargate deployment source. Only run the full teardown above if you're stopping after M4 entirely.

Cost while ECR holds your image: ~₹8/month per GB (~₹5/month for one image, capped via the lifecycle policy at 5 most-recent versions).

---

## What's next — Module 5

Take this ECR image and deploy it to **ECS Fargate behind an ALB**, with a **GitHub Actions CI/CD pipeline** that automatically rebuilds + redeploys on every push to `main`.

Module 5 repo: (link once published)

---

## License + credits

Course content built for the **AWS MLOps Master Course**. Module 4 is the second installment of the Truck Delay spine project that continues through M5 (ECS + CI/CD) → M6 (drift detection) → M7 (Hopsworks feature store) → M8 (SageMaker Pipelines).

Synthetic dataset based on a real-world logistics use case at "FreshBasket Logistics" — a fictional Pune-based grocery delivery company.
