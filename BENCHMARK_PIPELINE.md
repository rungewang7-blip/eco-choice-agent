# EcoChoice F1 Benchmark Data Quality Pipeline

The pipeline is independent of SQLite and does not modify the official `data/benchmark.json`. The active project is `C:\Users\AAA\eco-backend`; do not confuse it with the OMER checkout. The pipeline alone does not establish an Irish national per-capita annual benchmark.

## Offline verification

```powershell
cd C:\Users\AAA\eco-backend
$python = 'C:\Users\AAA\Documents\ChatGPT\OMER\.venv-f1\Scripts\python.exe'
& $python -m scripts.collect_benchmark --sources data/sources.demo.json --fixtures tests/fixtures
& $python -m pytest tests/test_benchmark_pipeline.py -q
```

The fixed CSV, HTML and JSON fixtures are synthetic. Expected counts are PASS 1, REVIEW 2 and REJECT 2. Demo records cannot be published. Each run writes `data/reports/<run-id>/quality_report.md`, a JSON report, a source snapshot, raw evidence and cleaned records. Use Python 3.10 or later with pytest. Run modules from the project root, not by double-clicking scripts. Runtime pipeline code uses the standard library.

## Configure real sources

`data/sources.json` stores per-source URLs, formats, mappings and metadata. The initial four entries were disabled; current enabled flags may reflect later edits. Verify the actual official download or table before adding mappings and enabling a source. Empty URLs need configuration. No live source collection is implied by saving a URL.

Example only; replace fields and metadata with verified source information:

```json
{
  "id": "verified_source",
  "enabled": true,
  "url": "https://official.example/data.csv",
  "format": "csv",
  "encoding": "utf-8-sig",
  "fields": {"indicator": "Indicator", "value": "Value", "year": "Year", "unit": "Unit"},
  "metadata": {
    "geography": "Ireland", "population_basis": "person", "period": "year",
    "statistic": "mean", "scope": "national",
    "methodology_url": "https://official.example/methodology",
    "license": "Verified terms of use or their URL"
  }
}
```

`fields` maps standard fields to original column names. Only unmapped fields use metadata; missing mapped columns do not silently fall back to constants. `field_origins` records source versus configuration provenance. Metadata remains a human-entered claim requiring review.

CSV headers must be unique and non-empty; row lengths must agree. HTML uses a zero-based `table_index` and the first row as headers. Merged cells, nested tables and dynamic JavaScript charts are unsupported. JSON uses a key/index `json_path` such as `["observations"]` to select an array of objects. JSON-stat and PXStat need dedicated adapters.

Numbers use a decimal point. Set `thousands_separator` only when confirmed for the source. The pipeline does not convert units, households to people, medians to means, or trips to annual totals.

```powershell
& $python -m scripts.collect_benchmark --sources data/sources.json
```

Enable one verified source first and compare extracted records with the original table. Each run creates a new directory. Individual download/parse failures are reported while other sources continue; failures produce exit code 1. All-disabled inputs produce SKIPPED and zero records, not success. Filesystem failures may prevent report creation.

## Quality states

| State | Meaning | Next step |
|---|---|---|
| PASS | Required fields, valid nonnegative value, Ireland/person/year/mean/national basis, permitted unit, methodology and license | Review representativeness and suitability; not yet approved |
| REVIEW | Retained observation with unresolved basis, units, duplicates, methodology or license | Verify evidence and document any justified conversion |
| REJECT | Missing required fields or invalid year, value or URL | Correct source or mapping and rerun |

Source results include download_status and SUCCESS/FAILED/SKIPPED. Records include extraction_valid, benchmark_candidate and status. A successful HTML download does not establish valid extraction. Household annual medians and trip percentages are REVIEW; missing units are REJECT. Allowed PASS units are km/person/year, kWh/person/year, kg/person/year and kgCO2e/person/year.

Review source_url, response_url, year, statistical basis, original_location, raw_record, raw_sha256, retrieved_at and field_origins. PASS does not establish authenticity, sound methodology, category coverage or parity with the EcoChoice calculation engine. Historical anomaly detection, latest-year discovery, scheduling, semantic cross-indicator checks and national-total extrapolation are not implemented.

## Human approval and separate publication

The publisher creates a non-overwritable approved candidate JSON. It does not promote PASS records automatically into the official benchmark. After reviewing real evidence, create an approval file:

```powershell
(Get-FileHash 'data/reports/RUN_ID/quality_report.json' -Algorithm SHA256).Hash.ToLower()
```

```json
{
  "reviewer": "Actual reviewer",
  "reason": "Evidence reviewed: source, statistical basis, representativeness and terms",
  "approved_at": "2026-10-30T15:00:00+08:00",
  "run_id": "COPY_FROM_REPORT",
  "report_sha256": "ACTUAL_LOWERCASE_SHA256",
  "record_ids": ["SELECTED_PASS_RECORD_ID"]
}
```

```powershell
& $python -m scripts.publish_benchmark --report 'data/reports/RUN_ID/quality_report.json' --approval approval.json
```

Only selected, revalidated, non-demo PASS records enter `data/approved`. Modified reports/evidence, REVIEW/REJECT records, unknown IDs and duplicate publication are rejected. Approval JSON is a local workflow record, not authenticated or digitally signed approval. Published candidates still set nationalBenchmarkReady=false. Formal integration requires representative inputs across categories and verified parity with the existing engine.
