# CrewAI Agents Projects

Three hands-on Google Colab notebooks that teach multi-agent workflows with [CrewAI](https://github.com/crewAIInc/crewAI), using Groq-hosted LLMs. Each notebook has a guided walkthrough followed by worked solutions to its "Try it yourself" exercises, with observations on what actually happened.

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

## Safety notes

- Outreach emails are **drafts only**. Nothing is sent automatically; keep it that way for classroom use.
- Never store passwords, API keys, payment details or sensitive personal data in agent memory.
- Example companies and people (CampusHelp, Northstar Learning, Aarav Mehta) are fictional. Exercise 3 in Notebook 3 uses a real public organisation purely for search comparison.
- Outputs from agents without search tools are unverified. Check facts before using them.

## Repository structure

```
crew_ai_agents_projects/
├── 1_research_write_article.ipynb
├── 2_customer_support.ipynb
├── 3_tools_customer_outreach.ipynb
└── README.md
```

## Known limitations

- Notebooks use `google.colab.userdata`, so they run as-is only in Colab. To run locally, replace it with `os.environ["GROQ_API_KEY"]`.
- Groq free-tier rate limits apply. Notebook 1 uses a 60 s cooldown between runs for this reason.
- Notebooks use top-level `await` (`kickoff_async`), which works in Colab/Jupyter but not in plain Python scripts.
- Saved cell outputs make the notebooks large (Notebook 1 is about 2 MB).

## Tech stack

Python, CrewAI, crewai-tools, LiteLLM, Groq API, Pydantic, pandas, Google Colab.
