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
import json

APP_VERSION = "1.6.2"  # optimized: config.json + N-line captions + unified params

# ----------------------------------------------------------------------
# Base paths (EXE or script) + model cache + config.json
# ----------------------------------------------------------------------
base_path = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__)

model_cache_dir = os.path.join(
    os.environ["PROGRAMDATA"],
    "Antix Digital",
    "AICS Service",
    "model_cache"
)

os.environ["XDG_CACHE_HOME"] = model_cache_dir
print("Loading Whisper model from:", os.environ.get("XDG_CACHE_HOME", "Default system cache"))

# Primary config in SAME FOLDER as app.py / EXE
CONFIG_PATH_PRIMARY = os.path.join(base_path, "config.json")

# Fallback config in ProgramData\Antix Digital\AICS Service\config.json
CONFIG_PATH_FALLBACK = os.path.join(
    os.environ["PROGRAMDATA"],
    "Antix Digital",
    "AICS Service",
    "config.json"
)

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

# ----------------------------------------------------------------------
# GLOBAL DEFAULT CONFIG  (overridden by config.json, then by request)
# ----------------------------------------------------------------------
DEFAULT_CONFIG: Dict = {
    "model": "large-v3-turbo",

    "avg_logprob_threshold": -1.0,
    "compression_ratio_threshold": 2.4,
    "no_speech_prob_threshold": 0.6,
    "temperature": 0.0,

    "vad_aggressiveness": 2,
    "vad_voice_ratio_threshold": 0.1,
    "min_text_length": 5,
    "wrap_length": 32,

    "enable_filtering": False,
    "enable_vad": True,
    "enable_caps": True,      # CAPS ON by default (per customer request)
    "pretty_json": False,

    "silence_threshold": 1.0,
    "max_caption_lines": 2    # N-line support, default = 2 (Riadh’s required default)
}


def load_config() -> Dict:
    """
    Load config.json from:
      1) Same folder as app.py / EXE (primary)
      2) ProgramData\Antix Digital\AICS Service\config.json (fallback)
    If missing or invalid, fall back to DEFAULT_CONFIG.
    """
    config = DEFAULT_CONFIG.copy()

    config_paths = [CONFIG_PATH_PRIMARY, CONFIG_PATH_FALLBACK]
    used_path = None

    for path in config_paths:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    for key, value in data.items():
                        if key in config:
                            config[key] = value
                    used_path = path
                    break
                else:
                    print(f"Config file at {path} is not a JSON object, ignoring.")
            except Exception as e:
                print(f"Failed to read config file at {path}: {e}. Ignoring and trying next.")

    if used_path:
        print(f"Loaded configuration from: {used_path}")
    else:
        print("No config.json found, using built-in defaults.")

    return config


BASE_CONFIG = load_config()

# ----------------------------------------------------------------------
# Filtering flags (bitmask)
# ----------------------------------------------------------------------
VAD_FILTER = 1
LOGPROB_FILTER = 2
COMP_RATIO_FILTER = 4
NO_SPEECH_FILTER = 8
MIN_TEXT_FILTER = 16


# ----------------------------------------------------------------------
# Caption state per stream
# ----------------------------------------------------------------------
class StreamCaptionState:
    def __init__(self) -> None:
        # For backward compatibility, keep last_line,
        # but we now support N-line scrolling using last_lines.
        self.last_line: str = ""
        self.last_lines: List[str] = []
        self.is_first_caption: bool = True
        self.prev_chunk_ended_with_silence: bool = False
        self.last_update: float = time.time()   # timestamp for auto-expiry


stream_states: Dict[str, StreamCaptionState] = {}
stream_states_lock = threading.Lock()


# ----------------------------------------------------------------------
# Helpers for text splitting and audio duration
# ----------------------------------------------------------------------
def split_text_to_lines(text: str, max_chars: int = 32) -> List[str]:
    """
    Splits the input text into lines, breaking at the last space before max_chars.
    This returns individual lines (no '\\n' inside each line).
    """
    words = text.strip().split()
    lines: List[str] = []
    current_line = ""

    for word in words:
        limit = max_chars
        additional_len = len(word) + (1 if current_line else 0)
        if len(current_line) + additional_len <= limit:
            current_line += (" " if current_line else "") + word
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines


def get_audio_duration_seconds(audio_path: str) -> float:
    """
    Returns audio duration in seconds using pydub.
    """
    audio = AudioSegment.from_file(audio_path)
    return len(audio) / 1000.0


def get_model(model_name: str):
    if model_name not in model_cache:
        model_cache[model_name] = whisper.load_model(model_name, device=device)
    return model_cache[model_name]


def is_voice_present(
    audio_path: str,
    aggressiveness: int = 2,
    voice_ratio_threshold: float = 0.1,
    frame_duration: int = 30
) -> bool:
    """
    Simple VAD-based check:
    - Converts to 16k mono
    - Splits into frames
    - Checks ratio of voiced frames
    """
    audio = AudioSegment.from_file(audio_path).set_frame_rate(16000).set_channels(1).set_sample_width(2)
    raw_audio = audio.raw_data
    vad = webrtcvad.Vad(int(aggressiveness))
    frame_size = int(16000 * frame_duration / 1000) * 2
    frames = [raw_audio[i:i + frame_size] for i in range(0, len(raw_audio), frame_size)]
    if not frames:
        return False

    num_voiced = sum(
        1 for frame in frames
        if len(frame) == frame_size and vad.is_speech(frame, 16000)
    )
    voice_ratio = num_voiced / len(frames)
    return voice_ratio > voice_ratio_threshold


def parse_bool(value: str, param_name: str) -> bool:
    """
    Strict boolean parser for 'true' / 'false'.
    Raises ValueError for anything else.
    """
    val = value.lower()
    if val not in ["true", "false"]:
        raise ValueError(f"Invalid value for {param_name} (must be 'true' or 'false')")
    return val == "true"


# ----------------------------------------------------------------------
# Core: process segments with scrolling captions + silence + N-line support
# ----------------------------------------------------------------------
def process_segments_with_scrolling_captions(
    segments: List[Dict],
    audio_duration: float,
    parameters: Dict,
    is_vad_silence: bool,
    stream_id: str
) -> None:
    """
    Mutates each segment in `segments` by adding:
      seg["antix"] = {
          "filtered": <reason>,
          "filtered_bin": "0bxxxxx",
          "wrapped_text": [ { "text": "...", "start": ..., "end": ... }, ... ]
      }

    Implements:
    - N-line scrolling behaviour (default 2-line: previous line + new line)
    - Single-line mode (with leading '\\n') after silence / first caption
    - Silence detection at:
        * start of chunk
        * end of chunk
        * gaps between segments
    - For VAD-identified silence chunks:
        * Treat as silence for caption STATE (reset next chunk)
        * Do NOT delete Whisper text; we still build wrapped_text
        * Do NOT update .last_lines or .is_first_caption from that chunk
        * Set VAD_FILTER bit so 9000EX can ignore if desired
    """

    silence_threshold = float(parameters["silence_threshold"])
    wrap_length = int(parameters["wrap_length"])
    enable_filtering = parameters["enable_filtering"]
    enable_caps = parameters["enable_caps"]
    max_caption_lines = max(1, int(parameters.get("max_caption_lines", 2)))

    # Get / create state for this stream
    with stream_states_lock:
        state = stream_states.get(stream_id)
        if state is None:
            state = StreamCaptionState()
            stream_states[stream_id] = state

    num_segments = len(segments)

    # Chunk considered "silence for state" if VAD says silence and duration >= threshold.
    # For such chunks:
    # - we still compute wrapped_text
    # - we mark them as filtered (VAD_FILTER) if filtering is enabled
    # - we DO NOT update state.last_lines / state.is_first_caption
    # - we DO set state.prev_chunk_ended_with_silence = True
    chunk_state_silent = is_vad_silence and (audio_duration >= silence_threshold)

    # Pure-silence chunk (no segments at all)
    if num_segments == 0:
        if audio_duration >= silence_threshold:
            state.prev_chunk_ended_with_silence = True
        # Nothing to attach; we return.
        return

    # ACTIVE STATE SELECTION LOGIC
    state.last_update = time.time()  # mark stream as active

    if chunk_state_silent:
        # A full-silence chunk → reset scrolling state
        active_state = StreamCaptionState()

        # Silence chunk NEVER scrolls previous lines
        active_state.last_lines = []
        active_state.last_line = ""

        # Preserve high-level continuity
        active_state.is_first_caption = state.is_first_caption
        active_state.prev_chunk_ended_with_silence = True  # IMPORTANT
    else:
        # Normal chunk → use the global stream state
        active_state = state

    # Silence at start / end of (non-silent) chunk using timing
    leading_silence = False
    trailing_silence = False

    if not chunk_state_silent:
        if num_segments > 0:
            first_seg_start = float(segments[0].get("start", 0.0))
            if first_seg_start >= silence_threshold:
                leading_silence = True

            last_seg_end = float(segments[-1].get("end", 0.0))
            end_silence = audio_duration - last_seg_end
            if end_silence >= silence_threshold:
                trailing_silence = True
        else:
            if audio_duration >= silence_threshold:
                trailing_silence = True
    else:
        # For VAD-silence chunks, we treat as trailing silence for the next chunk.
        trailing_silence = audio_duration >= silence_threshold

    # Single-line condition for the first segment in this chunk:
    # - first caption for this stream
    # - OR previous chunk ended with silence
    # - OR leading silence at start of this chunk
    next_segment_force_single_line = (
        active_state.is_first_caption
        or active_state.prev_chunk_ended_with_silence
        or leading_silence
    )

    prev_seg_end = None

    for idx, seg in enumerate(segments):
        text = seg.get("text", "").strip()
        seg_start = float(seg.get("start", 0.0))
        seg_end = float(seg.get("end", 0.0))
        seg_duration = max(seg_end - seg_start, 0.0)

        # Determine filtering reason
        reason = 0
        if enable_filtering:
            if is_vad_silence:
                reason |= VAD_FILTER
            if seg.get("avg_logprob", -1.0) < parameters["avg_logprob_threshold"]:
                reason |= LOGPROB_FILTER
            if seg.get("compression_ratio", 2.4) > parameters["compression_ratio_threshold"]:
                reason |= COMP_RATIO_FILTER
            if seg.get("no_speech_prob", 0.6) > parameters["no_speech_prob_threshold"]:
                reason |= NO_SPEECH_FILTER
            if len(text.strip()) < parameters["min_text_length"]:
                reason |= MIN_TEXT_FILTER

        # Nothing to display for this segment timing-wise
        if not text or seg_duration <= 0:
            seg["antix"] = {
                "filtered": reason,
                "filtered_bin": f"0b{reason:05b}",
                "wrapped_text": []
            }
            prev_seg_end = seg_end
            continue

        if enable_caps:
            text = text.upper()

        # Internal gap-based silence detection:
        # If there's a gap >= threshold from previous segment, the FIRST line of this segment is single-line.
        if idx > 0 and prev_seg_end is not None:
            gap = seg_start - prev_seg_end
            if gap >= silence_threshold:
                next_segment_force_single_line = True

        segment_force_single_line = next_segment_force_single_line

        # Split into single lines respecting wrap_length
        lines = split_text_to_lines(text, max_chars=wrap_length)

        # Proportionally distribute segment time across lines by character count (excluding spaces)
        char_counts = [len(line.replace(" ", "")) for line in lines]
        total_chars = sum(char_counts) or 1
        current_time = seg_start

        wrapped_entries: List[Dict] = []
        first_line_in_segment = True

        for line, chars in zip(lines, char_counts):
            if not line:
                continue

            duration = seg_duration * (chars / total_chars)
            line_start = current_time
            line_end = current_time + duration
            current_time = line_end

            # Decide whether this line should be single-line or N-line scrolling
            if first_line_in_segment and segment_force_single_line:
                # Single-line mode (bottom-aligned)
                block_text = "\n" + line
                segment_force_single_line = False
                if not chunk_state_silent:
                    active_state.is_first_caption = False
            else:
                # N-line scrolling: include up to max_caption_lines-1 previous lines + current line
                if max_caption_lines > 1 and active_state.last_lines:
                    history = active_state.last_lines[-(max_caption_lines - 1):]
                    lines_to_show = history + [line]
                    block_text = "\n".join(lines_to_show)
                else:
                    block_text = "\n" + line

                if not chunk_state_silent:
                    active_state.is_first_caption = False

            wrapped_entries.append({
                "text": block_text,
                "start": line_start,
                "end": line_end
            })

            # Update scrolling state only if this is not a VAD-silence chunk
            if not chunk_state_silent:
                if max_caption_lines > 1:
                    active_state.last_lines.append(line)
                    if len(active_state.last_lines) > (max_caption_lines - 1):
                        active_state.last_lines = active_state.last_lines[-(max_caption_lines - 1):]
                    active_state.last_line = active_state.last_lines[-1]
                else:
                    # max_caption_lines == 1 → only keep the most recent line
                    active_state.last_lines = []
                    active_state.last_line = line

            first_line_in_segment = False

        # After first segment in the chunk is processed, subsequent segments
        # will only use internal-gap silence rules (set at the top of loop)
        next_segment_force_single_line = False

        seg["antix"] = {
            "filtered": reason,
            "filtered_bin": f"0b{reason:05b}",
            "wrapped_text": wrapped_entries
        }

        prev_seg_end = seg_end

    # Propagate state changes:
    if chunk_state_silent:
        # Do NOT propagate last_lines / is_first_caption from this chunk,
        # but let next chunk know that we ended with silence.
        state.prev_chunk_ended_with_silence = True
        state.last_lines = []
        state.last_line = ""
    else:
        # active_state is 'state' itself in this branch, so we just update trailing_silence.
        state.prev_chunk_ended_with_silence = trailing_silence

    if not chunk_state_silent:
        state.last_lines = list(active_state.last_lines)
        state.last_line = active_state.last_line
        state.is_first_caption = active_state.is_first_caption


# ----------------------------------------------------------------------
# Flask app + endpoints
# ----------------------------------------------------------------------
app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = tempfile.gettempdir()


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

    temp_file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        next(tempfile._get_candidate_names()) + ".wav"
    )
    file.save(temp_file_path)

    # Start with global BASE_CONFIG for this request
    parameters: Dict = BASE_CONFIG.copy()

    try:
        # --------------------------
        # MODEL NAME
        # --------------------------
        if "model" in request.form:
            parameters["model"] = request.form.get("model", parameters["model"])
        model_name = parameters["model"]
        global last_used_model
        last_used_model = model_name
        model = get_model(model_name)

        # --------------------------
        # NUMERIC PARAMETERS
        # --------------------------
        if "avg_logprob_threshold" in request.form:
            parameters["avg_logprob_threshold"] = float(request.form["avg_logprob_threshold"])

        if "compression_ratio_threshold" in request.form:
            parameters["compression_ratio_threshold"] = float(request.form["compression_ratio_threshold"])

        if "no_speech_prob_threshold" in request.form:
            parameters["no_speech_prob_threshold"] = float(request.form["no_speech_prob_threshold"])

        if "temperature" in request.form:
            parameters["temperature"] = float(request.form["temperature"])

        if "vad_aggressiveness" in request.form:
            parameters["vad_aggressiveness"] = int(request.form["vad_aggressiveness"])

        if "vad_voice_ratio_threshold" in request.form:
            parameters["vad_voice_ratio_threshold"] = float(request.form["vad_voice_ratio_threshold"])

        if "min_text_length" in request.form:
            parameters["min_text_length"] = int(request.form["min_text_length"])

        if "wrap_length" in request.form:
            parameters["wrap_length"] = int(request.form["wrap_length"])

        if "silence_threshold" in request.form:
            parameters["silence_threshold"] = float(request.form["silence_threshold"])

        if "max_caption_lines" in request.form:
            parameters["max_caption_lines"] = int(request.form["max_caption_lines"])

        # --------------------------
        # BOOLEAN PARAMETERS
        # --------------------------
        if "enable_filtering" in request.form:
            parameters["enable_filtering"] = parse_bool(request.form["enable_filtering"], "enable_filtering")

        if "enable_caps" in request.form:
            parameters["enable_caps"] = parse_bool(request.form["enable_caps"], "enable_caps")

        if "enable_vad" in request.form:
            parameters["enable_vad"] = parse_bool(request.form["enable_vad"], "enable_vad")

        if "pretty_json" in request.form:
            parameters["pretty_json"] = parse_bool(request.form["pretty_json"], "pretty_json")

    except ValueError as e:
        os.remove(temp_file_path)
        return jsonify({"error": f"Invalid parameter value: {e}"}), 400

    # ------------------------------------------------------------------
    # id / stream_id / audio_id handling
    # ------------------------------------------------------------------
    # Accept legacy "id" OR new "stream_id/audio_id"
    legacy_id = request.form.get("id") or request.form.get("request_id")

    stream_id = request.form.get("stream_id")
    audio_id = request.form.get("audio_id")

    if legacy_id and not (stream_id or audio_id):
        # Legacy mode → use only "id"
        stream_id = legacy_id
        audio_id = legacy_id
        use_legacy = True
    else:
        use_legacy = False

    # Validate new mode
    if not use_legacy and (not stream_id or not audio_id):
        os.remove(temp_file_path)
        return jsonify({
            "error": "Missing identifiers. Send 'id' (legacy) OR both 'stream_id' and 'audio_id'."
        }), 400

    transcription_id = legacy_id if use_legacy else audio_id

    t0 = time.time()

    # VAD check (chunk-level)
    is_vad_silence = parameters["enable_vad"] and not is_voice_present(
        temp_file_path,
        parameters["vad_aggressiveness"],
        parameters["vad_voice_ratio_threshold"]
    )

    # Transcription
    with model_lock:
        result = model.transcribe(temp_file_path, temperature=parameters["temperature"])

    # Duration for silence rules
    audio_duration = get_audio_duration_seconds(temp_file_path)

    # Apply scrolling captions logic + antix fields
    segments = result.get("segments", [])
    process_segments_with_scrolling_captions(
        segments=segments,
        audio_duration=audio_duration,
        parameters=parameters,
        is_vad_silence=is_vad_silence,
        stream_id=stream_id
    )

    end = time.time()

    # Build antix metadata (this is also what we log)
    antix_meta = {
        "api_ver": APP_VERSION,
        "whisper_ver": whisper.version.__version__,
        "model": model_name,
        "device": device,
        "response_time": round(end - start, 3),

        # FULL PARAMETER VISIBILITY
        "enable_filtering": parameters["enable_filtering"],
        "enable_caps": parameters["enable_caps"],
        "enable_vad": parameters["enable_vad"],
        "pretty_json": parameters["pretty_json"],

        "silence_threshold": parameters["silence_threshold"],
        "wrap_length": parameters["wrap_length"],
        "max_caption_lines": parameters["max_caption_lines"],

        # Whisper decoding params
        "temperature": parameters["temperature"],
        "avg_logprob_threshold": parameters["avg_logprob_threshold"],
        "compression_ratio_threshold": parameters["compression_ratio_threshold"],
        "no_speech_prob_threshold": parameters["no_speech_prob_threshold"],
        "vad_aggressiveness": parameters["vad_aggressiveness"],
        "vad_voice_ratio_threshold": parameters["vad_voice_ratio_threshold"],
        "min_text_length": parameters["min_text_length"]
    }

    if use_legacy:
        antix_meta["id"] = transcription_id
    else:
        antix_meta["stream_id"] = stream_id
        antix_meta["audio_id"] = audio_id

    # Logging: show IDs exactly as they appear in JSON (via antix_meta)
    print("ANTIX META:", antix_meta)
    print("Whisper Transcribe time:", end - t0)
    print("Total Response time:", end - start)

    os.remove(temp_file_path)

    # Build response
    response_obj = {
        "antix": antix_meta,
        "result": result
    }

    pretty = parameters.get("pretty_json", False)

    if pretty:
        return app.response_class(
            response=json.dumps(response_obj, indent=2),
            mimetype="application/json"
        )
    else:
        return jsonify(response_obj)


@app.route("/health", methods=["GET"])
def health():
    return "OK", 200


@app.route("/reset_stream", methods=["POST"])
def reset_stream():
    sid = request.form.get("stream_id")
    if not sid:
        return jsonify({"error": "stream_id required"}), 400

    with stream_states_lock:
        if sid in stream_states:
            del stream_states[sid]
            return jsonify({"status": "reset", "stream_id": sid})
        else:
            return jsonify({"status": "not_found", "stream_id": sid})


STREAM_TTL_SECONDS = 300   # Auto-delete after 5 minutes inactivity
MAX_STREAMS = 100          # Keep only last 100 active streams


# --------------------------------------------------------------
# AUTO CLEANUP FOR STREAM STATES
# --------------------------------------------------------------
def cleanup_stream_states():
    while True:
        now = time.time()
        with stream_states_lock:
            # A) Remove expired streams
            expired = [
                sid for sid, st in stream_states.items()
                if now - st.last_update > STREAM_TTL_SECONDS
            ]
            for sid in expired:
                del stream_states[sid]

            # B) Enforce limit on number of streams
            if len(stream_states) > MAX_STREAMS:
                ordered = sorted(
                    stream_states.items(),
                    key=lambda x: x[1].last_update
                )
                excess = len(stream_states) - MAX_STREAMS
                for sid, _ in ordered[:excess]:
                    del stream_states[sid]

        time.sleep(10)  # run every 10 seconds


# start background cleanup thread
threading.Thread(target=cleanup_stream_states, daemon=True).start()


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
    model_cache["large-v3-turbo"] = whisper.load_model(
        "large-v3-turbo",
        device=device,
        download_root=model_cache_dir
    )
    warm_up(model_cache["large-v3-turbo"])
    print("Model is Ready to Use")

    from waitress import serve

    serve(app, host="0.0.0.0", port=8001)
