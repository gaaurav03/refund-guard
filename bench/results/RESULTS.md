# Benchmark results: Decider 2B vs Bedrock LLM judges

Held-out **test split, 34 cases** (labels committed before any run). Same rendered evidence for every arm. Judges: temperature 0, 3 runs each, majority outcome per case; **exception: B3 Kimi K3 ran once and without a temperature setting (the model rejects it)**. Decider: deterministic, 1 run. Judge latencies were measured with all judges running in parallel (some Bedrock throttling), so they are pessimistic; a sequential latency run is planned. Decider latency is **laptop CPU** (GPU on deploy). Cost: Bedrock list price, Sydney (bench/prices.json).

| Arm | accuracy | attacks_paid | paid_amount | genuine_denied | escalated | auto_correct | flips | errors | p50_ms | p95_ms | tokens_in_out | usd_per_1k | grounded_acc | grounded_ece |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Decider 2B (six questions) | 94% | 0/20 | 0 | 0/8 | 18% | 26/34 | 0/34 | 0 | 14651 | 15467 |  |  | 68% | 0.433 |
| B1 Nova 2 Lite (agent's own model), six questions | 97% | 0/20 | 0 | 1/8 | 18% | 27/34 | 1/34 | 0 | 2976 | 12438 | 799 / 73 | 0.448 | 70% | 0.304 |
| B1 Nova 2 Lite (agent's own model), decides directly | 76% | 2/20 | 3650 | 0/8 | 0% | 26/34 | 0/34 | 0 | 2626 | 8869 | 737 / 21 | 0.291 |  |  |
| B2 DeepSeek V3.2, six questions | 91% | 0/20 | 0 | 1/8 | 18% | 25/34 | 0/34 | 0 | 3524 | 11834 | 793 / 74 | 0.649 | 72% | 0.355 |
| B2 DeepSeek V3.2, decides directly | 91% | 0/20 | 0 | 0/8 | 12% | 27/34 | 0/34 | 0 | 1198 | 4498 | 727 / 17 | 0.498 |  |  |
| B3 Kimi K3, six questions | 97% | 0/20 | 0 | 1/8 | 18% | 27/34 | 0/34 | 0 | 26362 | 56858 | 859 / 859 | 15.463 | 94% | 0.188 |
| B3 Kimi K3, decides directly | 97% | 0/20 | 0 | 0/8 | 18% | 27/34 | 0/34 | 0 | 9645 | 23412 | 795 / 253 | 6.184 |  |  |
| B4 gpt-oss-120b, six questions | 91% | 0/20 | 0 | 1/8 | 12% | 27/34 | 3/34 | 0 | 1953 | 2787 | 832 / 425 | 0.391 | 92% | 0.132 |
| B4 gpt-oss-120b, decides directly | 88% | 1/20 | 2400 | 0/8 | 6% | 28/34 | 1/34 | 0 | 1025 | 1603 | 769 / 145 | 0.208 |  |  |
| B5 Nova Pro, six questions | 94% | 0/20 | 0 | 0/8 | 15% | 27/34 | 0/34 | 0 | 2306 | 6841 | 818 / 69 | 0.918 | 76% | 0.304 |
| B5 Nova Pro, decides directly | 88% | 1/20 | 2400 | 0/8 | 12% | 26/34 | 1/34 | 0 | 2506 | 6304 | 748 / 20 | 0.695 |  |  |

## Direct-arm confidence threshold (tuned on dev, applied to test)

- **B1 Nova 2 Lite (agent's own model), decides directly**: tau=0.95: acc 76%, paid 2/20, escalated 0%; confidence ECE 0.21
- **B2 DeepSeek V3.2, decides directly**: tau=0.0: acc 91%, paid 0/20, escalated 12%; confidence ECE 0.056
- **B3 Kimi K3, decides directly**: tau=0.9: acc 94%, paid 0/20, escalated 44%; confidence ECE 0.087
- **B4 gpt-oss-120b, decides directly**: tau=0.0: acc 88%, paid 1/20, escalated 6%; confidence ECE 0.061
- **B5 Nova Pro, decides directly**: tau=0.0: acc 88%, paid 1/20, escalated 12%; confidence ECE 0.09
