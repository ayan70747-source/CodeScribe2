
"""
CodeScribe Flask Application
---------------------------
This app provides a beautiful web interface for generating AI-powered code documentation.
It uses Google Gemini for code analysis and Markdown documentation generation.
"""

import ast
import io
import logging
import os
import re
import secrets
import sys
import shutil
import tempfile
import threading
import time
import zipfile
from collections import defaultdict, deque
from contextlib import redirect_stdout
from datetime import timedelta
from functools import wraps
from pathlib import Path

import astor
import graphviz
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, g, has_request_context
from dotenv import load_dotenv
from radon.complexity import cc_visit
from radon.metrics import mi_visit
from radon.raw import analyze as raw_analyze
from werkzeug.security import check_password_hash

# --- Load API Key ---
load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    raise ValueError("GEMINI_API_KEY not found. Make sure it's in your .env file.")

genai.configure(api_key=api_key)

# --- Gemini Model Configuration ---
GENERATION_CONFIG = {
    "temperature": 0.3,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
}
SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]
MODEL_NAME = 'gemini-2.5-flash-preview-09-2025'
MODEL_TIMEOUT_SECONDS = int(os.getenv('MODEL_TIMEOUT_SECONDS', '60'))

logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO').upper(),
    format='%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s %(message)s',
)
logger = logging.getLogger('codescribe')


class RequestIdFilter(logging.Filter):
    """Inject request IDs into logs emitted during request handling."""

    def filter(self, record):
        record.request_id = getattr(g, 'request_id', '-') if has_request_context() else '-'
        return True


logger.addFilter(RequestIdFilter())

DOC_SYSTEM_INSTRUCTION = """
You are "CodeScribe," an expert AI developer specializing in documenting legacy code.
A user will provide you with a block of code.
Your job is to return a comprehensive, well-structured documentation for it.
Format your response in Markdown.

Your documentation MUST include the following sections:

1.  ### 📚 High-Level Summary
    A brief, one-paragraph explanation of what this code does. Who is it for? What is its main purpose?

2.  ### ⚙️ Function Breakdown
    Go through each function (or class) one by one and explain:
    * **What it does:** A clear explanation of its logic.
    * **Parameters:** What does it take as input?
    * **Returns:** What does it give back as output?

3.  ### 🔗 Key Dependencies & Variables
    * **External Libraries:** List any libraries it imports (e.g., `os`, `Flask`) and why it needs them.
    * **Global Variables:** List any key variables and explain their purpose.

4.  ### 💡 Suggested Improvements (Optional)
    If you see any obvious old-fashioned code or potential bugs, briefly and politely suggest a modern improvement.
"""

AUDIT_SYSTEM_INSTRUCTION = """
You are "CodeAuditor," a senior cybersecurity analyst and software architect.
Your job is to audit the given code for vulnerabilities and technical debt.
Do NOT document what the functions do.
Format your response in Markdown.

Your report MUST include these two sections:

1.  ### 🚨 AI Security Audit
    * List all potential vulnerabilities (e.g., SQL Injection, Hardcoded Secrets, Insecure Deserialization, etc.).
    * Assign a severity (Critical, High, Medium, Low).
    * Suggest a brief, code-based fix for each.

2.  ### 📊 Refactor Risk Score
    * Analyze the code's Cyclomatic Complexity, readability, and maintainability.
    * Provide an overall "Technical Debt" score from 0 (Perfect) to 100 (High Risk).
    * List the top 3 "riskiest" functions that should be refactored first.
"""

TRACE_SYSTEM_INSTRUCTION = """
You are "CodeExplainer," an expert AI developer and debugger.
A user will provide you with two things: (1) a block of source code, and (2) a "trace log" that shows what happened *when that code was executed*.
The trace log shows the line number and the live values of all variables at that line.

Your job is to write a human-readable "story" of the execution.
* Explain *what* happened, step-by-step, using the trace log as your guide.
* Explain *why* the code took a certain path (e.g., "The code entered the `if` block on line 10 because `x` was 52, which is greater than 50.").
* Conclude with the final output or return value.
* Format this "story" as clear, explanatory Markdown.
"""

REFACTOR_SYSTEM_INSTRUCTION = """
You are "CodeFixer," a principal engineer and application security expert.
Given a codebase and a vulnerability description, produce a surgically precise refactor that mitigates the issue without altering unrelated behavior.
Respond with the revised code snippet only, formatted as Markdown inside a single fenced code block tagged with the appropriate language.
Briefly annotate risky changes inline using comments when essential.
"""

TEST_GEN_SYSTEM_INSTRUCTION = """
You are "TestPilot," a senior QA engineer specializing in automated testing.
Given the source for a function, design a comprehensive pytest test module that asserts happy path, edge cases, and regression-prone scenarios.
Return only executable pytest code in Markdown inside a ```python fenced block.
Include explanatory comments sparingly to justify non-obvious cases.
"""

ARCHITECT_SYSTEM_INSTRUCTION = """
You are "The Architect," a veteran software systems engineer.
Given the contents of an entire project, produce a concise but insightful project brief that covers:
1. Overall architecture and layering patterns.
2. Key modules and how they collaborate.
3. Observable coupling issues (e.g., circular dependencies, god modules, tight integration points).
4. The top architectural or maintainability risks the team should address next.
Format the response as Markdown, using headings and bullet points where appropriate.
"""

DBA_SYSTEM_INSTRUCTION = """
You are an expert PostgreSQL Database Administrator (DBA).
You will receive one or more SQL queries extracted from an application codebase.
For each query:
1. **Explain It** — Describe what the query does in plain language.
2. **Analyze Performance** — Highlight likely bottlenecks (full scans, missing indexes, sorting, locking, etc.).
3. **Rewrite for Performance** — Provide an optimized version of the query when possible.
4. **Infer Schema** — Guess the relevant table/column structure implied by the query.
Respond in Markdown under a "### Database Report" heading and keep each query separated with subheadings.
"""


def _build_model(system_instruction: str) -> genai.GenerativeModel:
    """Create a Gemini model instance with the shared configuration."""
    return genai.GenerativeModel(
        MODEL_NAME,
        generation_config=GENERATION_CONFIG,
        safety_settings=SAFETY_SETTINGS,
        system_instruction=system_instruction,
    )

app = Flask(__name__)

flask_secret_key = os.getenv('FLASK_SECRET_KEY')
if not flask_secret_key:
    raise ValueError('FLASK_SECRET_KEY not found. Set it in your environment.')

app.secret_key = flask_secret_key
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=12)

admin_username = os.getenv('APP_ADMIN_USERNAME')
admin_password_hash = os.getenv('APP_ADMIN_PASSWORD_HASH')
if not admin_username or not admin_password_hash:
    raise ValueError('APP_ADMIN_USERNAME and APP_ADMIN_PASSWORD_HASH are required in the environment.')

cors_allowed_origins = {
    origin.strip()
    for origin in os.getenv('CORS_ALLOWED_ORIGINS', 'http://127.0.0.1:8080,http://localhost:8080').split(',')
    if origin.strip()
}

rate_limit_lock = threading.Lock()
request_windows: dict[str, deque[float]] = defaultdict(deque)


def rate_limit(max_requests: int, window_seconds: int):
    """Apply a simple in-memory request cap per client and endpoint."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            client = request.headers.get('X-Forwarded-For', request.remote_addr or 'unknown').split(',')[0].strip()
            endpoint_key = f"{client}:{request.endpoint or func.__name__}"
            now = time.monotonic()
            cutoff = now - window_seconds

            with rate_limit_lock:
                window = request_windows[endpoint_key]
                while window and window[0] < cutoff:
                    window.popleft()
                if len(window) >= max_requests:
                    return jsonify({"error": "Rate limit exceeded. Please retry shortly."}), 429
                window.append(now)

            return func(*args, **kwargs)

        return wrapper

    return decorator


def login_required(func):
    """Protect routes that require an authenticated user session."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'user' not in session:
            return jsonify({"error": "Authentication required."}), 401
        return func(*args, **kwargs)

    return wrapper


def generate_csrf_token() -> str:
    """Create a per-session CSRF token for HTML forms."""
    token = session.get('_csrf_token')
    if not token:
        token = secrets.token_urlsafe(32)
        session['_csrf_token'] = token
    return token


def validate_csrf_token() -> bool:
    """Validate incoming CSRF token for form POST requests."""
    form_token = request.form.get('csrf_token', '')
    session_token = session.get('_csrf_token', '')
    return bool(form_token and session_token and secrets.compare_digest(form_token, session_token))


app.jinja_env.globals['csrf_token'] = generate_csrf_token


@app.before_request
def attach_request_context():
    """Attach request metadata used for observability and tracing."""
    g.request_id = secrets.token_hex(8)
    g.request_started = time.monotonic()


@app.route('/')
def index():
    """
    Home page route.
    Renders the main code documentation interface.
    Requires user to be logged in.
    """
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

def get_ai_documentation(code_str: str) -> str:
    """Send the user's code to the documentataion files."""
    doc_model = _build_model(DOC_SYSTEM_INSTRUCTION)
    chat_session = doc_model.start_chat(history=[])
    response = chat_session.send_message(
        f"""Here is the code:\n\n```
{code_str}
```"""
        ,
        request_options={"timeout": MODEL_TIMEOUT_SECONDS},
    )
    return response.text


def get_ai_security_audit(code_str: str) -> str:
    """Run the security audit persona against the provided source code."""
    audit_model = _build_model(AUDIT_SYSTEM_INSTRUCTION)
    chat_session = audit_model.start_chat(history=[])
    response = chat_session.send_message(
        f"""Audit the following code:\n\n```
{code_str}
```"""
        ,
        request_options={"timeout": MODEL_TIMEOUT_SECONDS},
    )
    return response.text


def get_ai_refactor(code_str: str, vulnerability_context: str) -> str:
    """Send the vulnerability details to the refactor persona."""
    if not vulnerability_context.strip():
        raise ValueError("vulnerability_context is required")
    refactor_model = _build_model(REFACTOR_SYSTEM_INSTRUCTION)
    chat_session = refactor_model.start_chat(history=[])
    prompt = (
        "Original Code:\n\n```python\n"
        f"{code_str}\n"
        "```\n\nVulnerability Context:\n"
        f"{vulnerability_context}"
    )
    response = chat_session.send_message(
        prompt,
        request_options={"timeout": MODEL_TIMEOUT_SECONDS},
    )
    return response.text


class FunctionCallVisitor(ast.NodeVisitor):
    """Collect function definitions and their outgoing call targets."""

    def __init__(self) -> None:
        self.current_function = None
        self.calls = {}

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        previous = self.current_function
        self.current_function = node.name
        self.calls.setdefault(node.name, set())
        self.generic_visit(node)
        self.current_function = previous

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)  # Treat async functions the same way.

    def visit_Call(self, node: ast.Call) -> None:
        if self.current_function:
            callee = self._resolve_callable_name(node.func)
            if callee:
                self.calls.setdefault(self.current_function, set()).add(callee)
        self.generic_visit(node)

    @staticmethod
    def _resolve_callable_name(node: ast.AST) -> str | None:
        try:
            return astor.to_source(node).strip()
        except (SyntaxError, ValueError, AttributeError):
            return None


def generate_visualizer_graph(code_str: str) -> dict[str, str]:
    """Produce Mermaid and Graphviz representations of the call graph."""
    try:
        tree = ast.parse(code_str)
    except SyntaxError as exc:
        return {
            "mermaid": "",
            "graphviz": "",
            "error": f"Failed to parse code: {exc}"
        }

    visitor = FunctionCallVisitor()
    visitor.visit(tree)

    adjacency: dict[str, list[str]] = {
        func: sorted(callees)
        for func, callees in visitor.calls.items()
    }

    all_nodes: set[str] = set(adjacency.keys())
    for callees in adjacency.values():
        all_nodes.update(callees)

    if not all_nodes:
        mermaid_graph = "graph TD\nplaceholder[\"No functions detected\"]"
        return {
            "mermaid": mermaid_graph,
            "graphviz": "",
            "message": "No functions detected."
        }

    node_id_map: dict[str, str] = {}
    used_ids: set[str] = set()

    def ensure_node_id(label: str) -> str:
        if label in node_id_map:
            return node_id_map[label]
        sanitized = re.sub(r"\W+", "_", label)
        if sanitized and sanitized[0].isdigit():
            sanitized = f"n_{sanitized}"
        sanitized = sanitized or "node"
        base = sanitized
        suffix = 1
        while sanitized in used_ids:
            suffix += 1
            sanitized = f"{base}_{suffix}"
        used_ids.add(sanitized)
        node_id_map[label] = sanitized
        return sanitized

    mermaid_lines = ["graph TD"]
    for label in sorted(all_nodes):
        node_id = ensure_node_id(label)
        display_label = label.replace('"', "'")
        mermaid_lines.append(f"{node_id}[\"{display_label}\"]")

    for caller, callees in sorted(adjacency.items()):
        caller_id = ensure_node_id(caller)
        for callee in callees:
            callee_id = ensure_node_id(callee)
            mermaid_lines.append(f"{caller_id} --> {callee_id}")

    graphviz_svg = ""
    try:
        graph = graphviz.Digraph(comment="Function Call Graph", format="svg")
        for node in sorted(all_nodes):
            graph.node(node)
        for caller, callees in sorted(adjacency.items()):
            for callee in callees:
                graph.edge(caller, callee)
        graphviz_svg = graph.pipe().decode("utf-8")
    except graphviz.backend.ExecutableNotFound:
        graphviz_svg = ""
    except Exception as exc:
        graphviz_svg = f"Graphviz rendering failed: {exc}"

    return {
        "mermaid": "\n".join(mermaid_lines),
        "graphviz": graphviz_svg,
    }


def isolate_function_code(full_code: str, function_name: str) -> str | None:
    """Extract the source code for the requested top-level function."""
    if not function_name:
        return None
    try:
        tree = ast.parse(full_code)
    except SyntaxError:
        return None

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            return astor.to_source(node).strip()
    return None


def get_ai_test_module(function_source: str, function_name: str) -> str:
    """Generate pytest code for the isolated function."""
    if not function_source:
        raise ValueError(f"Function '{function_name}' not found in provided code.")

    test_model = _build_model(TEST_GEN_SYSTEM_INSTRUCTION)
    chat_session = test_model.start_chat(history=[])
    prompt = (
        f"Generate pytest tests for the following function `{function_name}`.\n\n"
        "```python\n"
        f"{function_source}\n"
        "```"
    )
    response = chat_session.send_message(
        prompt,
        request_options={"timeout": MODEL_TIMEOUT_SECONDS},
    )
    return response.text


def get_ai_project_overview(project_code: str) -> str:
    """Summarize an entire project using the Architect persona."""
    architect_model = _build_model(ARCHITECT_SYSTEM_INSTRUCTION)
    chat_session = architect_model.start_chat(history=[])
    response = chat_session.send_message(
        "Provide a project-wide architecture brief for the following source files:\n\n" +
        project_code,
        request_options={"timeout": MODEL_TIMEOUT_SECONDS},
    )
    return response.text


SQL_KEYWORD_PATTERN = re.compile(
    r"\b(SELECT|INSERT|UPDATE|DELETE|CREATE\s+TABLE|ALTER\s+TABLE|WITH\s+|DROP\s+TABLE|MERGE)\b",
    re.IGNORECASE,
)


def extract_sql_queries(code_str: str) -> list[str]:
    """Scan Python source for inline SQL query strings."""

    def looks_like_sql(text: str) -> bool:
        stripped = text.strip()
        if len(stripped) < 6:
            return False
        return bool(SQL_KEYWORD_PATTERN.search(stripped))

    queries: list[str] = []
    seen: set[str] = set()
    try:
        tree = ast.parse(code_str)
    except SyntaxError:
        return []

    class SQLExtractor(ast.NodeVisitor):
        def _maybe_add(self, value: str) -> None:
            if not value:
                return
            candidate = value.strip()
            if looks_like_sql(candidate) and candidate not in seen:
                seen.add(candidate)
                queries.append(candidate)

        def visit_Constant(self, node: ast.Constant) -> None:  # type: ignore[override]
            if isinstance(node.value, str):
                self._maybe_add(node.value)

        def visit_Str(self, node: ast.Str) -> None:  # for Python <3.8 compatibility
            self._maybe_add(node.s)

        def visit_JoinedStr(self, node: ast.JoinedStr) -> None:
            literal_parts: list[str] = []
            for value in node.values:
                if isinstance(value, ast.Str):
                    literal_parts.append(value.s)
                elif isinstance(value, ast.Constant) and isinstance(value.value, str):
                    literal_parts.append(value.value)
            if literal_parts:
                self._maybe_add("".join(literal_parts))

    SQLExtractor().visit(tree)
    return queries


def get_ai_database_report(sql_queries: list[str]) -> str:
    """Delegate SQL performance and security review to the DBA persona."""
    if not sql_queries:
        return ""

    prompt_sections = []
    for idx, query in enumerate(sql_queries, start=1):
        prompt_sections.append(f"Query {idx}:\n```sql\n{query}\n```")

    prompt = "\n\n".join(prompt_sections)
    dba_model = _build_model(DBA_SYSTEM_INSTRUCTION)
    chat_session = dba_model.start_chat(history=[])
    response = chat_session.send_message(
        prompt,
        request_options={"timeout": MODEL_TIMEOUT_SECONDS},
    )
    return response.text


def collect_python_files(project_root: str) -> list[tuple[str, str]]:
    """Return (relative_path, source) tuples for all Python files under root."""
    python_files: list[tuple[str, str]] = []
    root_path = Path(project_root).resolve()
    for path in root_path.rglob('*.py'):
        if any(part.startswith('.') for part in path.relative_to(root_path).parts):
            continue
        if '__pycache__' in path.parts:
            continue
        try:
            source = path.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue
        rel_path = path.relative_to(root_path).as_posix()
        python_files.append((rel_path, source))
    return python_files


def _sanitize_node_id(label: str) -> str:
    sanitized = re.sub(r"\W+", "_", label)
    if sanitized and sanitized[0].isdigit():
        sanitized = f"n_{sanitized}"
    return sanitized or "node"


def build_project_call_graph(py_files: list[tuple[str, str]]):
    """Create a cross-file call graph for an entire project."""
    defined_functions: dict[str, set[str]] = {}
    nodes: dict[str, dict[str, str]] = {}
    edges: set[tuple[str, str]] = set()

    # First pass: collect defined functions
    for rel_path, source in py_files:
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qualified = f"{rel_path}:{node.name}"
                nodes[qualified] = {
                    "id": qualified,
                    "label": qualified,
                    "file": rel_path,
                    "function": node.name,
                    "type": "defined",
                }
                defined_functions.setdefault(node.name, set()).add(qualified)

    class ProjectCallGraphVisitor(ast.NodeVisitor):
        def __init__(self, file_label: str):
            self.file_label = file_label
            self.current_function: str | None = None

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            qualified = f"{self.file_label}:{node.name}"
            previous = self.current_function
            self.current_function = qualified
            self.generic_visit(node)
            self.current_function = previous

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self.visit_FunctionDef(node)

        def visit_Call(self, node: ast.Call) -> None:
            if not self.current_function:
                return
            callee_repr = FunctionCallVisitor._resolve_callable_name(node.func)
            if not callee_repr:
                return
            callee_basic = re.split(r"[\s(]", callee_repr)[0]
            callee_name = callee_basic.split('.')[-1]
            targets = defined_functions.get(callee_name)
            if targets:
                for target in targets:
                    edges.add((self.current_function, target))
            else:
                external_label = f"external::{callee_basic}"
                if external_label not in nodes:
                    nodes[external_label] = {
                        "id": external_label,
                        "label": callee_basic,
                        "file": "external",
                        "function": callee_basic,
                        "type": "external",
                    }
                edges.add((self.current_function, external_label))
            self.generic_visit(node)

    for rel_path, source in py_files:
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        ProjectCallGraphVisitor(rel_path).visit(tree)

    mermaid_lines = ["graph LR"]
    id_map: dict[str, str] = {}
    for label in sorted(nodes.keys()):
        node_id = _sanitize_node_id(label)
        suffix = 1
        base_id = node_id
        while node_id in id_map.values():
            suffix += 1
            node_id = f"{base_id}_{suffix}"
        id_map[label] = node_id
        safe_label = nodes[label]["label"].replace('"', "'")
        mermaid_lines.append(f"{node_id}[\"{safe_label}\"]")

    for source_id, target_id in sorted(edges):
        src = id_map.get(source_id)
        dst = id_map.get(target_id)
        if src and dst:
            mermaid_lines.append(f"{src} --> {dst}")

    metadata = {
        "files": len(py_files),
        "defined_functions": sum(1 for n in nodes.values() if n["type"] == "defined"),
        "external_nodes": sum(1 for n in nodes.values() if n["type"] == "external"),
        "edges": len(edges),
    }

    return {
        "mode": "project",
        "nodes": list(nodes.values()),
        "edges": [{"source": s, "target": t} for s, t in sorted(edges)],
        "mermaid": "\n".join(mermaid_lines),
        "metadata": metadata,
    }


def safe_extract(zip_ref: zipfile.ZipFile, destination: str) -> None:
    """Extract a zip file while preventing path traversal."""
    dest_path = Path(destination).resolve()
    for member in zip_ref.infolist():
        member_path = dest_path / member.filename
        if not str(member_path.resolve()).startswith(str(dest_path)):
            raise ValueError("Zip file contains unsafe paths.")
    zip_ref.extractall(destination)


def get_live_trace_explanation(code_str: str, trace_input: str) -> str:
    """Run the user's code with tracing and ask the explainer persona to narrate it."""

    trace_log: list[str] = []

    def trace_lines(frame, event, _arg):
        if event != "line":
            return trace_lines
        lineno = frame.f_lineno
        local_vars = {
            key: repr(value)
            for key, value in frame.f_locals.items()
            if not key.startswith("__")
        }
        trace_log.append(f"Line {lineno}: {local_vars}")
        return trace_lines

    safe_builtins = {
        "range": range,
        "len": len,
        "print": print,
        "enumerate": enumerate,
        "sum": sum,
        "min": min,
        "max": max,
        "sorted": sorted,
        "list": list,
        "dict": dict,
        "set": set,
        "tuple": tuple,
        "zip": zip,
        "abs": abs,
    }
    sandbox: dict[str, object] = {"__builtins__": safe_builtins}
    stdout_buffer = io.StringIO()

    try:
        compiled = compile(f"{code_str}\n", "<user_code>", "exec")
        compiled_trace = compile(trace_input, "<trace_input>", "exec") if trace_input else None
        with redirect_stdout(stdout_buffer):
            sys.settrace(trace_lines)
            try:
                exec(compiled, sandbox)
                if compiled_trace is not None:
                    exec(compiled_trace, sandbox)
            finally:
                sys.settrace(None)
        captured_stdout = stdout_buffer.getvalue()
        trace_report = "\n".join(trace_log)
        if captured_stdout:
            trace_report += f"\n\nstdout:\n{captured_stdout.strip()}"
    except Exception as exc:
        sys.settrace(None)
        trace_report = f"Trace execution failed: {exc}"

    trace_model = _build_model(TRACE_SYSTEM_INSTRUCTION)
    chat_session = trace_model.start_chat(history=[])
    prompt = (
        "Source Code:\n\n```python\n"
        f"{code_str}\n"
        "```\n\nTrace Log:\n\n```\n"
        f"{trace_report}\n"
        "```"
    )
    response = chat_session.send_message(
        prompt,
        request_options={"timeout": MODEL_TIMEOUT_SECONDS},
    )
    return response.text


@app.route('/healthz')
def healthz():
    """Return process liveness for infrastructure checks."""
    return jsonify({"status": "ok"}), 200


@app.route('/readyz')
def readyz():
    """Return readiness based on required runtime configuration."""
    ready = bool(api_key and app.secret_key and admin_username and admin_password_hash)
    status_code = 200 if ready else 503
    return jsonify({"ready": ready}), status_code


@app.route('/about')
def about():
    """
    About page route.
    Renders the About page with app info and credits.
    """
    return render_template('about.html')


@app.route('/analyze-all', methods=['POST'])
@login_required
@rate_limit(max_requests=15, window_seconds=60)
def analyze_all():
    """Aggregate documentation, security audit, call graph, and trace insights."""
    try:
        data = request.get_json() or {}
        code = (data.get('code') or '').strip()
        trace_input = (data.get('trace_input') or '').strip()

        if not code:
            return jsonify({"error": "No code provided"}), 400

        results: dict[str, object] = {}

        try:
            results['documentation'] = get_ai_documentation(code)
        except Exception as exc:
            results['documentation'] = f"Documentation generation failed: {exc}"

        try:
            results['audit'] = get_ai_security_audit(code)
        except Exception as exc:
            results['audit'] = f"Security audit failed: {exc}"

        results['visualizer'] = generate_visualizer_graph(code)

        if trace_input:
            try:
                results['trace'] = get_live_trace_explanation(code, trace_input)
            except Exception as exc:
                results['trace'] = f"Live trace explanation failed: {exc}"
        else:
            results['trace'] = "Please provide a sample input to run the Live Trace."

        sql_queries = extract_sql_queries(code)
        if sql_queries:
            try:
                results['database_report'] = get_ai_database_report(sql_queries)
            except Exception as exc:
                results['database_report'] = f"Database analysis failed: {exc}"
        else:
            results['database_report'] = "No SQL queries detected in the provided code."

        return jsonify(results)
    except Exception:
        logger.exception("Analyze-all failed")
        return jsonify({"error": "An internal error occurred."}), 500


@app.route('/upload-zip', methods=['POST'])
@login_required
@rate_limit(max_requests=6, window_seconds=60)
def upload_zip_endpoint():
    """Handle project-wide uploads for The Architect workflow."""
    if 'projectZip' not in request.files:
        return jsonify({"error": "No project .zip file was uploaded."}), 400

    uploaded = request.files['projectZip']
    if uploaded.filename == '':
        return jsonify({"error": "No file selected."}), 400

    temp_dir = tempfile.mkdtemp(prefix='codescribe_zip_')
    zip_path = os.path.join(temp_dir, 'project.zip')
    extract_dir = os.path.join(temp_dir, 'project')
    os.makedirs(extract_dir, exist_ok=True)

    try:
        uploaded.save(zip_path)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            safe_extract(zip_ref, extract_dir)

        python_files = collect_python_files(extract_dir)
        if not python_files:
            return jsonify({"error": "No Python files detected in the uploaded archive."}), 400

        combined_sections: list[str] = []
        for rel_path, source in python_files:
            combined_sections.append(f"# File: {rel_path}\n{source}\n")
        combined_code = "\n".join(combined_sections)

        project_graph = build_project_call_graph(python_files)

        try:
            project_summary = get_ai_project_overview(combined_code)
        except Exception as exc:
            project_summary = f"Project overview generation failed: {exc}"

        try:
            project_security = get_ai_security_audit(combined_code)
        except Exception as exc:
            project_security = f"Project security audit failed: {exc}"

        all_sql_queries: list[str] = []
        for _rel, source in python_files:
            all_sql_queries.extend(extract_sql_queries(source))

        if all_sql_queries:
            try:
                sql_report = get_ai_database_report(all_sql_queries)
            except Exception as exc:
                sql_report = f"Database analysis failed: {exc}"
        else:
            sql_report = "No SQL queries detected across the uploaded project."

        project_graph.setdefault('metadata', {})['sql_queries'] = len(all_sql_queries)

        payload = {
            "project_summary": project_summary,
            "project_security": project_security,
            "visualizer": project_graph,
            "file_count": len(python_files),
            "database_report": sql_report,
        }
        return jsonify(payload)
    except zipfile.BadZipFile:
        return jsonify({"error": "The uploaded file is not a valid zip archive."}), 400
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        logger.exception("Project upload failed")
        return jsonify({"error": "Failed to analyze the uploaded project."}), 500
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@app.route('/refactor-code', methods=['POST'])
@login_required
@rate_limit(max_requests=10, window_seconds=60)
def refactor_code():
    """Leverage the refactor persona to patch reported vulnerabilities."""
    try:
        payload = request.get_json() or {}
        code = (payload.get('code') or '').strip()
        context = (payload.get('vulnerability_context') or '').strip()

        if not code:
            return jsonify({"error": "No code provided"}), 400
        if not context:
            return jsonify({"error": "No vulnerability context provided"}), 400

        try:
            refactored = get_ai_refactor(code, context)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        return jsonify({"refactored_code": refactored})
    except Exception:
        logger.exception("Refactor request failed")
        return jsonify({"error": "An internal error occurred."}), 500


@app.route('/generate-test', methods=['POST'])
@login_required
@rate_limit(max_requests=10, window_seconds=60)
def generate_test():
    """Generate pytest scaffolding for a requested function."""
    try:
        payload = request.get_json() or {}
        code = (payload.get('code') or '').strip()
        function_name = (payload.get('function_name') or '').strip()

        if not code:
            return jsonify({"error": "No code provided"}), 400
        if not function_name:
            return jsonify({"error": "No function name provided"}), 400

        function_source = isolate_function_code(code, function_name)
        if not function_source:
            return jsonify({"error": f"Function '{function_name}' not found."}), 404

        test_module = get_ai_test_module(function_source, function_name)
        return jsonify({"test_code": test_module, "function_source": function_source})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        logger.exception("Test generation failed")
        return jsonify({"error": "An internal error occurred."}), 500


@app.route('/live-metrics', methods=['POST'])
@login_required
@rate_limit(max_requests=60, window_seconds=60)
def live_metrics():
    """Return instantaneous code metrics without invoking the LLM."""
    try:
        payload = request.get_json() or {}
        code = (payload.get('code') or '').strip()
        if not code:
            return jsonify({"error": "No code provided"}), 400
        return jsonify(calculate_code_metrics(code))
    except Exception:
        logger.exception("Live metrics failed")
        return jsonify({"error": "Failed to calculate metrics."}), 500


def calculate_code_metrics(code_str: str) -> dict[str, float | int]:
    """Compute quick structural metrics to power the Live Metrics panel."""
    metrics: dict[str, float | int] = {
        "cyclomatic_complexity_avg": 0.0,
        "cyclomatic_complexity_max": 0.0,
        "maintainability_index": 0.0,
        "loc": 0,
        "comment_lines": 0,
    }

    if not code_str or not code_str.strip():
        return metrics

    try:
        blocks = cc_visit(code_str)
        complexities = [block.complexity for block in blocks]
        if complexities:
            metrics["cyclomatic_complexity_avg"] = sum(complexities) / len(complexities)
            metrics["cyclomatic_complexity_max"] = max(complexities)
    except Exception:
        pass

    try:
        mi_score = mi_visit(code_str, False)
        if isinstance(mi_score, (int, float)):
            metrics["maintainability_index"] = max(0.0, min(100.0, mi_score))
    except Exception:
        pass

    try:
        raw_stats = raw_analyze(code_str)
        metrics["loc"] = raw_stats.loc
        metrics["comment_lines"] = raw_stats.comments + raw_stats.multi
    except Exception:
        lines = code_str.splitlines()
        metrics["loc"] = sum(1 for line in lines if line.strip())
        metrics["comment_lines"] = sum(1 for line in lines if line.strip().startswith('#'))

    return metrics

@app.after_request
def after_request(response):
    origin = request.headers.get('Origin')
    if origin and origin in cors_allowed_origins:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Vary'] = 'Origin'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-CSRF-Token'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    response.headers['X-Request-ID'] = getattr(g, 'request_id', '-')
    duration_ms = int((time.monotonic() - getattr(g, 'request_started', time.monotonic())) * 1000)
    response.headers['X-Response-Time-ms'] = str(max(duration_ms, 0))
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "base-uri 'self'; "
        "frame-ancestors 'none';"
    )
    return response

# --- Authentication Routes ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if request.method == 'POST':
        if not validate_csrf_token():
            return render_template('login.html', error='Invalid CSRF token.'), 400

        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''

        if username == admin_username and check_password_hash(admin_password_hash, password):
            session.permanent = True
            session['user'] = username
            return redirect(url_for('index'))
        return render_template('login.html', error='Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Handle user logout"""
    session.clear()
    return redirect(url_for('login'))

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """Handle user settings"""
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        if not validate_csrf_token():
            return render_template('settings.html', message='Invalid CSRF token.'), 400

        temperature_raw = (request.form.get('temperature') or '0.3').strip()
        try:
            temperature_value = float(temperature_raw)
        except ValueError:
            return render_template('settings.html', message='Temperature must be a number between 0 and 1.'), 400

        if temperature_value < 0 or temperature_value > 1:
            return render_template('settings.html', message='Temperature must be between 0 and 1.'), 400

        session['temperature'] = f"{temperature_value:.1f}"
        session.modified = True

        return render_template(
            'settings.html',
            message='Settings saved successfully. API keys are managed via environment variables.',
            temperature=session.get('temperature', '0.3'),
            api_key=''
        )

    temperature = session.get('temperature', '0.3')

    return render_template('settings.html', api_key='', temperature=temperature)

# --- Main Entrypoint ---
if __name__ == '__main__':
    app_port = int(os.getenv('PORT', '8080'))
    app_debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=app_port, debug=app_debug)