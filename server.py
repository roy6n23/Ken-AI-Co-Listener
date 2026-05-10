from flask import Flask, render_template, request, jsonify, send_from_directory
import os
from pathlib import Path
from pipeline import run_pipeline

app = Flask(__name__, static_folder='static', template_folder='templates')

UPLOAD_FOLDER = Path('uploads')
UPLOAD_FOLDER.mkdir(exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/session')
def session():
    return render_template('session.html')

@app.route('/summarize', methods=['POST'])
def summarize():
    data = request.get_json()
    text = data.get('text', '')
    category = data.get('category', 'legal')

    if not text.strip():
        return jsonify({'summary': '', 'keywords': []})

    try:
        from openai import OpenAI
        endpoint = os.environ.get("AMD_ENDPOINT", "http://134.199.198.41:8000/v1")
        model_name = os.environ.get("MODEL_NAME", "Qwen/Qwen3-14B")
        client = OpenAI(base_url=endpoint, api_key="not-required")

        prompt = f"""You are Ken, an AI co-listener. A user is about to enter a {category} consultation.

Their input: "{text}"

Return JSON with:
1. "summary": A 2-3 sentence summary of their situation (concise, factual)
2. "keywords": An array of 3-5 key topics/concerns to listen for during the conversation

Return ONLY valid JSON, no other text."""

        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.3,
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
        content = response.choices[0].message.content.strip()
        if "</think>" in content:
            content = content.split("</think>")[-1].strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        import json as json_mod
        result = json_mod.loads(content)
        return jsonify(result)
    except Exception as e:
        print(f"Summarize error: {e}")
        return jsonify({'summary': text[:200], 'keywords': []})


@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio'}), 400

    audio_file = request.files['audio']
    audio_path = UPLOAD_FOLDER / 'recording.webm'
    audio_file.save(audio_path)

    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("base", device="cpu", compute_type="int8")
        segments, _ = model.transcribe(str(audio_path), beam_size=3, language="en")
        text = " ".join(seg.text.strip() for seg in segments)
        return jsonify({'text': text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/process', methods=['POST'])
def process():
    if 'video' not in request.files:
        return jsonify({'error': 'No video file'}), 400

    video_file = request.files['video']
    profile_text = request.form.get('profile_text', '')
    profile_cat = request.form.get('profile_cat', 'Legal')

    # Save video temporarily
    video_path = UPLOAD_FOLDER / video_file.filename
    video_file.save(video_path)

    # Summarize user situation via LLM
    summary = summarize_situation(profile_text, profile_cat)

    # Build profile
    profile = {
        "name": "User",
        "situation": summary or f"{profile_cat}: {profile_text}",
        "knowledge_level": "intermediate",
        "concerns": [profile_text] if profile_text else []
    }

    # Run pipeline
    result = run_pipeline(str(video_path), profile)
    result['summary'] = summary

    return jsonify(result)


def summarize_situation(text, category):
    """Use LLM to summarize the user's situation into a concise profile."""
    if not text.strip():
        return ""
    try:
        from openai import OpenAI
        endpoint = os.environ.get("AMD_ENDPOINT", "http://134.199.198.41:8000/v1")
        model_name = os.environ.get("MODEL_NAME", "Qwen/Qwen3-14B")
        client = OpenAI(base_url=endpoint, api_key="not-required")

        prompt = f"""Summarize this user's situation in 2-3 concise sentences for a {category} consultation context. Focus on key facts and concerns.

User input: "{text}"

Return ONLY the summary, no preamble."""

        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.3,
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
        content = response.choices[0].message.content.strip()
        if "</think>" in content:
            content = content.split("</think>")[-1].strip()
        return content
    except Exception as e:
        print(f"Summarization error: {e}")
        return text[:200]

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7860, debug=True)
