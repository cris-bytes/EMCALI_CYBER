# EMCALI Cyber 2.0 Hybrid V12 — Benchmark V2

This V2 is designed to turn the V12 approved/stable baseline into a reproducible benchmark.

## What is real and what is synthetic
- Source-derived: CVE ID, vendor, product, vulnerability title, CISA KEV status/date, CWE.
- Official metrics fields: `cvss_official`, `cvss_version`, `cvss_vector`, `epss_official`,
  `epss_percentile`, `epss_date`. They are intentionally blank until refreshed from NIST/FIRST.
- Lab context: asset name, asset criticality, exposure and operational impact are synthetic test context.

## Refresh official CVSS/EPSS
On an Internet-connected test workstation:
1. Open a terminal in `scripts`.
2. Run:
   `python refresh_official_metrics.py ../benchmark_master_seed.csv ../benchmark_master_enriched.csv`
3. Preserve the enriched CSV and retrieval timestamp as evidence.
4. Import the enriched data into V12 or into the Master workbook as required.

## Test order
1. `01_Smoke_KEV_50.xlsx`: import/normalization.
2. `02_Risk_Baseline_50.xlsx`: risk engine.
3. `03_RAG_Local_50.xlsx`: local LLM + RAG.
4. `04_RAG_Cloud_Controlled_50.xlsx`: controlled cloud comparison.
5. `05`–`09`: load scaling from 100 to 1000 findings.
6. `10_E2E_Full_V12_200.xlsx`: complete V12 flow.

## Evidence to capture
- V12 build/version.
- Dataset SHA-256.
- Model/version/quantization/temperature/context.
- RAG corpus hash, embedding model, chunking and top-k.
- Median/p95/p99 latency, TTFT, tokens/s.
- CPU/RAM/GPU/VRAM.
- Precision@K, Recall@K, nDCG@K.
- Groundedness, remediation correctness, hallucination rate.
- Analyst minutes/finding and Accept/Edit/Reject rate.

Do not mix V13 Performance Lab results into the V12 baseline.
