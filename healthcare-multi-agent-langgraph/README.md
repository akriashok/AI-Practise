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
```bash
python -m venv venv && venv\Scripts\activate      # Windows (source venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
copy .env.example .env                              # then add your OPENROUTER_API_KEY
python -m healthcare_agents.seed_data               # builds data/healthcare.db (also auto-built on first run)
python app.py                                       # Gradio UI at http://localhost:7860
```
CLI: `python -m healthcare_agents.graph "Top 5 denial reasons by billed amount"`

The LLM is any OpenRouter chat model (`OPENROUTER_MODEL`, default `openai/gpt-oss-120b`).
For example, set it to `anthropic/claude-sonnet-4.5` to use Claude Sonnet 4.5.

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
