# M4 Lab A — Manual AWS Provisioning from the Console

> **Just want to ship it end-to-end via CLI?** See [M4_Docker_End_to_End_Student_Guide.md](M4_Docker_End_to_End_Student_Guide.md) — single doc that creates the ECR repo via `aws ecr create-repository` (CLI, no Console). This lab is the Console-clicks alternative for students who want to see every ECR screen hands-on.

> **Who this is for:** every student in Module 4 who prefers learning AWS services via the Console. M4 needs **one** AWS resource — a private ECR repository to receive the Docker image you'll push in Lab 4. This doc walks you through creating it via the AWS Console (click by click), setting a sensible lifecycle policy, and verifying your IAM permissions before Lab 4.
>
> **Time:** ~15 minutes the first time you do it.
>
> **Cost:** ~₹8/month (~$0.10) per GB of image storage. One typical Streamlit image ≈ 1.5 GB → ~₹12/month. With the lifecycle policy in Step 3, total ECR cost stays under ₹75/month even with frequent rebuilds.
>
> **Want to use the CLI instead?** The single-doc walkthrough at [M4_Docker_End_to_End_Student_Guide.md](M4_Docker_End_to_End_Student_Guide.md) creates the same ECR repo via `aws ecr create-repository`. Use this Console doc when you want to **learn the ECR service hands-on** — M4 is the first time you'll use it, so seeing every screen pays off.

---

## Table of contents

1. [What you'll provision (and why ECR)](#1-what-youll-provision-and-why-ecr)
2. [Prerequisites](#2-prerequisites)
3. [Pick your unique repository name](#3-pick-your-unique-repository-name)
4. **Provisioning steps**
   1. [Step 1: Create the ECR private repository](#step-1-create-the-ecr-private-repository)
   2. [Step 2: Set the lifecycle policy (keep last 5 images)](#step-2-set-the-lifecycle-policy-keep-last-5-images)
   3. [Step 3: Verify your IAM permissions for ECR](#step-3-verify-your-iam-permissions-for-ecr)
   4. [Step 4: Test docker login (CLI smoke test)](#step-4-test-docker-login-cli-smoke-test)
5. [End-to-end verification](#5-end-to-end-verification)
6. [Teardown — destroy the repo from the Console](#6-teardown--destroy-the-repo-from-the-console)
7. [Cost awareness](#7-cost-awareness)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. What you'll provision (and why ECR)

| # | Service | What it does for M4 |
|---|---|---|
| 1 | **ECR private repository** | Cloud-hosted Docker registry. Holds every version (tag) of the Truck Delay dashboard image. Lab 4 pushes here; Module 5 ECS will pull from here. |
| 2 | **ECR lifecycle policy** | Automatic image cleanup — keeps only the last 5 images. Without it, every rebuild adds 1.5 GB to your ECR bill forever. |
| 3 | **IAM permission check** | Confirms your IAM user has `AmazonEC2ContainerRegistryFullAccess` (or equivalent). If you used the admin user from M3, you're already covered. |

That's the entire AWS surface for M4. Everything else (building images, running containers, docker-compose with Postgres + MLflow) happens **locally on your laptop**. ECR is the only cloud resource — and it stays cheap because of the lifecycle policy.

> **Why ECR and not Docker Hub?** Docker Hub works for public images, but private images on the free tier are limited to 1 repo and rate-limited downloads. ECR integrates with AWS IAM (Module 5's ECS task role pulls images from ECR with no extra credentials), supports lifecycle policies natively, and stays in the same region as your other AWS resources (no cross-region egress charges). For an AWS-native MLOps stack, ECR is the right default.

---

## 2. Prerequisites

| What | Why | How to verify |
|---|---|---|
| AWS account with permissions for ECR + IAM | You'll be creating an ECR repo and inspecting your IAM user | AWS Console → IAM → Users → your username → Permissions tab |
| AWS Console open in a browser | The whole lab is Console-based | https://console.aws.amazon.com |
| Region picked (same as M3 if you ran it) | Keep it consistent — M5 will deploy ECS in the same region | Top-right corner of AWS Console. India: `ap-south-1` (Mumbai) |
| AWS CLI v2 installed | Step 4 uses `aws ecr get-login-password` | `aws --version` returns `aws-cli/2.x.x` |
| Docker Desktop running | Step 4's smoke test logs Docker into ECR | `docker --version` returns `Docker version 27.x.x` |
| Your 12-digit AWS account ID | You'll need it for the ECR URI | Top-right of Console (click your name → see "Account ID"), or run `aws sts get-caller-identity` |

> **One-time setup:** click the region selector at top-right of the Console and **lock in the same region you used for M3** (or pick `ap-south-1` if M4 is your first module). Mixing regions across labs is the #1 cause of "I created the repo but can't find it" confusion.

---

## 3. Pick your unique repository name

Choose a repository name that distinguishes you from classmates if you share an AWS account, e.g.:

```
truck-delay-app          ← if you have your own AWS account
priya-truck-delay-app    ← if classmates share the account
mlops-m4-2026-priya      ← matches the M3 project_name convention
```

Rules: lowercase, hyphens or underscores allowed, 2–256 chars, must start with a letter. We'll refer to your choice as `<REPO_NAME>` throughout the rest of this doc.

Write it down. You'll type it three times.

---

## Step 1: Create the ECR private repository

### Console clicks

1. Top search bar in the AWS Console: type **ECR** → select **Elastic Container Registry**.
2. Left sidebar: **Repositories** (under "Private registry").
3. Top-right: **Create repository** (orange button).
4. Fill in the form:

| Field | Value | Why |
|---|---|---|
| **Visibility settings** | **Private** | The dashboard image isn't for public consumption — keep it inside your AWS account. |
| **Repository name** | `<REPO_NAME>` (e.g. `truck-delay-app`) | The name you picked in §3. |
| **Tag immutability** | **Disabled** (default) | "Mutable" tags let you overwrite a tag like `v1` if you rebuild. Useful in early dev; you'll enable immutability in M5 when CI/CD takes over. |
| **Image scan settings → Scan on push** | **Enabled** | Free, runs Amazon Inspector's vulnerability scan on every push. Catches "your base image has 14 critical CVEs" before it ships. |
| **KMS encryption** | **Disabled** (default = AES-256) | AWS-managed encryption at rest is on by default. KMS adds key-rotation control; not needed for M4. |

5. Scroll down → **Create repository**.

`[SCREENSHOT: ECR "Create repository" form with the fields above filled in]`

### What was created

| Resource | Name | Where to view it |
|---|---|---|
| ECR repository | `<REPO_NAME>` | ECR → Repositories list |
| Repository URI | `<ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/<REPO_NAME>` | Click the repo name → top of the detail page |

**Copy the Repository URI now.** You'll paste it into the `docker tag` command in Lab 4.

`[SCREENSHOT: ECR repository detail page showing the URI at the top, with the "Copy URI" button highlighted]`

---

## Step 2: Set the lifecycle policy (keep last 5 images)

Without this, every Docker push adds another image to the repo, and ECR storage charges are per-GB-per-month. Five tags is enough to support rollback to the previous-but-one version; older builds get cleaned up automatically.

### Console clicks

1. From the repository detail page → left sidebar → **Lifecycle Policy**.
2. **Create rule** (or **Edit** if a default exists).
3. Fill in the form:

| Field | Value |
|---|---|
| **Rule priority** | `1` |
| **Rule description** | `Keep only the 5 most recent images` |
| **Image status** | **Any** |
| **Match criteria** | **Image count more than** → `5` |
| **Action** | **Expire** |

4. **Save**.

`[SCREENSHOT: Lifecycle policy rule form with the values above]`

### Verify the rule fires

You can dry-run lifecycle evaluation before any cleanup happens:

1. Left sidebar → **Lifecycle Policy** → **Save and apply rules**.
2. ECR shows you which images *would* be deleted on the next evaluation. For a brand-new empty repo, the list is empty — that's the right answer. After Lab 4 + a few rebuilds, this becomes useful.

> **When ECR actually deletes:** lifecycle policies run on a schedule (~daily), not on every push. So after a push you'll briefly have 6 images; ECR garbage-collects the oldest one within 24 hours.

---

## Step 3: Verify your IAM permissions for ECR

ECR push/pull requires specific IAM permissions. If you used the admin user from M3, you already have them — but verify before Lab 4 so you don't hit a permission error mid-class.

### Console clicks

1. Top search bar → **IAM** → **Users** (left sidebar).
2. Click your IAM username (the one whose access keys are in `aws configure`).
3. **Permissions** tab → scan the policies list.

You need **one of these** attached:

| Policy | What it lets you do |
|---|---|
| `AdministratorAccess` | Everything (including ECR push/pull). Most likely if you went through M3. |
| `AmazonEC2ContainerRegistryFullAccess` | ECR-only admin (create repos, push/pull, set lifecycle). |
| `AmazonEC2ContainerRegistryPowerUser` | ECR push/pull but cannot create or delete repos. Works if your admin created the repo for you. |

### If none of the above is attached

1. From the IAM user detail page → **Add permissions** (button) → **Attach policies directly**.
2. Search for `AmazonEC2ContainerRegistryFullAccess` → tick the checkbox.
3. **Next** → **Add permissions**.

> **Corporate AWS accounts:** if your account admin restricts you to specific managed policies, ask for `AmazonEC2ContainerRegistryPowerUser` (push/pull only) + permission to call `ecr:CreateRepository`. They may want you to use a shared repo your admin pre-created — in that case, skip Step 1 and use the URI they give you.

`[SCREENSHOT: IAM user → Permissions tab showing AmazonEC2ContainerRegistryFullAccess attached]`

---

## Step 4: Test docker login (CLI smoke test)

This is a 30-second sanity check that everything is wired up. If it fails, Lab 4 will fail at the same step, so catch it now.

### Run it

```bash
# Replace <REGION> with the region where you created the repo (e.g. ap-south-1)
# Replace <ACCOUNT_ID> with your 12-digit account ID

aws ecr get-login-password --region <REGION> \
  | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com
```

**Expected output:**

```
Login Succeeded
```

### What just happened

1. `aws ecr get-login-password` asks AWS for a short-lived (12-hour) authentication token.
2. The pipe (`|`) passes that token to `docker login`'s stdin.
3. Docker stores the credential in `~/.docker/config.json` (or Windows equivalent). All subsequent `docker push` / `docker pull` against your ECR registry now authenticate transparently.

### If it fails

| Error message | Cause | Fix |
|---|---|---|
| `Unable to locate credentials` | `aws configure` was never run, or `~/.aws/credentials` is empty | Run `aws configure` and enter access key + secret + region |
| `An error occurred (AccessDeniedException)` | IAM user lacks ECR permissions | Re-do Step 3 — attach `AmazonEC2ContainerRegistryFullAccess` |
| `Error response from daemon: Get "https://..."  no basic auth credentials` | Docker is running but the login pipe didn't work | On Windows PowerShell, the pipe sometimes mangles the token; try Git Bash or WSL |
| `Cannot connect to the Docker daemon` | Docker Desktop isn't running | Start Docker Desktop and wait for the whale icon to be steady |

---

## 5. End-to-end verification

Three checks. All should pass before you start Lab 4.

### Check 1: Console shows the empty repo

ECR → Repositories → your `<REPO_NAME>` should appear with `0 images`. URI visible at the top.

### Check 2: CLI sees the repo

```bash
aws ecr describe-repositories --region <REGION> \
    --repository-names <REPO_NAME>
```

Expected: JSON output with `repositoryArn`, `repositoryUri`, `createdAt`, etc.

### Check 3: Docker can log in (re-runs Step 4)

```bash
aws ecr get-login-password --region <REGION> \
  | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com
```

Expected: `Login Succeeded`.

If all three pass — you're ready for Lab 4. The Lab 4 doc assumes the repo exists and Docker is logged in; it picks up exactly where this lab ends.

---

## 6. Teardown — destroy the repo from the Console

Run this at the end of the M4 session (or at the end of the course) to stop ECR storage charges.

### Console clicks

1. ECR → Repositories → tick the checkbox next to `<REPO_NAME>`.
2. Top-right: **Delete**.
3. Type `delete` in the confirmation box → **Delete**.

### Or the CLI one-liner

```bash
aws ecr delete-repository \
    --repository-name <REPO_NAME> \
    --region <REGION> \
    --force         # --force lets you delete even if the repo has images
```

> **`--force` matters:** without it, ECR refuses to delete a non-empty repo. With it, all image versions are deleted along with the repo. Use this when you're sure nothing else (e.g. an ECS service in M5) is pulling from it.

### What's left after teardown

Nothing. ECR repos don't leave behind any orphan resources. IAM permissions stay attached to your user — they cost nothing and you'll want them again for M5.

---

## 7. Cost awareness

| Item | Rate | Realistic monthly cost |
|---|---|---|
| ECR storage | ~$0.10/GB/month (₹8/GB/month at the time of writing) | 5 images × 1.5 GB ≈ ₹60/month |
| ECR data transfer **in** (push from your laptop) | Free | ₹0 |
| ECR data transfer **out** (pull) within the same region (e.g. ECS in `ap-south-1` pulling) | Free | ₹0 |
| ECR data transfer **out** to another region or the public internet | $0.09/GB | Avoid this — pull from the same region |
| Image scanning (Amazon Inspector) | Free for "basic" scanning | ₹0 |

**Total expected cost for the M4 session:** under ₹75/month if you keep the lifecycle policy active, and ₹0 once you teardown.

---

## 8. Troubleshooting

| Symptom | Diagnosis | Fix |
|---|---|---|
| `aws ecr create-repository` says "repository already exists" | You ran this earlier, or a classmate is using the same name in a shared account | Either reuse the existing repo (find the URI in the Console) or pick a different `<REPO_NAME>` |
| "Tag immutability" prevents me from re-pushing `v1` | You enabled immutability (we said "disabled" — but maybe the default changed in your region) | ECR → repo → **Edit** → set Tag immutability to **Disabled** for dev work |
| Lifecycle policy doesn't seem to delete old images | Lifecycle evaluates on a schedule (~24 h), not on push | Wait a day, or trigger manually: ECR → repo → Lifecycle policy → **Save and apply rules** |
| Login Succeeded but `docker push` returns `denied: User: ... is not authorized to perform: ecr:InitiateLayerUpload` | The login worked but the IAM user lacks push permissions | Step 3 — attach `AmazonEC2ContainerRegistryFullAccess` (PowerUser includes push) |
| `no space left on device` when building the image locally | Docker's image storage is full | `docker system prune -a` reclaims unused images/layers; bigger fix is allocating more disk to Docker Desktop |
| Created the repo in the wrong region | Cross-region push needs explicit configuration | Delete it (Step 6 above) and re-create in the right region — costs nothing |

---

## What's next

Now run Lab 4 ([M4_Lab4_Push_to_ECR.md](M4_Lab4_Push_to_ECR.md)). It assumes:

- An ECR repo named `<REPO_NAME>` exists in `<REGION>` ✅ (Step 1)
- The lifecycle policy is set ✅ (Step 2)
- Your IAM user has ECR permissions ✅ (Step 3)
- Docker is authenticated to ECR ✅ (Step 4)

Lab 4 skips straight to tagging the local image and pushing it. The first push takes ~1–3 minutes depending on your upload bandwidth — most of the time is the 1.5 GB image transfer.
