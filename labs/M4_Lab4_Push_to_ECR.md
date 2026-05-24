# M4 Lab 4: Push Your Image to Amazon ECR

**Module 4 -- Containerization with Docker | Spine Project: Truck Delay Classification**

> **Just want to ship it end-to-end?** See [M4_Docker_End_to_End_Student_Guide.md](M4_Docker_End_to_End_Student_Guide.md) — single doc covering install → build → push → sanity check across Windows / macOS / Linux. This lab is the deep dive on tagging, ECR auth, and `docker push`.

| Detail | Value |
|---|---|
| Duration | 30 minutes |
| Difficulty | Beginner |
| Tools | AWS CLI v2, Docker, browser (AWS Console) |
| AWS Services | Amazon ECR, IAM |
| Prerequisite | Lab 2 complete (`truck-delay-app:v1` image built locally) AND an ECR repo to push to (Lab A — Console walkthrough — is the recommended way to create it; the CLI alternative is in Step 1 below) |
| Builds Toward | Module 5 (ECS deployment pulls this image from ECR) |
| Cost Estimate | ECR: ~$0.10/GB/month storage (~₹8/month for one image) |

---

## Learning Objectives

By the end of this lab you will be able to:

1. Create a private repository in Amazon Elastic Container Registry (ECR).
2. Authenticate the local Docker client to your ECR registry.
3. Tag a local image with the ECR repository URI and push it.
4. Pull and run the image on a different machine to prove portability.

---

## Business Context

Priya's container image currently lives only on her laptop. If her machine crashes or Arjun needs to deploy the dashboard on a staging server, the image is gone. FreshBasket needs a central, secure place to store container images -- the same way they store trained models in S3. Amazon ECR is a fully managed Docker registry that integrates with IAM for access control and with ECS for deployment. In this lab you will push the Truck Delay Dashboard image to ECR so it can be pulled from anywhere in the organisation.

---

## Prerequisites

### AWS CLI v2

Verify the AWS CLI is installed:

```bash
aws --version
```

You should see `aws-cli/2.x.x ...`. If not, install it:

> **🪟 Windows:** Download the MSI installer from [https://aws.amazon.com/cli/](https://aws.amazon.com/cli/) and run it. After installation, close and reopen your terminal.
>
> **🍎 macOS:**
> ```bash
> curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
> sudo installer -pkg AWSCLIV2.pkg -target /
> ```
>
> **🐧 Linux:**
> ```bash
> curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
> unzip awscliv2.zip
> sudo ./aws/install
> ```

### Configure AWS Credentials

If you have not already configured the AWS CLI (or if you are on a fresh machine), run:

```bash
aws configure
```

Enter the following when prompted:

| Prompt | Value |
|---|---|
| AWS Access Key ID | Your IAM user access key |
| AWS Secret Access Key | Your IAM user secret key |
| Default region name | `ap-south-1` |
| Default output format | `json` |

> **IAM permissions needed:** Your IAM user must have the `AmazonEC2ContainerRegistryFullAccess` managed policy attached (or equivalent custom permissions). If you created an admin user in Module 3, you already have this.

Verify your credentials work:

```bash
aws sts get-caller-identity
```

You should see your account ID, ARN, and user ID. Note down the **Account ID** (the 12-digit number) -- you will need it in the steps below.

`[SCREENSHOT: Terminal showing aws sts get-caller-identity output with account ID visible]`

### Docker Image

Confirm the image from Lab 2 still exists:

```bash
docker images truck-delay-app
```

You should see the `v1` tag. If not, go back to Lab 2 and rebuild the image.

---

## Step 1: Create an ECR Repository

An ECR repository holds all versions (tags) of a single container image -- similar to how a GitHub repository holds all versions of a codebase.

> **Already did Lab A (Console walkthrough)?** Skip this step — your repo exists. Note your Repository URI from Lab A Step 1 and jump to Step 2.

```bash
aws ecr create-repository \
    --repository-name truck-delay-app \
    --region ap-south-1
```

> **🪟 Windows Command Prompt:** Replace `\` with `^`:
> ```
> aws ecr create-repository ^
>     --repository-name truck-delay-app ^
>     --region ap-south-1
> ```

Expected output (key fields):

```json
{
    "repository": {
        "repositoryArn": "arn:aws:ecr:ap-south-1:123456789012:repository/truck-delay-app",
        "repositoryUri": "123456789012.dkr.ecr.ap-south-1.amazonaws.com/truck-delay-app",
        "repositoryName": "truck-delay-app",
        ...
    }
}
```

**Copy the `repositoryUri` value.** You will use it in Steps 3 and 4. It follows the pattern:

```
<ACCOUNT_ID>.dkr.ecr.ap-south-1.amazonaws.com/truck-delay-app
```

Now open the AWS Console in your browser, navigate to **ECR** (search for "Elastic Container Registry"), and confirm the repository appears in the Mumbai (ap-south-1) region.

`[SCREENSHOT: ECR Console showing the newly created truck-delay-app repository with zero images]`

> **Recommended — also set a lifecycle policy** to auto-delete older images once you've pushed 5+ versions. Without it, every rebuild adds ~600 MB to your ECR storage bill indefinitely. See [M4_Lab_A_AWS_Provisioning_from_Console.md § Step 2](M4_Lab_A_AWS_Provisioning_from_Console.md) for the Console click-path, or run the CLI version inline:
>
> ```bash
> aws ecr put-lifecycle-policy --repository-name truck-delay-app --region ap-south-1 \
>     --lifecycle-policy-text '{"rules":[{"rulePriority":1,"description":"Keep only the 5 most recent images","selection":{"tagStatus":"any","countType":"imageCountMoreThan","countNumber":5},"action":{"type":"expire"}}]}'
> ```

---

## Step 2: Authenticate Docker to ECR

Docker needs to log in to your ECR registry before it can push images. ECR uses temporary tokens (valid for 12 hours) generated by the AWS CLI:

```bash
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.ap-south-1.amazonaws.com
```

Replace `<ACCOUNT_ID>` with your 12-digit AWS account ID (from `aws sts get-caller-identity`).

> **🪟 Windows Command Prompt:** The pipe (`|`) works the same way in Command Prompt.
>
> **🪟 Windows PowerShell:** The pipe (`|`) works the same way in PowerShell.

**What this command does:**

1. `aws ecr get-login-password` generates a temporary authentication token from AWS.
2. The pipe (`|`) passes that token to the next command.
3. `docker login --password-stdin` uses the token to authenticate the Docker client with your ECR registry.

Expected output:

```
Login Succeeded
```

If you see "Login Succeeded", Docker can now push to and pull from your ECR registry for the next 12 hours.

> **"Error: Cannot perform an interactive login from a non TTY device"** -- This usually happens if the AWS CLI is not configured correctly or your IAM user lacks ECR permissions. Run `aws sts get-caller-identity` to confirm credentials are working, and check that the `AmazonEC2ContainerRegistryFullAccess` policy is attached to your IAM user.

---

## Step 3: Tag the Image for ECR

Docker images need to be tagged with the full ECR repository URI before they can be pushed. Think of this as giving the image a full address so Docker knows where to send it:

```bash
docker tag truck-delay-app:v1 <ACCOUNT_ID>.dkr.ecr.ap-south-1.amazonaws.com/truck-delay-app:v1
```

Replace `<ACCOUNT_ID>` with your 12-digit account ID.

**Example** (if your account ID is 123456789012):

```bash
docker tag truck-delay-app:v1 123456789012.dkr.ecr.ap-south-1.amazonaws.com/truck-delay-app:v1
```

This does not copy the image -- it adds a second name (tag) that points to the same image data. Verify with:

```bash
docker images | grep truck-delay-app
```

You should now see two entries: the original `truck-delay-app:v1` and the ECR-tagged version. Both share the same IMAGE ID.

---

## Step 4: Push the Image to ECR

Now push the tagged image:

```bash
docker push <ACCOUNT_ID>.dkr.ecr.ap-south-1.amazonaws.com/truck-delay-app:v1
```

Expected output:

```
The push refers to repository [123456789012.dkr.ecr.ap-south-1.amazonaws.com/truck-delay-app]
5a3b8c2d1e4f: Pushed
7f6e5d4c3b2a: Pushed
...
v1: digest: sha256:abc123... size: 3247
```

The push takes 2-5 minutes depending on your upload speed. Docker pushes each layer individually and skips layers that already exist in the registry (useful when pushing updated versions later).

After the push completes, go back to the ECR Console in your browser and click on the `truck-delay-app` repository. You should see the `v1` tag listed with its size and push timestamp.

`[SCREENSHOT: ECR Console showing the truck-delay-app repository with the v1 image listed, showing size and pushed timestamp]`

---

## Step 5: The "Aha Moment" -- Pull and Run on a Fresh Machine

This is where the value of ECR becomes real. You will pull the image onto a machine that has never seen your source code, Dockerfile, or requirements.txt -- and the app will run immediately.

### Option A: Use a Fresh EC2 Instance

If you have an EC2 instance from Module 3 (or launch a new one):

1. **SSH into the EC2 instance:**

    > **🪟 Windows (PowerShell):**
    > ```
    > ssh -i "m3-ec2-key.pem" ubuntu@<EC2_PUBLIC_IP>
    > ```
    >
    > **🍎 macOS / 🐧 Linux:**
    > ```bash
    > ssh -i "m3-ec2-key.pem" ubuntu@<EC2_PUBLIC_IP>
    > ```

2. **Install Docker on the EC2 instance** (if not already installed):

    ```bash
    sudo apt-get update
    sudo apt-get install -y docker.io
    sudo systemctl start docker
    sudo usermod -aG docker ubuntu
    # Log out and back in for the group change to take effect
    exit
    ```

    SSH back in after the logout.

3. **Install and configure the AWS CLI** on the EC2 instance:

    ```bash
    sudo apt-get install -y awscli
    aws configure
    # Enter your access key, secret key, ap-south-1, json
    ```

4. **Authenticate Docker to ECR** (same command as Step 2):

    ```bash
    aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.ap-south-1.amazonaws.com
    ```

5. **Pull and run the image:**

    ```bash
    docker pull <ACCOUNT_ID>.dkr.ecr.ap-south-1.amazonaws.com/truck-delay-app:v1
    docker run -d -p 8501:8501 --name truck-app <ACCOUNT_ID>.dkr.ecr.ap-south-1.amazonaws.com/truck-delay-app:v1
    ```

6. **Open in browser:** Navigate to `http://<EC2_PUBLIC_IP>:8501`

    Make sure port 8501 is open in the EC2 instance's security group (add an inbound rule for Custom TCP port 8501 from 0.0.0.0/0 if it is not already there).

`[SCREENSHOT: Streamlit Truck Delay Dashboard running in the browser, accessed via EC2 public IP, confirming the ECR pull worked]`

### Option B: Use a Different Local Machine

If you have access to a second computer (a colleague's laptop, a different VM), install Docker and the AWS CLI, authenticate to ECR, and run the same pull/run commands. The app will start without any access to your source code.

### The Key Takeaway

The EC2 instance (or second machine) has:
- No Python installed (Docker handles it)
- No source code files
- No requirements.txt
- No Dockerfile

Yet the Streamlit dashboard runs perfectly. Everything the app needs is inside the container image. **This is what "ship the container, not the code" means.**

In Module 3, deploying on a new machine took 20+ minutes of manual setup. With the container image in ECR, it takes **under 2 minutes** -- and most of that is the pull download time.

---

## Step 6: Clean Up

### What to Keep

**Do NOT delete the ECR repository or the v1 image.** You will need them in Module 5 when you deploy the container to Amazon ECS with auto-scaling and a load balancer.

### What to Remove

If you launched a new EC2 instance just for this test, stop it to avoid charges:

```bash
# From your local machine (not the EC2 instance)
aws ec2 stop-instances --instance-ids <INSTANCE_ID> --region ap-south-1
```

Remove the ECR-tagged image from your local machine to save disk space (the image is safely stored in ECR):

```bash
docker rmi <ACCOUNT_ID>.dkr.ecr.ap-south-1.amazonaws.com/truck-delay-app:v1
```

### Cost Awareness

| Resource | Cost | Monthly Estimate |
|---|---|---|
| ECR storage | $0.10 per GB per month | ~$0.11 (~₹8) for one 1.08 GB image |
| ECR data transfer (pull) | Free within same region | $0 if EC2 and ECR are both in ap-south-1 |
| ECR data transfer (cross-region) | $0.09 per GB | Avoid by keeping everything in ap-south-1 |

A single container image costs roughly ₹8/month to store. This is negligible, which is why we leave it in place for Module 5.

---

## Bridge to Module 5

Your container runs on a single EC2 instance. You started it manually with `docker run`. This raises several questions:

- **Scaling:** What if 10,000 users hit the dashboard at once and one instance cannot handle the load?
- **Availability:** What if the EC2 instance crashes at 3 AM? Who restarts the container?
- **Updates:** How do you deploy a new version (v2) without downtime?

In **Module 5**, you will deploy this same ECR image to **Amazon ECS (Elastic Container Service)** with an **Application Load Balancer** and **auto-scaling rules**. ECS answers all three questions: it distributes traffic across multiple containers, automatically replaces crashed ones, and supports rolling deployments. Your ECR image (`truck-delay-app:v1`) is the input -- ECS is the orchestrator.

---

## Checkpoint

Before moving to Module 5, verify:

- [ ] `aws ecr describe-repositories --region ap-south-1` lists `truck-delay-app`.
- [ ] The ECR Console shows the `v1` image in the repository.
- [ ] You successfully pulled and ran the image on a different machine (EC2 or second laptop).
- [ ] You understand the three-step workflow: **authenticate** -> **tag** -> **push**.

---

*FreshBasket Logistics -- Pune | Module 4, Lab 4 of 4*
