import os
import queue
import threading
import time

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

import crews
import events
from crews import make_llm, build_article_crew, build_support_crew, build_outreach_crew
from ui_graph import render_graph, GRAPH_H

load_dotenv()
events.register()
st.set_page_config(page_title="CrewAI Agent Quest", page_icon="🗺️", layout="wide")
st.markdown("<h1 style='margin-bottom:0'>🗺️ CrewAI Agent Quest</h1>", unsafe_allow_html=True)
st.caption("Launch a crew and watch every agent think, use tools and hand off work in real time.")

# ------------------------------------------------------------------ sidebar (keys are never pre-filled)
env_groq = os.getenv("GROQ_API_KEY", "").strip()
env_serper = os.getenv("SERPER_API_KEY", "").strip()
with st.sidebar:
    st.header("⚙️ Settings")
    if env_groq:
        st.success("Groq key loaded from .env")
    typed_groq = st.text_input("Groq key" + (" (override, optional)" if env_groq else ""), value="", type="password")
    if env_serper:
        st.success("Serper key loaded from .env")
    typed_serper = st.text_input("Serper key (optional)" + (" (override)" if env_serper else ""), value="", type="password")
    groq_key = typed_groq.strip() or env_groq
    serper_key = typed_serper.strip() or env_serper
    main_model = st.text_input("Main model", "groq/openai/gpt-oss-120b")
    research_model = st.text_input("Research model (project 3)", "groq/openai/gpt-oss-20b")
    deep = st.checkbox("🧠 Deep planning mode", value=False,
                       help="Agents write a plan before acting. Shows richer thinking but uses more tokens / rate limit.")
    st.divider()
    project = st.radio("Quest", ["1. Research & write article", "2. Customer support", "3. Customer outreach"])

# ------------------------------------------------------------------ inputs per project
inputs, opts = {}, {}
if project.startswith("1"):
    inputs["topic"] = st.text_input("Topic", "Agentic AI in higher education")
    c1, c2 = st.columns(2)
    opts["words"] = c1.selectbox("Target length (words)", ["300-400", "700-900", "1,200-1,500"], index=1)
    opts["fact_check"] = c2.checkbox("Add Fact Checker agent", value=False)
elif project.startswith("2"):
    inputs["customer"] = st.text_input("Customer", "CampusHelp (fictional customer)")
    inputs["person"] = st.text_input("Contact person", "Aarav")
    inputs["inquiry"] = st.text_area("Question", "How can I enable memory for a CrewAI crew, and what should I consider?")
    opts["use_qa"] = st.checkbox("Include QA reviewer (with guardrail)", value=True)
else:
    c1, c2 = st.columns(2)
    inputs["lead_name"] = c1.text_input("Lead organisation", "Northstar Learning Pvt Ltd")
    inputs["industry"] = c2.text_input("Industry", "Online education")
    inputs["contact_name"] = c1.text_input("Contact name", "Aarav Mehta")
    inputs["contact_role"] = c2.text_input("Contact role (supplied)", "Partnerships Manager")
    inputs["context"] = st.text_area("Context", "The organisation is exploring ways to improve learner engagement. "
                                     "This is a fictional scenario, not a verified milestone.")
    st.info("Draft only. Nothing is ever sent.")

run = st.button("⚔️ Start quest", type="primary", use_container_width=True)


# ------------------------------------------------------------------ helpers
def classify_step(s):
    """Turn a CrewAI step object into (kind, short text). Field names differ across versions."""
    tool = getattr(s, "tool", None)
    if tool:
        return "tool", f"Using tool “{tool}” — {str(getattr(s, 'tool_input', ''))[:120]}"
    out = getattr(s, "output", None)
    if out:
        return "answer", f"Drafted an answer: {str(out)[:180]}…"
    thought = getattr(s, "thought", None)
    if thought:
        return "thought", str(thought)[:180]
    return "other", str(s)[:150]


def draw(slot, labels, done, status, steps):
    with slot:
        components.html(render_graph(labels, done, status, steps), height=GRAPH_H, scrolling=False)


# ------------------------------------------------------------------ run
if run:
    if not groq_key:
        st.error("Add your Groq key in .env or in the sidebar.")
        st.stop()

    q: queue.Queue = queue.Queue()
    events.set_queue(q)          # thinking / tool events now stream into this run's queue
    crews.REASONING = deep
    step_cb = None               # CrewAI events (events.py) replace the old step callback
    task_cb = lambda t: q.put(("task", t))

    llm = make_llm(groq_key, main_model)
    if project.startswith("1"):
        crew, labels = build_article_crew(llm, opts["words"], opts["fact_check"], step_cb, task_cb)
    elif project.startswith("2"):
        crew, labels = build_support_crew(llm, opts["use_qa"], step_cb, task_cb)
    else:
        crew, labels = build_outreach_crew(llm, make_llm(groq_key, research_model), serper_key or None, step_cb, task_cb)

    def worker():
        try:
            q.put(("done", crew.kickoff(inputs=inputs)))
        except Exception as e:
            q.put(("error", f"{type(e).__name__}: {e}"))

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    start = time.time()

    graph_slot = st.empty()
    timer_slot = st.empty()
    steps, outputs, done_count, final, error = [], [], 0, None, None
    draw(graph_slot, labels, 0, "running", steps)

    while True:
        try:
            kind, payload = q.get(timeout=0.4)
        except queue.Empty:
            timer_slot.caption(f"⏱ {time.time() - start:.0f}s elapsed")
            if not t.is_alive() and q.empty():
                break
            continue

        if kind == "step":
            steps.append(payload)
            draw(graph_slot, labels, done_count, "running", steps)
        elif kind == "task":
            role = str(getattr(payload, "agent", None) or labels[min(done_count, len(labels) - 1)]).strip()
            outputs.append((role, payload.raw))
            done_count += 1
            steps.append(("task", f"{role} completed their task"))
            draw(graph_slot, labels, done_count, "running", steps)
        elif kind == "done":
            final = payload
            break
        elif kind == "error":
            error = payload
            break

    # keep results across reruns (e.g. clicking the download button)
    st.session_state["res"] = dict(
        project=project, labels=labels, steps=steps, outputs=outputs, done=done_count,
        status="error" if error else "done", error=error,
        final=final.raw if final else None, seconds=time.time() - start)
    st.rerun()

# ------------------------------------------------------------------ show last result
res = st.session_state.get("res")
if res:
    st.divider()
    st.subheader(f"Last quest: {res['project']}  ·  ⏱ {res['seconds']:.0f}s")
    components.html(render_graph(res["labels"], res["done"], res["status"], res["steps"]),
                    height=GRAPH_H, scrolling=False)

    if res["error"]:
        st.error(res["error"])
        st.caption("Groq free-tier limits are per model and per minute. Wait a minute or change the model in the sidebar.")
    if res["outputs"]:
        st.subheader("🧾 What each agent produced")
        for i, (role, text) in enumerate(res["outputs"], 1):
            with st.expander(f"{i}. {role}"):
                st.markdown(text)
    if res["final"]:
        st.subheader("🏆 Final result")
        st.markdown(res["final"])
        st.download_button("⬇ Download as .md", res["final"], file_name="result.md")
        if res["project"].startswith("1"):
            st.caption(f"{len(res['final'].split())} words · no search tool was used, so references are unverified.")