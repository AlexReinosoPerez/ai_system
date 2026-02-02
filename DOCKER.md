# Docker Usage Guide

## Build Image

```bash
docker build -t ai_system:1.0.0 .
```

---

## Gmail OAuth Setup (ONE-TIME)

### Prerequisites

1. **Google Cloud Console Setup**
   - Go to https://console.cloud.google.com
   - Create a new project or select existing
   - Enable Gmail API
   - Create OAuth 2.0 credentials (Desktop app)
   - Download `credentials.json`

2. **Local Secrets Directory**
   ```bash
   # Create secrets directory on host
   mkdir -p secrets
   
   # Copy credentials.json to secrets/
   cp ~/Downloads/credentials.json secrets/
   
   # Verify file exists
   ls -la secrets/credentials.json
   ```

3. **OAuth Authorization Flow (Interactive)**
   ```bash
   # Run container with secrets mounted and port exposed
   docker run -it --rm \
     -v $(pwd)/secrets:/app/secrets \
     -p 8080:8080 \
     --env-file .env \
     ai_system:1.0.0 \
     python -c "from node_events.gmail_reader import GmailReader; \
                from shared.config import config; \
                reader = GmailReader(config.GMAIL_CREDENTIALS_PATH, config.GMAIL_TOKEN_PATH); \
                reader.get_inbox(1)"
   ```
   
   **Expected flow:**
   - Browser will open automatically
   - Login with your Google account
   - Grant permission to read Gmail (readonly scope)
   - `token.json` will be saved to `secrets/token.json`
   
   **Note:** This step is required ONLY ONCE. After `token.json` is created,
   subsequent runs will use the existing token (auto-refresh on expiration).

4. **Verify OAuth Success**
   ```bash
   # Check token.json was created
   ls -la secrets/token.json
   
   # Expected output: token.json with ~2KB size
   ```

---

## Run Container

### Interactive Shell (Default)

```bash
docker run -it --rm \
  -v $(pwd)/secrets:/app/secrets \
  -v $(pwd)/audits:/app/audits \
  -v $(pwd)/node_programmer/workspaces:/app/node_programmer/workspaces \
  --env-file .env \
  ai_system:1.0.0
```

### Telegram Bot (with Gmail support)

```bash
docker run -d \
  --name ai_system_bot \
  -v $(pwd)/secrets:/app/secrets \
  -v $(pwd)/audits:/app/audits \
  -v $(pwd)/node_programmer/workspaces:/app/node_programmer/workspaces \
  --env-file .env \
  ai_system:1.0.0 \
  python node_interface/telegram_bot.py
```

**Test Gmail via Telegram:**
```
/inbox
/inbox 20
```

### Scheduler (One-time Execution)

```bash
docker run --rm \
  -v $(pwd)/audits:/app/audits \
  -v $(pwd)/node_programmer/workspaces:/app/node_programmer/workspaces \
  -v $(pwd)/node_dds/dds.json:/app/node_dds/dds.json \
  --env-file .env \
  ai_system:1.0.0 \
  python -c "from node_scheduler import Scheduler; Scheduler().run()"
```

### Cron-scheduled Execution

```bash
# Add to crontab on host:
0 2 * * * docker run --rm -v $(pwd)/audits:/app/audits -v $(pwd)/node_programmer/workspaces:/app/node_programmer/workspaces --env-file .env ai_system:1.0.0 python -c "from node_scheduler import Scheduler; Scheduler().run()"
```

---

## Volume Mounts Explained

| Volume | Purpose | Read/Write | Required |
|--------|---------|------------|----------|
| `secrets/` | Gmail OAuth credentials + token | RW | Optional (Gmail only) |
| `audits/` | Execution logs and audit trail | RW | Recommended |
| `node_programmer/workspaces/` | Ephemeral code execution workspaces | RW | Required for DDS execution |
| `.env` | Environment variables (TELEGRAM_BOT_TOKEN, etc.) | RO | Required |

**Security Model:**
- `secrets/` directory is mounted as volume (NOT baked into image)
- `credentials.json` is read-only after initial setup
- `token.json` is read-write (auto-refresh on expiration)
- Container runs as non-root user (uid 1000)

---

## Environment Variables (.env)

```bash
# Required
TELEGRAM_BOT_TOKEN=your_token_here

# Optional (defaults provided)
LOG_LEVEL=INFO
GMAIL_CREDENTIALS_PATH=secrets/credentials.json
GMAIL_TOKEN_PATH=secrets/token.json
```

**Gmail Path Configuration:**
- Default paths assume `secrets/` volume mount
- Override via environment variables if using custom structure
- Paths are relative to container's `/app` directory

---

## Testing Gmail Integration

### 1. Test OAuth Flow (Manual)
```bash
docker run -it --rm \
  -v $(pwd)/secrets:/app/secrets \
  -p 8080:8080 \
  ai_system:1.0.0 \
  python -c "from node_events.gmail_reader import GmailReader; \
             from shared.config import config; \
             r = GmailReader(config.GMAIL_CREDENTIALS_PATH, config.GMAIL_TOKEN_PATH); \
             emails = r.get_inbox(5); \
             print(f'Fetched {len(emails)} emails')"
```

### 2. Test via Python REPL
```bash
docker run -it --rm \
  -v $(pwd)/secrets:/app/secrets \
  ai_system:1.0.0 \
  python

>>> from node_events.gmail_reader import GmailReader
>>> from shared.config import config
>>> reader = GmailReader(config.GMAIL_CREDENTIALS_PATH, config.GMAIL_TOKEN_PATH)
>>> emails = reader.get_inbox(3)
>>> print(f"Found {len(emails)} emails")
>>> print(emails[0]['subject'])
```

### 3. Test via Telegram Bot
```bash
# Start bot
docker run -d --name test_bot \
  -v $(pwd)/secrets:/app/secrets \
  --env-file .env \
  ai_system:1.0.0 \
  python node_interface/telegram_bot.py

# Send command in Telegram
/inbox 10

# Check logs
docker logs test_bot
```

---

## Troubleshooting

### Error: "Credentials file not found"
```bash
# Verify secrets/ mount
docker run --rm -v $(pwd)/secrets:/app/secrets ai_system:1.0.0 ls -la /app/secrets

# Expected: credentials.json present
```

### Error: "Google API libraries not installed"
```bash
# Rebuild image (dependencies already in requirements.txt)
docker build -t ai_system:1.0.0 .
```

### Error: "Token expired" or "Invalid token"
```bash
# Delete token.json and re-run OAuth flow
rm secrets/token.json

# Run OAuth flow again (see "Gmail OAuth Setup" section)
```

### Gmail works locally but not in Docker
```bash
# Check volume mount paths
docker run --rm -v $(pwd)/secrets:/app/secrets ai_system:1.0.0 \
  python -c "import os; print(os.listdir('/app/secrets'))"

# Expected output: ['credentials.json', 'token.json']
```

### Port 8080 already in use during OAuth
```bash
# Use different port
docker run -it --rm \
  -v $(pwd)/secrets:/app/secrets \
  -p 8888:8888 \
  ai_system:1.0.0 \
  python -c "from node_events.gmail_reader import GmailReader; ..."

# OAuth flow will auto-select available port
```

---

## Security Notes

1. **Never commit** `secrets/`, `credentials.json`, `token.json`, or `.env`
2. **Mount secrets** at runtime as volume, don't bake into image
3. Container runs as **non-root user** (uid 1000)
4. OAuth token has **readonly Gmail scope** only
5. Token auto-refreshes on expiration (no re-authorization needed)
6. Logs do NOT print sensitive data (token, credentials)

---

## Testing

```bash
docker run --rm ai_system:1.0.0 python -m pytest
```

---

## Cleanup

```bash
# Remove stopped containers
docker container prune

# Remove unused images
docker image prune

# Remove specific image
docker rmi ai_system:1.0.0

# Clean secrets (CAUTION: will require OAuth re-authorization)
# rm -rf secrets/
```
