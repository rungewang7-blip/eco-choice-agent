# Benchmark Source Manager

The active project is `C:\Users\AAA\eco-backend`. The manager supports source creation, editing, deletion, collection and quality reports. Advanced extraction settings are preserved by updates.

## Source configuration findings

- `cso_transport_2019` was already disabled in the initial pipeline configuration. Its note says extractable tables, fields and terms of use need verification. It has a URL but empty `fields` and `metadata`.
- `seai_energy`, `diet` and `consumer_items` are initial placeholders: disabled, null URL, empty `fields` and `metadata`. They do not contain collected benchmark observations.
- The current `cso_energy_2025`, `cso_diet_hbs` and `cso_items_hbs` entries are separate enabled entries. Their saved URLs alone do not establish extraction readiness or benchmark suitability.
- GET `/admin/benchmark/sources` reads the persisted enabled flag. It supplies legacy category names but does not disable records. POST defaults to disabled if the flag is omitted; PUT saves the submitted flag. No per-edit audit trail identifies historical user actions.

## Save feedback

Only a successful POST or PUT response triggers the green notification. Creation and updates identify the source ID with different messages. The notification closes after six seconds or with Close. Submission is disabled while processing. Starting another action clears stale feedback.

Failed saves show a persistent red error and retain form data. An expired token requires reconnecting. If saving succeeds but reloading the list fails, the page explicitly reports that the source was saved and asks the user to reconnect to refresh the list. Do not create the same source again.

## Start locally

In the backend PowerShell session:

```powershell
cd C:\Users\AAA\eco-backend
$py = 'C:\Users\AAA\Documents\ChatGPT\OMER\.venv-f1\Scripts\python.exe'
# Generate a token only if this session does not already have one.
if (-not $env:ECO_ADMIN_TOKEN) { $env:ECO_ADMIN_TOKEN = (& $py -c "import secrets; print(secrets.token_urlsafe(32))") }
$env:BENCHMARK_ALLOWED_HOSTS = 'www.cso.ie,www-cloud.cso.ie,data.cso.ie,www.seai.ie'
$env:ECO_ADMIN_TOKEN | Set-Clipboard
& $py -m uvicorn main:app --host 127.0.0.1 --port 8000
```

In a second PowerShell session:

```powershell
cd C:\Users\AAA\eco-backend\eco-frontend
npm run dev -- --host 127.0.0.1
```

Open http://127.0.0.1:5173/admin/benchmark and paste the token. Select a category, enter a unique Source ID and Source URL, choose the format and save. Verify extraction mappings before enabling collection. To inspect a report, use View latest report; 404 means none exists yet.

## Security and collection limits

The API requires an ECO_ADMIN_TOKEN of at least 32 characters. The browser keeps it only in memory. The API enforces an exact HTTPS hostname allowlist, public DNS addresses, pinned connections and TLS hostname verification. Redirects are rejected. There are at most 32 sources and 10 MiB per download. A file lock serializes mutations and collection. Stop all backend and collection processes before removing an abandoned lock.

These protections apply to the admin API. The trusted-operator CLI retains its existing behavior. PASS is not human approval. Collection does not publish or update the official benchmark. Use HTTPS and backend secret configuration when deploying; individual user accounts are not implemented.

## Verification

```powershell
cd C:\Users\AAA\eco-backend
& 'C:\Users\AAA\Documents\ChatGPT\OMER\.venv-f1\Scripts\python.exe' -m pytest test_main.py tests -q
cd eco-frontend
npm run build
```

Browser tests in `eco-frontend/e2e/admin.spec.ts` use a mock API to cover delayed success, creation, update, dismissal, automatic expiry, HTTP/network failures, failed refresh, CRUD, reports and token clearing. They do not verify live official-site extraction or deployment. Historical reports remain unchanged as evidence; newly generated reports use English.
