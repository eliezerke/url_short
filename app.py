from flask import Flask, request, redirect, render_template, jsonify
import firebase_admin
from firebase_admin import credentials, db
import string
import secrets
import os
import dotenv
import json

dotenv.load_dotenv()

app = Flask(__name__)

# ====================== Firebase Setup ======================
firebase_initialized = False

dta = os.getenv("ENV_KEY_ONE", "")

try:
    cred = credentials.Certificate(json.loads(dta))
    firebase_admin.initialize_app(cred, {
        'databaseURL': os.getenv("FB_URL", "")
    })
    firebase_initialized = True
    print("✅ Firebase initialized successfully!")
except Exception as e:
    print(f"⚠️ Firebase initialization failed: {e}")

# ====================== Base62 Configuration ======================
BASE62_ALPHABET = string.ascii_letters + string.digits  # 62 characters

def generate_short_code(length: int = 6) -> str:
    """Generate a secure random Base62 code"""
    return ''.join(secrets.choice(BASE62_ALPHABET) for _ in range(length))

# ====================== Routes ======================
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/shorten', methods=['POST'])
def shorten():
    if not firebase_initialized:
        return jsonify({"error": "Service not configured"}), 500

    long_url = request.form.get('url')
    if not long_url:
        return jsonify({"error": "URL is required"}), 400

    ref = db.reference('urls')
    max_attempts = 10  # Safety limit to prevent infinite loops

    for attempt in range(max_attempts):
        short_code = generate_short_code(length=6)
        
        # Check if code already exists
        existing = ref.child(short_code).get()
        
        if not existing:
            # No collision → save it
            ref.child(short_code).set({
                'long_url': long_url,
                'clicks': 0,
                'created_at': {".sv": "timestamp"}  # Optional: add timestamp
            })
            
            short_url = f"{request.host_url.rstrip('/')}/{short_code}"
            
            return jsonify({
                "short_url": short_url,
                "original_url": long_url,
                "code": short_code,
                "attempts": attempt + 1
            })
        
        # Collision occurred, try again with new code

    # Rare case: too many collisions
    return jsonify({"error": "Failed to generate unique code. Please try again."}), 500


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
            # Increment clicks atomically
            ref.child('clicks').transaction(lambda current: (current or 0) + 1)
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