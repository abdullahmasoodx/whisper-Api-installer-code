from flask import Flask, request, jsonify
import datetime

app = Flask(__name__)
LOG_FILE = "logs.txt"
model_name = "default"



def log_message(message):
    timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} {message}\n")


@app.route('/testapi')
def test_api():
    ip = request.remote_addr or "unknown"
    user_agent = request.headers.get('User-Agent', 'unknown')
    log_message(f"✅ /testapi was hit by {ip} | UA: {user_agent}")
    #log_message(f"✅ /testapi was hit by {ip} | UA: ")
    return jsonify({"message": "Test API hit!", "model": model_name})

@app.route('/set_model', methods=['POST'])
def set_model():
    global model_name
    data = request.get_json()
    new_model = data.get("model")
    if new_model:
        model_name = new_model
        log_message(f"🚀 Model updated to: {model_name}")
        return jsonify({"status": "success", "model": model_name})
    return jsonify({"status": "error", "message": "Model not provided"}), 400

if __name__ == "__main__":
    app.run(port=5000)
