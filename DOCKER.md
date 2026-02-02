# Docker Usage Guide

## Build Image

```bash
docker build -t ai_system:1.0.0 .
```

## Run Container

### Interactive Shell (Default)

```bash
docker run -it --rm \
  -v $(pwd)/credentials.json:/app/credentials.json:ro \
  -v $(pwd)/token.json:/app/token.json \
  -v $(pwd)/audits:/app/audits \
  -v $(pwd)/node_programmer/workspaces:/app/node_programmer/workspaces \
  --env-file .env \
  ai_system:1.0.0
```

### Telegram Bot

```bash
docker run -d \
  --name ai_system_bot \
  -v $(pwd)/credentials.json:/app/credentials.json:ro \
  -v $(pwd)/token.json:/app/token.json \
  -v $(pwd)/audits:/app/audits \
  -v $(pwd)/node_programmer/workspaces:/app/node_programmer/workspaces \
  --env-file .env \
  ai_system:1.0.0 \
  python node_interface/telegram_bot.py
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

## Volume Mounts

- `credentials.json`: Gmail OAuth credentials (read-only)
- `token.json`: Gmail OAuth token (read-write)
- `audits/`: Execution logs and audit trail
- `node_programmer/workspaces/`: Ephemeral workspaces for code execution
- `.env`: Environment variables (TELEGRAM_BOT_TOKEN, etc.)

## Security Notes

1. **Never commit** `credentials.json`, `token.json`, or `.env`
2. **Mount secrets** at runtime, don't bake into image
3. Container runs as **non-root user** (uid 1000)
4. Use **read-only mounts** for credentials when possible

## Environment Variables (.env)

```bash
TELEGRAM_BOT_TOKEN=your_token_here
LOG_LEVEL=INFO
```

## Testing

```bash
docker run --rm ai_system:1.0.0 python -m pytest
```

## Cleanup

```bash
# Remove stopped containers
docker container prune

# Remove unused images
docker image prune

# Remove specific image
docker rmi ai_system:1.0.0
```
