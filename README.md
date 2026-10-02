# DLES — Data Lake Table Enhancement System

My undergraduate thesis project: a system that enhances a user's table with relevant data found in a data lake.

- **Backend**: FastAPI (`dles-backend/`)
- **Frontend**: Vue 3 + TypeScript + Vite (`dles-frontend/DLES/`)
- **Design and algorithms**: see the thesis in this repository
  - [English translation](<yuming ding undergraduate thesis.pdf>) (translated by GPT6.1 Sol)
  - [中文原文](<丁郁明 毕业论文 终稿.pdf>)

`real_data_lake_benchmark_query_tables.csv` lists the query tables of the real data lake benchmark used in the experiments.

## Repository layout

```
dles-backend/      FastAPI service (login, settings, table enhancement, model training)
dles-frontend/DLES Vue 3 web client
```

## Prerequisites

- Python 3.10, Node.js 18+, MySQL
- A local data lake of CSV tables, plus the pretrained models
  [`jinaai/jina-embeddings-v2-base-en`](https://huggingface.co/jinaai/jina-embeddings-v2-base-en) and
  [`google-bert/bert-base-uncased`](https://huggingface.co/google-bert/bert-base-uncased)
- A [DashScope](https://dashscope.aliyun.com/) API key for the Qwen LLM calls

## Backend

```bash
cd dles-backend
python -m venv .venv
.venv/Scripts/activate        # Windows; on Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
mysql -u root -p < database/schema.sql
python main.py                # serves on http://127.0.0.1:8080 (docs at /docs)
```

Secrets are read from environment variables. Copy `.env.example` to `dles-backend/.env` and fill it in:

| Variable | Purpose |
| --- | --- |
| `DLES_DB_PASSWORD` | MySQL password |
| `DLES_JWT_SECRET_KEY` | JWT signing key |
| `DLES_MAIL_SENDER`, `DLES_MAIL_TOKEN` | SMTP account for verification mails |
| `DASHSCOPE_API_KEY` | DashScope (Qwen) API key |
| `DLES_COOKIE_SECURE` | Set to `1` when serving over HTTPS (login cookie is `Secure`) |

Login uses an `httpOnly`, `SameSite=Lax` cookie, so the frontend and the API must be on the same site (same hostname, ports may differ). The frontend uses the current page's hostname by default; override with `VITE_API_BASE_URL`. Changing the password invalidates all previously issued tokens, and failed logins are rate limited (in memory, per process).

Non-secret settings are in the `config.json` files next to each module: `database/` (MySQL user, database name, optional `host`/`port`), `utils/authorization/` (token lifetime), and `embedding/`, `transformer/`, `enhance/enhance_main/service/` (paths to the data lake, models and embedding folders, currently absolute `E:/DLES_System/...` paths — change them to your own).

## Frontend

```bash
cd dles-frontend/DLES
npm install
npm run dev                   # http://localhost:5173
```

The API base URL (`http://127.0.0.1:8080`) is set in `src/util/request.ts`.

## License

[MIT](LICENSE)
