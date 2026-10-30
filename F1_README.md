# F1 reference data API

Data flow: validated CSV → SQLite → FastAPI → Vue.

## Behavior

- `/factors` reads `carbon_factors` and returns `{factorVersion, factors}`.
- `/catalog` returns food and item activity options. Both endpoints support `?version=2026-10-f1`.
- `/benchmark` is a pinned, illustrative three-person household scenario, not an Irish national per-capita benchmark. It has `nationalBenchmarkReady=false` and `annualKgCO2e=null`.
- Imports require nine CSV columns and reject missing sources, unknown units, non-positive or non-finite values, duplicate IDs, mixed versions and incorrect headers before writing any rows.
- The primary key is `(factorVersion,id)`. Legacy single-version tables are retained as `carbon_factors_legacy`; valid rows migrate and unrelated tables remain intact.
- Importing Python modules does not create the database or insert test data. Run `bootstrap.py` explicitly. Repeated initialization rejects conflicting version contents.

## Windows startup

```powershell
cd C:\Users\AAA\eco-backend
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe bootstrap.py
.\venv\Scripts\python.exe -m pytest -q
.\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Use an installed compatible environment if `venv` is unavailable; the source-manager guide gives the shared local environment path. Stop an existing backend before restarting. Browse http://127.0.0.1:8000/docs.

```powershell
Invoke-RestMethod http://127.0.0.1:8000/factors
Invoke-RestMethod http://127.0.0.1:8000/catalog
Invoke-RestMethod http://127.0.0.1:8000/benchmark
.\venv\Scripts\python.exe import_factors.py data\factors.csv --db eco.db
```

Data changes require a new factorVersion.

## Recorded source assumptions

These are the existing implementation's source notes, not a fresh online verification:

- [SEAI residential energy](https://www.seai.ie/data-and-insights/seai-statistics/residential): 2022 household electricity 4513 kWh and non-electricity 12636 kWh. Treating all non-electricity as natural gas and dividing by three people are example assumptions.
- [SEAI conversion factors](https://www.seai.ie/data-and-insights/seai-statistics/conversion-factors): provisional 2025 electricity 197.8 and natural gas GCV 183.5 g CO2/kWh, divided by 1000 for kg. These are CO2, not full lifecycle CO2e; electricity excludes emissions from overseas generation.
- [DESNZ 2025](https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2025): retained transport and paper factors. UK transport is a proxy for Ireland; paper is converted from tonnes to kilograms.
- [Poore / Nemecek data](https://ourworldindata.org/grapher/ghg-per-kg-poore): retained global-average food factors, not Irish measurements; research year 2018.

Travel days and distance, food mix, zero flights, paper use and household allocation are assumptions. Representative transport, diet, goods and fuel-mix inputs remain incomplete.

## Historical validation

The earlier preparation run recorded 25 passing pytest tests and 94.66% coverage on Python 3.10.11, with a Starlette/httpx deprecation warning. These are historical results. Python 3.12 was not verified. Tests and builds in the separate OMER checkout do not establish F2/F3 completion in this project. CI, hosting and national benchmark acceptance remain separate tasks.
