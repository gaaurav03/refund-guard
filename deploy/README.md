# Deploy (single free-tier EC2, Sydney)

One `m7i-flex.large` (2 vCPU, 8 GB, free-plan eligible) runs everything:

| Service | Unit | Listens on |
|---|---|---|
| Decider 2B (CPU) | `rg-decider.service` | `127.0.0.1:8099` (never public) |
| Web app (FastAPI + built frontend) | `rg-web.service` | `0.0.0.0:80` |

Bedrock and DynamoDB are reached through the instance role `refund-guard-ec2-role`
(inline policy `refund-guard-app-access`: `bedrock:InvokeModel*` + the `rg_*` tables only).
No access keys live on the machine.

## Steps
1. Swap: a permanent 4 GB `/swapfile` (in `/etc/fstab`); Decider's load briefly exceeds 7.7 GB RAM.
2. `~/dec` venv: `pip install -r backend/requirements.txt` (pulls strands-decider + torch).
3. Code in `~/app` (`git archive HEAD` + `frontend/dist`), settings in `~/app/.env` (chmod 600;
   `STRANDS_DECIDER_URL=http://127.0.0.1:8099`, `DECIDER_TIMEOUT_MS=90000`, a fresh `REVIEWER_TOKEN`).
4. Copy both unit files to `/etc/systemd/system/`, then `sudo systemctl daemon-reload && sudo systemctl enable --now rg-decider rg-web`.
5. Security group: port 80 open to the world, port 22 only from the operator's IP.

Both services start on boot, so **starting the instance = the demo is up** (Decider needs ~1–4 min
to load; until then `/try` shows the "Decider offline" banner and refunds fail closed to a human).
**Stopping the instance = the demo is down.** The public IP changes on every start.

## Public link (fixed, HTTPS): https://dl0e9zh1uq30l.cloudfront.net

```
https://dl0e9zh1uq30l.cloudfront.net   (CloudFront distribution E3HTJOA64JFRZD)
   ├─ /*      → S3 bucket refund-guard-site-4c4ec94c (private, read only by CloudFront via OAC)
   │            CloudFront Function refund-guard-spa maps /try, /review … to /index.html
   └─ /api/*  → EC2 via Elastic IP 3.105.96.122 (port 80, security group admits ONLY the
                CloudFront origin-facing prefix list pl-b8a742d1); no caching; 60 s read timeout
```

- **Instance stopped** → pages still load from S3; `/api/*` returns 504 in ~3 s and the site shows
  "The demo is sleeping". **Instance started** → the demo is live again within ~1–4 minutes.
- Chat turns run as background jobs (`POST /api/chat/jobs`, then poll) because a refund check can
  outlast CloudFront's 60 s origin timeout.
- Rate limits use `CloudFront-Viewer-Address` (set by CloudFront), never `X-Forwarded-For`.
- Cost: S3 + CloudFront are within the free allowances at demo traffic. The Elastic IP is billed
  ~$0.005/hour (~$3.60/month) whether the instance runs or not, paid from credits.

## Redeploy
Frontend (after `npm run build`):
```
aws s3 sync frontend/dist s3://refund-guard-site-4c4ec94c/ --delete
aws cloudfront create-invalidation --distribution-id E3HTJOA64JFRZD --paths "/*"
```
Backend: upload `git archive HEAD` to `~/app` (keep `~/app/.env`), then `sudo systemctl restart rg-web`.

Before the judging window: `python scripts/reset_demo_data.py --yes` (empties the scoreboard,
decisions and review queue; re-seeds the store; benchmark results are untouched).
