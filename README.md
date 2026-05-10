---
title: Ken AI Co-Listener
emoji: 🎧
colorFrom: yellow
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# Ken — AI Co-Listener for Professional Conversations

An AI co-listener that gives explainable, personalized interventions during professional conversations — built on AMD ROCm.

## Quick Start

```bash
pip install -r requirements.txt
python server.py
```

Open http://localhost:7860

## Environment Variables

```bash
export AMD_ENDPOINT="http://your-endpoint:8000/v1"
export MODEL_NAME="Qwen/Qwen3-14B"
```

## How It Works

1. **Onboarding** — User selects a domain (Legal/Medical/Immigration/Career) and describes their situation
2. **Processing** — Upload a conversation recording → Whisper transcribes → LLM detects 4 trigger types
3. **Session** — Cards appear time-synced as the video plays

## Trigger Types

| Trigger | Detects | User's Gap |
|---------|---------|-----------|
| Jargon | Domain-specific terminology | "What does that mean?" |
| Impact | Content affecting YOUR situation | "How does this affect me?" |
| Question | Vague/hedge language | "What should I ask?" |
| Tracked | Dates, amounts, action items | "Will I remember this?" |

## Tech Stack

- **ASR:** faster-whisper (base model, CPU)
- **LLM:** Qwen3-14B on AMD Instinct MI300X via vLLM + ROCm
- **Backend:** Flask
- **Frontend:** Vanilla HTML/CSS/JS (Ken design system)
- **Infrastructure:** AMD Developer Cloud

## Project Structure

```
server.py          — Flask app (run this)
pipeline.py        — Whisper transcription + parallel LLM trigger detection
triggers.py        — 4 prompt templates
templates/
  index.html       — Onboarding page
  session.html     — Session/processing page
```

## License

MIT

## Built With

- AMD Instinct MI300X (192 GB HBM3)
- AMD Developer Cloud + ROCm
- Qwen3 (Alibaba Cloud)
- vLLM inference engine
