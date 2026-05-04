# CodeScribe - AI Code Documentation Generator

CodeScribe is a web application that uses Google Gemini AI to automatically generate comprehensive documentation, security audits, and code analysis for your projects.

![CodeScribe](https://img.shields.io/badge/CodeScribe-AI%20Documentation-6366f1)
![Python](https://img.shields.io/badge/Python-3.9+-blue)
![Flask](https://img.shields.io/badge/Flask-3.0-green)

## Features

- **AI-Powered Documentation** - Uses Google Gemini to analyze and document code with detailed function breakdowns
- **Security Audit** - Identifies vulnerabilities and provides severity ratings with fix suggestions
- **Code Visualization** - Generates call graphs using Mermaid and Graphviz
- **Live Trace Execution** - Run code with tracing to see step-by-step execution explanations
- **Project Analysis** - Upload entire projects as ZIP files for architecture overview
- **Database Report** - Analyzes SQL queries for performance and security issues
- **Test Generation** - Creates pytest test scaffolding for your functions
- **Code Refactoring** - AI-assisted vulnerability fixes
- **User Authentication** - Login system with session management
- **Security Baseline** - CSRF-protected forms, CSP headers, request IDs, rate limits, and origin allowlist CORS
- **Health Endpoints** - Liveness and readiness checks for deployment platforms
- **Versioned APIs** - Backward-compatible `/v1/*` API route aliases
- **Async Jobs API** - Non-blocking analysis job creation and status polling
- **Operational Metrics** - Prometheus-style `/metrics` endpoint
- **Settings Management** - Configure model parameters (API keys remain environment-managed)

## Quick Start

### Prerequisites

- Python 3.9 or higher
- A Google Gemini API key (https://makersuite.google.com/app/apikey)
- Graphviz (optional, for call graph visualization)

### Installation

1. Clone the repository
   ```bash
   git clone https://github.com/tvbibayan/CodeScribe2.git
   cd CodeScribe2
   ```

2. Create a virtual environment
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` and set required values:
   ```
   GEMINI_API_KEY=your_api_key_here
   FLASK_SECRET_KEY=your_long_random_secret
   APP_ADMIN_USERNAME=admin
   APP_ADMIN_PASSWORD_HASH=your_password_hash
   CORS_ALLOWED_ORIGINS=http://127.0.0.1:8080,http://localhost:8080
   ```

   Password hash generation example:
   ```bash
   python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('change-me'))"
   ```

5. Run the application
   ```bash
   python app.py
   ```

6. Open your browser
   Navigate to `http://localhost:8080`

## Project Structure

```
codeScribe2/
├── app.py              # Flask application and API routes
├── requirements.txt    # Python dependencies
├── .env.example        # Example environment variables
├── static/
│   ├── style.css       # Main styles
│   ├── cosmic.css      # Animation styles
│   └── script.js       # Frontend JavaScript
└── templates/
    ├── index.html      # Main page
    ├── about.html      # About page
    ├── login.html      # Login page
    └── settings.html   # Settings page
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main application page |
| `/login` | GET/POST | User authentication |
| `/logout` | GET | End user session |
| `/settings` | GET/POST | User settings management |
| `/about` | GET | About page |
| `/analyze-all` | POST | Full code analysis (docs, audit, graph, trace) |
| `/v1/analyze-all` | POST | Versioned alias for full code analysis |
| `/upload-zip` | POST | Project-wide analysis from ZIP upload |
| `/v1/upload-zip` | POST | Versioned alias for project upload |
| `/refactor-code` | POST | AI-assisted code refactoring |
| `/v1/refactor-code` | POST | Versioned alias for refactor endpoint |
| `/generate-test` | POST | Generate pytest tests for a function |
| `/v1/generate-test` | POST | Versioned alias for test generation |
| `/v1/live-metrics` | POST | Versioned alias for live metrics |
| `/v1/jobs/analyze` | POST | Submit asynchronous analysis job |
| `/v1/jobs/<job_id>` | GET | Poll asynchronous analysis result |
| `/healthz` | GET | Liveness endpoint |
| `/readyz` | GET | Readiness endpoint |
| `/metrics` | GET | Prometheus-style service metrics |

## Configuration

The application uses the following environment variables:

| Variable | Description |
|----------|-------------|
| `GEMINI_API_KEY` | Your Google Gemini API key (required) |
| `FLASK_SECRET_KEY` | Flask session signing secret (required) |
| `APP_ADMIN_USERNAME` | Login username (required) |
| `APP_ADMIN_PASSWORD_HASH` | Password hash generated with Werkzeug (required) |
| `APP_ADMIN_ROLE` | Role assigned to the configured admin user |
| `CORS_ALLOWED_ORIGINS` | Comma-separated browser origin allowlist |
| `MODEL_TIMEOUT_SECONDS` | Timeout in seconds for model requests |
| `DEMO_MODE` | Set `true` to return deterministic demo responses when AI backend is unavailable |
| `FLASK_DEBUG` | Enables Flask debug mode when true |
| `PORT` | Application port |
| `SESSION_COOKIE_SECURE` | Secure-cookie flag for HTTPS environments |
| `MAX_FAILED_LOGINS` | Failed attempts before lockout |
| `LOCKOUT_SECONDS` | Lockout duration after threshold is reached |

## Professor Evaluation Setup

Use this flow so your professor can test with just a public URL and no personal API key.

1. Deploy the app to Railway/Render using `gunicorn app:app`.
2. Set environment variables on the host:
   - `GEMINI_API_KEY=<your-evaluation-key>`
   - `FLASK_SECRET_KEY=<long-random-secret>`
   - `APP_ADMIN_USERNAME=<shared-eval-username>`
   - `APP_ADMIN_PASSWORD_HASH=<werkzeug-hash>`
   - `SESSION_COOKIE_SECURE=true`
   - `CORS_ALLOWED_ORIGINS=<your-public-app-url>`
   - `DEMO_MODE=false`
3. Share only the app URL and login credentials with your professor.

Recommended safety for evaluation keys:

- Create a dedicated short-lived key for the project demo.
- Set billing/quota alerts in Google Cloud.
- Revoke or rotate the key after grading.

Optional fallback for offline/demo-only grading:

- Set `DEMO_MODE=true` and unset `GEMINI_API_KEY`.
- The app remains testable end-to-end, but responses are deterministic demo text instead of live AI output.

## Testing and CI

- Run tests locally:
   ```bash
   pytest -q
   ```
- GitHub Actions workflow at `.github/workflows/ci.yml` runs:
   - pytest
   - pip-audit vulnerability scan

Note: The CI scan temporarily ignores advisories tied to environment tooling (`pip`) and an upstream transitive `protobuf` advisory until compatible upstream packages are upgraded.

## Deployment

### Deploy to Render

1. Push your code to GitHub
2. Connect your GitHub repo to Render (https://render.com)
3. Create a new Web Service
4. Set the following:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
5. Add your `GEMINI_API_KEY` as an environment variable

### Deploy to Railway

1. Push your code to GitHub
2. Connect your GitHub repo to Railway (https://railway.app)
3. Add your `GEMINI_API_KEY` as an environment variable
4. Deploy
