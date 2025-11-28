# DEPLOYMENT.md

This document explains how to run, deploy, containerize, and manage the **AI Support Assistant** built using Streamlit + Gemini API.

---

# 1. Requirements

## System Requirements

* Python **3.10+** (3.12/3.13 supported)
* Pip 23+
* Virtual environment recommended
* Internet connection (Gemini API calls)
* Port **8501** open (Streamlit default)

## Environment Variables

Set this before running:

```bash
export GEMINI_API_KEY="your_api_key_here"
```

Or create a `.env` file:

```
GEMINI_API_KEY=your_api_key_here
```

---

# 2. Local Development Setup

### Step 1 — Clone the Repo

```bash
git clone <repo-url>
cd <repo-folder>
```

### Step 2 — Create and Activate Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
.venv\Scripts\activate      # Windows
```

### Step 3 — Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4 — Run the App

```bash
streamlit run app.py
```

Your local app will run on:

```
http://localhost:8501
```

---

# 3. Deployment Options

# Option A — Docker Deployment (Recommended)

Create a **Dockerfile**:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . /app
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
ENV GEMINI_API_KEY=""
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.headless=true"]
```

Build and run:

```bash
docker build -t ai-support-agent .
docker run -p 8501:8501 -e GEMINI_API_KEY=$GEMINI_API_KEY ai-support-agent
```

---

# Option B — Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'
services:
  ai-support:
    build: .
    ports:
      - "8501:8501"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    restart: unless-stopped
    volumes:
      - ./data:/app/data
```

Run with:

```bash
docker compose up -d
```

---

# Option C — Systemd Server Deployment

For Ubuntu/Linux servers.

Create service file:

```
/etc/systemd/system/ai-support.service
```

Add:

```ini
[Unit]
Description=AI Support Streamlit App
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/opt/ai-support
Environment=GEMINI_API_KEY=your_key_here
ExecStart=/opt/ai-support/.venv/bin/streamlit run app.py --server.port=8501 --server.headless true
Restart=always

[Install]
WantedBy=multi-user.target
```

Run:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-support
sudo systemctl start ai-support
sudo journalctl -u ai-support -f
```

---

# 4. Scaling & Production Notes

### ❗ Streamlit is NOT a production-grade backend server

Use a reverse proxy:

* **Nginx**
* **Traefik**
* **Caddy**

### For high traffic:

* Extract AI logic into a microservice (FastAPI)
* Keep Streamlit only for UI
* Add Redis or DB for persistent chat history

### For enterprise setups:

* Add OAuth (Google or Azure AD) login
* Use secret manager (GCP Secret Manager, AWS SecretsMgr)
* Add monitoring (Datadog, Prometheus, Grafana)

---

# 5. Troubleshooting

| Problem               | Solution                                                    |
| --------------------- | ----------------------------------------------------------- |
| `ModuleNotFoundError` | Reinstall environment, check versions                       |
| Gemini API 404        | Your model name not supported — auto-selection handles this |
| Slow responses        | Check network or Gemini rate limits                         |
| Streamlit rerun loops | Remove `st.rerun()` from inside model calls                 |

---

# 6. Deployment Checklist

* [ ] GEMINI_API_KEY set
* [ ] HTTPS enabled
* [ ] Logs enabled
* [ ] Docker container tested
* [ ] Systemd or Compose configured
* [ ] Reverse proxy configured

---