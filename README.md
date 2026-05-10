# Lexis — Explainable AI Co-Listener for Professional Conversations

> An open-source, domain-aware AI co-listener that gives explainable, personalized interventions during professional conversations — built on AMD ROCm.

## The Problem

When you talk to professionals — lawyers, accountants, doctors — they speak fast, in jargon, in *their* mental model. You miss things, don't know what to ask, and walk out confused.

Existing solutions either summarize *after* it's too late (Otter, Fireflies) or intervene as a blackbox you can't predict (Hedy, Cluely).

## How Lexis is Different

Lexis intervenes through **4 explicit, explainable trigger types** — each tied to a real cognitive gap:

| Trigger | Detects | User's Gap |
|---------|---------|-----------|
| 🟡 Jargon Bomb | Domain-specific terminology | "What does that mean?" |
| 🔴 Impact Alert | Content affecting YOUR situation | "How does this affect me?" |
| 🟢 Question Suggester | Vague/hedge language | "What should I ask?" |
| 📌 Commitment Tracker | Dates, amounts, action items | "Will I remember this?" |

Every intervention is **personalized** to your profile. Same conversation → different insights for different users.

## Tech Stack

- **ASR:** faster-whisper (medium)
- **LLM:** Qwen3 on AMD Instinct MI300X via vLLM + ROCm
- **Frontend:** Gradio with timestamp-synced card playback
- **Infrastructure:** AMD Developer Cloud

## Quick Start

```bash
pip install -r requirements.txt
python app.py
```

Set your AMD endpoint:
```bash
export AMD_ENDPOINT="http://your-droplet-ip:8000/v1"
export MODEL_NAME="Qwen/Qwen3-14B"
```

## Demo Domain: Immigration Law

Our demo uses immigration lawyer conversations to showcase all 4 triggers. The same framework extends to any professional domain by customizing trigger prompts.

## Architecture

```
Audio File + User Profile
    → Whisper ASR (timestamped segments)
    → 4x Trigger Detection (parallel, per segment)
    → Personalized Card Generation
    → Timestamp-synced playback UI
```

## License

MIT

## Built With

- AMD Instinct MI300X (192 GB HBM3)
- AMD Developer Cloud
- ROCm (open-source GPU computing)
- Qwen3 (Alibaba Cloud)
- vLLM inference engine
