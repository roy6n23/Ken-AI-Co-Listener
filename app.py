import gradio as gr
import json
import os
import tempfile
from pathlib import Path
from pipeline import run_pipeline
from profiles import PROFILES

CARD_COLORS = {
    "jargon": ("#FEF3C7", "#D97706", "Jargon"),
    "impact": ("#FEE2E2", "#DC2626", "Impact Alert"),
    "question": ("#D1FAE5", "#059669", "Ask This"),
    "commitment": ("#DBEAFE", "#2563EB", "Commitment"),
}


def format_card_html(card: dict) -> str:
    trigger = card["trigger"]
    label_map = {"jargon": "Jargon", "impact": "Impact", "question": "Ask This", "commitment": "Tracked"}
    badge_class_map = {"jargon": "amber", "impact": "rose", "question": "emerald", "commitment": "blue"}

    label = label_map.get(trigger, "Info")
    badge_class = badge_class_map.get(trigger, "blue")
    timestamp = card["timestamp"]
    minutes = int(timestamp // 60)
    seconds = int(timestamp % 60)

    data = card.get("data", {})
    title = ""
    content_html = ""

    if trigger == "jargon":
        for item in data.get("cards", []):
            title = item.get("title", item.get("term", ""))
            summary = item.get("summary", item.get("definition", ""))
            detail = item.get("detail", item.get("relevance", ""))
            content_html += f"""
            <div class="lexis-card-summary">{summary}</div>
            <div class="lexis-card-detail">{detail}</div>"""
    elif trigger == "impact":
        impact = data.get("impact", {})
        if impact:
            title = impact.get("title", "")
            summary = impact.get("summary", impact.get("what", ""))
            detail = impact.get("detail", impact.get("how_it_affects_you", ""))
            action = impact.get("action", impact.get("suggested_action", ""))
            content_html = f"""
            <div class="lexis-card-summary">{summary}</div>
            <div class="lexis-card-detail">{detail}</div>"""
            if action:
                content_html += f"""<div class="lexis-card-action">→ {action}</div>"""
    elif trigger == "question":
        q = data.get("question", {})
        if q:
            title = q.get("title", "Ask This")
            vague = q.get("vague_phrase", "")
            suggested = q.get("suggested_question", "")
            why = q.get("why_it_matters", q.get("why_ask", ""))
            content_html = f"""
            <div class="lexis-question-quote">Speaker said: "{vague}"</div>
            <div class="lexis-question-suggested">"{suggested}"</div>
            <div class="lexis-card-detail">{why}</div>"""
    elif trigger == "commitment":
        items = data.get("commitments", [])
        if items:
            title = items[0].get("title", "Tracked")
        for item in items:
            actionable = item.get("actionable", False)
            badge_text = "Action needed" if actionable else "Context"
            content_html += f"""
            <div style="margin-bottom:8px;">
                <span class="lexis-badge lexis-badge-{badge_class}" style="font-size:0.7rem;padding:2px 6px;">{badge_text}</span>
                <span class="lexis-card-summary" style="display:inline;margin-left:6px;">{item.get('summary', item.get('content', ''))}</span>
                <div class="lexis-card-detail" style="margin-top:4px;">{item.get('detail', '')}</div>
            </div>"""

    if not title:
        title = label

    return f"""
    <div class="card lexis-card" data-timestamp="{timestamp}" data-trigger="{trigger}">
        <div class="lexis-card-header">
            <div>
                <span class="lexis-badge lexis-badge-{badge_class}">{label}</span>
                <span class="lexis-card-title" style="margin-left:8px;">{title}</span>
            </div>
            <span class="lexis-time">{minutes}:{seconds:02d}</span>
        </div>
        <div>{content_html}</div>
    </div>"""


INLINE_CSS = """
<style>
:root {
  --font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --font-mono: ui-monospace, 'SF Mono', 'Monaco', monospace;
  --slate-50: #f8fafc; --slate-100: #f1f5f9; --slate-200: #e2e8f0; --slate-300: #cbd5e1;
  --slate-400: #94a3b8; --slate-500: #64748b; --slate-600: #475569; --slate-700: #334155;
  --slate-800: #1e293b; --slate-900: #0f172a;
  --amber-50: #fffbeb; --amber-500: #d97706; --rose-50: #fff1f2; --rose-500: #e11d48;
  --emerald-50: #ecfdf5; --emerald-500: #10b981; --blue-50: #eff6ff; --blue-500: #3b82f6;
  --shadow: 0 1px 3px 0 rgba(15,23,42,0.1), 0 1px 2px -1px rgba(15,23,42,0.1);
  --shadow-md: 0 4px 6px -1px rgba(15,23,42,0.1), 0 2px 4px -2px rgba(15,23,42,0.1);
  --ease-spring: cubic-bezier(0.16, 1, 0.3, 1);
}
* { font-family: var(--font-sans); }
.lexis-card { background: white; border-radius: 12px; padding: 16px 20px; margin-bottom: 12px;
  box-shadow: var(--shadow); border: 1px solid var(--slate-200); transition: all 0.3s var(--ease-spring);
  display: none; animation: slideIn 0.4s var(--ease-spring); }
.lexis-card:hover { box-shadow: var(--shadow-md); transform: translateY(-1px); }
.lexis-card[data-trigger="jargon"] { border-left: 3px solid var(--amber-500);
  background: linear-gradient(to right, var(--amber-50) 0%, white 8%); }
.lexis-card[data-trigger="impact"] { border-left: 3px solid var(--rose-500);
  background: linear-gradient(to right, var(--rose-50) 0%, white 8%); }
.lexis-card[data-trigger="question"] { border-left: 3px solid var(--emerald-500);
  background: linear-gradient(to right, var(--emerald-50) 0%, white 8%); }
.lexis-card[data-trigger="commitment"] { border-left: 3px solid var(--blue-500);
  background: linear-gradient(to right, var(--blue-50) 0%, white 8%); }
.lexis-filter { padding: 6px 14px; border-radius: 20px; border: 1px solid var(--slate-300);
  background: white; color: var(--slate-700); font-size: 0.875rem; font-weight: 500; cursor: pointer;
  transition: all 0.2s var(--ease-spring); outline: none; }
.lexis-filter:hover { border-color: var(--slate-400); background: var(--slate-50);
  transform: translateY(-1px); box-shadow: var(--shadow); }
.lexis-filter:active { transform: translateY(0) scale(0.98); }
.lexis-filter.active { background: var(--slate-900); color: white; border-color: var(--slate-900); }
.lexis-filter[data-filter="jargon"].active { background: var(--amber-500); border-color: var(--amber-500); }
.lexis-filter[data-filter="impact"].active { background: var(--rose-500); border-color: var(--rose-500); }
.lexis-filter[data-filter="question"].active { background: var(--emerald-500); border-color: var(--emerald-500); }
.lexis-filter[data-filter="commitment"].active { background: var(--blue-500); border-color: var(--blue-500); }
.lexis-badge { display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 0.75rem;
  font-weight: 600; text-transform: uppercase; letter-spacing: 0.025em; }
.lexis-badge-amber { background: var(--amber-500); color: white; }
.lexis-badge-rose { background: var(--rose-500); color: white; }
.lexis-badge-emerald { background: var(--emerald-500); color: white; }
.lexis-badge-blue { background: var(--blue-500); color: white; }
.lexis-time { font-family: var(--font-mono); font-size: 0.8125rem; color: var(--slate-500);
  font-variant-numeric: tabular-nums; }
.lexis-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.lexis-card-title { font-weight: 600; font-size: 0.9375rem; color: var(--slate-900); letter-spacing: -0.01em; }
.lexis-card-summary { font-size: 0.9375rem; font-weight: 500; color: var(--slate-800); line-height: 1.5; margin-bottom: 8px; }
.lexis-card-detail { font-size: 0.875rem; color: var(--slate-600); line-height: 1.6; }
.lexis-card-action { margin-top: 10px; padding: 8px 12px; background: var(--slate-100);
  border-radius: 8px; font-size: 0.875rem; color: var(--slate-700); border-left: 2px solid var(--emerald-500); }
.lexis-question-quote { font-size: 0.875rem; color: var(--slate-500); font-style: italic; margin-bottom: 8px; }
.lexis-question-suggested { padding: 10px 12px; background: var(--emerald-50); border-radius: 8px;
  font-size: 0.9375rem; font-weight: 500; color: var(--slate-900); margin: 8px 0; }
.lexis-section-title { font-size: 1.5rem; font-weight: 600; letter-spacing: -0.02em; color: var(--slate-900); }
.lexis-hero-title { font-size: clamp(2rem, 5vw, 3.5rem); font-weight: 700; letter-spacing: -0.03em; line-height: 1.1; }
.lexis-subtitle { font-size: clamp(1rem, 2.5vw, 1.25rem); font-weight: 400; color: var(--slate-600); line-height: 1.5; max-width: 65ch; }
@keyframes slideIn { from { opacity: 0; transform: translateX(20px); } to { opacity: 1; transform: translateX(0); } }
</style>
"""

def build_synced_cards_html(cards: list) -> str:
    """Build cards HTML with filter buttons. JS sync logic is in the global head script."""
    cards_html = "\n".join(format_card_html(c) for c in cards)
    total = len(cards)

    jargon_count = sum(1 for c in cards if c["trigger"] == "jargon")
    impact_count = sum(1 for c in cards if c["trigger"] == "impact")
    question_count = sum(1 for c in cards if c["trigger"] == "question")
    commitment_count = sum(1 for c in cards if c["trigger"] == "commitment")

    return f"""
    {INLINE_CSS}
    <div id="lexis-cards-container">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
            <h3 class="lexis-section-title" style="margin:0;">Insights</h3>
            <span id="card-count" class="lexis-time">(0/{total})</span>
        </div>
        <div id="lexis-filters" style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px;">
            <button class="filter-btn lexis-filter active" data-filter="all">All ({total})</button>
            <button class="filter-btn lexis-filter active" data-filter="jargon">Jargon ({jargon_count})</button>
            <button class="filter-btn lexis-filter active" data-filter="impact">Impact ({impact_count})</button>
            <button class="filter-btn lexis-filter active" data-filter="question">Questions ({question_count})</button>
            <button class="filter-btn lexis-filter active" data-filter="commitment">Commitments ({commitment_count})</button>
        </div>
        <div id="lexis-status" style="font-size:0.875rem;color:var(--slate-500);margin-bottom:12px;">
            Press play on the video. Cards appear as the conversation progresses.
        </div>
        <div id="lexis-cards" style="max-height:550px;overflow-y:auto;">
            {cards_html}
        </div>
    </div>
    """


GLOBAL_JS = """
<script>
(function() {
    let lastTime = -1;
    let activeFilters = new Set(['jargon', 'impact', 'question', 'commitment']);

    // Filter button click handler
    document.addEventListener('click', function(e) {
        const btn = e.target.closest('.filter-btn');
        if (!btn) return;

        const filter = btn.dataset.filter;
        if (filter === 'all') {
            // Toggle all
            const allActive = activeFilters.size === 4;
            if (allActive) {
                activeFilters.clear();
            } else {
                activeFilters = new Set(['jargon', 'impact', 'question', 'commitment']);
            }
        } else {
            if (activeFilters.has(filter)) {
                activeFilters.delete(filter);
            } else {
                activeFilters.add(filter);
            }
        }

        // Update button styles
        document.querySelectorAll('.filter-btn').forEach(b => {
            const f = b.dataset.filter;
            if (f === 'all') {
                b.classList.toggle('active', activeFilters.size === 4);
                b.style.opacity = activeFilters.size === 4 ? '1' : '0.4';
            } else {
                const isActive = activeFilters.has(f);
                b.classList.toggle('active', isActive);
                b.style.opacity = isActive ? '1' : '0.4';
            }
        });

        // Force re-render cards
        lastTime = -1;
    });

    function tick() {
        const cards = document.querySelectorAll('.card[data-timestamp]');
        if (cards.length === 0) return;

        const videos = document.querySelectorAll('video');
        let activeVideo = null;
        for (const v of videos) {
            if (v.currentTime > 0 || !v.paused) {
                activeVideo = v;
                break;
            }
        }
        if (!activeVideo && videos.length > 0) {
            activeVideo = videos[videos.length - 1];
        }
        if (!activeVideo) return;

        const t = activeVideo.currentTime;
        if (t === lastTime) return;
        lastTime = t;

        let revealed = 0;
        let filtered = 0;
        const cardContainer = document.getElementById('lexis-cards');
        cards.forEach(card => {
            const ts = parseFloat(card.dataset.timestamp);
            const trigger = card.dataset.trigger;
            const passesFilter = activeFilters.has(trigger);
            const passesTime = t >= ts;

            if (passesTime && passesFilter) {
                if (card.style.display === 'none') {
                    card.style.display = 'block';
                    card.style.animation = 'slideIn 0.4s ease-out';
                    if (cardContainer) cardContainer.scrollTop = cardContainer.scrollHeight;
                }
                revealed++;
            } else {
                card.style.display = 'none';
            }
            if (passesTime) filtered++;
        });

        const countEl = document.getElementById('card-count');
        const status = document.getElementById('lexis-status');
        const total = cards.length;
        if (countEl) countEl.textContent = `(${revealed}/${total})`;
        if (status) {
            const mins = Math.floor(t / 60);
            const secs = Math.floor(t % 60).toString().padStart(2, '0');
            status.textContent = `${mins}:${secs} | ${revealed} shown`;
        }
    }

    setInterval(tick, 250);
})();
</script>
"""


def process_media_with_profile(media_file, profile_text):
    if media_file is None:
        return None, "<p style='color:red;'>Please upload a video.</p>", "{}"

    # Build a custom profile from user's free-text input
    profile = {
        "name": "User",
        "situation": profile_text if profile_text.strip() else "General professional seeking to understand the conversation.",
        "knowledge_level": "beginner",
        "concerns": [],
    }

    # Try to infer concerns from the text
    text_lower = profile_text.lower()
    if any(w in text_lower for w in ["h1b", "visa", "green card", "immigration", "i-140", "perm", "opt"]):
        profile["knowledge_level"] = "intermediate" if any(w in text_lower for w in ["i-140", "priority date", "aos"]) else "beginner"
    if any(w in text_lower for w in ["concern", "worry", "anxious", "afraid", "want to know"]):
        profile["concerns"] = [profile_text.strip()]
    else:
        profile["concerns"] = [profile_text.strip()]

    result = run_pipeline(media_file, profile)
    cards = result["cards"]
    cards_html = build_synced_cards_html(cards)

    return media_file, cards_html, json.dumps(result, indent=2)


def create_app():
    with gr.Blocks(title="Lexis — AI Co-Listener") as app:

        # ============ PAGE 1: ONBOARDING ============
        with gr.Column(visible=True) as onboarding_page:
            gr.HTML(f"""
            {INLINE_CSS}
            <div style="text-align:center;padding:60px 20px 40px;max-width:800px;margin:0 auto;">
                <h1 class="lexis-hero-title" style="margin-bottom:16px;">Lexis</h1>
                <p class="lexis-subtitle" style="margin:0 auto 24px;">
                    Your AI co-listener that gives <strong>explainable, personalized</strong> interventions during professional conversations.
                </p>
                <p style="font-size:0.9375rem;color:#64748b;max-width:560px;margin:0 auto;">
                    Tell us about yourself so Lexis can tailor insights to <em>your</em> specific situation.
                </p>
            </div>
            """)

            with gr.Column(elem_classes=["onboarding-form"]):
                profile_text = gr.Textbox(
                    label="Tell us about your situation",
                    placeholder="Example: I'm on H-1B at a tech company, I-140 approved in 2021 with priority date March 2021. I'm considering switching employers and want to understand how the new $100K fee might affect me. I'm also planning to visit my parents in China.",
                    lines=5,
                    max_lines=10,
                )

                with gr.Row():
                    profile_file = gr.File(
                        label="Upload supporting docs (optional)",
                        file_types=[".pdf", ".txt", ".json"],
                        type="filepath",
                    )
                    voice_input = gr.Audio(
                        label="Or describe by voice",
                        type="filepath",
                        sources=["microphone"],
                    )

                proceed_btn = gr.Button(
                    "Continue →",
                    variant="primary",
                    size="lg",
                )

        # ============ PAGE 2: MAIN PROCESSING ============
        with gr.Column(visible=False) as main_page:
            gr.Markdown("## Lexis — Co-Listening Session")

            with gr.Accordion("Upload & Configure", open=True) as upload_accordion:
                with gr.Row():
                    media_input = gr.Video(label="Upload Conversation Video")
                    with gr.Column():
                        profile_display = gr.Textbox(
                            label="Your Profile",
                            interactive=False,
                            lines=3,
                        )
                        process_btn = gr.Button("Process Conversation", variant="primary", size="lg")
                        back_btn = gr.Button("← Edit Profile", variant="secondary", size="sm")

            with gr.Row():
                with gr.Column(scale=1):
                    video_output = gr.Video(label="Playback", interactive=False)
                with gr.Column(scale=1):
                    output_html = gr.HTML(label="Insights")

            with gr.Accordion("Raw JSON Output", open=False):
                output_json = gr.Code(language="json", label="Pipeline Output")

        # ============ STATE ============
        profile_state = gr.State("")

        # ============ ACTIONS ============

        def transcribe_voice(audio_path):
            """Convert voice input to text and append to profile textbox."""
            if audio_path is None:
                return gr.Textbox()
            from faster_whisper import WhisperModel
            model = WhisperModel("base", device="cpu", compute_type="int8")
            segments, _ = model.transcribe(audio_path, beam_size=3, language="en")
            text = " ".join(seg.text.strip() for seg in segments)
            return text

        def on_voice_recorded(audio_path, current_text):
            if audio_path is None:
                return current_text
            transcribed = transcribe_voice(audio_path)
            if current_text.strip():
                return current_text.strip() + "\n" + transcribed
            return transcribed

        def on_proceed(profile_text_val):
            """Switch from onboarding to main page."""
            return (
                gr.Column(visible=False),  # hide onboarding
                gr.Column(visible=True),   # show main
                profile_text_val,          # store in state
                profile_text_val,          # display in profile_display
            )

        def on_back():
            """Switch back to onboarding."""
            return (
                gr.Column(visible=True),   # show onboarding
                gr.Column(visible=False),  # hide main
            )

        def on_process(media_file, stored_profile):
            video, html, json_out = process_media_with_profile(media_file, stored_profile)
            return video, html, json_out, gr.Accordion(open=False)

        # Wire events
        voice_input.change(
            fn=on_voice_recorded,
            inputs=[voice_input, profile_text],
            outputs=[profile_text],
        )

        proceed_btn.click(
            fn=on_proceed,
            inputs=[profile_text],
            outputs=[onboarding_page, main_page, profile_state, profile_display],
        )

        back_btn.click(
            fn=on_back,
            inputs=[],
            outputs=[onboarding_page, main_page],
        )

        process_btn.click(
            fn=on_process,
            inputs=[media_input, profile_state],
            outputs=[video_output, output_html, output_json, upload_accordion],
        )

    return app


if __name__ == "__main__":
    app = create_app()
    custom_theme = gr.themes.Soft(primary_hue="teal", secondary_hue="slate", neutral_hue="slate")
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        allowed_paths=["/"],
        head=GLOBAL_JS,
        theme=custom_theme,
    )
