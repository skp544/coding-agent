# CodingAgentMVP1

A minimal command-line coding agent built with [LangChain](https://docs.langchain.com/) and [LangGraph](https://langchain-ai.github.io/langgraph/). You chat with it in the terminal; it reads, lists, writes and edits real files in a sandboxed working folder, and can run bash commands (including long-running servers). Every write, edit and command needs your approval by default.

```
You: Create app.py with a Flask hello-world and run it in the background

----human in the loop-------
0. write_file (Write or overwrite a file on disk)
    path: app.py
    content: ...
Allow write_file? (y/n): y
...
LLM: The server is running at http://127.0.0.1:5000/ ...
```

## Features

- **File tools** — `list_files`, `read_file`, `write_file`, `edit_file`, all confined to the working directory.
- **Shell tools** — `run_command` (foreground or background), `list_jobs`, `stop_job`. Server-style commands (`flask run`, `uvicorn`, `npm start`, ...) are auto-backgrounded, and their logs are captured.
- **Human-in-the-loop** — `write_file`, `edit_file` and `run_command` pause for a `y/n` decision. Rejecting tells the model not to blindly retry.
- **Guardrails** — protected paths (`.env`, `.git`, keys, `*.log`), path-escape checks, blocked dangerous shell patterns, and a cap on model calls per turn.
- **Audit log** — every tool call is appended as JSON to `<work dir>/.agent_audit.log`.
- **Structured turn summary** — after each turn the agent returns a `TurnSummary` (`summary`, `files_touched`, `status`).
- **Multiple providers** — OpenAI, OpenRouter or Groq, picked automatically from whichever API key is set.
- **Editable prompts** — the system prompt and greeting are Jinja templates in `prompts/`; change agent behavior without touching code.

## Requirements

- Python 3.13 (the version this was developed on)
- `bash` on your `PATH` — needed by `run_command`. On Windows use Git Bash or WSL.
- An API key for at least one supported provider

The repo has no `requirements.txt` or `pyproject.toml` yet. From the imports, the dependencies are:

| Package | Used for |
| --- | --- |
| `langchain` (1.x agent + middleware API) | `create_agent`, middleware, tools |
| `langgraph` | checkpointing, human-in-the-loop resume |
| `langchain-openai` | `ChatOpenAI` client (also used for OpenRouter and Groq) |
| `python-dotenv` | loading `.env` |
| `jinja2` | prompt templates |
| `pydantic` | `TurnSummary` schema |

## Setup

```bash
# from the project root
uv venv
# activate: .venv\Scripts\activate (Windows) or source .venv/bin/activate (macOS/Linux)
uv pip install langchain langgraph langchain-openai python-dotenv jinja2 pydantic
```

(Plain `python -m venv .venv` + `pip install ...` works too.)

Create a `.env` file in the project root with at least one key:

```env
OPENAI_API_KEY=sk-...
# or
OPENROUTER_API_KEY=...
# or
GROQ_API_KEY=...
```

## Run

```bash
python src/main.py
```

Type a request at the `You:` prompt. Type `exit`, `quit`, `stop`, `bye` or `q` to leave.

Things to try:

- `List the files in workspace.`
- `Create greet.js that exports a function greet(name) returning "Hello, name"`
- `Create Hello.java that prints Hello, World`
- `Run the flask app in app.py in the background`

## Configuration

All settings are optional environment variables (put them in `.env`).

| Variable | Default | Description |
| --- | --- | --- |
| `OPENAI_API_KEY` / `OPENROUTER_API_KEY` / `GROQ_API_KEY` | — | Provider credentials. If several are set, the first in that order wins. |
| `WORK_DIR` | `<project>/workspace` | Folder the agent may read, write and run commands in. |
| `HITL_ENABLED` | `true` | Set to `false` (or `0`/`no`) to skip approval prompts. Use with care. |
| `MAX_MODEL_CALLS_PER_RUN` | `10` | Max LLM calls per user turn before the run ends. |

Providers and their default models (see `src/models.py`):

| Provider | Model |
| --- | --- |
| OpenAI | `gpt-4o-mini` |
| OpenRouter | `openai/gpt-4o` |
| Groq | `openai/gpt-oss-20b` |

## How it works

`create_agent` wires the model, tools and prompt together, wrapped in middleware layers (outermost first):

1. **`ModelCallLimitMiddleware`** — stops a runaway loop after `MAX_MODEL_CALLS_PER_RUN` model calls.
2. **`AuditMiddleware`** — records each tool call to `.agent_audit.log`.
3. **`ProtectionMiddleware`** — short-circuits file-tool calls that hit protected paths, escape the working directory, read files over 10 MB, or write payloads containing patterns like `subprocess`, `eval(` or `exec(`.
4. **`HumanInTheLoopMiddleware`** — interrupts before `write_file`, `edit_file` and `run_command`; the CLI asks you to approve or reject.

Read-only tools (`read_file`, `list_files`, `list_jobs`) and `stop_job` run without prompting.

Conversation state is kept per session in LangGraph's in-memory checkpointer, so history is lost when you exit.

## Project layout

```
.
├── prompts/
│   ├── system.jinja        # system prompt (tools list, coding + shell rules)
│   └── greeting.jinja      # banner shown at startup
├── src/
│   ├── main.py             # interactive CLI loop and approval prompts
│   ├── agent.py            # builds the agent and middleware stack
│   ├── runtime.py          # start/resume a turn, parse results, format interrupts
│   ├── models.py           # provider selection and chat-model construction
│   ├── prompts.py          # Jinja rendering for system prompt and greeting
│   ├── messages.py         # helpers for extracting text from message lists
│   ├── config/config.py    # paths and env-driven settings
│   ├── memory/memory.py    # in-memory checkpointer and thread config
│   ├── schemas/schema.py   # TurnSummary model
│   ├── middlewares/        # audit.py, protection.py, hitl.py
│   └── tools/              # read/write/edit/list files, shell, background jobs
└── workspace/              # default working directory (git-ignored, created on first run)
```

## Safety notes

- **`run_command` runs on your machine, not in a container.** A regex blocklist rejects things like `sudo`, `rm -rf`, `mkfs`, `shutdown`, `dd if=` and `curl | sh`, but a blocklist is a best-effort filter, not a security boundary. Keep `HITL_ENABLED=true` and read each command before approving it.
- File tools are confined to the working directory and refuse protected paths. Shell commands are only started *in* that directory; they are not restricted to it.
- Background job logs live in `<work dir>/.agent_jobs/`.
