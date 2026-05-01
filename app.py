"""阿里云盘 TV Token 获取工具"""
import os, time, json, hashlib, base64, requests, sys
from flask import Flask, jsonify, send_file, request
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

app = Flask(__name__)
HEADERS = {"User-Agent": "Dalvik/2.1.0 (Linux; U; Android 12; 23046RP50C Build/SP1A.210812.016)"}

# ─── AES 解密（与原项目 decode.ts 完全一致）────────────────
def _h(char_array, modifier):
    unique_chars = list(dict.fromkeys(char_array))
    numeric_modifier = int(str(modifier)[7:]) if len(str(modifier)) > 7 else int(str(modifier))
    result = []
    for ch in unique_chars:
        new_code = abs(ord(ch) - (numeric_modifier % 127) - 1)
        if new_code < 33: new_code += 33
        result.append(chr(new_code))
    return "".join(result)

def get_params(t):
    return {"akv":"2.8.1496","apv":"1.3.6","b":"XiaoMi","d":"e87a4d5f4f28d7a17d73c524eaa8ac37","m":"23046RP50C","mac":"","n":"23046RP50C","t":t,"wifiMac":"020000000000"}

def _generate_key(t):
    params = get_params(t)
    sorted_keys = sorted(params.keys())
    concat = "".join(str(params[k]) for k in sorted_keys if k != "t")
    return hashlib.md5(_h(list(concat), t).encode("utf-8")).hexdigest()

def decrypt_token(ciphertext, iv, t):
    """ciphertext = Base64, iv = Hex (与原项目 CryptoES 行为一致)"""
    key = _generate_key(t)
    key_bytes = key.encode("utf-8")
    iv_bytes = bytes.fromhex(iv)                  # CryptoES.enc.Hex.parse(iv)
    ct_bytes = base64.b64decode(ciphertext)       # CryptoES.AES.decrypt 默认 Base64
    cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
    return unpad(cipher.decrypt(ct_bytes), AES.block_size).decode("utf-8")

def exchange_token(code):
    """用 authCode 换取 access_token + refresh_token，只调用一次"""
    t = int(time.time())
    params = get_params(t)
    params["code"] = code
    hdrs = {k: str(v) for k, v in params.items()}
    hdrs["Content-Type"] = "application/json"
    hdrs["User-Agent"] = HEADERS["User-Agent"]
    tr = requests.post("https://api.extscreen.com/aliyundrive/v3/token",
        headers=hdrs, json=params, timeout=15)
    print(f"[TOKEN] HTTP={tr.status_code} body={tr.text[:500]}", file=sys.stderr, flush=True)
    tr.raise_for_status()
    te = tr.json()
    if "data" not in te or "ciphertext" not in te.get("data", {}):
        raise Exception(f"Token API error: {te}")
    plain = decrypt_token(te["data"]["ciphertext"], te["data"]["iv"], t)
    return json.loads(plain)

# ─── 路由 ──────────────────────────────────────────────────
@app.route("/")
def index():
    return send_file("index.html")

@app.route("/api/generate_qr", methods=["POST"])
def generate_qr():
    try:
        resp = requests.post("https://api.extscreen.com/aliyundrive/qrcode",
            headers=HEADERS,
            json={"scopes":"user:base,file:all:read,file:all:write","width":500,"height":500},
            timeout=10)
        resp.raise_for_status()
        data = resp.json()["data"]
        sid = data["sid"]
        auth_url = f"https://www.alipan.com/o/oauth/authorize?sid={sid}"
        print(f"[QR] sid={sid}", file=sys.stderr, flush=True)
        return jsonify({"sid": sid, "auth_url": auth_url})
    except Exception as e:
        print(f"[QR] ERROR: {e}", file=sys.stderr, flush=True)
        return jsonify({"error": str(e)}), 500

@app.route("/api/check_status/<sid>")
def check_status(sid):
    try:
        resp = requests.get(f"https://openapi.alipan.com/oauth/qrcode/{sid}/status", timeout=15)
        print(f"[CHK] sid={sid[:20]}.. HTTP={resp.status_code} body={resp.text[:300]}", file=sys.stderr, flush=True)
        resp.raise_for_status()
        sd = resp.json()
        status = sd.get("status", "")

        if status == "LoginSuccess" and "authCode" in sd:
            auth_code = sd["authCode"]
            print(f"[CHK] LoginSuccess! authCode={auth_code[:20]}...", file=sys.stderr, flush=True)
            try:
                ti = exchange_token(auth_code)
                print(f"[CHK] SUCCESS at={ti.get('access_token','')[:20]}...", file=sys.stderr, flush=True)
                return jsonify({
                    "status": "LoginSuccess",
                    "access_token": ti.get("access_token", ""),
                    "refresh_token": ti.get("refresh_token", ""),
                })
            except Exception as e:
                print(f"[CHK] TOKEN_EXCHANGE_FAILED: {e}", file=sys.stderr, flush=True)
                return jsonify({"status": "TokenExchangeFailed", "error": str(e)})

        return jsonify(sd)
    except Exception as e:
        print(f"[CHK] ERROR: {e}", file=sys.stderr, flush=True)
        return jsonify({"error": str(e)}), 500

@app.route("/api/oauth/alipan/token", methods=["GET", "POST"])
def oauth_token():
    try:
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            refresh_token_val = data.get("refresh_token", "")
        else:
            refresh_token_val = request.args.get("refresh_ui", "")
        if not refresh_token_val:
            return jsonify({"error": "refresh_token is required"}), 400
        ti = exchange_token_refresh(refresh_token_val)
        return jsonify({
            "token_type": "Bearer",
            "access_token": ti.get("access_token", ""),
            "refresh_token": ti.get("refresh_token", ""),
            "expires_in": ti.get("expires_in", 0),
        })
    except Exception as e:
        return jsonify({"code": 500, "message": str(e), "data": None}), 500

def exchange_token_refresh(refresh_token_val):
    t = int(time.time())
    params = get_params(t)
    params["refresh_token"] = refresh_token_val
    hdrs = {k: str(v) for k, v in params.items()}
    hdrs["Content-Type"] = "application/json"
    hdrs["User-Agent"] = HEADERS["User-Agent"]
    resp = requests.post("https://api.extscreen.com/aliyundrive/v3/token",
        headers=hdrs, json=params, timeout=10)
    resp.raise_for_status()
    te = resp.json()
    plain = decrypt_token(te["data"]["ciphertext"], te["data"]["iv"], t)
    return json.loads(plain)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5800))
    print(f"\n  ✅ 阿里云盘 TV Token 工具已启动\n  🌐 http://localhost:{port}\n", flush=True)
    app.run(host="0.0.0.0", port=port, debug=False)
