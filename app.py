import time
import json
import requests
import urllib3
import binascii
from datetime import datetime
from flask import Flask, request, jsonify, Response
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

# প্রোটোবাফ ফাইলগুলো (অবশ্যই সার্ভারে এই ৪টি ফাইল থাকতে হবে)
import data_pb2
import encode_id_clan_pb2
import my_pb2
import output_pb2

# গেম ভার্সন ভেরিয়েবল ইমপোর্ট করা হলো
from game_version import (
    CLIENT_VERSION,
    CLIENT_VERSION_CODE,
    UNITY_VERSION,
    RELEASE_VERSION,
    MSDK_VERSION,
    USER_AGENT_MODEL,
    ANDROID_OS_VERSION
)

# SSL Warning বন্ধ করার জন্য
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
app.json.sort_keys = False

# AES এনক্রিপশন কি (Key) এবং আইভি (IV) - Login এবং Clan Data উভয়ের জন্য
AES_KEY = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
AES_IV = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

def encrypt_message(plaintext, key_bytes, iv_bytes):
    cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
    padded_message = pad(plaintext, AES.block_size)
    return cipher.encrypt(padded_message)

# =====================================================================
# নতুন PROTOBUF ভিত্তিক লগইন সিস্টেম (আপনার দেওয়া ফাইল থেকে)
# =====================================================================

def get_access_token(uid, password):
    oauth_url = "https://100067.connect.garena.com/oauth/guest/token/grant"
    payload = {
        'uid': uid,
        'password': password,
        'response_type': "token",
        'client_type': "2",
        'client_secret': "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
        'client_id': "100067"
    }
    
    headers = {
        'User-Agent': f"GarenaMSDK/{MSDK_VERSION}({USER_AGENT_MODEL} ;{ANDROID_OS_VERSION};pt;BR;)",
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip"
    }

    try:
        response = requests.post(oauth_url, data=payload, headers=headers, timeout=15, verify=False)
        if response.status_code == 200:
            data = response.json()
            if 'access_token' in data and 'open_id' in data:
                return {"success": True, "access_token": data["access_token"], "open_id": data["open_id"]}
        return {"success": False, "error": "Invalid UID or Password"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def major_login(access_token, open_id, platform_type=4):
    try:
        game_data = my_pb2.GameData()
        game_data.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        game_data.game_name = "free fire"
        game_data.game_version = 1
        game_data.version_code = CLIENT_VERSION
        game_data.os_info = f"{ANDROID_OS_VERSION} / API-29 (rel.cjw.20220518.114133)"
        game_data.device_type = "Handheld"
        game_data.network_provider = "Verizon Wireless"
        game_data.connection_type = "WIFI"
        game_data.screen_width = 1280
        game_data.screen_height = 960
        game_data.dpi = "240"
        game_data.cpu_info = "ARMv7 VFPv3 NEON VMH | 2400 | 4"
        game_data.total_ram = 5951
        game_data.gpu_name = "Adreno (TM) 640"
        game_data.gpu_version = "OpenGL ES 3.0"
        game_data.user_id = "Google|74b585a9-0268-4ad3-8f36-ef41d2e53610"
        game_data.ip_address = "172.190.111.97"
        game_data.language = "en"
        game_data.open_id = open_id
        game_data.access_token = access_token
        game_data.platform_type = platform_type
        game_data.field_99 = str(platform_type)
        game_data.field_100 = str(platform_type)

        serialized_data = game_data.SerializeToString()
        encrypted_data = encrypt_message(serialized_data, AES_KEY[:16], AES_IV[:16])
        hex_encrypted_data = binascii.hexlify(encrypted_data).decode('utf-8')

        url = "https://loginbp.ggpolarbear.com/MajorLogin"
        
        headers = {
            "User-Agent": f"Dalvik/2.1.0 (Linux; U; {ANDROID_OS_VERSION}; {USER_AGENT_MODEL} Build/PI)",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip",
            "Content-Type": "application/octet-stream",
            "Expect": "100-continue",
            "X-Unity-Version": UNITY_VERSION,
            "X-GA": "v1 1",
            "ReleaseVersion": RELEASE_VERSION
        }
        edata = bytes.fromhex(hex_encrypted_data)

        response = requests.post(url, data=edata, headers=headers, timeout=20, verify=False)

        if response.status_code == 200:
            try:
                example_msg = output_pb2.Garena_420()
                example_msg.ParseFromString(response.content)
                data_dict = {field.name: getattr(example_msg, field.name)
                             for field in example_msg.DESCRIPTOR.fields
                             if field.name not in ["binary", "binary_data", "Garena420"]}
            except:
                data_dict = response.json()

            if data_dict and "token" in data_dict:
                return {"success": True, "jwt_token": data_dict["token"]}
        return {"success": False, "error": f"MajorLogin failed. Status: {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": f"MajorLogin error: {str(e)}"}


############## TOKEN MANAGEMENT ##########
jwt_token = None
token_expiry = 0

def get_jwt_token():
    global jwt_token, token_expiry
    
    # টোকেন ভ্যালিড থাকলে সেটাই রিটার্ন করবে
    if jwt_token and time.time() < token_expiry:
        return jwt_token

    target_uid = "3763606630"
    target_pass = "7FF33285F290DDB97D9A31010DCAA10C2021A03F27C4188A2F6ABA418426527C"
    
    print("Generating new JWT token via Protobuf...")
    access_result = get_access_token(target_uid, target_pass)
    
    if access_result['success']:
        jwt_result = major_login(access_result['access_token'], access_result['open_id'])
        if jwt_result['success']:
            jwt_token = jwt_result['jwt_token']
            token_expiry = time.time() + (5 * 3600)  # ৫ ঘণ্টার জন্য ক্যাশ
            return jwt_token
        else:
            print(f"MajorLogin Error: {jwt_result.get('error')}")
    else:
        print(f"Access Token Error: {access_result.get('error')}")
            
    return None

# =====================================================================
# API ROUTES (Guild Info)
# =====================================================================

@app.route('/', methods=['GET'])
def index():
    data = {
        "Developer": "Riduanul Islam",
        "TelegramBot": "https://t.me/RiduanFFBot",
        "TelegramChannel": "https://t.me/RiduanOfficialBD",
        "Project": "Riduan FF Info API",
        "Message": "Welcome to Riduan API",
        "API_Usage_Guide": {
            "API_Format": {
                "Get_Clan_Info": "/guild?clan_id=[Clan_ID]"
            },
            "Examples": {
                "By_ID": "/guild?clan_id=3036683032"
            }
        }
    }
    return Response(json.dumps(data, sort_keys=False, indent=4), mimetype='application/json')

@app.route('/guild', methods=['GET'])
def get_clan_info():
    current_token = get_jwt_token()
    if not current_token:
        return jsonify({"error": "Failed to generate JWT token. Please try again."}), 500
    
    clan_id = request.args.get('clan_id')
    if not clan_id:
        return jsonify({"error": "Clan ID is required"}), 400
    
    try:
        json_data = '''
        {{
            "1": {},
            "2": 1
        }}
        '''.format(clan_id)
        data_dict = json.loads(json_data)
        
        my_data = encode_id_clan_pb2.MyData()
        my_data.field1 = data_dict["1"]
        my_data.field2 = data_dict["2"]
        
        data_bytes = my_data.SerializeToString()
        encrypted_data = encrypt_message(data_bytes, AES_KEY[:16], AES_IV[:16])
        formatted_encrypted_data = ' '.join([f"{byte:02X}" for byte in encrypted_data])
        
        url = "https://clientbp.ggblueshark.com/GetClanInfoByClanID"
        request_bytes = bytes.fromhex(formatted_encrypted_data.replace(" ", ""))
        
        headers = {
            "Expect": "100-continue",
            "Authorization": f"Bearer {current_token}",
            "X-Unity-Version": UNITY_VERSION,
            "X-GA": "v1 1",
            "ReleaseVersion": RELEASE_VERSION.lower(),
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": f"Dalvik/2.1.0 (Linux; U; {ANDROID_OS_VERSION}; {USER_AGENT_MODEL} Build/RP1A.200720.012)",
            "Host": "clientbp.ggblueshark.com",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip"
        }
        
        response = requests.post(url, headers=headers, data=request_bytes, verify=False, timeout=60)
            
        if response.status_code == 200:
            if response.content:
                response_message = data_pb2.response()
                response_message.ParseFromString(response.content)
                timestamp1_normal = datetime.fromtimestamp(response_message.timestamp1)
                timestamp2_normal = datetime.fromtimestamp(response_message.timestamp2)
                
                try:
                    officers_list = json.loads(response_message.big_numbers) if response_message.big_numbers else []
                except:
                    officers_list = response_message.big_numbers

                formatted_response = {
                    "Developer": "Riduanul Islam",
                    "TelegramBot": "https://t.me/RiduanFFBot",
                    "TelegramChannel": "https://t.me/RiduanOfficialBD",
                    "guild_info": {
                        "guild_name": response_message.special_code,
                        "guild_id": response_message.id,
                        "level": response_message.rank,
                        "region": response_message.region,
                        "creation_date": timestamp1_normal.strftime("%Y-%m-%d %H:%M:%S"),
                        "last_updated": timestamp2_normal.strftime("%Y-%m-%d %H:%M:%S")
                    },
                    "guild_members": {
                        "max_capacity": response_message.sub_type,
                        "current_members": response_message.version
                    },
                    "glory_stats": {
                        "total_glory": response_message.total_playtime,
                        "weekly_glory": response_message.energy,
                        "guild_xp": response_message.balance
                    },
                    "notice": response_message.welcome_message,
                    
                    "guild_leader": response_message.status_code,
                    "acting_leader": response_message.value_a,
                    "guild_officers": officers_list,
                    
                    "system_info": {
                        "error_code": response_message.error_code
                    }
                }
                
                return Response(json.dumps(formatted_response, sort_keys=False, indent=4), mimetype='application/json')
            else:
                return jsonify({"error": "No content in response from Free Fire server"}), 500

        else:
            return jsonify({"error": f"Failed to fetch data: {response.status_code}"}), response.status_code

    except Exception as e:
        return jsonify({
            "error": "An internal server error occurred.",
            "details": str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
