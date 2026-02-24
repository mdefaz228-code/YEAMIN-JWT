import sys
sys.path.append("/")

from flask import Flask, jsonify, request, make_response, render_template, send_file, session
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
import asyncio
import aiohttp
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import multiprocessing
from queue import Queue
import logging

# Ignore SSL certificate warnings
warnings.filterwarnings("ignore", category=InsecureRequestWarning)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# AES encryption key and initialization vector
AES_KEY = b'Yg&tc%DEuh6%Zc^8'
AES_IV = b'6oyZDr22E3ychjM%'

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Store job status
jobs = {}
jobs_lock = threading.Lock()

# Rotating User Agents (expanded)
USER_AGENTS = [
    "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
    "Dalvik/2.1.0 (Linux; U; Android 10; SM-G975F Build/QP1A.190711.020)",
    "Dalvik/2.1.0 (Linux; U; Android 11; Pixel 5 Build/RD1A.201105.003)",
    "Dalvik/2.1.0 (Linux; U; Android 12; SM-G998B Build/SP1A.210812.016)",
    "Dalvik/2.1.0 (Linux; U; Android 13; SM-S908B Build/TP1A.220624.014)",
    "Dalvik/2.1.0 (Linux; U; Android 8.1.0; Redmi Note 5 Build/O11019)",
    "Dalvik/2.1.0 (Linux; U; Android 7.1.2; Redmi 4X Build/N2G47H)",
    "Dalvik/2.1.0 (Linux; U; Android 6.0; ASUS_Z010D Build/MMB29P)",
    "Dalvik/2.1.0 (Linux; U; Android 14; SM-S918B Build/UP1A.230105)",
    "Dalvik/2.1.0 (Linux; U; Android 5.1.1; SM-G900H Build/LMY48G)"
]

# IP ranges for X-Forwarded-For
IP_RANGES = [
    "172.190.{}.{}", "192.168.{}.{}", "10.0.{}.{}", "172.16.{}.{}",
    "172.31.{}.{}", "192.168.{}.{}", "10.10.{}.{}", "172.20.{}.{}"
]

# ==================== OPTIMIZATION 1: Connection Pooling ====================
def create_session():
    """Create a requests session with retry strategy and connection pooling"""
    session = requests.Session()
    retry_strategy = Retry(
        total=2,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=100,  # Increased pool size
        pool_maxsize=100,
        pool_block=False
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

# Create session pool (50 sessions for parallel processing)
SESSION_POOL = [create_session() for _ in range(50)]
session_counter = 0

def get_session():
    """Get a session from pool (round-robin)"""
    global session_counter
    session = SESSION_POOL[session_counter % len(SESSION_POOL)]
    session_counter += 1
    return session

# ==================== OPTIMIZATION 2: Async/AIOHTTP ====================
async def fetch_token_async(session, uid, password):
    """Async token fetch using aiohttp"""
    url = "https://ffmconnect.live.gop.garenanow.com/oauth/guest/token/grant"
    
    headers = {
        "Host": "100067.connect.garena.com",
        "User-Agent": random.choice(USER_AGENTS),
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "X-Forwarded-For": f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
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
        async with session.post(url, headers=headers, data=data, ssl=False, timeout=10) as response:
            if response.status == 200:
                return await response.json()
    except:
        return None
    return None

async def fetch_login_async(session, edata, headers):
    """Async login request using aiohttp"""
    url = "https://loginbp.ggblueshark.com/MajorLogin"
    try:
        async with session.post(url, data=edata, headers=headers, ssl=False, timeout=10) as response:
            if response.status == 200:
                return await response.read()
    except:
        pass
    return None

# ==================== OPTIMIZATION 3: Batch Processing ====================
def get_random_ip():
    """Generate random IP fast"""
    template = random.choice(IP_RANGES)
    return template.format(random.randint(1, 254), random.randint(1, 254))

def get_token_fast(uid, password):
    """Ultra-fast token retrieval with connection pooling"""
    url = "https://ffmconnect.live.gop.garenanow.com/oauth/guest/token/grant"
    
    headers = {
        "Host": "100067.connect.garena.com",
        "User-Agent": random.choice(USER_AGENTS),
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
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
        session = get_session()
        response = session.post(url, headers=headers, data=data, timeout=10, verify=False)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.error(f"Token error for {uid}: {e}")
    return None

def encrypt_message_fast(plaintext):
    """Fast AES encryption - pre-computed where possible"""
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

# ==================== OPTIMIZATION 4: Pre-computed Game Data ====================
BASE_GAME_DATA = {
    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "game_name": "free fire",
    "game_version": 1,
    "version_code": "1.108.3",
    "os_info": "Android OS 9 / API-28",
    "device_type": "Handheld",
    "network_provider": "Verizon",
    "connection_type": "WIFI",
    "screen_width": 1280,
    "screen_height": 960,
    "dpi": "240",
    "cpu_info": "ARMv7 | 2400 | 4",
    "total_ram": 5951,
    "gpu_name": "Adreno 640",
    "user_id": "Google|74b585a9-0268-4ad3-8f36-ef41d2e53610",
    "language": "en",
    "platform_type": 4,
    "device_form_factor": "Handheld",
    "device_model": "Asus ASUS_I005DA",
    "library_path": "/data/app/com.dts.freefireth/lib/arm",
    "apk_info": "5b892aaabd688e571f688053118a162b|base.apk",
    "os_architecture": "32",
    "build_number": "2019117877",
    "graphics_backend": "OpenGLES2",
    "max_texture_units": 16383,
    "rendering_api": 4,
    "encoded_field_89": "\u0017T\u0011\u0017\u0002\b\u000eUMQ\bEZ\u0003@ZK;Z\u0002\u000eV\ri[QVi\u0003\ro\t\u0007e",
    "marketplace": "3rd_party",
    "encryption_key": "KqsHT2B4It60T/65PGR5PXwFxQkVjGNi+IMCK3CFBCBfrNpSUA1dZnjaT3HcYchlIFFL1ZJOg0cnulKCPGD3C3h1eFQ=",
    "total_storage": 111107,
    "field_99": "4",
    "field_100": "4"
}

NUMERIC_FIELDS = [
    ('field_60', 32968), ('field_61', 29815), ('field_62', 2479),
    ('field_63', 914), ('field_64', 31213), ('field_65', 32968),
    ('field_66', 31213), ('field_67', 32968), ('field_70', 4),
    ('field_73', 2), ('field_76', 1), ('field_78', 6),
    ('field_79', 1), ('field_85', 1), ('field_92', 9204),
    ('field_97', 1), ('field_98', 1)
]

def create_game_data_fast(uid, token_data):
    """Ultra-fast game data creation using pre-computed template"""
    game_data = my_pb2.GameData()
    
    # Copy base data
    for key, value in BASE_GAME_DATA.items():
        if hasattr(game_data, key):
            setattr(game_data, key, value)
    
    # Set dynamic fields
    game_data.ip_address = get_random_ip()
    game_data.open_id = token_data.get('open_id', '')
    game_data.access_token = token_data.get('access_token', '')
    
    # Set numeric fields in batch
    for field, value in NUMERIC_FIELDS:
        setattr(game_data, field, value)
    
    return game_data

# ==================== OPTIMIZATION 5: Parallel Processing with Thread Pools ====================
def process_single_account(params):
    """
    Process a single account - optimized for parallel execution
    """
    uid, password = params
    
    try:
        # Step 1: Get token (fast)
        token_data = get_token_fast(uid, password)
        if not token_data:
            return None
        
        # Step 2: Create game data (ultra-fast)
        game_data = create_game_data_fast(uid, token_data)
        
        # Step 3: Serialize
        serialized_data = game_data.SerializeToString()
        
        # Step 4: Encrypt
        encrypted_data = encrypt_message_fast(serialized_data)
        hex_data = binascii.hexlify(encrypted_data).decode('utf-8')
        
        # Step 5: Send login request
        url = "https://loginbp.ggblueshark.com/MajorLogin"
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Connection': "keep-alive",
            'Accept-Encoding': "gzip",
            'Content-Type': "application/octet-stream",
            'X-GA': "v1 1",
            'X-Unity-Version': "2018.4.11f1",
            'ReleaseVersion': "OB52",
            'X-Forwarded-For': get_random_ip()
        }
        
        edata = bytes.fromhex(hex_data)
        session = get_session()
        response = session.post(url, data=edata, headers=headers, verify=False, timeout=10)
        
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

def process_batch_super_fast(accounts, max_workers=50):
    """
    Process accounts in parallel with maximum speed
    """
    # Prepare parameters
    params = [(acc.get('uid'), acc.get('password')) for acc in accounts if acc.get('uid') and acc.get('password')]
    
    results = []
    
    # Use ThreadPoolExecutor with optimal worker count
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_account = {
            executor.submit(process_single_account, param): param 
            for param in params
        }
        
        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_account):
            try:
                result = future.result(timeout=30)
                if result:
                    results.append(result)
            except concurrent.futures.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Future error: {e}")
    
    return results

# ==================== OPTIMIZATION 6: Async Batch Processing ====================
async def process_account_async(uid, password, semaphore):
    """Async version for even faster processing"""
    async with semaphore:
        try:
            async with aiohttp.ClientSession() as session:
                # Get token
                token_data = await fetch_token_async(session, uid, password)
                if not token_data:
                    return None
                
                # Create game data (can't be async, but it's fast)
                game_data = create_game_data_fast(uid, token_data)
                serialized_data = game_data.SerializeToString()
                encrypted_data = encrypt_message_fast(serialized_data)
                hex_data = binascii.hexlify(encrypted_data).decode('utf-8')
                
                # Login request
                headers = {
                    'User-Agent': random.choice(USER_AGENTS),
                    'Connection': "keep-alive",
                    'Accept-Encoding': "gzip",
                    'Content-Type': "application/octet-stream",
                    'X-GA': "v1 1",
                    'X-Unity-Version': "2018.4.11f1",
                    'ReleaseVersion': "OB52"
                }
                
                edata = bytes.fromhex(hex_data)
                response_data = await fetch_login_async(session, edata, headers)
                
                if response_data:
                    example_msg = output_pb2.Garena_420()
                    example_msg.ParseFromString(response_data)
                    parsed_resp = parse_response_fast(str(example_msg))
                    token = parsed_resp.get("token", "N/A")
                    
                    if token != "N/A":
                        return {"uid": uid, "token": token}
        except:
            pass
    
    return None

async def process_batch_async(accounts, max_concurrent=100):
    """Async batch processing for maximum speed"""
    semaphore = asyncio.Semaphore(max_concurrent)
    tasks = []
    
    for account in accounts:
        uid = account.get('uid')
        password = account.get('password')
        if uid and password:
            tasks.append(process_account_async(uid, password, semaphore))
    
    results = await asyncio.gather(*tasks)
    return [r for r in results if r]

# ==================== OPTIMIZATION 7: Chunked Processing ====================
def process_batch_chunked(accounts, chunk_size=20):
    """
    Process in chunks to avoid overwhelming the system
    """
    all_results = []
    total_accounts = len(accounts)
    
    # Split into chunks
    for i in range(0, total_accounts, chunk_size):
        chunk = accounts[i:i+chunk_size]
        logger.info(f"Processing chunk {i//chunk_size + 1}/{(total_accounts-1)//chunk_size + 1}")
        
        # Process chunk in parallel
        chunk_results = process_batch_super_fast(chunk, max_workers=min(50, len(chunk)*2))
        all_results.extend(chunk_results)
        
        # Small delay between chunks to avoid rate limiting
        if i + chunk_size < total_accounts:
            time.sleep(2)
    
    return all_results

# ==================== FLASK ROUTES ====================
@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload with super fast processing"""
    if 'file' not in request.files:
        return render_template('index.html', error="No file uploaded")
    
    file = request.files['file']
    if file.filename == '':
        return render_template('index.html', error="No file selected")
    
    if not file.filename.endswith('.json'):
        return render_template('index.html', error="Please upload a JSON file")
    
    try:
        # Read and parse the uploaded JSON file
        accounts = json.load(file)
        
        # Limit to 1000 accounts
        if len(accounts) > 1000:
            return render_template('index.html', error="Maximum 1000 accounts allowed")
        
        start_time = time.time()
        
        # Use chunked processing for large batches
        if len(accounts) > 100:
            results = process_batch_chunked(accounts, chunk_size=30)
        else:
            results = process_batch_super_fast(accounts, max_workers=50)
        
        processing_time = time.time() - start_time
        
        # Create output with metadata
        output_data = {
            "metadata": {
                "total": len(accounts),
                "successful": len(results),
                "failed": len(accounts) - len(results),
                "time_seconds": round(processing_time, 2),
                "speed": f"{round(len(results)/processing_time, 2)} tokens/sec",
                "timestamp": datetime.now().isoformat()
            },
            "tokens": results
        }
        
        # Create downloadable file
        json_output = json.dumps(output_data, indent=2)
        output_file = io.BytesIO()
        output_file.write(json_output.encode('utf-8'))
        output_file.seek(0)
        
        filename = f'tokens_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        return send_file(
            output_file,
            mimetype='application/json',
            as_attachment=True,
            download_name=filename
        )
        
    except json.JSONDecodeError:
        return render_template('index.html', error="Invalid JSON file format")
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return render_template('index.html', error=f"Error: {str(e)}")

@app.route('/upload-ultra', methods=['POST'])
def upload_ultra():
    """Ultra-fast endpoint using async processing"""
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    try:
        accounts = json.load(file)
        
        # Run async processing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(process_batch_async(accounts, max_concurrent=100))
        loop.close()
        
        return jsonify({
            "success": True,
            "total": len(accounts),
            "successful": len(results),
            "failed": len(accounts) - len(results),
            "results": results
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/token', methods=['GET', 'POST'])
def get_token_response():
    """Single token endpoint"""
    if request.method == 'POST':
        uid = request.form.get('uid')
        password = request.form.get('password')
    else:
        uid = request.args.get('uid')
        password = request.args.get('password')
    
    if not uid or not password:
        return render_template('index.html', error="UID and Password are required!")
    
    result = process_single_account((uid, password))
    
    if not result:
        return render_template('index.html', error="Failed to generate token", uid=uid, password=password)
    
    return render_template('index.html', 
                         success=True, 
                         token_data=result,
                         uid=uid, 
                         password=password)

@app.route('/api/token', methods=['GET', 'POST'])
def api_token():
    """API endpoint for single token"""
    if request.method == 'POST':
        uid = request.form.get('uid')
        password = request.form.get('password')
    else:
        uid = request.args.get('uid')
        password = request.args.get('password')
    
    if not uid or not password:
        return jsonify({"error": "Missing parameters"}), 400
    
    result = process_single_account((uid, password))
    
    if not result:
        return jsonify({"error": "Failed to generate token"}), 500
    
    return jsonify(result)

@app.route('/history')
def history():
    """View history page"""
    return render_template('history.html')

@app.route('/stats')
def stats():
    """API stats endpoint"""
    return jsonify({
        "status": "online",
        "version": "4.0",
        "features": [
            "ultra_fast_parallel",
            "async_processing",
            "connection_pooling",
            "chunked_processing"
        ],
        "performance": {
            "max_workers": 50,
            "pool_size": 100,
            "max_accounts": 1000,
            "estimated_speed": "50-100 tokens/second"
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True, threaded=True)
