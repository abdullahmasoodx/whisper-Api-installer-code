import whisper
import torch
import webrtcvad
from flask import Flask, request, jsonify
from pydub import AudioSegment
import tempfile
import time
import whisper.version
from typing import List, Dict
import warnings
import os
import sys
import threading

APP_VERSION = "1.5.0"

base_path = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__)
model_cache_dir = os.path.join(os.environ["PROGRAMDATA"], "WhisperApi", "model_cache")
os.environ["XDG_CACHE_HOME"] = model_cache_dir
print("Loading Whisper model from:", os.environ.get("XDG_CACHE_HOME", "Default system cache"))

warnings.filterwarnings("ignore")

device = "cuda" if torch.cuda.is_available() else "cpu"
print("Using device:", device)

model_lock = threading.Lock()

available_models = {
    "tiny": "tiny",
    "tiny.en": "tiny.en",
    "base": "base",
    "base.en": "base.en",
    "small": "small",
    "small.en": "small.en",
    "medium": "medium",
    "medium.en": "medium.en",
    "large": "large",
    "large-v1": "large-v1",
    "large-v2": "large-v2",
    "large-v3": "large-v3",
    "large-v3-turbo": "large-v3-turbo"
}

model_cache = {}
last_used_model = "large-v3-turbo"



app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = tempfile.gettempdir()

def split_text_to_lines(text: str, max_chars: int = 32) -> List[str]:
    """
    Splits the input text into lines, breaking at the last space before max_chars.
    """
    import textwrap
    words = text.strip().split()
    lines = []
    current_line = ""

    for word in words:
        if len(current_line) + len(word) + 1 <= max_chars:
            current_line += (" " if current_line else "") + word
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines


def wrap_text_by_char_proportion(text: str, start: float, end: float, max_chars: int = 32) -> List[Dict]:
    """
    Wraps text into blocks, each with up to 2 lines of ≤ max_chars/2, and assigns proportional timings.
    """
    max_chars = max_chars * 2
    full_duration = end - start
    max_line_length = max_chars // 2
    lines = split_text_to_lines(text, max_chars=max_line_length)

    # Group into 2-line blocks
    line_blocks = []
    i = 0
    while i < len(lines):
        block = lines[i]
        if i + 1 < len(lines):
            block += "\n" + lines[i + 1]
        line_blocks.append(block)
        i += 2

    total_chars = sum(len(block.replace("\n", "").replace(" ", "")) for block in line_blocks)

    result = []
    cumulative_time = start

    for block in line_blocks:
        char_count = len(block.replace("\n", "").replace(" ", ""))
        duration = (char_count / total_chars) * full_duration if total_chars > 0 else 0
        result.append({
            "text": block,
            "start": cumulative_time,
            "end": cumulative_time + duration
        })
        cumulative_time += duration

    return result
def get_model(model_name):
    if model_name not in model_cache:
        model_cache[model_name] = whisper.load_model(model_name, device=device)
    return model_cache[model_name]

def is_voice_present(audio_path, aggressiveness=2, voice_ratio_threshold=0.1, frame_duration=30):
    audio = AudioSegment.from_file(audio_path).set_frame_rate(16000).set_channels(1).set_sample_width(2)
    raw_audio = audio.raw_data
    vad = webrtcvad.Vad(int(aggressiveness))
    frame_size = int(16000 * frame_duration / 1000) * 2
    frames = [raw_audio[i:i + frame_size] for i in range(0, len(raw_audio), frame_size)]
    if not frames:
        return False
    num_voiced = sum(1 for frame in frames if len(frame) == frame_size and vad.is_speech(frame, 16000))
    voice_ratio = num_voiced / len(frames)
    return voice_ratio > voice_ratio_threshold


@app.route("/version", methods=["GET"])
def get_versions():
    return jsonify({
        "app_version": APP_VERSION,
        "whisper_version": whisper.version.__version__,
        "device": device
    })


@app.route("/model", methods=["GET"])
def get_model_name():
    return jsonify({"model": last_used_model, "device": device})


@app.route("/transcribe", methods=["POST"])
def transcribe():
    start = time.time()
    if "audio" not in request.files:
        return jsonify({"error": "No audio file part in the request"}), 400
    file = request.files["audio"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    temp_file_path = os.path.join(app.config["UPLOAD_FOLDER"], next(tempfile._get_candidate_names()) + ".wav")
    file.save(temp_file_path)

    try:
        model_name = request.form.get("model", "large-v3-turbo")
        global last_used_model
        last_used_model = model_name
        model = get_model(model_name)

        parameters = {}

        try:
            parameters["avg_logprob_threshold"] = float(request.form.get("avg_logprob_threshold", -1.0))
            parameters["compression_ratio_threshold"] = float(request.form.get("compression_ratio_threshold", 2.4))
            parameters["no_speech_prob_threshold"] = float(request.form.get("no_speech_prob_threshold", 0.6))
            parameters["temperature"] = float(request.form.get("temperature", 0.0))
            parameters["vad_aggressiveness"] = int(request.form.get("vad_aggressiveness", 2))
            parameters["vad_voice_ratio_threshold"] = float(request.form.get("vad_voice_ratio_threshold", 0.1))
            parameters["min_text_length"] = int(request.form.get("min_text_length", 5))
            parameters["wrap_length"] = int(request.form.get("wrap_length", 32))
            parameters["enable_filtering"] = request.form.get("enable_filtering", "false").lower() == "true"


        except ValueError as e:
            raise ValueError(f"Invalid parameter value: {e}")

        enable_vad_raw = request.form.get("enable_vad", "true").lower()
        if enable_vad_raw not in ["true", "false"]:
            raise ValueError("Invalid value for enable_vad (must be 'true' or 'false')")
        parameters["enable_vad"] = enable_vad_raw == "true"

    except ValueError as e:
        os.remove(temp_file_path)
        return jsonify({"error": str(e)}), 400

    transcription_id = request.form.get("request_id", "1234")
    t0 = time.time()

    VAD_FILTER = 1
    LOGPROB_FILTER = 2
    COMP_RATIO_FILTER = 4
    NO_SPEECH_FILTER = 8
    MIN_TEXT_FILTER = 16

    is_vad_silence = parameters["enable_vad"] and not is_voice_present(
        temp_file_path, parameters["vad_aggressiveness"], parameters["vad_voice_ratio_threshold"])
    with model_lock:
        result = model.transcribe(temp_file_path, temperature=parameters["temperature"])

    for seg in result.get("segments", []):
        reason = 0
        if parameters["enable_filtering"]:
            if is_vad_silence:
                reason |= VAD_FILTER
            if seg.get("avg_logprob", -1.0) < parameters["avg_logprob_threshold"]:
                reason |= LOGPROB_FILTER
            if seg.get("compression_ratio", 2.4) > parameters["compression_ratio_threshold"]:
                reason |= COMP_RATIO_FILTER
            if seg.get("no_speech_prob", 0.6) > parameters["no_speech_prob_threshold"]:
                reason |= NO_SPEECH_FILTER
            if len(seg.get("text", "").strip()) < parameters["min_text_length"]:
                reason |= MIN_TEXT_FILTER

        text = seg.get("text", "").strip()
        segment_start = seg.get("start", 0.0)
        segment_end = seg.get("end", 0.0)

        wrapped_text = wrap_text_by_char_proportion(
            text=text,
            start=segment_start,
            end=segment_end,
            max_chars=parameters["wrap_length"]
        )

        antix = {
            "filtered": reason,
            "filtered_bin": f'0b{reason:05b}',
            "wrapped_text": wrapped_text
        }

        seg["antix"] = antix

    end = time.time()

    print("Request ID:", transcription_id)
    print("Whisper Transcribe time:", end - t0)
    print("Total Response time:", end - start)

    return jsonify({
        "antix": {
            "request_id": transcription_id,
            "api_ver": APP_VERSION,
            "whisper_ver": whisper.version.__version__,
            "model": model_name,
            "device": device,
            "response_time": round(end - start, 3),
            "enable_filtering": parameters.get("enable_filtering", False)
        },
        "result": result
    })

@app.route("/health", methods=["GET"])
def health():
    return "OK", 200

def warm_up(model):
    import numpy as np
    from scipy.io.wavfile import write
    dummy_path = os.path.join(tempfile.gettempdir(), "dummy.wav")
    sample_rate = 16000
    samples = np.zeros(sample_rate, dtype=np.int16)
    write(dummy_path, sample_rate, samples)
    model.transcribe(dummy_path)
    os.remove(dummy_path)


if __name__ == "__main__":
    print("Preloading Whisper model...")
    model_cache["large-v3-turbo"] = whisper.load_model("large-v3-turbo", device=device, download_root=model_cache_dir)
    warm_up(model_cache["large-v3-turbo"])
    print("Model is Ready to Use")

    from waitress import serve

    serve(app, host="0.0.0.0", port=8001)