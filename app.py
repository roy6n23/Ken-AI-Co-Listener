import gradio as gr
import json
from pipeline import run_pipeline

def format_card_html(card: dict) -> str:
    trigger = card["trigger"]
    labels = {"jargon": "Jargon", "impact": "Impact", "question": "Ask This", "commitment": "Tracked"}
    badge_colors = {"jargon": "#d97706", "impact": "#e11d48", "question": "#10b981", "commitment": "#3b82f6"}

    label = labels.get(trigger, "Info")
    color = badge_colors.get(trigger, "#666")
    ts = card["timestamp"]
    mins, secs = int(ts // 60), int(ts % 60)
    data = card.get("data", {})

    title, content = "", ""
    if trigger == "jargon":
        for item in data.get("cards", []):
            title = item.get("title", "")
            content += f"<div style='margin-bottom:8px;'>{item.get('summary', '')}</div>"
    elif trigger == "impact":
        impact = data.get("impact", {})
        if impact:
            title = impact.get("title", "")
            content = f"<div>{impact.get('summary', '')}</div>"
    elif trigger == "question":
        q = data.get("question", {})
        if q:
            title = q.get("title", "")
            content = f"<div style='font-style:italic;margin-bottom:8px;'>\"{q.get('suggested_question', '')}\"</div>"
    elif trigger == "commitment":
        items = data.get("commitments", [])
        if items: title = items[0].get("title", "")
        for item in items:
            content += f"<div style='margin-bottom:6px;'>{item.get('summary', '')}</div>"

    return f"""<div class="lexis-card" data-timestamp="{ts}" data-trigger="{trigger}" style="display:none;">
        <div style="display:flex;justify-content:space-between;margin-bottom:10px;">
            <span style="background:{color};color:white;padding:2px 8px;border-radius:6px;font-size:0.75rem;font-weight:600;">{label}</span>
            <span style="font-family:monospace;color:#666;font-size:0.85rem;">{mins}:{secs:02d}</span>
        </div>
        <div style="font-weight:600;margin-bottom:8px;">{title}</div>
        <div style="color:#666;line-height:1.6;">{content}</div>
    </div>"""

def build_cards_html(cards):
    total = len(cards)
    counts = {t: sum(1 for c in cards if c["trigger"] == t) for t in ["jargon", "impact", "question", "commitment"]}
    cards_html = "\n".join(format_card_html(c) for c in cards)

    return f"""<div id="cards-wrapper">
        <div style="display:flex;justify-content:space-between;margin-bottom:16px;">
            <h3 style="margin:0;">Insights</h3>
            <span id="card-count" style="font-family:monospace;">(0/{total})</span>
        </div>
        <div id="filters" style="display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap;">
            <button class="filter-btn active" data-filter="all">All ({total})</button>
            <button class="filter-btn active" data-filter="jargon">Jargon ({counts['jargon']})</button>
            <button class="filter-btn active" data-filter="impact">Impact ({counts['impact']})</button>
            <button class="filter-btn active" data-filter="question">Questions ({counts['question']})</button>
            <button class="filter-btn active" data-filter="commitment">Tracked ({counts['commitment']})</button>
        </div>
        <div id="cards-container" style="max-height:550px;overflow-y:auto;">{cards_html}</div>
    </div>"""

SYNC_JS = """<script>
(function(){
let filters = new Set(['jargon','impact','question','commitment']);
let lastTime = -1;
document.addEventListener('click', e => {
    const btn = e.target.closest('.filter-btn');
    if(!btn) return;
    const f = btn.dataset.filter;
    if(f==='all') filters = filters.size===4 ? new Set() : new Set(['jargon','impact','question','commitment']);
    else filters.has(f) ? filters.delete(f) : filters.add(f);
    document.querySelectorAll('.filter-btn').forEach(b => {
        if(b.dataset.filter==='all') b.classList.toggle('active', filters.size===4);
        else b.classList.toggle('active', filters.has(b.dataset.filter));
    });
    lastTime = -1;
});
function tick(){
    const cards = document.querySelectorAll('.lexis-card');
    if(!cards.length) return;
    const video = document.querySelector('video');
    if(!video) return;
    const t = video.currentTime;
    if(t === lastTime) return;
    lastTime = t;
    let shown = 0;
    cards.forEach(card => {
        const ts = parseFloat(card.dataset.timestamp);
        const trigger = card.dataset.trigger;
        if(t >= ts && filters.has(trigger)){
            card.style.display = 'block';
            shown++;
        } else {
            card.style.display = 'none';
        }
    });
    const countEl = document.getElementById('card-count');
    if(countEl) countEl.textContent = `(${shown}/${cards.length})`;
}
setInterval(tick, 250);
})();
</script>
<style>
.filter-btn { padding:6px 14px; border-radius:20px; border:1px solid #e2e8f0; background:white;
    color:#666; font-size:0.875rem; cursor:pointer; transition:all 0.2s; }
.filter-btn:hover { background:#f5f5f5; border-color:#999; }
.filter-btn.active { background:#1a1a1a; color:white; border-color:#1a1a1a; }
.lexis-card { background:white; padding:16px; margin-bottom:12px; border-radius:12px;
    box-shadow:0 1px 3px rgba(0,0,0,0.1); border-left:3px solid #3a4a32; }
</style>"""

def process_media(media, text, cat):
    if not media: return None, "<p style='color:red;'>Upload a video first.</p>", "{}"
    profile = {
        "name": "User",
        "situation": f"{cat}: {text}" if text else f"{cat} consultation",
        "knowledge_level": "intermediate",
        "concerns": [text] if text else []
    }
    result = run_pipeline(media, profile)
    return media, build_cards_html(result["cards"]), json.dumps(result, indent=2)

CSS = """
:root {
    --bg: #f4ece0;
    --bg-card: #fffdf8;
    --ink: #1f1812;
    --ink-2: #524539;
    --ink-3: #93836f;
    --line: #ebe0cc;
    --accent: #3a4a32;
    --radius: 22px;
}
.gradio-container { background: var(--bg) !important; font-family: 'Inter', sans-serif !important; }
footer { display: none !important; }

/* Paper grain */
body::before {
    content: ""; position: fixed; inset: 0; pointer-events: none;
    background-image: radial-gradient(rgba(26,24,20,0.025) 1px, transparent 1px);
    background-size: 3px 3px; z-index: 0; mix-blend-mode: multiply;
}

/* Topbar */
.topbar { display: flex !important; justify-content: space-between !important; align-items: center !important;
    padding: 22px 32px !important; position: relative !important; z-index: 5 !important; }
.brand { font-family: 'Instrument Serif', serif !important; font-size: 22px !important; color: var(--ink) !important;
    display: inline-flex !important; align-items: center !important; gap: 8px !important; }
.brand::before { content: ""; width: 8px; height: 8px; border-radius: 50%; background: var(--accent); }

/* Stage */
.stage { min-height: calc(100vh - 80px) !important; display: flex !important; flex-direction: column !important;
    align-items: center !important; padding: 6vh 24px 60px !important; position: relative !important; z-index: 1 !important; }

/* Hero */
.hero { text-align: center !important; margin-bottom: 38px !important; max-width: 720px !important; }
.wordmark { font-family: 'Instrument Serif', serif !important; font-weight: 400 !important; font-style: italic !important;
    font-size: clamp(64px, 11vw, 112px) !important; line-height: 0.95 !important; letter-spacing: -0.02em !important;
    margin: 0 !important; color: var(--ink) !important; }
.tagline { font-size: 18px !important; line-height: 1.5 !important; color: var(--ink-2) !important;
    margin-top: 18px !important; max-width: 560px !important; margin-left: auto !important; margin-right: auto !important; }

/* Profile chips */
.chips { display: flex !important; flex-wrap: wrap !important; justify-content: center !important; gap: 8px !important;
    max-width: 720px !important; margin: 0 auto 14px !important; }
.chips button { padding: 9px 16px !important; background: rgba(255,255,255,0.55) !important; border: 1px solid var(--line) !important;
    border-radius: 999px !important; font-size: 13.5px !important; font-weight: 500 !important; color: var(--ink-2) !important;
    cursor: pointer !important; transition: all 0.18s cubic-bezier(.2,.8,.2,1) !important; backdrop-filter: blur(6px) !important; }
.chips button:hover { background: #fff !important; border-color: #c3b5a0 !important; color: var(--ink) !important;
    transform: translateY(-1px) !important; }
.chips button.selected { background: var(--ink) !important; color: #f7f4ec !important; border-color: var(--ink) !important;
    box-shadow: 0 6px 18px -10px rgba(0,0,0,.5) !important; }

/* Input card */
.input-card { background: var(--bg-card) !important; border: 1px solid var(--line) !important;
    border-radius: var(--radius) !important; box-shadow: 0 1px 0 rgba(26,24,20,0.04), 0 18px 40px -22px rgba(26,24,20,0.18) !important;
    padding: 22px !important; max-width: 720px !important; margin: 0 auto !important; }
.input-card textarea { border: none !important; background: transparent !important; font-size: 16px !important;
    line-height: 1.55 !important; color: var(--ink) !important; padding: 4px !important; resize: none !important; }
.input-card textarea::placeholder { color: #c3b5a0 !important; }

/* Action buttons */
.actions { display: flex !important; justify-content: space-between !important; align-items: center !important;
    padding-top: 10px !important; margin-top: 6px !important; border-top: 1px solid var(--line) !important; }
.iconbtn { width: 38px !important; height: 38px !important; background: #fff !important; border: 1px solid var(--line) !important;
    border-radius: 12px !important; color: var(--ink-2) !important; display: inline-flex !important;
    align-items: center !important; justify-content: center !important; cursor: pointer !important; }
.iconbtn:hover { border-color: var(--ink-3) !important; color: var(--ink) !important; background: #fefdfa !important; }
.submitbtn { height: 38px !important; padding: 0 18px !important; background: var(--ink) !important; color: #f7f4ec !important;
    border: none !important; border-radius: 999px !important; font-size: 13.5px !important; font-weight: 500 !important;
    cursor: pointer !important; margin-left: 4px !important; }
.submitbtn:hover { background: #000 !important; }

/* Footer */
.foot { margin-top: 64px !important; text-align: center !important; color: var(--ink-3) !important;
    font-size: 13.5px !important; max-width: 540px !important; line-height: 1.7 !important; }

/* Hide labels */
.stage label { display: none !important; }
"""

with gr.Blocks(title="Lexis", css=CSS, head=SYNC_JS) as app:

    # Onboarding page
    with gr.Column(visible=True, elem_classes=["stage"]) as onboarding:
        gr.HTML('<div class="topbar"><div class="brand">Lexis</div><a href="#" style="font-size:13px;color:#524539;text-decoration:none;">Sign in</a></div>')

        gr.HTML('''<div class="hero">
            <h1 class="wordmark">Lexis<span style="color:#3a4a32;">.</span></h1>
            <p class="tagline">Tell us a little about your situation.<br/>
            We'll listen along and surface what <em style="font-family:'Instrument Serif',serif;font-size:1.12em;">actually</em> matters — in real time.</p>
        </div>''')

        with gr.Row(elem_classes=["chips"]):
            legal_btn = gr.Button("§ Legal", elem_classes=["selected"])
            medical_btn = gr.Button("℞ Medical")
            immigration_btn = gr.Button("✦ Immigration")
            career_btn = gr.Button("¶ Career")
            add_btn = gr.Button("+", elem_classes=["chip-add"])

        with gr.Column(elem_classes=["input-card"]):
            profile_input = gr.Textbox(
                placeholder="Tell me about the case. Counterparty, the contract you're reviewing, what's at stake…",
                lines=3, show_label=False, container=False
            )

            with gr.Row(elem_classes=["actions"]):
                gr.HTML('<div style="font-family:monospace;font-size:11px;color:#93836f;">⌘ ↵ to begin</div>')
                voice_btn = gr.Button("🎤", elem_classes=["iconbtn"], scale=0)
                file_btn = gr.Button("📎", elem_classes=["iconbtn"], scale=0)
                continue_btn = gr.Button("Begin →", elem_classes=["submitbtn"], scale=0)

        gr.HTML('<div class="foot">Don\'t take the shortcut. Lexis doesn\'t summarize.<br/>We show you where to look instead.</div>')

        profile_cat = gr.State("Legal")
        voice_input = gr.Audio(sources=["microphone"], type="filepath", visible=False)
        file_input = gr.File(visible=False)

    # Main page
    with gr.Column(visible=False) as main_page:
        gr.Markdown("## Lexis — Co-Listening Session")
        with gr.Accordion("Upload", open=True):
            with gr.Row():
                media_input = gr.Video(label="Upload Video")
                with gr.Column():
                    profile_display = gr.Textbox(label="Profile", interactive=False, lines=2)
                    process_btn = gr.Button("Process", variant="primary")
                    back_btn = gr.Button("← Back", variant="secondary")

        with gr.Row():
            video_output = gr.Video(label="Playback")
            output_html = gr.HTML()

        with gr.Accordion("Debug", open=False):
            output_json = gr.Code(language="json")

    profile_state = gr.State("")

    # Chip selection
    def sel_legal(): return "Legal", gr.Button(elem_classes=["selected"]), gr.Button(), gr.Button(), gr.Button()
    def sel_medical(): return "Medical", gr.Button(), gr.Button(elem_classes=["selected"]), gr.Button(), gr.Button()
    def sel_immigration(): return "Immigration", gr.Button(), gr.Button(), gr.Button(elem_classes=["selected"]), gr.Button()
    def sel_career(): return "Career", gr.Button(), gr.Button(), gr.Button(), gr.Button(elem_classes=["selected"])

    legal_btn.click(sel_legal, outputs=[profile_cat, legal_btn, medical_btn, immigration_btn, career_btn])
    medical_btn.click(sel_medical, outputs=[profile_cat, legal_btn, medical_btn, immigration_btn, career_btn])
    immigration_btn.click(sel_immigration, outputs=[profile_cat, legal_btn, medical_btn, immigration_btn, career_btn])
    career_btn.click(sel_career, outputs=[profile_cat, legal_btn, medical_btn, immigration_btn, career_btn])

    # Voice
    def on_voice(audio):
        if not audio: return ""
        try:
            from faster_whisper import WhisperModel
            model = WhisperModel("base", device="cpu", compute_type="int8")
            segments, _ = model.transcribe(audio, beam_size=3, language="en")
            return " ".join(seg.text.strip() for seg in segments)
        except: return ""

    voice_btn.click(lambda: gr.Audio(visible=True), outputs=[voice_input])
    voice_input.change(on_voice, inputs=[voice_input], outputs=[profile_input])

    file_btn.click(lambda: gr.File(visible=True), outputs=[file_input])

    # Navigation
    def on_proceed(text, cat):
        full = f"{cat}: {text}" if text else f"{cat} consultation"
        return gr.Column(visible=False), gr.Column(visible=True), full, full

    continue_btn.click(on_proceed, inputs=[profile_input, profile_cat],
                      outputs=[onboarding, main_page, profile_state, profile_display])

    back_btn.click(lambda: (gr.Column(visible=True), gr.Column(visible=False)),
                  outputs=[onboarding, main_page])

    process_btn.click(process_media, inputs=[media_input, profile_state, profile_cat],
                     outputs=[video_output, output_html, output_json])

if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=7860, share=True)
