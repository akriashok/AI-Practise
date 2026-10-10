# Healthcare Multi-Agent System (LangGraph)

A LangGraph multi-agent system over a synthetic healthcare database (SQLite, **40 tables**, ~70k rows).
A supervisor sends each question to one of four specialist agents. A **Reflection Agent** then reviews the
answer before the user sees it.

| Agent | What it does |
|---|---|
| **Data Explorer (NL2SQL)** | Turns plain-English questions into SQLite SQL, runs the query read-only and answers from the result. If a query fails or returns no rows, it fixes the SQL and tries again. |
| **Reporting** | Runs curated KPI queries (claims, denials, provider network, file pipeline) and writes a summary and impact report for business review. |
| **File Tracker** | Follows submitted files through validation (12 rules), then approval, then load (LANDING → STAGING → CORE). It shows failed rules, stuck files and the next action. |
| **Data Visualization** | Charts each submitter's files: how many passed or failed validation and how many reached the core layer. Also shows a funnel, a monthly trend and status by file type (Plotly). |
| **Reflection** | Checks the answer against the exact data the agent used (question fit, number accuracy, SQL logic, PHI exposure). If it rejects the answer, it sends it back to the same agent with fix instructions (up to 2 rounds). |

**Front end:** Gradio. The page has a chat panel with example questions and, beside it, the answer's Plotly
charts, generated SQL, result table and agent trace. There are also Architecture (LangGraph diagram) and Database
(40-table row counts) tabs.

```
START -> router -> {data_explorer | reporting | file_tracker | data_visualization} -> reflection
reflection -> (approved or max rounds) END | (rejected) same specialist with feedback
```

## Database domains (40 tables)
- **Provider:** organizations, facilities, specialties, providers, provider_specialties, provider_locations,
  provider_credentials, networks, provider_network_participation, provider_contracts
- **Member/Plan:** health_plans, plan_benefits, members, member_eligibility, member_pcp_assignments
- **Clinical:** appointments, encounters, diagnosis_codes, procedure_codes, encounter_diagnoses,
  encounter_procedures, lab_tests, lab_results, vital_signs, medications, pharmacies, prescriptions
- **Claims:** claims, claim_lines, claim_payments, denial_reasons, claim_denials, prior_authorizations, referrals
- **File operations:** submitter_users, file_submissions, validation_rules, file_validation_results,
  file_approvals, file_load_stages

All data is synthetic. It comes from `healthcare_agents/seed_data.py` with a fixed random seed.

## Run locally

### Requirements
- Python 3.11+
- An OpenRouter API key (https://openrouter.ai/keys)

### 1. Get the code and install dependencies (Windows PowerShell)
```powershell
git clone -b claude/code-usage-nbotoo https://github.com/akriashok/AI-Practise.git
cd AI-Practise\healthcare-multi-agent-langgraph
python -m venv venv
.\venv\Scripts\Activate.ps1          # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure the LLM
```powershell
copy .env.example .env               # macOS/Linux: cp .env.example .env
```
Edit `.env` and set:
```
OPENROUTER_API_KEY=<your key>
OPENROUTER_MODEL=openai/gpt-oss-120b
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```
`.env` is git-ignored, so never commit your key. Any OpenRouter chat model works; for example, set
`OPENROUTER_MODEL=anthropic/claude-sonnet-4.5` to use Claude Sonnet 4.5.

The app loads settings from the first of these files that exists: `<project>/.env`, `<parent folder>/.venv` (a file),
`<project>/.venv`. Real environment variables (for example on Render) always work too.

### 3. Start the app
```powershell
python app.py
```
Open **http://localhost:7860**. Startup takes about 10–20 seconds; wait for `Running on local URL`. Press
**Ctrl+C** to stop it. The first run builds the SQLite database at `data\healthcare.db` automatically.

### Other commands (with the venv active)
| Task | Command |
|---|---|
| Ask one question from the terminal (no UI) | `python -m healthcare_agents.graph "Top 5 denial reasons by billed amount"` |
| Rebuild the 40-table database from scratch | `python -m healthcare_agents.seed_data` |
| Try another model for one run | `$env:OPENROUTER_MODEL="anthropic/claude-sonnet-4.5"; python app.py` |
| Use another port | `$env:PORT="7861"; python app.py` |

### Environment variables
| Variable | Default | Purpose |
|---|---|---|
| `OPENROUTER_API_KEY` | (required) | OpenRouter API key |
| `OPENROUTER_MODEL` | `openai/gpt-oss-120b` | Chat model used by every agent |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | OpenAI-compatible endpoint |
| `PORT` | `7860` | Port for the Gradio server |
| `HOST` | `0.0.0.0` | Address to bind; use `127.0.0.1` to allow local access only |
| `HEALTHCARE_DB_PATH` | `data/healthcare.db` | SQLite database location |
| `MAX_REFLECTIONS` | `2` | Most times the Reflection agent can send an answer back for correction |

### Troubleshooting
- **"running scripts is disabled on this system"** when activating: run
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then activate again.
- **Port 7860 already in use:** another copy of the app is still running. Close that terminal, or set `PORT`
  to a different value.
- **`OPENROUTER_API_KEY is not set`:** create `.env` as in step 2, in the folder that contains `app.py`.
- **Answers are slow:** this is expected. Each question makes several LLM calls (router, agent, reflection) and
  takes about 15–60 seconds, longer when the Reflection agent asks for a correction.

## Deploy on Render
1. On Render, choose **New → Blueprint**, select the `AI-Practise` repo and set the **Blueprint path** to
   `healthcare-multi-agent-langgraph/render.yaml` (the service uses `rootDir: healthcare-multi-agent-langgraph`).
2. When asked, enter `OPENROUTER_API_KEY`, then deploy. The app runs at `https://<service>.onrender.com`.

## Example questions
- How many active providers are there in each specialty?
- Which providers have credentials expiring in the next 90 days?
- Create an impact report on claim denials for the business review
- Where is file FS-20250007 in the pipeline?
- Which files submitted by pkumar failed validation and why?
- Chart how many files each user passed or failed validation and reached core
