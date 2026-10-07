# Parking Reservation Chatbot — Stage 2: Human Approval

A conversational parking assistant that combines the Stage 1 RAG knowledge
base and reservation flow with a LangChain-powered administrator agent.
After collecting the user's reservation details, the chatbot creates a
pending request, notifies the administrator, and reports the administrator's
approval or refusal when the user checks the request status.

## Stage 2 Workflow

```text
User
 │ asks to reserve
 ▼
ParkingChatbot (Stage 1)
 │ collects name, car number, dates/times, optional parking lot
 ▼
AdminAgent.escalate()
 │ writes PENDING request and sends notification
 ▼
Shared SQLite request store (data/admin_requests.db)
 │                                 ▲
 │                         administrator decides
 │                         LangChain CLI or REST API
 ▼                                 │
ParkingChatbot polls request status and tells the user
```

The two agents coordinate through the same SQLite-backed request store.
Notifications can be sent to the console, email, Slack, or an external REST
endpoint. The administrator records the actual decision using the
LangChain-powered admin CLI or the Admin REST API; email and Slack are
notification channels, not reply-processing channels.

## Features

- Answers static parking questions from ingested PDFs using retrieval-augmented
  generation, and dynamic hours, prices, and availability questions from SQLite.
- Collects reservation details through conversational slot filling.
- Escalates completed reservations to the administrator with a generated
  summary and unique request ID.
- Supports pending, approved, and refused decisions, including an optional
  administrator reason.
- Lets administrators manage requests in natural language with LangChain tools
  or through a REST API.
- Applies PII scanning/redaction to protect user information in chat.

## Project Structure

```text
admin_agent/
  agent.py       LangChain admin agent, escalation, and approval tools
  api.py         FastAPI endpoints for requests and decisions
  cli.py         Interactive natural-language admin console
  models.py      Shared reservation request/status model
  notifier.py    Console, SMTP email, Slack webhook, and REST notifications
  store.py       Shared SQLite request store
src/
  chatbot.py     User-facing assistant and Stage 2 handoff/status check
  reservation.py Reservation detail collection
  rag_chain.py   Intent routing, RAG answers, and dynamic lookups
  ...            PDF ingestion, vector store, metadata, and PII guardrails
data/
  pdfs/          Knowledge-base PDFs
  ingest.py      PDF to chunks, metadata DB, and vector DB
tests/           Offline tests for chatbot, admin agent, API, and Stage 1
```

## Setup

Requires Python 3.11+, an OpenAI API key for the LangChain agents and RAG,
and optionally Docker if you want to run Milvus. From PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m spacy download en_core_web_sm
Copy-Item .env.example .env
```

Set `OPENAI_API_KEY` in `.env`. The default admin notification channel is
`console`, which requires no additional setup. Set `ADMIN_DB_PATH` to the
same SQLite file for the chatbot and Admin API processes; the default is
`data/admin_requests.db`.

Optional notification configuration in `.env`:

| Channel | Setting | Additional settings |
|---|---|---|
| Console (default) | `ADMIN_NOTIFICATION_CHANNEL=console` | None |
| Email | `ADMIN_NOTIFICATION_CHANNEL=email` | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `ADMIN_EMAIL` |
| Slack | `ADMIN_NOTIFICATION_CHANNEL=slack` | `SLACK_WEBHOOK_URL` |
| External REST | `ADMIN_NOTIFICATION_CHANNEL=rest` | `ADMIN_REST_ENDPOINT`, optional `ADMIN_REST_API_KEY` |

Set `ADMIN_API_KEY` to protect Admin API POST routes. When it is set, provide
the same value in the `x-api-key` header. If unset, API key verification is
disabled, which is intended only for local development.

## Run the Chatbot

Generate sample knowledge-base PDFs or add your own PDFs under `data/pdfs/`,
then ingest and start the chatbot:

```powershell
python -m data.generate_sample_pdfs
python -m data.ingest
python main.py
```

Ask to make a reservation and provide the requested details. The bot responds
with a request ID once the request has been sent. Ask to check your
reservation status to see whether it is pending, approved, or refused.

Milvus is optional. If it is not running, the vector store can fall back to
Chroma. To start the Docker Compose services, including Milvus and the Admin
API, run `docker compose up -d` after creating `.env`.

## Administrator Approval

### LangChain Admin CLI

Run the interactive admin agent in a separate terminal. It uses LangChain
tools to list, approve, refuse, and check the status of requests in the shared
SQLite store:

```powershell
python -m admin_agent.cli
```

Example prompts:

```text
list pending requests
approve request <request-id> because a space is available
refuse request <request-id> because the lot is full
check status of request <request-id>
```

### Admin REST API

Start the API when running it outside Docker:

```powershell
uvicorn admin_agent.api:app --host 127.0.0.1 --port 8001
```

Interactive API documentation is available at `http://localhost:8001/docs`.
The chatbot itself escalates through the shared request store; the API is an
alternative interface for creating, viewing, and deciding requests.

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/reservations` | Create and notify about a reservation request |
| `GET` | `/reservations` | List requests; optionally filter with `?status=pending` |
| `GET` | `/reservations/{request_id}` | Read one request and its current status |
| `POST` | `/reservations/{request_id}/decision` | Approve or refuse a request |

Example: submit a decision from PowerShell (include the API key header if
`ADMIN_API_KEY` is configured):

```powershell
$headers = @{ "x-api-key" = "your-admin-api-key" }
$body = @{ approved = $true; reason = "Space available" } | ConvertTo-Json
Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8001/reservations/<request-id>/decision" `
  -Headers $headers -ContentType "application/json" -Body $body
```

## Tests

The tests use fake LLMs, temporary SQLite databases, and mocked collaborators;
they do not require live API credentials or network services:

```powershell
pytest -v
```

## Evaluation

Generate questions from ingested PDFs and evaluate retrieval and answer
quality:

```powershell
python -m evaluation.generate_qa_from_pdfs --per-chunk 2
python -m evaluation.evaluate --grader llm
```

The report is written to `evaluation/REPORT.md`, with detailed results in
`evaluation/eval_results.json`.

## Docker and Infrastructure

Build and run the chatbot container:

```powershell
docker build -t parking-chatbot .
docker run --rm -it --env-file .env parking-chatbot
```

Docker Compose also defines the Milvus stack and the Admin API on port 8001:

```powershell
docker compose up -d
```

Terraform files for Milvus and optional app deployment are in `terraform/`;
see [terraform/README.md](terraform/README.md) for details.

## Stage 1 Components Retained

The administrator approval workflow builds on the original RAG chatbot:
PDF knowledge is semantically chunked and indexed for retrieval, document
metadata is persisted in SQLite, dynamic parking data is stored separately,
and PII guardrails protect chat input and output. See `src/`, `data/`, and
`evaluation/` for these components.