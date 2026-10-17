# Docker Guide: Healthcare Multi-Agent System

Step-by-step instructions for building, running, publishing and deploying the healthcare multi-agent app
(LangGraph + Gradio) with Docker. Commands are shown for **Windows PowerShell**. On macOS/Linux, use the
`# macOS/Linux:` alternative where one is given.

## Contents
1. [What gets containerized](#1-what-gets-containerized)
2. [Install Docker](#2-install-docker)
3. [Get the code](#3-get-the-code)
4. [Configure your OpenRouter key](#4-configure-your-openrouter-key)
5. [Option A: Run with Docker Compose (recommended)](#5-option-a-run-with-docker-compose-recommended)
6. [Option B: Run with plain Docker commands](#6-option-b-run-with-plain-docker-commands)
7. [Option C: Run the prebuilt image from GitHub (GHCR)](#7-option-c-run-the-prebuilt-image-from-github-ghcr)
8. [Use the app](#8-use-the-app)
9. [Everyday commands](#9-everyday-commands)
10. [Update to a new version](#10-update-to-a-new-version)
11. [How the image is published to GitHub (CI/CD)](#11-how-the-image-is-published-to-github-cicd)
12. [Deploy the container to a server](#12-deploy-the-container-to-a-server)
13. [Environment variables](#13-environment-variables)
14. [Troubleshooting](#14-troubleshooting)
15. [Clean up](#15-clean-up)

---

## 1. What gets containerized

| File | Purpose |
|---|---|
| `Dockerfile` | Builds the image: Python 3.11 slim, installs `requirements.txt`, creates the 40-table SQLite database at build time, runs as a non-root user, exposes port **7860**, and adds a health check. |
| `.dockerignore` | Keeps `.env`, virtual environments, `__pycache__` and local `data/*.db` out of the image, so your API key never goes into the image. |
| `docker-compose.yml` | One-command start: `docker compose up --build -d`. Reads settings from `.env`. |
| `../.github/workflows/docker-healthcare-agents.yml` | GitHub Actions workflow. It builds the image on every PR and publishes it to `ghcr.io/akriashok/healthcare-multi-agent`. |

How the container runs:
```
docker run  ->  python app.py  ->  Gradio UI on 0.0.0.0:7860
                         |
                         +-> LangGraph agents -> OpenRouter LLM (needs OPENROUTER_API_KEY)
                         +-> SQLite database at /app/data/healthcare.db (built into the image)
```

The database is synthetic and built from a fixed random seed, so every image contains the same data. You don't need a
volume for it.

---

## 2. Install Docker

### Windows / macOS
1. Download **Docker Desktop**: https://www.docker.com/products/docker-desktop/
2. Install it and start it. On Windows, accept the WSL 2 backend if asked, then restart if prompted.
3. Wait until Docker Desktop shows **Engine running**.

### Linux (Ubuntu)
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER      # lets you run docker without sudo
newgrp docker                       # or log out and back in
```

### Check the install
```powershell
docker --version
docker compose version
docker run --rm hello-world
```
All three should work without errors. If `docker compose` isn't found, update Docker Desktop. Compose v2 is built in.

---

## 3. Get the code

```powershell
git clone https://github.com/akriashok/AI-Practise.git
cd AI-Practise\healthcare-multi-agent-langgraph       # macOS/Linux: cd AI-Practise/healthcare-multi-agent-langgraph
```

Every command below is run from this `healthcare-multi-agent-langgraph` folder, which contains `Dockerfile` and
`docker-compose.yml`.

---

## 4. Configure your OpenRouter key

1. Create an API key at https://openrouter.ai/keys.
2. Copy the example settings file:
   ```powershell
   copy .env.example .env               # macOS/Linux: cp .env.example .env
   ```
3. Open `.env` in an editor and set your key:
   ```
   OPENROUTER_API_KEY=sk-or-v1-...your key...
   OPENROUTER_MODEL=openai/gpt-oss-120b
   OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
   ```
4. Optional extra settings you can add to `.env`:
   ```
   MAX_REFLECTIONS=2      # max times the Reflection agent can send an answer back
   PORT=7860              # host port when using docker compose
   ```

`.env` is git-ignored and Docker-ignored. It is passed to the container **at run time** and never copied into
the image. Never commit it.

---

## 5. Option A: Run with Docker Compose (recommended)

### Step 5.1: Build and start
```powershell
docker compose up --build -d
```
- `--build`: builds the image from the `Dockerfile`. The first build takes 1–3 minutes.
- `-d`: runs in the background (detached).

If you see `Set OPENROUTER_API_KEY in .env`, go back to [step 4](#4-configure-your-openrouter-key).

### Step 5.2: Check that it is running
```powershell
docker compose ps
```
Wait until the `STATUS` column shows `Up ... (healthy)`. This takes about 20–60 seconds.

### Step 5.3: Watch the logs (optional)
```powershell
docker compose logs -f
```
The app is ready when you see `Running on local URL:  http://0.0.0.0:7860`. Press **Ctrl+C** to stop following
the logs. The container keeps running.

### Step 5.4: Open the app
Go to **http://localhost:7860** (or the `PORT` you set in `.env`).

### Step 5.5: Stop it
```powershell
docker compose down
```

---

## 6. Option B: Run with plain Docker commands

### Step 6.1: Build the image
```powershell
docker build -t healthcare-multi-agent .
```
The final `.` means "use the current folder as the build context". During the build, the log prints the 40 table
names and row counts.

### Step 6.2: Check that the image exists
```powershell
docker images healthcare-multi-agent
```
The image is about 830 MB.

### Step 6.3: Run the container
```powershell
docker run -d --name healthcare-multi-agent -p 7860:7860 --env-file .env --restart unless-stopped healthcare-multi-agent
```
| Flag | Meaning |
|---|---|
| `-d` | Run in the background |
| `--name healthcare-multi-agent` | Name the container so you can refer to it later |
| `-p 7860:7860` | Map host port 7860 to container port 7860. Use `-p 8080:7860` to serve on host port 8080 instead. |
| `--env-file .env` | Pass your OpenRouter settings into the container |
| `--restart unless-stopped` | Restart automatically after a crash or reboot |

Without a `.env` file, pass the key directly:
```powershell
docker run -d --name healthcare-multi-agent -p 7860:7860 -e OPENROUTER_API_KEY=sk-or-v1-... healthcare-multi-agent
```

### Step 6.4: Check health and logs
```powershell
docker ps                                   # STATUS should become "(healthy)"
docker logs -f healthcare-multi-agent       # Ctrl+C to stop following
```

### Step 6.5: Open the app
Go to **http://localhost:7860**.

### Step 6.6: Stop and remove
```powershell
docker stop healthcare-multi-agent
docker rm healthcare-multi-agent
```

---

## 7. Option C: Run the prebuilt image from GitHub (GHCR)

GitHub Actions publishes the image to GitHub Container Registry, so you can run it without building.

### Step 7.1: Log in to GHCR (needed while the package is private)
1. Create a GitHub **Personal access token (classic)** with the `read:packages` scope:
   GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token.
2. Log in:
   ```powershell
   docker login ghcr.io -u akriashok
   ```
   Paste the token when it asks for a password.

To skip this step for everyone, make the package public: GitHub → your profile → **Packages** →
`healthcare-multi-agent` → **Package settings** → **Change visibility** → Public.

### Step 7.2: Pull the image
```powershell
docker pull ghcr.io/akriashok/healthcare-multi-agent:latest
```
Available tags:
| Tag | Built from |
|---|---|
| `latest` | Latest commit on the default branch |
| `claude-code-usage-nbotoo`, `main` | Latest commit on that branch |
| `sha-<short-sha>` | One exact commit. Use this to pin a version. |
| `1.2.3` | A git tag `v1.2.3` |

### Step 7.3: Run it
```powershell
docker run -d --name healthcare-multi-agent -p 7860:7860 --env-file .env --restart unless-stopped ghcr.io/akriashok/healthcare-multi-agent:latest
```

With Compose, `docker compose pull` followed by `docker compose up -d` uses the same image, because
`docker-compose.yml` names it `ghcr.io/akriashok/healthcare-multi-agent:latest`.

---

## 8. Use the app

1. Open **http://localhost:7860**.
2. In the **Chat** tab, click an example question or type your own, for example:
   - `How many active providers are there in each specialty?`
   - `Where is file FS-20250007 in the pipeline?`
   - `Chart how many files each user passed or failed validation and reached core`
3. Each answer takes about 15–60 seconds. The router, the specialist agent and the Reflection agent each make LLM
   calls.
4. The right-hand panel shows charts, the generated SQL, the result table and the agent trace.
5. The **Architecture** tab shows the LangGraph diagram. The **Database** tab shows row counts for the 40 tables.

---

## 9. Everyday commands

| Task | Docker Compose | Plain Docker |
|---|---|---|
| Start | `docker compose up -d` | `docker start healthcare-multi-agent` |
| Stop | `docker compose stop` | `docker stop healthcare-multi-agent` |
| Stop and remove | `docker compose down` | `docker rm -f healthcare-multi-agent` |
| Restart (e.g. after editing `.env`) | `docker compose up -d --force-recreate` | `docker rm -f healthcare-multi-agent`, then re-run step 6.3 |
| Logs | `docker compose logs -f` | `docker logs -f healthcare-multi-agent` |
| Status / health | `docker compose ps` | `docker ps` |
| Shell inside container | `docker compose exec healthcare-agents bash` | `docker exec -it healthcare-multi-agent bash` |
| Ask one question from the CLI | `docker compose exec healthcare-agents python -m healthcare_agents.graph "Top 5 denial reasons by billed amount"` | `docker exec -it healthcare-multi-agent python -m healthcare_agents.graph "Top 5 denial reasons by billed amount"` |
| Resource usage | `docker stats` | `docker stats` |

`docker restart` alone does **not** reload `.env`. Recreate the container instead.

---

## 10. Update to a new version

### If you build locally
```powershell
git pull
docker compose up --build -d
```

### If you use the GHCR image
```powershell
docker compose pull
docker compose up -d
# or, plain Docker:
docker pull ghcr.io/akriashok/healthcare-multi-agent:latest
docker rm -f healthcare-multi-agent
docker run -d --name healthcare-multi-agent -p 7860:7860 --env-file .env --restart unless-stopped ghcr.io/akriashok/healthcare-multi-agent:latest
```

---

## 11. How the image is published to GitHub (CI/CD)

The workflow lives at `.github/workflows/docker-healthcare-agents.yml` in the repository root.

| Event | What happens |
|---|---|
| Pull request that changes `healthcare-multi-agent-langgraph/**` | Builds the image to check that it compiles. Nothing is pushed. |
| Push to `claude/code-usage-nbotoo` or `main` | Builds and **pushes** to `ghcr.io/akriashok/healthcare-multi-agent` (`latest`, branch and `sha-` tags). |
| Push of a tag such as `v1.0.0` | Builds and pushes the `1.0.0` tag. |
| Manual run | GitHub → **Actions** → *Docker - healthcare multi-agent* → **Run workflow**. |

It authenticates with the built-in `GITHUB_TOKEN`, so **you don't need to add any secrets**.

### Step 11.1: Publish the first image
1. Merge the Docker pull request into the default branch (`claude/code-usage-nbotoo`).
2. Open GitHub → **Actions** and wait for *Docker - healthcare multi-agent* to finish (green check).
3. Open your GitHub profile → **Packages**. `healthcare-multi-agent` is listed there.
4. Optional: make it public, as described in [step 7.1](#step-71-log-in-to-ghcr-needed-while-the-package-is-private).
5. Optional: link the package to the repo. Package page → **Package settings** → **Connect repository** →
   `AI-Practise`.

### Step 11.2: Release a versioned image
```powershell
git tag v1.0.0
git push origin v1.0.0
```
This publishes `ghcr.io/akriashok/healthcare-multi-agent:1.0.0`.

---

## 12. Deploy the container to a server

Any host that can run Docker can serve the app. Two common options:

### 12.1 A Linux VM (AWS EC2, Azure VM, GCP, DigitalOcean, etc.)
1. Create a VM (Ubuntu, at least 1 vCPU / 2 GB RAM) and open inbound port **7860** (or 80/443 if you use a
   reverse proxy).
2. SSH in and install Docker ([step 2, Linux](#linux-ubuntu)).
3. Create `.env` on the server with your `OPENROUTER_API_KEY` ([step 4](#4-configure-your-openrouter-key)).
4. Log in to GHCR if the package is private ([step 7.1](#step-71-log-in-to-ghcr-needed-while-the-package-is-private)).
5. Run:
   ```bash
   docker run -d --name healthcare-multi-agent -p 7860:7860 --env-file .env --restart unless-stopped \
     ghcr.io/akriashok/healthcare-multi-agent:latest
   ```
6. Open `http://<server-ip>:7860`.
7. For HTTPS, put a reverse proxy such as Caddy or Nginx in front of port 7860, and only expose 80/443.

### 12.2 Render (Docker runtime)
The repository already has a Python-based `render.yaml`. To run the Docker image on Render instead:
1. Render → **New → Web Service** → connect the `AI-Practise` repo.
2. Set **Root Directory** to `healthcare-multi-agent-langgraph`, and **Runtime** to **Docker**. Render detects the
   `Dockerfile`.
3. Under **Environment**, add `OPENROUTER_API_KEY`. Render sets `PORT` automatically, and the app reads it.
4. Click **Create Web Service**.

Other platforms that accept a Dockerfile or GHCR image work the same way: Railway, Fly.io, Google Cloud Run,
Azure Container Apps and AWS App Runner. Set `OPENROUTER_API_KEY` and expose the port given by `PORT` (default 7860).

---

## 13. Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `OPENROUTER_API_KEY` | (required) | OpenRouter API key |
| `OPENROUTER_MODEL` | `openai/gpt-oss-120b` | Chat model used by every agent |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | OpenAI-compatible endpoint |
| `MAX_REFLECTIONS` | `2` | Most times the Reflection agent can send an answer back |
| `PORT` | `7860` | `docker run` / cloud hosts: the port the app listens on inside the container. Docker Compose: only the host port; the container always listens on 7860. |
| `HOST` | `0.0.0.0` | Bind address. Keep `0.0.0.0` inside Docker. |
| `HEALTHCARE_DB_PATH` | `/app/data/healthcare.db` | SQLite location. It is built into the image. |

---

## 14. Troubleshooting

| Problem | Fix |
|---|---|
| `docker: command not found` / `Cannot connect to the Docker daemon` | Start Docker Desktop and wait for **Engine running**. On Linux, run `sudo systemctl start docker`. |
| `Set OPENROUTER_API_KEY in .env` when running compose | `.env` is missing, or has no key. See [step 4](#4-configure-your-openrouter-key). |
| Chat answers show `OPENROUTER_API_KEY is not set` | The container was started without `--env-file .env` or `-e OPENROUTER_API_KEY=...`. Recreate it. |
| `401` / `invalid api key` errors in answers | The key is wrong or revoked. Fix `.env`, then run `docker compose up -d --force-recreate`. |
| `port is already allocated` | Port 7860 is in use. Stop the other app, or use another port: set `PORT=7861` in `.env` (compose) or `-p 7861:7860` (docker run). |
| Status stays `(health: starting)` or becomes `unhealthy` | Check `docker logs healthcare-multi-agent`. Startup takes 10–20 s, and the health check allows 60 s. |
| Browser can't reach `localhost:7860` | Check that `docker ps` shows `0.0.0.0:7860->7860/tcp`. On a remote server, open the port in the firewall or security group. |
| `denied` / `unauthorized` on `docker pull ghcr.io/...` | Run `docker login ghcr.io` with a PAT that has `read:packages`, or make the package public. |
| `manifest unknown` on pull | The workflow hasn't published yet. Merge to the default branch and wait for the Actions run. |
| Build fails at `pip install` | Check your network or proxy, then rebuild with `docker compose build --no-cache`. |
| Answers are slow | This is expected. Each question makes several LLM calls (15–60 s). |
| Windows: line-ending or permission issues | Clone with Git's default settings and run Docker Desktop with the WSL 2 backend. |

---

## 15. Clean up

```powershell
docker compose down --rmi all                        # stop and remove the container and its image
docker rm -f healthcare-multi-agent                  # plain docker: remove the container
docker rmi healthcare-multi-agent ghcr.io/akriashok/healthcare-multi-agent:latest   # remove images
docker system prune                                  # remove unused containers, networks and dangling images
```
