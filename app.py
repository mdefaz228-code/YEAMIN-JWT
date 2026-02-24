import sys
sys.path.append("/")

from flask import Flask, jsonify, request, render_template, send_file, session
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import binascii
from protobuf import my_pb2, output_pb2
import os
import warnings
from urllib3.exceptions import InsecureRequestWarning
import json
from datetime import datetime
import io
import time
import concurrent.futures
import threading
import uuid
import random
import logging
from functools import lru_cache
from cachetools import TTLCache

# Ignore SSL warnings
warnings.filterwarnings("ignore", category=InsecureRequestWarning)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# AES encryption
AES_KEY = b'Yg&tc%DEuh6%Zc^8'
AES_IV = b'6oyZDr22E3ychjM%'

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ============= 🚀 OPTIMIZATION 1: CACHING =============
# Cache for encryption results
encryption_cache = TTLCache(maxsize=100, ttl=300)
# Cache for tokens
token_cache = TTLCache(maxsize=1000, ttl=600)

# ============= 🚀 OPTIMIZATION 2: PRE-COMPUTED DATA =============
# Fast User Agents (smaller set)
FAST_USER_AGENTS = [
    "Dalvik/2.1.0 (Android 12; SM-G998B)",
    "Dalvik/2.1.0 (Android 13; SM-S908B)",
    "Dalvik/2.1.0 (Android 11; Pixel 5)",
    "Dalvik/2.1.0 (Android 10; SM-G975F)",
]

# Fast IPs (pre-generated)
FAST_IPS = [
    f"172.190.{x}.{y}" for x in range(1, 5) for y in range(1, 5)
][:50]  # 50 pre-generated IPs

# ============= 🚀 OPTIMIZATION 3: BATCH PROCESSING ENGINE =============
class FastBatchProcessor:
    def __init__(self):
        self.session = self._create_fast_session()
        self.results = []
        self.lock = threading.Lock()
    
    def _create_fast_session(self):
        """Single optimized session"""
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=2
        )
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session
    
    def _get_token_fast(self, uid, password):
        """Ultra fast token retrieval"""
        # Check cache first
        cache_key = f"{uid}:{password}"
        if cache_key in token_cache:
            return token_cache[cache_key]
        
        url = "https://ffmconnect.live.gop.garenanow.com/oauth/guest/token/grant"
        
        headers = {
            "User-Agent": random.choice(FAST_USER_AGENTS),
            "Content-Type": "application/x-www-form-urlencoded",
            "Connection": "keep-alive",
            "X-Forwarded-For": random.choice(FAST_IPS)
        }
        
        data = {
            "uid": uid,
            "password": password,
            "response_type": "token",
            "client_type": "2",
            "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
            "client_id": "100067"
        }
        
        try:
            response = self.session.post(url, headers=headers, data=data, timeout=5, verify=False)
            if response.status_code == 200:
                token_data = response.json()
                token_cache[cache_key] = token_data
                return token_data
        except:
            return None
        return None
    
    def _encrypt_fast(self, data):
        """Cached encryption"""
        data_hash = hash(data)
        if data_hash in encryption_cache:
            return encryption_cache[data_hash]
        
        cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
        padded = pad(data, AES.block_size)
        encrypted = cipher.encrypt(padded)
        encryption_cache[data_hash] = encrypted
        return encrypted
    
    def _process_single(self, account):
        """Process one account super fast"""
        uid = account.get('uid')
        password = account.get('password')
        
        if not uid or not password:
            return None
        
        try:
            # Step 1: Get token (cached)
            token_data = self._get_token_fast(uid, password)
            if not token_data:
                return None
            
            # Step 2: Create minimal game data
            game_data = my_pb2.GameData()
            game_data.open_id = token_data.get('open_id', '')
            game_data.access_token = token_data.get('access_token', '')
            game_data.ip_address = random.choice(FAST_IPS)
            
            # Step 3: Serialize & Encrypt (cached)
            serialized = game_data.SerializeToString()
            encrypted = self._encrypt_fast(serialized)
            hex_data = binascii.hexlify(encrypted).decode('utf-8')
            
            # Step 4: Login request
            url = "https://loginbp.ggblueshark.com/MajorLogin"
            headers = {
                'User-Agent': random.choice(FAST_USER_AGENTS),
                'Content-Type': "application/octet-stream",
                'X-GA': "v1 1",
                'X-Forwarded-For': random.choice(FAST_IPS)
            }
            
            edata = bytes.fromhex(hex_data)
            response = self.session.post(url, data=edata, headers=headers, timeout=5, verify=False)
            
            if response.status_code == 200:
                example_msg = output_pb2.Garena_420()
                example_msg.ParseFromString(response.content)
                
                # Fast parsing
                resp_str = str(example_msg)
                token_start = resp_str.find('token:"') + 7
                if token_start > 6:
                    token_end = resp_str.find('"', token_start)
                    token = resp_str[token_start:token_end]
                    
                    if token and token != "N/A":
                        return {
                            "uid": uid,
                            "token": token,
                            "time": datetime.now().isoformat()
                        }
        except Exception as e:
            logger.error(f"Error: {e}")
        
        return None
    
    def process_batch(self, accounts, max_workers=20):
        """Process batch with thread pool"""
        self.results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            futures = [executor.submit(self._process_single, acc) for acc in accounts]
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result(timeout=10)
                    if result:
                        with self.lock:
                            self.results.append(result)
                except:
                    pass
        
        return self.results

# Initialize processor
processor = FastBatchProcessor()

# ============= 🚀 OPTIMIZATION 4: STREAMING RESPONSE =============
def generate_streaming_response(results, total):
    """Generate JSON in chunks for faster download start"""
    yield '{"metadata": {"total": ' + str(total) + ', "successful": ' + str(len(results)) + ', "timestamp": "' + datetime.now().isoformat() + '"}, "tokens": ['
    
    for i, result in enumerate(results):
        yield json.dumps(result)
        if i < len(results) - 1:
            yield ','
    
    yield ']}'

# ============= 🚀 FLASK ROUTES =============
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Super fast file upload with streaming download"""
    if 'file' not in request.files:
        return render_template('index.html', error="No file uploaded")
    
    file = request.files['file']
    if not file.filename.endswith('.json'):
        return render_template('index.html', error="Please upload a JSON file")
    
    try:
        # Read JSON file
        accounts = json.load(file)
        
        # Limit accounts
        if len(accounts) > 500:
            accounts = accounts[:500]
        
        start_time = time.time()
        
        # Process batch (faster with smaller workers)
        results = processor.process_batch(accounts, max_workers=15)
        
        processing_time = time.time() - start_time
        
        # Create streaming response
        def generate():
            yield f'{{"processing_time": {processing_time}, "successful": {len(results)}, "total": {len(accounts)}, "tokens": ['
            for i, r in enumerate(results):
                yield json.dumps(r)
                if i < len(results) - 1:
                    yield ','
            yield ']}'
        
        response = app.response_class(
            generate(),
            mimetype='application/json',
            headers={
                'Content-Disposition': f'attachment; filename=tokens_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
                'X-Processing-Time': str(processing_time),
                'X-Success-Count': str(len(results))
            }
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return render_template('index.html', error=f"Error: {str(e)}")

@app.route('/fast-upload', methods=['POST'])
def fast_upload():
    """Even faster endpoint for small batches"""
    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400
    
    file = request.files['file']
    
    try:
        accounts = json.load(file)
        
        # Process with minimal workers for speed
        results = processor.process_batch(accounts[:100], max_workers=10)
        
        return jsonify({
            "success": True,
            "count": len(results),
            "results": results,
            "time": time.time()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/token', methods=['GET', 'POST'])
def get_token():
    """Single token endpoint"""
    if request.method == 'POST':
        uid = request.form.get('uid')
        password = request.form.get('password')
    else:
        uid = request.args.get('uid')
        password = request.args.get('password')
    
    if not uid or not password:
        return render_template('index.html', error="UID and Password required!")
    
    # Process single account
    result = processor._process_single({"uid": uid, "password": password})
    
    if result:
        return render_template('index.html', success=True, token_data=result)
    else:
        return render_template('index.html', error="Failed to generate token")

@app.route('/stats')
def stats():
    """Fast stats endpoint"""
    return jsonify({
        "status": "online",
        "version": "5.0",
        "cache": {
            "token_cache": len(token_cache),
            "encryption_cache": len(encryption_cache)
        },
        "performance": "ultra_fast"
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
