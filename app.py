from flask import Flask, request, redirect, render_template, jsonify
import firebase_admin
from firebase_admin import credentials, db
import string
import random
import os, dotenv

dotenv.load_dotenv()

app = Flask(__name__)

# ====================== Firebase Setup ======================
firebase_initialized = False

try:
        cred = credentials.Certificate(os.getenv("ENV_KEY_ONE", ""))
        firebase_admin.initialize_app(cred, {
            'databaseURL': os.getenv("FB_URL", "")  # ← CHANGE THIS
        })
        firebase_initialized = True
        print("✅ Firebase initialized successfully!")
except Exception as e:
    print(f"⚠️ Firebase initialization failed: {e}")

# ====================== Helper Functions ======================
def generate_short_code(length=6):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

# ====================== Routes ======================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/shorten', methods=['POST'])
def shorten():
    if not firebase_initialized:
        return jsonify({"error": "We received an invalid request"}), 500

    long_url = request.form.get('url')
    if not long_url:
        return jsonify({"error": "URL is required"}), 400

    short_code = generate_short_code()
    ref = db.reference('urls')
    
    # Ensure unique short code
    while ref.child(short_code).get():
        short_code = generate_short_code()

    ref.child(short_code).set({
        'long_url': long_url,
        'clicks': 0
    })

    short_url = f"{request.host_url.rstrip('/')}/{short_code}"
    
    return jsonify({
        "short_url": short_url,
        "original_url": long_url,
        "code": short_code
    })

@app.route('/<short_code>')
def redirect_url(short_code):
    if short_code in ['favicon.ico', 'robots.txt']:
        return "Not found", 404

    if not firebase_initialized:
        return "Service not configured", 500

    try:
        ref = db.reference(f'urls/{short_code}')
        url_data = ref.get()
        
        if url_data and 'long_url' in url_data:
            ref.child('clicks').set(url_data.get('clicks', 0) + 1)
            return redirect(url_data['long_url'])
        else:
            return "❌ Short URL not found", 404
    except Exception:
        return "Internal error", 500

@app.route('/stats/<short_code>')
def stats(short_code):
    if not firebase_initialized:
        return jsonify({"error": "Firebase not configured"}), 500
    ref = db.reference(f'urls/{short_code}')
    data = ref.get()
    return jsonify(data) if data else jsonify({"error": "Not found"}), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)