import json
import sys
import os
import concurrent.futures
from pathlib import Path
from openai import OpenAI
from faster_whisper import WhisperModel

from triggers import TRIGGER_PROMPTS
from profiles import PROFILES

AMD_ENDPOINT = os.environ.get("AMD_ENDPOINT", "http://134.199.198.41:8000/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "Qwen/Qwen3-14B")

client = OpenAI(base_url=AMD_ENDPOINT, api_key="not-required")


def transcribe(audio_path: str) -> list[dict]:
    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(audio_path, beam_size=3, language="en")
    results = []
    for seg in segments:
        text = seg.text.strip()
        if len(text) > 10:
            results.append({
                "start": round(seg.start, 2),
                "end": round(seg.end, 2),
                "text": text,
            })
    return results


def merge_segments(segments: list[dict], max_chars: int = 300) -> list[dict]:
    """Merge short segments into chunks to reduce LLM calls."""
    merged = []
    current = None
    for seg in segments:
        if current is None:
            current = {**seg}
        elif len(current["text"]) + len(seg["text"]) < max_chars:
            current["text"] += " " + seg["text"]
            current["end"] = seg["end"]
        else:
            merged.append(current)
            current = {**seg}
    if current:
        merged.append(current)
    return merged


def run_trigger(trigger_name: str, prompt_template: str, segment: dict, profile: dict) -> dict | None:
    prompt = prompt_template.format(
        name=profile.get("name", ""),
        situation=profile.get("situation", ""),
        knowledge_level=profile.get("knowledge_level", "intermediate"),
        concerns=", ".join(profile.get("concerns", [])),
        segment_text=segment["text"],
    )

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.3,
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
        content = response.choices[0].message.content.strip()
        if "</think>" in content:
            content = content.split("</think>")[-1].strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        result = json.loads(content)
        if result.get("triggered"):
            return {
                "trigger": trigger_name,
                "timestamp": segment["start"],
                "end": segment["end"],
                "segment_text": segment["text"],
                "data": result,
            }
    except (json.JSONDecodeError, Exception) as e:
        print(f"  [{trigger_name}] parse error on segment @{segment['start']}s: {e}", file=sys.stderr)
    return None


def process_segment_triggers(args: tuple) -> list[dict]:
    """Process one trigger on one segment (for parallel execution)."""
    trigger_name, template, segment, profile = args
    result = run_trigger(trigger_name, template, segment, profile)
    return [result] if result else []


def run_pipeline(audio_path: str, profile: dict, max_workers: int = 8) -> dict:
    print(f"[1/3] Transcribing: {audio_path}")
    segments = transcribe(audio_path)
    print(f"  → {len(segments)} raw segments")

    chunks = merge_segments(segments)
    print(f"  → merged into {len(chunks)} chunks")

    print(f"[2/3] Running triggers ({len(chunks)} chunks × 4 triggers = {len(chunks)*4} calls, {max_workers} workers)...")

    all_tasks = []
    for chunk in chunks:
        for trigger_name, template in TRIGGER_PROMPTS.items():
            all_tasks.append((trigger_name, template, chunk, profile))

    all_cards = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_segment_triggers, task) for task in all_tasks]
        for future in concurrent.futures.as_completed(futures):
            all_cards.extend(future.result())

    all_cards.sort(key=lambda c: c["timestamp"])
    print(f"[3/3] Done. {len(all_cards)} cards generated.")

    return {
        "profile": profile["name"],
        "audio_file": audio_path,
        "total_segments": len(segments),
        "total_chunks": len(chunks),
        "total_cards": len(all_cards),
        "cards": all_cards,
        "transcript": segments,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pipeline.py <audio_file> [profile_name]")
        print("  profile_name: user_a or user_b (default: user_a)")
        sys.exit(1)

    audio_file = sys.argv[1]
    profile_name = sys.argv[2] if len(sys.argv) > 2 else "user_a"
    profile = PROFILES.get(profile_name)

    if not profile:
        print(f"Unknown profile: {profile_name}. Choose from: {list(PROFILES.keys())}")
        sys.exit(1)

    result = run_pipeline(audio_file, profile)

    output_path = Path(audio_file).stem + f"_{profile_name}_cards.json"
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"Output saved to: {output_path}")
