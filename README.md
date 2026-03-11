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
| `/upload-zip` | POST | Project-wide analysis from ZIP upload |
| `/refactor-code` | POST | AI-assisted code refactoring |
| `/generate-test` | POST | Generate pytest tests for a function |
| `/healthz` | GET | Liveness endpoint |
| `/readyz` | GET | Readiness endpoint |

## Configuration

The application uses the following environment variables:

| Variable | Description |
|----------|-------------|
| `GEMINI_API_KEY` | Your Google Gemini API key (required) |
| `FLASK_SECRET_KEY` | Flask session signing secret (required) |
| `APP_ADMIN_USERNAME` | Login username (required) |
| `APP_ADMIN_PASSWORD_HASH` | Password hash generated with Werkzeug (required) |
| `CORS_ALLOWED_ORIGINS` | Comma-separated browser origin allowlist |
| `MODEL_TIMEOUT_SECONDS` | Timeout in seconds for model requests |
| `FLASK_DEBUG` | Enables Flask debug mode when true |
| `PORT` | Application port |
| `SESSION_COOKIE_SECURE` | Secure-cookie flag for HTTPS environments |

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
