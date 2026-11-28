"""Crew builders for the three projects. Each returns (crew, [agent role per task])."""
import re
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


REASONING = False  # set by the UI: agents plan before acting (extra LLM calls)


def make_llm(api_key: str, model: str = "groq/openai/gpt-oss-120b") -> LLM:
    return LLM(model=model, api_key=api_key, temperature=0.2)


def _agent(role, goal, backstory, llm, tools=None, max_iter=5):
    extra = {"reasoning": True, "max_reasoning_attempts": 2} if REASONING else {}
    return Agent(role=role, goal=goal, backstory=backstory, llm=llm,
                 tools=tools or [], allow_delegation=False, verbose=False, max_iter=max_iter, **extra)


def _crew(agents, tasks, step_cb, task_cb):
    return Crew(agents=agents, tasks=tasks, process=Process.sequential,
                step_callback=step_cb, task_callback=task_cb, verbose=False)


# ---------------------------------------------------------------- 1. Article
def build_article_crew(llm, words, fact_check, step_cb, task_cb):
    planner = _agent("Content Planner",
        "Create a useful, balanced and evidence-aware plan about {topic}",
        "You are an experienced content strategist. You identify the audience, key questions, "
        "themes and evidence needed for a clear educational article. Do not invent sources.", llm)
    writer = _agent("Content Writer",
        "Write a clear, engaging article using the approved content plan",
        "You are a technical writer. You distinguish established facts from interpretation "
        "and do not introduce unsupported claims.", llm)
    editor = _agent("Editorial Reviewer",
        "Improve clarity, structure, consistency and factual caution",
        "You are a careful editor. You remove repetition, flag unsupported claims "
        "and preserve the intended meaning.", llm)

    plan = Task(description=("Prepare a content plan for an educational article on {topic}. Identify the "
                  "audience, 4-6 key sections, important terms, questions to answer and claims that "
                  "require verification. Do not claim to have searched the web."),
                expected_output="A structured content plan with audience, outline, key points, terms and claims to verify.",
                agent=planner)
    write = Task(description=("Using the content plan, write an educational article on {topic}. Explain "
                  "technical terms, use meaningful headings, and separate facts from opinions."),
                 expected_output=f"A well-structured Markdown article of approximately {words} words.",
                 agent=writer, markdown=True)
    agents, tasks = [planner, writer], [plan, write]

    if fact_check:
        fc = _agent("Fact Checker",
            "Identify claims in the draft that need verification and rate how well supported they are",
            "You have no web access, so you never claim to have verified anything online. You flag "
            "statistics, dates, named studies and strong claims, and rate each honestly.", llm)
        tasks.append(Task(description="Review the draft article on {topic}. List risky claims and rate each (supported / needs source / doubtful).",
                          expected_output="A fact-check report listing flagged claims with ratings.", agent=fc))
        agents.append(fc)

    edit = Task(description=("Edit the article for clarity, flow, grammar and consistency. Do not add facts. "
                 "End with a short 'Editorial Note' listing claims that need independent verification."),
                expected_output="The final polished Markdown article with an Editorial Note.",
                agent=editor, markdown=True)
    agents.append(editor); tasks.append(edit)
    return _crew(agents, tasks, step_cb, task_cb), [t.agent.role for t in tasks]


# ---------------------------------------------------------------- 2. Support
FAQ = {
    "memory": "CrewAI memory can be enabled at the crew level. It may retain information across task executions "
              "depending on the configured storage and embedding provider. Configure the provider explicitly for production.",
    "sequential": "A sequential crew executes tasks in the order they are listed. The output of earlier tasks can be passed as context to later tasks.",
    "tools": "Tools are callable capabilities that let an agent interact with external systems or do more than generate text.",
    "guardrail": "A guardrail is a validation function attached to a task. If it returns (False, reason), CrewAI sends the reason "
                 "back to the agent to retry, up to guardrail_max_retries times.",
    "delegation": "Delegation lets an agent hand part of its work to another agent. It is controlled by allow_delegation on the agent.",
}


class FAQInput(BaseModel):
    query: str = Field(..., description="The topic or question to look up in the FAQ.")


class SupportFAQTool(BaseTool):
    name: str = "Approved Support FAQ"
    description: str = "Search a small approved FAQ about CrewAI concepts. Use it before answering."
    args_schema: type[BaseModel] = FAQInput

    def _run(self, query: str) -> str:
        q = query.lower()
        hits = [v for k, v in FAQ.items() if k in q]
        return "\n".join(hits) if hits else ("No matching FAQ entry was found. State that the local "
                                             "knowledge base does not contain this information.")


def support_guardrail(output):
    text = output.raw.strip()
    if len(text) < 40:
        return (False, "The answer is too brief. Answer in complete sentences.")
    if "invent" in text.lower():
        return (False, "Rewrite the answer without unsupported assumptions.")
    return (True, text)


def build_support_crew(llm, use_qa, step_cb, task_cb):
    support = _agent("Customer Support Specialist",
        "Answer the customer's question accurately using the approved FAQ",
        "You are a patient support specialist. Use the approved FAQ tool. If the answer is not in "
        "the FAQ, say so clearly and suggest consulting official documentation.", llm, tools=[SupportFAQTool()])
    t1 = Task(description=("Customer: {customer}\nContact: {person}\nQuestion: {inquiry}\n\n"
              "Use the Approved Support FAQ tool. Answer only what is supported. "
              "If the FAQ does not contain the answer, say what is missing."),
              expected_output="A concise, friendly answer with a note about the source or limitation.", agent=support)
    agents, tasks = [support], [t1]
    if use_qa:
        qa = _agent("Support Quality Reviewer",
            "Check that the proposed answer is accurate, complete and transparent",
            "You review support answers. You remove unsupported claims and make sure uncertainty is stated.", llm, max_iter=4)
        tasks.append(Task(description=("Review the draft response for {customer}. Confirm it answers the question, "
                          "uses only the FAQ information, and states any limitation. Return the corrected final answer."),
                          expected_output="A final customer-ready answer with unsupported claims removed.",
                          agent=qa, guardrail=support_guardrail, guardrail_max_retries=2))
        agents.append(qa)
    return _crew(agents, tasks, step_cb, task_cb), [t.agent.role for t in tasks]


# ---------------------------------------------------------------- 3. Outreach
class SentimentInput(BaseModel):
    text: str = Field(..., description="Text whose sentiment should be estimated.")


class SimpleSentimentTool(BaseTool):
    name: str = "Simple Rule-Based Sentiment"
    description: str = "Estimate sentiment with a small keyword list. A demo, not a production model."
    args_schema: type[BaseModel] = SentimentInput

    def _run(self, text: str) -> str:
        pos = {"good", "great", "excellent", "helpful", "success", "interested", "pleased", "improved", "benefit", "love"}
        neg = {"bad", "poor", "issue", "problem", "delay", "disappointed", "difficult", "failed", "hate", "complaint"}
        tokens = set(re.findall(r"[a-z']+", text.lower()))
        p, n = len(tokens & pos), len(tokens & neg)
        label = "positive" if p > n else "negative" if n > p else "neutral"
        return f"Estimated sentiment: {label}. Positive matches: {p}; negative matches: {n}. Rule-based estimate; may miss context or sarcasm."


def build_outreach_crew(llm, researcher_llm, serper_key, step_cb, task_cb):
    tools = []
    if serper_key:
        import os
        from crewai_tools import SerperDevTool
        os.environ["SERPER_API_KEY"] = serper_key
        tools = [SerperDevTool(n_results=3)]

    researcher = _agent("Organisation Research Analyst",
        "Prepare a concise, evidence-aware profile of {lead_name}",
        "You research organisations using only the tools you were explicitly given. If you have no tools, "
        "use ONLY the supplied inputs and state that independent verification was not performed. Separate "
        "verified facts from assumptions, include source links when search is used. Use at most 2 searches.",
        researcher_llm, tools=tools, max_iter=6)
    writer = _agent("Customer Outreach Writer",
        "Create a relevant, respectful and personalized outreach email draft",
        "You write professional outreach. Use only facts in the research brief or supplied inputs. "
        "Do not invent personal details, relationships, product claims or milestones.",
        llm, tools=[SimpleSentimentTool()])

    profile = Task(description=("Prepare a profile of {lead_name}, operating in {industry}. Use web search if available; "
                   "otherwise rely only on the supplied brief and say verification was not performed. "
                   "Do not infer who the decision-maker is."),
                   expected_output="A short profile: verified facts, source URLs if any, possible needs, and a list of unknowns.",
                   agent=researcher)
    outreach = Task(description=("Using the profile of {lead_name}, draft an outreach email to {contact_name}, whose supplied "
                    "role is {contact_role}. Context: {context}. Do not add unsupported facts. Use the sentiment tool "
                    "to review tone. Return a subject line and email body only."),
                    expected_output="One concise, personalized email draft with a subject line and body.",
                    agent=writer, markdown=True)
    return _crew([researcher, writer], [profile, outreach], step_cb, task_cb), [researcher.role, writer.role]