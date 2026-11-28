# CrewAI Agents Projects

Three hands-on Google Colab notebooks that teach multi-agent workflows with [CrewAI](https://github.com/crewAIInc/crewAI), using Groq-hosted LLMs. Each notebook has a guided walkthrough followed by worked solutions to its "Try it yourself" exercises, with observations on what actually happened.

The same three crews also run in a **Streamlit web app** (`crew_ui/`) with a live "quest map" that shows each agent working, its thinking steps and tool calls, and the final result. See [Web UI](#web-ui-streamlit).

## Notebooks

| # | Notebook | What it builds | Key concepts |
|---|----------|----------------|--------------|
| 1 | `1_research_write_article.ipynb` | Planner → Writer → Editor crew that produces an educational article | Agents (`role`, `goal`, `backstory`), Tasks (`description`, `expected_output`), sequential process, context passing, output guardrail |
| 2 | `2_customer_support.ipynb` | Support agent + QA reviewer answering questions from a local FAQ | Custom `BaseTool`, task guardrails with retries, crew memory (optional demo) |
| 3 | `3_tools_customer_outreach.ipynb` | Researcher + outreach writer drafting a personalized email | Optional Serper web search, custom tools with Pydantic schemas, rule-based sentiment tool, human approval gate |

## Setup

**Requirements:** Google Colab, a free [Groq API key](https://console.groq.com/keys).

1. Open a notebook in Google Colab (upload it, or open it from GitHub).
2. In Colab, go to **Secrets** (key icon) and add:
   - `GROQ_API_KEY` (required, enable notebook access)
   - `SERPER_API_KEY` (optional, only for live web search in Notebook 3, Exercise 3)
3. Run the install cell:
   ```python
   %pip -q install -U "crewai[litellm]" crewai-tools groq
   ```
4. Run the cells top to bottom.

Package versions are intentionally not pinned. After a successful run, freeze your environment (`pip freeze > requirements.txt`) for repeatability.

## Models

Called through LiteLLM via Groq:

- `groq/openai/gpt-oss-120b` for the main agents (notebooks 1 and 2, and the default in 3)
- `groq/openai/gpt-oss-20b` and `groq/qwen/qwen3.8-27b` in Notebook 3 (researcher, and fallback models once the daily quota on the main one is used up)

Model availability on Groq changes. If a model ID fails, list current ones with the `/openai/v1/models` call included in Notebook 3 and update the `LLM(model=...)` lines.

## Notebook details

### 1. Research and write an article
- Three agents with distinct roles run in order: Content Planner, Content Writer, Editorial Reviewer.
- Includes an `editorial_guardrail` (minimum length, Markdown headings). In the main flow it is defined but **not attached** to the task, so the notebook applies it manually to the final output.
- Exercises: new topic, adding a Fact Checker agent, short vs long articles, one agent doing all three jobs.
- Findings: the length instruction (~800 words) was not followed closely (1,582 words returned). With no search tool, any cited references are unverified and may be invented, so output should be treated as a draft.

### 2. Multi-agent customer support
- `CollegeSupportFAQTool` looks up answers in a small local `FAQ` dictionary (matched by key appearing in the question), so no external API is needed.
- A QA agent reviews the support agent's draft; `support_answer_guardrail` validates it and retries up to 2 times.
- Exercises: known vs unknown questions, extending the FAQ, forcing guardrail failure (fail-once and impossible rules), with vs without the QA task.
- Findings: the support agent correctly says when the FAQ has no answer (e.g. refund policy). The QA reviewer was less reliable and sometimes asked for the draft or added unsupported details. Memory needs an explicitly configured embedder because Groq has no embedding model.

### 3. Custom tools for customer outreach
- `SimpleSentimentTool`: transparent keyword-count sentiment, for teaching only.
- `EmailStructureCheckerTool`: checks for greeting, clear purpose and closing.
- Optional `SerperDevTool` for live search; the notebook works without it using a fictional company brief.
- Human-in-the-loop: emails are drafts only. An `APPROVE` gate with an audit log guards a **stub** send function that never actually sends anything.
- Findings: the sentiment tool got 2 of 5 test sentences right. It fails on mixed sentiment, sarcasm and negation.

## Web UI (Streamlit)

`crew_ui/` runs the same three crews in the browser and visualises them as a game-style quest map.

**Features**
- Agent graph: each agent is a node that pulses while working and turns green with a ✓ when done; data packets travel along the edges as work is handed over.
- Live thinking feed: agent start, model reasoning, tool calls (FAQ lookup, sentiment, Serper search) and tool results, streamed from CrewAI's event bus.
- XP bar, levels and achievement badges that update as the crew runs.
- Expandable output of every agent, plus the final result with a Markdown download.
- Options: Fact Checker agent (project 1), QA reviewer with guardrail (project 2), Serper search (project 3), and an optional Deep planning mode where agents write a plan first.
- API keys are read from `.env` and never shown in the interface.

**Run locally (Windows PowerShell)**
```powershell
cd crew_ui
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env      # then add your GROQ_API_KEY to .env
python -m streamlit run app.py
```
Use Python 3.10 to 3.12. On macOS/Linux, activate with `source venv/bin/activate`.
If `pip.exe` or `streamlit.exe` is blocked by a device policy, always call them through `python -m`, as above.

**UI files**

| File | Purpose |
|------|---------|
| `crew_ui/app.py` | Streamlit interface, run loop and result display |
| `crew_ui/crews.py` | Builds the three crews (agents, tasks, tools, guardrail) |
| `crew_ui/events.py` | Forwards CrewAI events (thinking, tool use) to the UI |
| `crew_ui/ui_graph.py` | Renders the animated quest map (HTML/SVG) |
| `crew_ui/requirements.txt` | Dependencies |
| `crew_ui/.env.example` | Template for your keys (copy to `.env`, never commit `.env`) |

### Deploy on Streamlit Community Cloud
1. Push this repo to GitHub and sign in at [share.streamlit.io](https://share.streamlit.io) with GitHub.
2. Click **Create app**, choose this repository and branch `main`, and set **Main file path** to `crew_ui/app.py`.
3. Under **Advanced settings**, select **Python 3.12** and add your secrets:
   ```toml
   GROQ_API_KEY = "your_groq_key"
   # SERPER_API_KEY = "optional"
   ```
4. Click **Deploy**. Later `git push` commits redeploy automatically.

Deployment notes:
- A key stored in Secrets is shared by every visitor and counts against your Groq quota. For a public app, leave it out and let visitors paste their own key in the sidebar, or restrict viewers by email in the app's Share settings.
- Live events use one global queue, so two people running a crew at the same time will see mixed activity. Fine for a demo; it needs per-session routing for real multi-user use.
- CrewAI is a heavy install. If the free tier runs out of memory, deploy to a host with more RAM (e.g. Hugging Face Spaces with Docker or Render).

## Safety notes

- Outreach emails are **drafts only**. Nothing is sent automatically; keep it that way for normal learning use.
- Never store passwords, API keys, payment details or sensitive personal data in agent memory.
- Example companies and people (CampusHelp, Northstar Learning, Aarav Mehta) are fictional. Exercise 3 in Notebook 3 uses a real public organisation purely for search comparison.
- Outputs from agents without search tools are unverified. Check facts before using them.

## Repository structure

```
crew_ai_agents_projects/
├── 1_research_write_article.ipynb
├── 2_customer_support.ipynb
├── 3_tools_customer_outreach.ipynb
├── readme.md
└── crew_ui/
    ├── app.py
    ├── crews.py
    ├── events.py
    ├── ui_graph.py
    ├── requirements.txt
    ├── .env.example
    └── .gitignore
```

## Known limitations

- Notebooks use `google.colab.userdata`, so they run as-is only in Colab. To run locally, replace it with `os.environ["GROQ_API_KEY"]`.
- Groq free-tier rate limits apply. Notebook 1 uses a 60 s cooldown between runs for this reason.
- Notebooks use top-level `await` (`kickoff_async`), which works in Colab/Jupyter but not in plain Python scripts.
- Saved cell outputs make the notebooks large (Notebook 1 is about 2 MB).
- Web UI: thinking steps come from the model's visible replies and CrewAI events. Hidden reasoning from `gpt-oss` is not exposed through CrewAI, so projects without tools (project 1) show fewer steps.
- Web UI: only one crew run at a time is supported per server (see deployment notes).

## Tech stack

Python, CrewAI, crewai-tools, LiteLLM, Groq API, Pydantic, pandas, Streamlit, Google Colab.
