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
