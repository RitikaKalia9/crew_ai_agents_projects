"""Renders the gamified live agent graph as a self-contained HTML page (shown via components.html)."""
import html

GRAPH_H = 640

_ICONS = [("outreach", "📧"), ("quality", "🛡️"), ("fact", "🔎"), ("research", "🔬"),
          ("planner", "🧭"), ("writer", "✍️"), ("editor", "🧐"), ("review", "🧐"), ("support", "🎧")]

_KIND_STYLE = {"tool": ("🔧", "#fbbf24"), "answer": ("💬", "#34d399"),
               "thought": ("🧠", "#a78bfa"), "task": ("✅", "#22d3ee"), "start": ("🚀", "#22d3ee"),
               "result": ("📥", "#fb923c"), "other": ("•", "#94a3b8")}

_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',system-ui,sans-serif;color:#e2e8f0;background:transparent}
.wrap{background:radial-gradient(1200px 500px at 20% -10%,#3b2a7a 0%,transparent 60%),
      linear-gradient(135deg,#0b1026,#1a1446 60%,#0b1026);border:1px solid #3b3a7a;border-radius:18px;padding:18px}
.top{display:flex;justify-content:space-between;align-items:center;gap:14px;flex-wrap:wrap}
.title{font-size:20px;font-weight:800;letter-spacing:.5px}
.lvl{display:flex;align-items:center;gap:10px;min-width:260px}
.lvl b{background:#fbbf24;color:#1a1446;border-radius:8px;padding:3px 9px;font-size:13px}
.bar{flex:1;height:12px;background:#1e1b4b;border-radius:99px;overflow:hidden;border:1px solid #4c4a96}
.bar i{display:block;height:100%;background:linear-gradient(90deg,#22d3ee,#a78bfa,#f472b6);border-radius:99px;transition:width .6s}
.xp{font-size:12px;color:#c7d2fe}
svg{width:100%;height:auto;display:block;margin-top:6px}
.nname{font-size:14px;font-weight:700;fill:#f1f5f9;text-anchor:middle}
.nstat{font-size:12px;text-anchor:middle}
.glowring{transform-box:fill-box;transform-origin:center;animation:pulse 1.4s ease-in-out infinite}
@keyframes pulse{0%,100%{transform:scale(1);opacity:.55}50%{transform:scale(1.28);opacity:.12}}
.flow{stroke-dasharray:8 8;animation:dash 0.7s linear infinite}
@keyframes dash{to{stroke-dashoffset:-16}}
.spin{transform-box:fill-box;transform-origin:center;animation:spin 3s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.bubble{margin-top:6px;background:#17143f;border:1px solid #4c4a96;border-radius:14px;padding:12px 16px;font-size:14px;min-height:52px;position:relative}
.bubble .who{color:#a78bfa;font-weight:700;margin-right:6px}
.dots span{display:inline-block;width:7px;height:7px;margin:0 2px;background:#a78bfa;border-radius:50%;animation:b 1s infinite}
.dots span:nth-child(2){animation-delay:.15s}.dots span:nth-child(3){animation-delay:.3s}
@keyframes b{0%,80%,100%{transform:translateY(0);opacity:.4}40%{transform:translateY(-6px);opacity:1}}
.badges{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}
.badge{font-size:12px;padding:4px 10px;border-radius:99px;border:1px solid #4c4a96;background:#1e1b4b;color:#64748b}
.badge.on{color:#1a1446;background:linear-gradient(90deg,#fde68a,#fbbf24);border-color:#fbbf24;font-weight:700}
.log{margin-top:12px;max-height:190px;overflow:auto;display:flex;flex-direction:column;gap:6px}
.row{font-size:13px;padding:6px 10px;border-left:4px solid;background:#13113a;border-radius:6px;animation:in .35s}
@keyframes in{from{opacity:0;transform:translateX(-10px)}to{opacity:1;transform:none}}
.banner{margin-top:10px;text-align:center;font-weight:800;font-size:16px;padding:10px;border-radius:12px}
.win{background:linear-gradient(90deg,#065f46,#0e7490);color:#ecfeff}
.err{background:#7f1d1d;color:#fee2e2}
"""


def icon_for(role: str) -> str:
    r = role.lower()
    for key, icon in _ICONS:
        if key in r:
            return icon
    return "🤖"


def render_graph(labels, done, status, steps, outputs_words=None, elapsed=0.0):
    """labels: agent role per task. done: tasks finished. status: running|done|error.
    steps: list of (kind, text) tuples."""
    n = len(labels)
    xp = 100 * done + 10 * len(steps)
    level, into = xp // 200 + 1, xp % 200
    W, H, CY, R = 260 * n, 230, 105, 44
    parts = []

    # defs
    parts.append('<defs><filter id="glow" x="-50%" y="-50%" width="200%" height="200%">'
                 '<feGaussianBlur stdDeviation="5" result="b"/><feMerge><feMergeNode in="b"/>'
                 '<feMergeNode in="SourceGraphic"/></feMerge></filter></defs>')

    # edges
    for i in range(n - 1):
        x1, x2 = 130 + i * 260 + R + 6, 130 + (i + 1) * 260 - R - 6
        parts.append(f'<line x1="{x1}" y1="{CY}" x2="{x2}" y2="{CY}" stroke="#312e81" stroke-width="5" stroke-linecap="round"/>')
        if i < done:
            parts.append(f'<line x1="{x1}" y1="{CY}" x2="{x2}" y2="{CY}" stroke="#34d399" stroke-width="5" stroke-linecap="round"/>')
        if i + 1 == done and status == "running":
            parts.append(f'<line class="flow" x1="{x1}" y1="{CY}" x2="{x2}" y2="{CY}" stroke="#22d3ee" stroke-width="5"/>')
            parts.append(f'<circle r="7" fill="#f472b6" filter="url(#glow)"><animateMotion dur="1.2s" repeatCount="indefinite" '
                         f'path="M{x1},{CY} L{x2},{CY}"/></circle>')

    # nodes
    for i, lab in enumerate(labels):
        cx = 130 + i * 260
        if status == "done" or i < done:
            state = "done"
        elif i == done and status == "running":
            state = "active"
        elif i == done and status == "error":
            state = "error"
        else:
            state = "idle"
        color = {"done": "#34d399", "active": "#22d3ee", "error": "#f87171", "idle": "#475569"}[state]
        fill = {"done": "#064e3b", "active": "#0c2a4a", "error": "#450a0a", "idle": "#16143c"}[state]
        text = {"done": "Complete", "active": "Working…", "error": "Failed", "idle": "Waiting"}[state]
        if state == "active":
            parts.append(f'<circle class="glowring" cx="{cx}" cy="{CY}" r="{R + 10}" fill="{color}"/>')
            parts.append(f'<circle class="spin" cx="{cx}" cy="{CY}" r="{R + 6}" fill="none" stroke="{color}" stroke-width="3" stroke-dasharray="14 12"/>')
        glow_attr = ' filter="url(#glow)"' if state in ("active", "done") else ""
        parts.append(f'<circle cx="{cx}" cy="{CY}" r="{R}" fill="{fill}" stroke="{color}" stroke-width="4"{glow_attr}/>')
        parts.append(f'<text x="{cx}" y="{CY + 13}" font-size="38" text-anchor="middle">{icon_for(lab)}</text>')
        if state == "done":
            parts.append(f'<circle cx="{cx + 32}" cy="{CY - 32}" r="13" fill="#34d399"/>'
                         f'<text x="{cx + 32}" y="{CY - 26}" font-size="16" font-weight="700" fill="#022c22" text-anchor="middle">✓</text>')
        parts.append(f'<text class="nname" x="{cx}" y="{CY + R + 28}">{html.escape(lab)}</text>')
        parts.append(f'<text class="nstat" x="{cx}" y="{CY + R + 48}" fill="{color}">{text}</text>')
        parts.append(f'<text x="{cx - 36}" y="{CY - 36}" font-size="12" fill="#94a3b8" text-anchor="middle">#{i + 1}</text>')

    svg = f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">{"".join(parts)}</svg>'

    # thought bubble
    if status == "running":
        who = labels[min(done, n - 1)]
        last = next((t for k, t in reversed(steps) if k in ("thought", "tool", "answer", "result")), None)
        body = (html.escape(last) if last else '<span class="dots"><span></span><span></span><span></span></span>')
        bubble = f'<div class="bubble"><span class="who">{icon_for(who)} {html.escape(who)}:</span>{body}</div>'
    elif status == "done":
        bubble = '<div class="banner win">🏆 QUEST COMPLETE — all agents finished</div>'
    else:
        bubble = '<div class="banner err">💥 The quest failed — see the error below</div>'

    # achievements
    used_tool = any(k == "tool" for k, _ in steps)
    ach = [("⚡ First Blood", done >= 1), ("🔧 Tool Master", used_tool),
           ("🧠 Deep Thinker", len(steps) >= 10), ("🏆 Quest Complete", status == "done")]
    badges = "".join(f'<span class="badge{" on" if on else ""}">{t}</span>' for t, on in ach)

    # log (newest first)
    rows = []
    for kind, text in reversed(steps[-40:][-8:]):
        icon, col = _KIND_STYLE.get(kind, _KIND_STYLE["other"])
        rows.append(f'<div class="row" style="border-color:{col}">{icon} {html.escape(text)}</div>')
    log = f'<div class="log">{"".join(rows)}</div>' if rows else ""

    return (f"<style>{_CSS}</style><div class='wrap'>"
            f"<div class='top'><div class='title'>🗺️ Agent Quest Map</div>"
            f"<div class='lvl'><b>LVL {level}</b><div class='bar'><i style='width:{into / 2:.0f}%'></i></div>"
            f"<span class='xp'>{xp} XP</span></div></div>"
            f"{svg}{bubble}<div class='badges'>{badges}</div>{log}</div>")