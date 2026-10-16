# Runbook: running Refund Guard yourself

Everything below is run from **PowerShell** in the project folder unless it says otherwise.
Commands call the project's Python directly (`.\.venv\Scripts\python.exe`), so you never need to "activate" anything.

```powershell
cd D:\Desktop\RefendGuardAgent
```

## The pieces and how they talk

| Piece | What it is | Where it runs | Port |
|---|---|---|---|
| **Website + API** | FastAPI (`backend/app`) serving the React build (`frontend/dist`) and `/api/*` | your laptop (later: EC2) | 8080 |
| **Decider 2B server** | `strands-decider serve`: answers the six yes/no questions | your laptop **or** the AWS machine | 8099 |
| **Bedrock** (Nova) | the chat model | AWS, nothing to start | – |
| **DynamoDB** (`rg_*` tables) | orders, deliveries, decisions, review queue | AWS, nothing to start | – |

The website finds Decider at `STRANDS_DECIDER_URL` in `.env` (default `http://127.0.0.1:8099`). Whatever answers on
port 8099 of your laptop is "the Decider": a local server, or the AWS one through an SSH tunnel (section 3).

---

## 1. Start the website

```powershell
# only after you change frontend code: rebuild the React app into frontend/dist
cd frontend; npm run build; cd ..

# start the website + API (reads .env automatically); leave this window open
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8080
```

Open http://127.0.0.1:8080. Stop it with **Ctrl+C**. Check it: http://127.0.0.1:8080/api/health shows
`"decider":{"ok":true}` when a Decider is reachable.

## 2. Option A: Decider on your laptop (free, ~7 GB RAM, ~15 s per check)

New PowerShell window, leave it open:

```powershell
cd D:\Desktop\RefendGuardAgent
.\.venv\Scripts\strands-decider.exe serve StrandsAgents/strands-decider-2B-qwen3.5-v1-2610 --port 8099 --device cpu
```

Ready when it prints `Uvicorn running on http://127.0.0.1:8099`. The model files are already in `D:\devcache\huggingface`
(the `HF_HOME` variable points there), so nothing is downloaded again. Stop with **Ctrl+C** to get the RAM back.

## 3. Option B: Decider on the AWS machine (~$0.12/hour of credits, ~30 s per check)

Instance `i-06cb6df7c51354bfd` (`m7i-flex.large`, Sydney). The SSH key is `D:\devcache\keys\refund-guard-gpu.pem`.

**One-time:** Windows' ssh refuses keys that other users can read. Lock the file to your user:

```powershell
icacls D:\devcache\keys\refund-guard-gpu.pem /inheritance:r /grant:r "$($env:USERNAME):R"
```

**a) Start the machine and get its address** (the address changes on every start):

```powershell
$aws = ".\.venv\Scripts\python.exe -m awscli --region ap-southeast-2"
Invoke-Expression "$aws ec2 start-instances --instance-ids i-06cb6df7c51354bfd"
# wait ~1 minute, then:
Invoke-Expression "$aws ec2 describe-instances --instance-ids i-06cb6df7c51354bfd --query Reservations[0].Instances[0].[State.Name,PublicIpAddress] --output text"
```

You can also do this in the console: EC2 → Instances → `refund-guard-cpu-test` → Instance state → Start.

**b) Log in, set a safety power-off, start Decider** (replace `IP` with the address from step a):

```powershell
ssh -i D:\devcache\keys\refund-guard-gpu.pem ubuntu@IP
```

Then, on the server:

```bash
sudo shutdown -h +120          # safety net: powers off in 2 hours no matter what
swapon --show                  # must list /swapfile (4G); without it Decider is killed while loading
nohup ~/dec/bin/strands-decider serve StrandsAgents/strands-decider-2B-qwen3.5-v1-2610 --port 8099 --device cpu > serve.log 2>&1 &
curl -s http://127.0.0.1:8099/health    # repeat until it says "status":"ok" (about 4 minutes)
exit
```

**c) Connect your laptop's port 8099 to it** (new PowerShell window, leave it open):

```powershell
ssh -i D:\devcache\keys\refund-guard-gpu.pem -N -L 127.0.0.1:8099:127.0.0.1:8099 ubuntu@IP
```

It prints nothing; that is normal. While this window is open, your laptop's 8099 *is* the AWS Decider.
The first decision after starting takes ~4 minutes (one-time warm-up), then ~30 s each.

**d) When you are done: stop the machine** (this is what stops the credit use):

```powershell
Invoke-Expression "$aws ec2 stop-instances --instance-ids i-06cb6df7c51354bfd"
```

Close the tunnel window with **Ctrl+C**. If you forget, the machine still powers itself off at the time you set in step b.

**Security group:** SSH is only allowed from your home IP (`sg-0c3b8aa18767db139`). If your IP changes, ssh hangs:
EC2 → Security Groups → `rg-gpu-ssh` → Edit inbound rules → SSH → Source: **My IP** → Save.

---

## 4. Run the tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q          # backend + reusable pattern (~130 tests, no AWS needed)
.\.venv\Scripts\ruff.exe check .                  # lint
.\.venv\Scripts\mypy.exe                          # types
cd frontend; npm test; cd ..                      # frontend (~16 tests)
```

All of these use a **fake Decider** and fake data, so they run in seconds and cost nothing.

## 5. Re-run the benchmark (needs a running Decider, section 2 or 3)

```powershell
# Decider on the 34 held-out test cases with the production questions (V2): ~15-30 s per case
.\.venv\Scripts\python.exe bench\eval_questions.py --variants V2 --split test --out bench\results\my_run.json
```

`--split` can be `dev`, `test`, `extra`, `fresh` or `all`; `--variants` can be `V0,V1,V2,V3,V3c,V4` (see `bench/variants.py`).
The LLM-judge comparison (costs Bedrock credits, ~$0.70 without Kimi):

```powershell
.\.venv\Scripts\python.exe bench\run_judges.py --judges B1,B2,B4,B5 --arms six,direct --repeats 3
.\.venv\Scripts\python.exe bench\report_judges.py > bench\results\RESULTS.md
```

## 6. Chat with the agent in the terminal (no website)

```powershell
# Asha's genuine cracked-mug claim, sent as one message (needs Bedrock + a running Decider)
.\.venv\Scripts\python.exe scripts\chat_cli.py --customer CUST-007 --say "My blue mug arrived cracked. Can I get a refund for the mug?"
```

Customers: CUST-007 Asha (genuine), CUST-011 Ravi ("never arrived", but delivered with proof), and the others on `/try`.

## 7. Where to look when something is off

| Symptom | Check |
|---|---|
| Every refund "sent to a human", reason *Decider didn't answer* | Is anything on port 8099? http://127.0.0.1:8099/health. Tunnel window still open? |
| `/try` shows "Decider 2B is offline" | same as above |
| Page looks old after a change | `npm run build`, then Ctrl+F5 |
| ssh hangs | your IP changed (section 3, security group) or the machine is stopped |
| Credits | AWS console → account menu → Free plan status (updates with ~1 day delay) |
