# Observability Agent — Complete Setup Guide

This guide walks you through setting up the Observability Agent from zero to a live deployment on Azure.
No prior cloud experience needed — every step is explained.

---

## Table of Contents

1. [What This System Does](#1-what-this-system-does)
2. [How It Works (Architecture)](#2-how-it-works-architecture)
3. [What You Need Before Starting](#3-what-you-need-before-starting)
4. [Step 1 — Get Your DataDog Keys](#4-step-1--get-your-datadog-keys)
5. [Step 2 — Set Up Azure OpenAI](#5-step-2--set-up-azure-openai)
6. [Step 3 — Run Locally (Test Before Deploying)](#6-step-3--run-locally-test-before-deploying)
7. [Step 4 — Deploy to Azure](#7-step-4--deploy-to-azure)
8. [Step 5 — Configure Environment Variables on Azure](#8-step-5--configure-environment-variables-on-azure)
9. [Step 6 — Test the Live Deployment](#9-step-6--test-the-live-deployment)
10. [All Environment Variables Reference](#10-all-environment-variables-reference)
11. [Troubleshooting Common Issues](#11-troubleshooting-common-issues)

---

## 1. What This System Does

This is a chat-based observability assistant. You open a browser, type a question like:

> "Are there any monitors firing right now?"
> "Show me error rate for the payments service in the last hour"
> "What does CPU look like on the api-gateway hosts?"

The assistant connects to your DataDog account, queries the real data, and replies in plain English.

It uses:
- **DataDog** as the data source (your metrics, logs, monitors, alerts)
- **Azure OpenAI (GPT-4o)** as the AI brain that understands your question
- **FastAPI (Python)** as the backend server
- **React** as the browser UI

---

## 2. How It Works (Architecture)

```
Your Browser
     |
     | (types a question)
     v
React UI  (frontend)
     |
     | HTTP POST /chat
     v
FastAPI Server  (backend)
     |
     |--- sends question + history --> Azure OpenAI GPT-4o
     |                                        |
     |                                        | "call this DataDog tool"
     |                                        v
     |--- calls tool -----------------> DataDog MCP Server
     |                                        |
     |                                        | returns metrics/logs/alerts
     |                                        v
     |<--- final answer <------------- Azure OpenAI GPT-4o
     |
     v
React UI displays the answer
```

**MCP** (Model Context Protocol) is a standard way for AI models to call external tools.
The DataDog MCP server is a small program that translates the AI's requests into DataDog API calls.

---

## 3. What You Need Before Starting

Install these on your machine before anything else.

### Required Software

| Tool | What it is | Install |
|------|-----------|---------|
| **Python 3.11+** | Runs the backend | https://www.python.org/downloads/ |
| **Node.js 18+** | Runs the frontend + DataDog MCP | https://nodejs.org/en/download |
| **Docker Desktop** | Packages the app for deployment | https://www.docker.com/products/docker-desktop/ |
| **Azure CLI** | Controls Azure from your terminal | https://learn.microsoft.com/en-us/cli/azure/install-azure-cli |
| **Git** | Version control | https://git-scm.com/downloads |

### Verify everything is installed

Open a terminal and run these commands. Each should print a version number:

```bash
python --version        # should show Python 3.11.x or higher
node --version          # should show v18.x.x or higher
npm --version           # should show 9.x.x or higher
docker --version        # should show Docker version 24.x or higher
az --version            # should show azure-cli 2.x.x or higher
```

### Required Accounts

- A **DataDog account** (your company should already have one)
- An **Azure subscription** with permission to create resources
- Access to **Azure OpenAI** (requires approval from Microsoft — ask your Azure admin if not enabled)

---

## 4. Step 1 — Get Your DataDog Keys

You need two keys from DataDog: an **API Key** and an **Application Key**.

### Get the API Key

1. Log in to DataDog at https://app.datadoghq.com
2. In the left sidebar, click **Organization Settings** (bottom left, gear icon)
3. Click **API Keys**
4. Click **+ New Key**
5. Name it: `observability-agent`
6. Click **Create Key**
7. **Copy the key now** — DataDog will not show it again

> Save it somewhere safe temporarily. You will paste it into your config file later.

### Get the Application Key

1. Still in **Organization Settings**, click **Application Keys**
2. Click **+ New Key**
3. Name it: `observability-agent`
4. Click **Create Key**
5. **Copy the key now**

### Find Your DataDog Site

Your DataDog site depends on which region your account is on:

| If your DataDog URL is... | Your DD_SITE value is |
|--------------------------|----------------------|
| app.datadoghq.com | `datadoghq.com` |
| app.datadoghq.eu | `datadoghq.eu` |
| us3.datadoghq.com | `us3.datadoghq.com` |
| us5.datadoghq.com | `us5.datadoghq.com` |

---

## 5. Step 2 — Set Up Azure OpenAI

### Part A — Create an Azure OpenAI Resource

1. Go to https://portal.azure.com
2. In the search bar at the top, type **"Azure OpenAI"** and click it
3. Click **+ Create**
4. Fill in the form:
   - **Subscription**: select your subscription
   - **Resource group**: create new → name it `observability-agent-rg`
   - **Region**: choose `East US` or `West Europe` (GPT-4o availability varies by region)
   - **Name**: `observability-agent-openai` (must be globally unique — add your initials if taken)
   - **Pricing tier**: Standard S0
5. Click **Review + Create**, then **Create**
6. Wait ~2 minutes for deployment to complete
7. Click **Go to resource**

### Part B — Deploy the GPT-4o Model

You are inside your Azure OpenAI resource now.

1. Click **Model deployments** in the left menu
2. Click **Manage Deployments** — this opens Azure OpenAI Studio
3. Click **+ New deployment**
4. Fill in:
   - **Model**: select `gpt-4o`
   - **Deployment name**: `gpt-4o` (write this down — it goes in your config)
   - **Version**: latest available
   - **Tokens per minute**: 40K (can increase later)
5. Click **Deploy**

### Part C — Get Your Azure OpenAI Keys

Back in the Azure Portal (not OpenAI Studio):

1. Go to your Azure OpenAI resource
2. In the left menu, click **Keys and Endpoint** (under Resource Management)
3. Copy **KEY 1** — this is your `AZURE_OPENAI_KEY`
4. Copy the **Endpoint** URL — this is your `AZURE_OPENAI_ENDPOINT`
   - It looks like: `https://observability-agent-openai.openai.azure.com/`

---

## 6. Step 3 — Run Locally (Test Before Deploying)

Always test locally first. It is much faster to debug than on Azure.

### Set Up the Backend

```bash
# Navigate to the backend folder
cd observability-agent/backend

# Create a copy of the example config file
cp .env.example .env
```

Now open `.env` in any text editor and fill in your values:

```env
# Azure OpenAI — from Step 2
AZURE_OPENAI_KEY=abc123...             # your KEY 1
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT=gpt-4o         # the deployment name you chose

# DataDog — from Step 1
DD_API_KEY=abc123...                   # your DataDog API Key
DD_APP_KEY=xyz789...                   # your DataDog Application Key
DD_SITE=datadoghq.com                  # your site from the table above

# Leave this as-is for local development
FRONTEND_URL=http://localhost:5173
```

Save the file.

```bash
# Create a Python virtual environment (keeps dependencies isolated)
python -m venv venv

# Activate it
# On Mac/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Start the backend server
uvicorn main:app --reload --port 8000
```

You should see:
```
[agent] Connected to DataDog MCP — 12 tools loaded
INFO:     Uvicorn running on http://0.0.0.0:8000
```

If you see the "tools loaded" line, the DataDog connection is working.

### Set Up the Frontend

Open a **new terminal window** (keep the backend running):

```bash
cd observability-agent/frontend

# Install Node dependencies
npm install

# Start the frontend
npm run dev
```

You should see:
```
  VITE v5.x.x  ready in 300ms
  ➜  Local:   http://localhost:5173/
```

Open http://localhost:5173 in your browser. You should see the chat interface.

### Quick Local Test

Type this in the chat:

> "Are there any active monitors right now?"

If you get a real response about your DataDog monitors, everything is working correctly.

---

## 7. Step 4 — Deploy to Azure

We will deploy using **Azure Container Apps** — Azure's managed container service.
It handles scaling, HTTPS certificates, and restarts automatically.

### Overview of what we create

```
Azure Resource Group: observability-agent-rg
├── Azure Container Registry (ACR)   ← stores our Docker images
├── Container Apps Environment       ← the network they run in
├── Container App: backend           ← the FastAPI server
└── Container App: frontend          ← the React UI
```

### Part A — Log in to Azure

```bash
az login
```

A browser window opens. Sign in with your Azure account.

```bash
# Verify you are on the right subscription
az account show --query "{name:name, id:id}" -o table

# If wrong subscription, switch to the correct one:
az account set --subscription "Your Subscription Name"
```

### Part B — Create the Resource Group

```bash
az group create \
  --name observability-agent-rg \
  --location eastus
```

### Part C — Create Azure Container Registry

This is where your Docker images will be stored.

```bash
# Create the registry (name must be globally unique, letters/numbers only)
az acr create \
  --resource-group observability-agent-rg \
  --name obsagentregistry \
  --sku Basic \
  --admin-enabled true
```

Log in to your registry:

```bash
az acr login --name obsagentregistry
```

### Part D — Build and Push the Backend Image

```bash
cd observability-agent/backend

# Build the Docker image
docker build -t obsagentregistry.azurecr.io/obs-backend:latest .

# Push it to Azure Container Registry
docker push obsagentregistry.azurecr.io/obs-backend:latest
```

> If you get "Dockerfile not found", create one — see the Dockerfile section below.

### Part E — Build and Push the Frontend Image

```bash
cd observability-agent/frontend

# Build the Docker image
docker build -t obsagentregistry.azurecr.io/obs-frontend:latest .

# Push it to Azure Container Registry
docker push obsagentregistry.azurecr.io/obs-frontend:latest
```

### Part F — Create the Container Apps Environment

```bash
# Install the Container Apps extension if not already installed
az extension add --name containerapp --upgrade

# Create the environment (the shared network for your containers)
az containerapp env create \
  --name obs-agent-env \
  --resource-group observability-agent-rg \
  --location eastus
```

### Part G — Deploy the Backend Container App

```bash
# Get your ACR password
ACR_PASSWORD=$(az acr credential show \
  --name obsagentregistry \
  --query "passwords[0].value" \
  --output tsv)

# Deploy backend
az containerapp create \
  --name obs-backend \
  --resource-group observability-agent-rg \
  --environment obs-agent-env \
  --image obsagentregistry.azurecr.io/obs-backend:latest \
  --registry-server obsagentregistry.azurecr.io \
  --registry-username obsagentregistry \
  --registry-password "$ACR_PASSWORD" \
  --target-port 8000 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 3 \
  --cpu 0.5 \
  --memory 1.0Gi
```

Get the backend URL:

```bash
BACKEND_URL=$(az containerapp show \
  --name obs-backend \
  --resource-group observability-agent-rg \
  --query "properties.configuration.ingress.fqdn" \
  --output tsv)

echo "Backend URL: https://$BACKEND_URL"
```

Save this URL — you need it for the frontend.

### Part H — Deploy the Frontend Container App

```bash
az containerapp create \
  --name obs-frontend \
  --resource-group observability-agent-rg \
  --environment obs-agent-env \
  --image obsagentregistry.azurecr.io/obs-frontend:latest \
  --registry-server obsagentregistry.azurecr.io \
  --registry-username obsagentregistry \
  --registry-password "$ACR_PASSWORD" \
  --target-port 80 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 2 \
  --cpu 0.25 \
  --memory 0.5Gi

# Get the frontend URL
FRONTEND_URL=$(az containerapp show \
  --name obs-frontend \
  --resource-group observability-agent-rg \
  --query "properties.configuration.ingress.fqdn" \
  --output tsv)

echo "Frontend URL: https://$FRONTEND_URL"
```

---

## 8. Step 5 — Configure Environment Variables on Azure

Your backend needs all the secret keys. Never bake secrets into Docker images.
Set them as environment variables on the Container App.

```bash
az containerapp update \
  --name obs-backend \
  --resource-group observability-agent-rg \
  --set-env-vars \
    AZURE_OPENAI_KEY="your_key_here" \
    AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/" \
    AZURE_OPENAI_API_VERSION="2024-02-15-preview" \
    AZURE_OPENAI_DEPLOYMENT="gpt-4o" \
    DD_API_KEY="your_datadog_api_key" \
    DD_APP_KEY="your_datadog_app_key" \
    DD_SITE="datadoghq.com" \
    FRONTEND_URL="https://$FRONTEND_URL"
```

Update the frontend to point to the live backend:

```bash
az containerapp update \
  --name obs-frontend \
  --resource-group observability-agent-rg \
  --set-env-vars \
    VITE_API_URL="https://$BACKEND_URL"
```

Restart both apps to pick up the new variables:

```bash
az containerapp revision restart \
  --name obs-backend \
  --resource-group observability-agent-rg

az containerapp revision restart \
  --name obs-frontend \
  --resource-group observability-agent-rg
```

---

## 9. Step 6 — Test the Live Deployment

### Test 1 — Backend Health Check

Open your browser and go to:

```
https://<your-backend-url>/health
```

You should see a JSON response like:
```json
{
  "status": "ok",
  "tools_loaded": 12,
  "tool_names": ["list_monitors", "query_metrics", "get_logs", ...]
}
```

If `tools_loaded` is 0, the DataDog MCP connection failed. Check your DD_API_KEY and DD_APP_KEY.

### Test 2 — API via curl

```bash
# Create a session
curl -X POST https://<your-backend-url>/session

# Response: {"session_id": "abc-123-..."}

# Send a message (replace the session_id)
curl -X POST https://<your-backend-url>/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "abc-123-...", "message": "How many monitors are currently OK?"}'
```

Expected response:
```json
{
  "session_id": "abc-123-...",
  "response": "Currently, 47 out of 50 monitors are in OK state. 3 monitors are alerting: ..."
}
```

### Test 3 — Frontend UI

Open the frontend URL in your browser:
```
https://<your-frontend-url>
```

You should see the dark chat interface. Type:

> "Show me the top 5 services by error rate in the last 30 minutes"

A real answer from your DataDog account should appear within 10–15 seconds.

### Test 4 — Full Conversation Test

Try this multi-turn conversation to verify session history works:

```
You:   "What's the error rate on the payments service?"
Agent: [returns data]
You:   "Compare that to yesterday at the same time"
Agent: [should remember we're talking about payments service]
You:   "Are there any alerts related to this service?"
Agent: [should still know the context]
```

If the agent remembers context across messages, sessions are working correctly.

---

## 10. All Environment Variables Reference

Complete reference for every environment variable in the system.

### Backend Variables (set in backend/.env)

| Variable | Required | Example Value | Description |
|----------|----------|---------------|-------------|
| `AZURE_OPENAI_KEY` | YES | `abc123def456...` | Your Azure OpenAI API key (KEY 1 from portal) |
| `AZURE_OPENAI_ENDPOINT` | YES | `https://my-resource.openai.azure.com/` | Your Azure OpenAI resource endpoint URL |
| `AZURE_OPENAI_API_VERSION` | YES | `2024-02-15-preview` | API version — keep as-is unless told to update |
| `AZURE_OPENAI_DEPLOYMENT` | YES | `gpt-4o` | The deployment name you set in Azure OpenAI Studio |
| `DD_API_KEY` | YES | `abc123...` | DataDog API Key (from Org Settings > API Keys) |
| `DD_APP_KEY` | YES | `xyz789...` | DataDog Application Key (from Org Settings > App Keys) |
| `DD_SITE` | YES | `datadoghq.com` | Your DataDog site (see table in Step 1) |
| `FRONTEND_URL` | YES | `http://localhost:5173` | URL of the frontend (for CORS). Use full Azure URL in production |

### Frontend Variables

| Variable | Required | Example Value | Description |
|----------|----------|---------------|-------------|
| `VITE_API_URL` | Only in production | `https://obs-backend.azurecontainerapps.io` | Backend URL. Not needed locally (Vite proxy handles it) |

---

## 11. Troubleshooting Common Issues

### "tools_loaded: 0" on the health endpoint

**Cause:** DataDog MCP server failed to start or connect.

**Fix:**
1. Check `DD_API_KEY` and `DD_APP_KEY` are correct — no extra spaces or newlines
2. Verify `DD_SITE` matches your DataDog account region
3. Check Node.js is installed (`node --version`) — the MCP server needs it
4. Check backend logs: `az containerapp logs show --name obs-backend --resource-group observability-agent-rg --follow`

---

### "CORS error" in browser console

**Cause:** The frontend URL does not match the `FRONTEND_URL` environment variable on the backend.

**Fix:**
Update `FRONTEND_URL` on the backend to exactly match your frontend's URL (including `https://`):
```bash
az containerapp update \
  --name obs-backend \
  --resource-group observability-agent-rg \
  --set-env-vars FRONTEND_URL="https://obs-frontend.azurecontainerapps.io"
```

---

### "AuthenticationError" from Azure OpenAI

**Cause:** Wrong key, wrong endpoint, or deployment name does not exist.

**Fix:**
1. Double-check `AZURE_OPENAI_KEY` — copy it fresh from Azure Portal
2. Make sure `AZURE_OPENAI_ENDPOINT` ends with a `/`
3. Verify `AZURE_OPENAI_DEPLOYMENT` matches exactly what you named the deployment in Azure OpenAI Studio (case-sensitive)
4. Test the key directly:
```bash
curl https://YOUR-ENDPOINT/openai/deployments/gpt-4o/chat/completions?api-version=2024-02-15-preview \
  -H "Content-Type: application/json" \
  -H "api-key: YOUR-KEY" \
  -d '{"messages":[{"role":"user","content":"hello"}]}'
```

---

### Frontend shows "Something went wrong" on every message

**Cause:** Frontend cannot reach the backend.

**Fix locally:** Make sure the backend is running on port 8000 and the Vite proxy is configured.

**Fix on Azure:**
1. Check the frontend can reach the backend URL:
```bash
curl https://<backend-url>/health
```
2. If that works, check `VITE_API_URL` is set correctly on the frontend container app.

---

### Backend container keeps restarting on Azure

**Cause:** Usually a missing environment variable causing a crash at startup.

**Fix:**
```bash
# View live logs
az containerapp logs show \
  --name obs-backend \
  --resource-group observability-agent-rg \
  --follow
```
Look for the error message in the first few lines. Usually it says which variable is missing.

---

### Sessions expire too quickly

**Cause:** Default TTL is 60 minutes. Long gaps between messages will reset context.

**Fix:** Change the TTL in `session.py`:
```python
sessions = SessionStore(ttl_minutes=120)  # 2 hours
```
Rebuild and redeploy the backend image.

---

### How to update the app after making code changes

```bash
# 1. Rebuild the image
docker build -t obsagentregistry.azurecr.io/obs-backend:latest ./backend

# 2. Push the new image
docker push obsagentregistry.azurecr.io/obs-backend:latest

# 3. Force Azure to pull the latest image
az containerapp update \
  --name obs-backend \
  --resource-group observability-agent-rg \
  --image obsagentregistry.azurecr.io/obs-backend:latest
```

Repeat with `obs-frontend` for frontend changes.

---

## Credentials Summary (fill this in and store securely)

Use a password manager or Azure Key Vault to store these. Never commit them to Git.

```
AZURE_OPENAI_KEY         = ________________________________
AZURE_OPENAI_ENDPOINT    = ________________________________
AZURE_OPENAI_DEPLOYMENT  = gpt-4o
DD_API_KEY               = ________________________________
DD_APP_KEY               = ________________________________
DD_SITE                  = ________________________________
ACR_NAME                 = obsagentregistry
BACKEND_URL              = ________________________________
FRONTEND_URL             = ________________________________
```
