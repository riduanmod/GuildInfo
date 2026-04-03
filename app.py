import time
import json
import threading
import requests
import urllib3
from datetime import datetime
from flask import Flask, request, jsonify, Response
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

import data_pb2
import encode_id_clan_pb2

# --- গেম ভার্সন ভেরিয়েবল ইমপোর্ট করা হলো ---
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
# Flask এর ডিফল্ট JSON sorting বন্ধ করার জন্য
app.json.sort_keys = False

###########FREE-FIRE-VERSION###########
freefire_version = RELEASE_VERSION.lower()

#############KEY-AES-CBC#############
key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

####### LOGIN CONFIG ########
REGION_LANG = {"ME": "ar","IND": "hi","ID": "id","VN": "vi","TH": "th","BD": "bn","PK": "ur","TW": "zh","CIS": "ru","SAC": "es","BR": "pt","SG": "en","NA": "en"}
login_hex_key = "32656534343831396539623435393838343531343130363762323831363231383734643064356437616639643866376530306331653534373135623764316533"
login_key = bytes.fromhex(login_hex_key)

def encrypt_api(plain_text):
    plain_text = bytes.fromhex(plain_text)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    cipher_text = cipher.encrypt(pad(plain_text, AES.block_size))
    return cipher_text.hex()

######## LOCAL JWT GENERATOR #########
def login_process(uid, password, region="BD"):
    try:
        url = "https://100067.connect.garena.com/oauth/guest/token/grant"
        
        headers = {
            "User-Agent": f"GarenaMSDK/{MSDK_VERSION}({USER_AGENT_MODEL};{ANDROID_OS_VERSION};en;US;)", 
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        body = {"uid": uid, "password": password, "response_type": "token", "client_type": "2", "client_secret": login_key, "client_id": "100067"}
        resp = requests.post(url, headers=headers, data=body, timeout=20, verify=False)
        
        try:
            data = resp.json()
        except:
            return None 

        if 'access_token' not in data: 
            return None
            
        access_token, open_id = data['access_token'], data['open_id']

        if region in ["ME", "TH"]: 
            url, host = "https://loginbp.common.ggbluefox.com/MajorLogin", "loginbp.common.ggbluefox.com"
        else: 
            url, host = "https://loginbp.ggblueshark.com/MajorLogin", "loginbp.ggblueshark.com"
        lang = REGION_LANG.get(region, "en")
        
        binary_head = b'\x1a\x132025-08-30 05:19:21"\tfree fire(\x01:\x081.120.13B2Android OS 9 / API-28 (PI/rel.cjw.20220518.114133)J\x08HandheldR\nATM MobilsZ\x04WIFI`\xb6\nh\xee\x05r\x03300z\x1fARMv7 VFPv3 NEON VMH | 2400 | 2\x80\x01\xc9\x0f\x8a\x01\x0fAdreno (TM) 640\x92\x01\rOpenGL ES 3.2\x9a\x01+Google|dfa4ab4b-9dc4-454e-8065-e70c733fa53f\xa2\x01\x0e105.235.139.91\xaa\x01\x02'
        binary_tail = b'\xb2\x01 1d8ec0240ede109973f3321b9354b44d\xba\x01\x014\xc2\x01\x08Handheld\xca\x01\x10Asus ASUS_I005DA\xea\x01@afcfbf13334be42036e4f742c80b956344bed760ac91b3aff9b607a610ab4390\xf0\x01\x01\xca\x02\nATM Mobils\xd2\x02\x04WIFI\xca\x03 7428b253defc164018c604a1ebbfebdf\xe0\x03\xa8\x81\x02\xe8\x03\xf6\xe5\x01\xf0\x03\xaf\x13\xf8\x03\x84\x07\x80\x04\xe7\xf0\x01\x88\x04\xa8\x81\x02\x90\x04\xe7\xf0\x01\x98\x04\xa8\x81\x02\xc8\x04\x01\xd2\x04=/data/app/com.dts.freefireth-PdeDnOilCSFn37p1AH_FLg==/lib/arm\xe0\x04\x01\xea\x04_2087f61c19f57f2af4e7feff0b24d9d9|/data/app/com.dts.freefireth-PdeDnOilCSFn37p1AH_FLg==/base.apk\xf0\x04\x03\xf8\x04\x01\x8a\x05\x0232\x9a\x05\n2019119621\xb2\x05\tOpenGLES2\xb8\x05\xff\x7f\xc0\x05\x04\xe0\x05\xf3F\xea\x05\x07android\xf2\x05pKqsHT5ZLWrYljNb5Vqh//yFRlaPHSO9NWSQsVvOmdhEEn7W+VHNUK+Q+fduA3ptNrGB0Ll0LRz3WW0jOwesLj6aiU7sZ40p8BfUE/FI/jzSTwRe2\xf8\x05\xfb\xe4\x06\x88\x06\x01\x90\x06\x01\x9a\x06\x014\xa2\x06\x014\xb2\x06"GQ@O\x00\x0e^\x00D\x06UA\x0ePM\r\x13hZ\x07T\x06\x0cm\\V\x0ejYV;\x0bU5'
        
        full_payload = binary_head + lang.encode("ascii") + binary_tail
        temp_data = full_payload.replace(b'afcfbf13334be42036e4f742c80b956344bed760ac91b3aff9b607a610ab4390', access_token.encode())
        temp_data = temp_data.replace(b'1d8ec0240ede109973f3321b9354b44d', open_id.encode())
        
        final_body = bytes.fromhex(encrypt_api(temp_data.hex()))
        
        headers = {
            "User-Agent": f"Dalvik/2.1.0 (Linux; U; {ANDROID_OS_VERSION}; {USER_AGENT_MODEL} Build/PI)", 
            "Content-Type": "application/x-www-form-urlencoded", 
            "Host": host, 
            "X-GA": "v1 1", 
            "ReleaseVersion": RELEASE_VERSION.upper()
        }
        resp = requests.post(url, headers=headers, data=final_body, verify=False, timeout=30)
        
        if "eyJ" in resp.text:
            token = resp.text[resp.text.find("eyJ"):]
            end = token.find(".", token.find(".") + 1)
            return token[:end + 44] if end != -1 else None
        return None
    except Exception as e:
        print(f"Error generating token locally: {e}")
        return None

############## TOKEN BACKGROUND TASK ##########
jwt_token = None

def get_jwt_token():
    global jwt_token
    target_uid = "3763606630"
    target_pass = "7FF33285F290DDB97D9A31010DCAA10C2021A03F27C4188A2F6ABA418426527C"
    
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        print(f"Generating JWT token locally... (Attempt {attempt}/{max_retries})")
        token = login_process(target_uid, target_pass, "BD")
        
        if token:
            jwt_token = token
            print("JWT Token generated successfully.")
            return
        else:
            print(f"Failed to generate JWT token on attempt {attempt}.")
            if attempt < max_retries:
                print("Retrying in 5 seconds...")
                time.sleep(5)
                
    print("All attempts to generate JWT token failed.")

def token_updater():
    while True:
        get_jwt_token()
        time.sleep(8 * 3600)

threading.Thread(target=token_updater, daemon=True).start()

# --- রুট URL এর সাজানো রেসপন্স ---
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
    global jwt_token
    if not jwt_token:
        return jsonify({"error": "JWT token is missing or generating, please try again in a few seconds."}), 500
    
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
        padded_data = pad(data_bytes, AES.block_size)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        encrypted_data = cipher.encrypt(padded_data)
        formatted_encrypted_data = ' '.join([f"{byte:02X}" for byte in encrypted_data])
        
        url = "https://clientbp.ggblueshark.com/GetClanInfoByClanID"
        request_bytes = bytes.fromhex(formatted_encrypted_data.replace(" ", ""))
        
        headers = {
            "Expect": "100-continue",
            "Authorization": f"Bearer {jwt_token}",
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

                # ডিকশনারিতে মূল পরিবর্তনগুলো করা হয়েছে
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
                    
                    # লিডারের তথ্য এখানে আপডেট করা হয়েছে
                    "guild_leader": response_message.status_code,  # মূল গিল্ড লিডারের আইডি (Field 5)
                    "acting_leader": response_message.value_a,     # অ্যাক্টিং/ভারপ্রাপ্ত লিডারের আইডি (Field 4)
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
