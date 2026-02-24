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
import random
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging

# Ignore SSL warnings
warnings.filterwarnings("ignore", category=InsecureRequestWarning)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# AES Configuration
AES_KEY = b'Yg&tc%DEuh6%Zc^8'
AES_IV = b'6oyZDr22E3ychjM%'

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ==================== OPTIMIZATION 1: MEGA CONNECTION POOL ====================
def create_mega_session():
    """Create ultra-optimized session for maximum speed"""
    session = requests.Session()
    
    # Optimized retry strategy - minimal retries for speed
    retry_strategy = Retry(
        total=1,  # Only 1 retry for speed
        backoff_factor=0.1,
        status_forcelist=[429, 500, 502, 503],
    )
    
    # Massive connection pool
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=200,
        pool_maxsize=200,
        pool_block=False
    )
    
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Set default headers once
    session.headers.update({
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive'
    })
    
    return session

# Create 100 sessions in pool for parallel processing
SESSION_POOL = [create_mega_session() for _ in range(100)]
session_counter = 0

def get_mega_session():
    """Get session instantly from pool (round-robin)"""
    global session_counter
    session = SESSION_POOL[session_counter % len(SESSION_POOL)]
    session_counter += 1
    return session

# ==================== OPTIMIZATION 2: MEGA USER AGENT POOL ====================
# Generate 100+ user agents dynamically
USER_AGENTS = []
android_versions = ['5.0', '6.0', '7.0', '8.0', '9.0', '10', '11', '12', '13', '14']
devices = [
    ('SM-G988B', 'RP1A.200720.009'),
    ('Pixel 6', 'SP1A.210812.016'),
    ('Redmi Note 10', 'RQ1A.210105.003'),
    ('OnePlus 9', 'RP1A.200720.009'),
    ('ASUS_Z01QD', 'PI'),
    ('SM-G975F', 'QP1A.190711.020'),
    ('Pixel 5', 'RD1A.201105.003'),
    ('SM-G998B', 'SP1A.210812.016'),
    ('Redmi 4X', 'N2G47H'),
    ('SM-S908B', 'TP1A.220624.014')
]

for android in android_versions:
    for device, build in devices:
        USER_AGENTS.append(f"Dalvik/2.1.0 (Linux; U; Android {android}; {device} Build/{build})")

# IP Ranges for X-Forwarded-For
IP_RANGES = [f"172.{i}.{j}.{k}" for i in range(16, 32) for j in range(0, 255) for k in range(1, 255)][:500]

# ==================== OPTIMIZATION 3: PRE-COMPUTED DATA ====================
# Static game data that never changes
STATIC_GAME_DATA = {
    "game_name": "free fire",
    "game_version": 1,
    "version_code": "1.108.3",
    "os_info": "Android OS 9",
    "device_type": "Handheld",
    "network_provider": "Verizon Wireless",
    "connection_type": "WIFI",
    "screen_width": 1280,
    "screen_height": 960,
    "dpi": "240",
    "cpu_info": "ARMv7 VFPv3 NEON VMH | 2400 | 4",
    "total_ram": 5951,
    "gpu_name": "Adreno (TM) 640",
    "gpu_version": "OpenGL ES 3.0",
    "user_id": "Google|74b585a9-0268-4ad3-8f36-ef41d2e53610",
    "language": "en",
    "platform_type": 4,
    "device_form_factor": "Handheld",
    "device_model": "Asus ASUS_I005DA",
    "library_path": "/data/app/com.dts.freefireth-QPvBnTUhYWE-7DMZSOGdmA==/lib/arm",
    "apk_info": "5b892aaabd688e571f688053118a162b|/data/app/com.dts.freefireth-QPvBnTUhYWE-7DMZSOGdmA==/base.apk",
    "os_architecture": "32",
    "build_number": "2019117877",
    "graphics_backend": "OpenGLES2",
    "max_texture_units": 16383,
    "rendering_api": 4,
    "encoded_field_89": "\u0017T\u0011\u0017\u0002\b\u000eUMQ\bEZ\u0003@ZK;Z\u0002\u000eV\ri[QVi\u0003\ro\t\u0007e",
    "marketplace": "3rd_party",
    "encryption_key": "KqsHT2B4It60T/65PGR5PXwFxQkVjGNi+IMCK3CFBCBfrNpSUA1dZnjaT3HcYchlIFFL1ZJOg0cnulKCPGD3C3h1eFQ=",
    "total_storage": 111107
}

# Numeric fields that never change
NUMERIC_FIELDS = [
    ('field_60', 32968), ('field_61', 29815), ('field_62', 2479),
    ('field_63', 914), ('field_64', 31213), ('field_65', 32968),
    ('field_66', 31213), ('field_67', 32968), ('field_70', 4),
    ('field_73', 2), ('field_76', 1), ('field_78', 6),
    ('field_79', 1), ('field_85', 1), ('field_92', 9204),
    ('field_97', 1), ('field_98', 1)
]

# ==================== OPTIMIZATION 4: ULTRA FAST FUNCTIONS ====================
def get_random_ip():
    """Get random IP instantly"""
    return random.choice(IP_RANGES)

def get_random_ua():
    """Get random user agent instantly"""
    return random.choice(USER_AGENTS)

def get_token_fast(uid, password):
    """Super fast token retrieval"""
    url = "https://ffmconnect.live.gop.garenanow.com/oauth/guest/token/grant"
    
    headers = {
        "Host": "100067.connect.garena.com",
        "User-Agent": get_random_ua(),
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Forwarded-For": get_random_ip()
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
        session = get_mega_session()
        response = session.post(url, headers=headers, data=data, timeout=5, verify=False)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.error(f"Token error for {uid}: {e}")
    
    return None

def encrypt_message_fast(plaintext):
    """Fast AES encryption"""
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    padded_message = pad(plaintext, AES.block_size)
    return cipher.encrypt(padded_message)

def parse_response_fast(response_content):
    """Fast response parsing"""
    response_dict = {}
    lines = response_content.split("\n")
    for line in lines:
        if ":" in line:
            key, value = line.split(":", 1)
            response_dict[key.strip()] = value.strip().strip('"')
    return response_dict

def create_game_data_fast(uid, token_data):
    """Ultra fast game data creation"""
    game_data = my_pb2.GameData()
    
    # Set static fields (fastest way)
    for key, value in STATIC_GAME_DATA.items():
        if hasattr(game_data, key):
            setattr(game_data, key, value)
    
    # Set dynamic fields
    game_data.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    game_data.ip_address = get_random_ip()
    game_data.open_id = token_data.get('open_id', '')
    game_data.access_token = token_data.get('access_token', '')
    game_data.field_99 = "4"
    game_data.field_100 = "4"
    
    # Set numeric fields in batch
    for field, value in NUMERIC_FIELDS:
        setattr(game_data, field, value)
    
    return game_data

def process_single_account_fast(account):
    """Process one account super fast"""
    uid = account.get('uid')
    password = account.get('password')
    
    if not uid or not password:
        return None
    
    try:
        # Step 1: Get token (1-2 seconds)
        token_data = get_token_fast(uid, password)
        if not token_data:
            return None
        
        # Step 2: Create game data (< 0.1 second)
        game_data = create_game_data_fast(uid, token_data)
        
        # Step 3: Serialize (< 0.1 second)
        serialized_data = game_data.SerializeToString()
        
        # Step 4: Encrypt (< 0.1 second)
        encrypted_data = encrypt_message_fast(serialized_data)
        hex_data = binascii.hexlify(encrypted_data).decode('utf-8')
        
        # Step 5: Send login request (1-2 seconds)
        url = "https://loginbp.ggblueshark.com/MajorLogin"
        headers = {
            'User-Agent': get_random_ua(),
            'Content-Type': "application/octet-stream",
            'X-GA': "v1 1",
            'X-Unity-Version': "2018.4.11f1",
            'ReleaseVersion': "OB52",
            'X-Forwarded-For': get_random_ip()
        }
        
        edata = bytes.fromhex(hex_data)
        session = get_mega_session()
        response = session.post(url, data=edata, headers=headers, verify=False, timeout=5)
        
        if response.status_code == 200:
            example_msg = output_pb2.Garena_420()
            example_msg.ParseFromString(response.content)
            parsed_resp = parse_response_fast(str(example_msg))
            token = parsed_resp.get("token", "N/A")
            
            if token != "N/A":
                return {
                    "uid": uid,
                    "token": token
                }
        
    except Exception as e:
        logger.error(f"Error processing {uid}: {e}")
    
    return None

# ==================== OPTIMIZATION 5: PARALLEL PROCESSING ====================
def process_batch_parallel(accounts, workers=50):
    """Process accounts in parallel for maximum speed"""
    total = len(accounts)
    results = []
    
    logger.info(f"Starting parallel processing of {total} accounts with {workers} workers")
    
    # Use ThreadPoolExecutor for parallel execution
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        # Submit all tasks
        future_to_account = {
            executor.submit(process_single_account_fast, account): account 
            for account in accounts
        }
        
        # Collect results as they complete
        completed = 0
        for future in concurrent.futures.as_completed(future_to_account):
            completed += 1
            result = future.result(timeout=10)
            if result:
                results.append(result)
            
            # Log progress every 10 accounts
            if completed % 10 == 0:
                logger.info(f"Progress: {completed}/{total} accounts processed")
    
    return results

# ==================== OPTIMIZATION 6: CHUNKED PROCESSING ====================
def process_batch_chunked(accounts, chunk_size=20):
    """Process in chunks to avoid overwhelming"""
    all_results = []
    total = len(accounts)
    
    # Split into chunks
    for i in range(0, total, chunk_size):
        chunk = accounts[i:i+chunk_size]
        chunk_num = i//chunk_size + 1
        total_chunks = (total-1)//chunk_size + 1
        
        logger.info(f"Processing chunk {chunk_num}/{total_chunks} ({len(chunk)} accounts)")
        
        # Process chunk in parallel
        chunk_results = process_batch_parallel(chunk, workers=min(50, len(chunk)*2))
        all_results.extend(chunk_results)
        
        # Small delay between chunks to avoid rate limiting
        if i + chunk_size < total:
            time.sleep(1)
    
    return all_results

# ==================== FLASK ROUTES ====================
@app.route('/')
def index():
    """Render main page"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload with super fast processing"""
    if 'file' not in request.files:
        return render_template('index.html', error="No file uploaded")
    
    file = request.files['file']
    if file.filename == '':
        return render_template('index.html', error="No file selected")
    
    try:
        # Read JSON file
        accounts = json.load(file)
        
        # Limit accounts
        if len(accounts) > 500:
            return render_template('index.html', error="Maximum 500 accounts allowed")
        
        start_time = time.time()
        
        # Process accounts (auto-select best method based on size)
        if len(accounts) > 100:
            results = process_batch_chunked(accounts, chunk_size=25)
        else:
            results = process_batch_parallel(accounts, workers=50)
        
        processing_time = time.time() - start_time
        
        # Calculate speed
        speed = len(results) / processing_time if processing_time > 0 else 0
        
        # Create output
        output_data = {
            "metadata": {
                "total": len(accounts),
                "successful": len(results),
                "failed": len(accounts) - len(results),
                "time_seconds": round(processing_time, 2),
                "speed": f"{round(speed, 2)} tokens/sec",
                "timestamp": datetime.now().isoformat()
            },
            "tokens": results
        }
        
        # Create downloadable file
        json_output = json.dumps(output_data, indent=2)
        output_file = io.BytesIO()
        output_file.write(json_output.encode('utf-8'))
        output_file.seek(0)
        
        return send_file(
            output_file,
            mimetype='application/json',
            as_attachment=True,
            download_name=f'tokens_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        )
        
    except json.JSONDecodeError:
        return render_template('index.html', error="Invalid JSON file format")
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return render_template('index.html', error=f"Error: {str(e)}")

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
    
    account = {"uid": uid, "password": password}
    result = process_single_account_fast(account)
    
    if not result:
        return render_template('index.html', error="Failed to generate token")
    
    return render_template('index.html', success=True, token_data=result)

@app.route('/api/process', methods=['POST'])
def api_process():
    """API endpoint for batch processing"""
    try:
        data = request.get_json()
        accounts = data.get('accounts', [])
        
        if not accounts:
            return jsonify({"error": "No accounts provided"}), 400
        
        start_time = time.time()
        results = process_batch_parallel(accounts, workers=50)
        processing_time = time.time() - start_time
        
        return jsonify({
            "success": True,
            "total": len(accounts),
            "successful": len(results),
            "time": round(processing_time, 2),
            "results": results
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/stats')
def stats():
    """API stats"""
    return jsonify({
        "status": "online",
        "version": "5.0",
        "performance": {
            "workers": 50,
            "pool_size": 100,
            "max_accounts": 500,
            "speed": "20-30 tokens/sec"
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True, threaded=True)
