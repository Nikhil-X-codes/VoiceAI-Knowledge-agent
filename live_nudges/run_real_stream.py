from __future__ import annotations

import argparse
import wave
from pathlib import Path

from live_nudges.streaming import run_stream, transcribe_chunk


def read_wav(path: Path) -> tuple[bytes, int, int, int]:
    with wave.open(str(path), "rb") as audio:
        if audio.getcomptype() != "NONE":
            raise ValueError(f"{path} must be uncompressed PCM WAV")
        return audio.readframes(audio.getnframes()), audio.getframerate(), audio.getnchannels(), audio.getsampwidth()


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay real customer and agent WAV files through Groq Whisper.")
    parser.add_argument("--customer", type=Path, required=True)
    parser.add_argument("--agent", type=Path, required=True)
    parser.add_argument("--language", default="en")
    parser.add_argument("--output", type=Path, default=Path("live_nudges/data/real_latency.csv"))
    parser.add_argument("--no-sleep", action="store_true", help="Process as fast as possible instead of real-time pacing.")
    args = parser.parse_args()

    customer_audio, sample_rate, channels, sample_width = read_wav(args.customer)
    agent_audio, agent_rate, agent_channels, agent_width = read_wav(args.agent)
    if (sample_rate, channels, sample_width) != (agent_rate, agent_channels, agent_width):
        raise ValueError("Customer and agent WAV files must have matching audio format")

    import time
    from live_nudges.controls import NudgeController
    from live_nudges.latency import latency_report, write_latency_row
    from live_nudges.signals import SignalWindow, extract_signals
    from live_nudges.streaming import chunk_audio, replay_chunks

    window = SignalWindow(max_turns=6)
    controller = NudgeController()
    call_state = {"required_disclosure_spoken": False}
    output_path = Path(args.output)
    if output_path.exists():
        output_path.unlink()

    print(f"Replaying dual-channel audio stream (Customer: {args.customer.name}, Agent: {args.agent.name})...")
    chunk_idx = 0
    all_chunks = []
    
    # Interleave chunks from customer and agent to simulate conversational flow
    c_chunks = chunk_audio(customer_audio, sample_rate, channels, sample_width)
    a_chunks = chunk_audio(agent_audio, agent_rate, agent_channels, agent_width)
    max_len = max(len(c_chunks), len(a_chunks))
    for i in range(max_len):
        if i < len(c_chunks):
            all_chunks.append(("customer", c_chunks[i]))
        if i < len(a_chunks):
            all_chunks.append(("agent", a_chunks[i]))

    for speaker, chunk in all_chunks:
        chunk_idx += 1
        t_in = time.perf_counter()
        lang = args.language if speaker == "customer" else "en"
        transcript = transcribe_chunk(chunk.payload, language=lang)
        t_asr = time.perf_counter()

        turns = window.add(speaker, transcript)
        signals = extract_signals(turns, call_state)
        t_signal = time.perf_counter()

        nudges = controller.accept(signals, now=t_signal, turns=turns, call_state=call_state)
        t_llm = time.perf_counter()

        # Simulated delivery to WebSocket
        t_disp = time.perf_counter() + 0.001

        write_latency_row(output_path, "live-replay-1", chunk_idx, t_in, t_asr, t_signal, t_llm, t_disp)
        print(f"[{speaker.upper()}] \"{transcript}\"")
        if nudges:
            for n in nudges:
                print(f"   >>> NUDGE: [{n['priority'].upper()}] {n['text']} (Signal: {n['signal']})")

    report = latency_report(output_path)
    print("\n--- LATENCY BENCHMARK (P50 / P95) ---")
    for comp, stats in report.items():
        print(f"{comp:15s} P50: {stats['p50_ms']:>8.2f} ms | P95: {stats['p95_ms']:>8.2f} ms")


if __name__ == "__main__":
    main()
