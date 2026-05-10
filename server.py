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

    # Build profile
    profile = {
        "name": "User",
        "situation": f"{profile_cat}: {profile_text}" if profile_text else f"{profile_cat} consultation",
        "knowledge_level": "intermediate",
        "concerns": [profile_text] if profile_text else []
    }

    # Run pipeline
    result = run_pipeline(str(video_path), profile)

    return jsonify(result)

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7860, debug=True)
