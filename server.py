import http.server
import socketserver
import os
import json
import sys
import mimetypes
import urllib.parse
import re
import shutil
import hashlib
import hmac
import time
import uuid
import base64
from http import cookies

# --- КОНФИГУРАЦИЯ ---
PORT = 8000
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(ROOT_DIR, 'nanocms.json')

# Ограничения безопасности
ALLOWED_EXT = {'.html', '.htm', '.css', '.js', '.txt', '.xml', '.php', '.md', '.json', '.jpg', '.png', '.svg', '.gif', '.jpeg', '.webp'}
IMAGE_EXT = {'.jpg', '.png', '.svg', '.gif', '.jpeg', '.webp'}
EXCLUDE_FILES = {'server.py', 'nanocms.php', 'nanocms.json', '.htaccess', '.git', '.DS_Store', '__pycache__'}
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_TIME = 300  # 5 минут блокировки

# --- КЛАСС БЕЗОПАСНОСТИ ---
class SecurityManager:
    def __init__(self):
        self.config = self.load_config()
        self.login_attempts = {} # ip -> [timestamp, count]

    def load_config(self):
        default_config = {
            "password_hash": self.hash_password("admin"),
            "secret_key": os.urandom(32).hex()
        }
        if not os.path.exists(CONFIG_FILE):
            self.save_config(default_config)
            return default_config
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            return default_config

    def save_config(self, config):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        self.config = config

    def hash_password(self, password):
        salt = os.urandom(16)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        return salt.hex() + ':' + pwd_hash.hex()

    def verify_password(self, stored_password, provided_password):
        try:
            salt_hex, hash_hex = stored_password.split(':')
            salt = bytes.fromhex(salt_hex)
            pwd_hash = hashlib.pbkdf2_hmac('sha256', provided_password.encode(), salt, 100000)
            return hmac.compare_digest(pwd_hash.hex(), hash_hex)
        except:
            return False

    def check_brute_force(self, ip):
        now = time.time()
        if ip in self.login_attempts:
            last_time, count = self.login_attempts[ip]
            if count >= MAX_LOGIN_ATTEMPTS:
                if now - last_time < LOCKOUT_TIME:
                    return False
                else:
                    self.login_attempts[ip] = [now, 0]
        return True

    def register_attempt(self, ip, success):
        now = time.time()
        if success:
            if ip in self.login_attempts: del self.login_attempts[ip]
        else:
            if ip not in self.login_attempts: self.login_attempts[ip] = [now, 0]
            self.login_attempts[ip][1] += 1
            self.login_attempts[ip][0] = now

    def generate_token(self):
        return hmac.new(
            bytes.fromhex(self.config['secret_key']),
            str(time.time()).encode(),
            hashlib.sha256
        ).hexdigest()

    def sign_cookie(self, value):
        msg = base64.b64encode(value.encode()).decode()
        sig = hmac.new(bytes.fromhex(self.config['secret_key']), msg.encode(), hashlib.sha256).hexdigest()
        return f"{msg}.{sig}"

    def unsign_cookie(self, signed_value):
        try:
            msg, sig = signed_value.split('.')
            expected_sig = hmac.new(bytes.fromhex(self.config['secret_key']), msg.encode(), hashlib.sha256).hexdigest()
            if hmac.compare_digest(sig, expected_sig):
                return base64.b64decode(msg).decode()
        except:
            pass
        return None

security = SecurityManager()

# --- ОБРАБОТЧИК ЗАПРОСОВ ---
class CMSHandler(http.server.SimpleHTTPRequestHandler):
    def get_client_ip(self):
        return self.client_address[0]

    def check_auth(self):
        if "Cookie" in self.headers:
            c = cookies.SimpleCookie(self.headers["Cookie"])
            if "nanocms_session" in c:
                signed_val = c["nanocms_session"].value
                val = security.unsign_cookie(signed_val)
                if val == "authorized":
                    return True
        return False

    def send_api_response(self, success, data=None, message=None):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        resp = {'status': 'success' if success else 'error'}
        if data: resp['data'] = data
        if message: resp['message'] = message
        self.wfile.write(json.dumps(resp).encode('utf-8'))

    def do_GET(self):
        if self.path == '/admin' or self.path == '/admin/':
            if self.check_auth(): self.serve_ui()
            else: self.serve_login()
            return

        if self.path.startswith('/api/'):
            if not self.check_auth(): self.send_error(403); return

            if self.path == '/api/list':
                self.send_api_response(True, self.get_file_tree(ROOT_DIR))
                return

            if self.path.startswith('/api/load'):
                query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                filename = query.get('file', [''])[0]
                self.serve_file_content(filename)
                return

        # Clean URL support: Try adding .html if file not found
        safe_path = self.get_safe_path(self.path)
        if not safe_path or not os.path.exists(safe_path):
             if self.path.endswith('/'):
                 # Directory index is handled by super().do_GET() or we can force it
                 pass
             else:
                 # Try appending .html
                 html_path = self.path + '.html'
                 safe_html = self.get_safe_path(html_path)
                 if safe_html and os.path.exists(safe_html):
                     self.path = html_path

        super().do_GET()

    def do_POST(self):
        if self.path == '/login':
            length = int(self.headers.get('Content-Length', 0))
            data = json.loads(self.rfile.read(length).decode('utf-8'))
            password = data.get('password', '')
            ip = self.get_client_ip()

            if not security.check_brute_force(ip):
                self.send_api_response(False, message="Too many attempts. Wait 5 min.")
                return

            if security.verify_password(security.config['password_hash'], password):
                security.register_attempt(ip, True)
                self.send_response(200)
                c = cookies.SimpleCookie()
                c["nanocms_session"] = security.sign_cookie("authorized")
                c["nanocms_session"]["path"] = "/"
                c["nanocms_session"]["httponly"] = True
                self.send_header("Set-Cookie", c.output(header="", sep=""))
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'success'}).encode('utf-8'))
            else:
                security.register_attempt(ip, False)
                self.send_api_response(False, message="Invalid password")
            return

        if not self.check_auth(): self.send_error(403); return

        if self.path == '/api/upload':
            self.handle_upload()
            return

        length = int(self.headers.get('Content-Length', 0))
        try:
            body = self.rfile.read(length).decode('utf-8')
            data = json.loads(body)
        except: data = {}

        if self.path == '/api/save':
            if self.save_file(data.get('file'), data.get('content')):
                self.send_api_response(True)
            else:
                self.send_api_response(False, message="Write error")

        elif self.path == '/api/create_file':
            if self.create_fs_item(data.get('path'), False): self.send_api_response(True)
            else: self.send_api_response(False, message="Create error")

        elif self.path == '/api/create_folder':
            if self.create_fs_item(data.get('path'), True): self.send_api_response(True)
            else: self.send_api_response(False, message="Create error")

        elif self.path == '/api/delete':
            if self.delete_fs_item(data.get('path')): self.send_api_response(True)
            else: self.send_api_response(False, message="Delete error")

        elif self.path == '/api/rename':
            if self.rename_fs_item(data.get('old_path'), data.get('new_name')): self.send_api_response(True)
            else: self.send_api_response(False, message="Rename error")

        elif self.path == '/api/change_password':
            new_pass = data.get('password')
            if new_pass:
                conf = security.config
                conf['password_hash'] = security.hash_password(new_pass)
                security.save_config(conf)
                self.send_api_response(True)
            else: self.send_api_response(False, message="Empty password")

        else: self.send_error(404)

    # --- ФАЙЛОВЫЕ ОПЕРАЦИИ ---

    def get_safe_path(self, path):
        if not path: return None
        safe_path = os.path.normpath(os.path.join(ROOT_DIR, path.lstrip('/')))
        if not safe_path.startswith(ROOT_DIR): return None
        if os.path.basename(safe_path) in EXCLUDE_FILES: return None
        return safe_path

    def get_file_tree(self, directory):
        items = []
        try:
            for entry in os.scandir(directory):
                if entry.name.startswith('.') or entry.name in EXCLUDE_FILES: continue

                item = {
                    'name': entry.name,
                    'path': os.path.relpath(entry.path, ROOT_DIR).replace('\\', '/'),
                    'type': 'folder' if entry.is_dir() else 'file'
                }
                if entry.is_dir():
                    item['children'] = self.get_file_tree(entry.path)
                elif os.path.splitext(entry.name)[1].lower() in ALLOWED_EXT:
                    pass
                else: continue
                items.append(item)
            return sorted(items, key=lambda x: (x['type'] != 'folder', x['name']))
        except: return []

    def serve_file_content(self, filename):
        safe_path = self.get_safe_path(filename)
        if safe_path and os.path.exists(safe_path) and os.path.isfile(safe_path):
            try:
                # Определяем, бинарный файл или текстовый
                ext = os.path.splitext(safe_path)[1].lower()
                if ext in IMAGE_EXT:
                    with open(safe_path, 'rb') as f:
                        content = f.read()
                    self.send_response(200)
                    # MIME types
                    mime = mimetypes.guess_type(safe_path)[0] or 'application/octet-stream'
                    self.send_header('Content-type', mime)
                    self.end_headers()
                    self.wfile.write(content)
                else:
                    with open(safe_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(content.encode('utf-8'))
            except: self.send_error(500, "Read error")
        else: self.send_error(404)

    def save_file(self, filename, content):
        safe_path = self.get_safe_path(filename)
        if safe_path:
            try:
                with open(safe_path, 'w', encoding='utf-8') as f: f.write(content)
                return True
            except: pass
        return False

    def create_fs_item(self, path, is_folder):
        safe_path = self.get_safe_path(path)
        if not safe_path or os.path.exists(safe_path): return False
        try:
            if is_folder: os.makedirs(safe_path)
            else:
                os.makedirs(os.path.dirname(safe_path), exist_ok=True)
                with open(safe_path, 'w', encoding='utf-8') as f: f.write("")
            return True
        except: return False

    def delete_fs_item(self, path):
        safe_path = self.get_safe_path(path)
        if not safe_path: return False
        try:
            if os.path.isdir(safe_path): shutil.rmtree(safe_path)
            else: os.remove(safe_path)
            return True
        except: return False

    def rename_fs_item(self, old_path, new_name):
        safe_old = self.get_safe_path(old_path)
        if not safe_old or not os.path.exists(safe_old): return False
        new_name = os.path.basename(new_name)
        if not new_name or new_name in EXCLUDE_FILES: return False
        safe_new = os.path.join(os.path.dirname(safe_old), new_name)
        if os.path.exists(safe_new): return False
        try:
            os.rename(safe_old, safe_new)
            return True
        except: return False

    def handle_upload(self):
        import cgi
        try:
            form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={'REQUEST_METHOD': 'POST'})
            upload_path = form.getvalue('path', '')
            fileitem = form['file']

            # Если путь пустой или корень, принудительно используем 'resources'
            if not upload_path or upload_path == '.' or upload_path == '/':
                upload_path = 'resources'

            # Создаем папку resources если её нет
            safe_dir = self.get_safe_path(upload_path)
            if safe_dir and not os.path.exists(safe_dir):
                os.makedirs(safe_dir)

            if fileitem.filename:
                fn = os.path.basename(fileitem.filename)
                target_path = os.path.join(upload_path, fn)
                safe_path = self.get_safe_path(target_path)
                if safe_path:
                    with open(safe_path, 'wb') as f: f.write(fileitem.file.read())
                    self.send_api_response(True)
                else: self.send_api_response(False, message="Invalid path")
            else: self.send_api_response(False, message="No file")
        except Exception as e: self.send_api_response(False, message=str(e))

    # --- UI ---
    def serve_login(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        html = """<!DOCTYPE html><html><head><title>Login</title><meta name="viewport" content="width=device-width, initial-scale=1"><style>body{background:#f0f2f5;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;display:flex;height:100vh;align-items:center;justify-content:center;margin:0}form{background:#fff;padding:40px;border-radius:12px;box-shadow:0 2px 15px rgba(0,0,0,0.1);width:320px}h2{margin:0 0 20px;text-align:center;color:#1a1a1a}input{width:100%;padding:12px;margin-bottom:15px;border:1px solid #ddd;border-radius:6px;box-sizing:border-box}button{width:100%;padding:12px;background:#007aff;color:#fff;border:none;border-radius:6px;font-weight:600;cursor:pointer}button:hover{background:#0062cc}#msg{color:red;text-align:center;margin-bottom:10px;font-size:14px;min-height:20px}</style></head><body><form onsubmit="event.preventDefault(); login()"><h2>NanoCMS Ultimate</h2><div id="msg"></div><input type="password" id="pass" placeholder="Password" autofocus required><button type="submit">Sign In</button></form><script>async function login(){let p=document.getElementById('pass').value;let m=document.getElementById('msg');m.innerText='Checking...';try{let r=await fetch('/login',{method:'POST',body:JSON.stringify({password:p})});let d=await r.json();if(d.status==='success')location.reload();else m.innerText=d.message||'Error';}catch(e){m.innerText='Connection error'}}</script></body></html>"""
        self.wfile.write(html.encode('utf-8'))

    def serve_ui(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        html = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>NanoCMS Ultimate</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/ace/1.4.12/ace.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        :root { --bg: #f8f9fa; --sidebar: #ffffff; --border: #e9ecef; --text: #212529; --accent: #0d6efd; --danger: #dc3545; }
        body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; height: 100vh; display: flex; overflow: hidden; background: var(--bg); color: var(--text); }
        #sidebar { width: 300px; background: var(--sidebar); border-right: 1px solid var(--border); display: flex; flex-direction: column; }
        .sb-header { padding: 15px; border-bottom: 1px solid var(--border); font-weight: bold; display: flex; justify-content: space-between; align-items: center; }
        .sb-tools { padding: 8px; display: flex; gap: 5px; border-bottom: 1px solid var(--border); }
        .tool-btn { border: none; background: transparent; cursor: pointer; padding: 6px; border-radius: 4px; color: #6c757d; }
        .tool-btn:hover { background: #e9ecef; color: var(--text); }
        #tree { flex: 1; overflow-y: auto; padding: 10px 0; }
        .t-item { padding: 6px 15px; cursor: pointer; display: flex; align-items: center; font-size: 14px; white-space: nowrap; overflow: hidden; user-select: none; }
        .t-item:hover { background: #f1f3f5; }
        .t-item.active { background: #e7f1ff; color: var(--accent); }
        .t-item i { width: 20px; text-align: center; margin-right: 8px; color: #adb5bd; }
        .t-item.folder i { color: #ffd43b; }
        #main { flex: 1; display: flex; flex-direction: column; position: relative; }
        #toolbar { height: 50px; background: var(--sidebar); border-bottom: 1px solid var(--border); display: flex; align-items: center; padding: 0 20px; justify-content: space-between; }
        .btn { background: var(--accent); color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-weight: 500; font-size: 13px; }
        .btn:disabled { opacity: 0.6; cursor: not-allowed; }
        #editors { flex: 1; position: relative; background: white; }
        #ace-editor { position: absolute; top: 0; left: 0; right: 0; bottom: 0; }
        #visual-editor { width: 100%; height: 100%; border: none; display: none; }
        #ctx-menu { position: fixed; background: white; border: 1px solid var(--border); box-shadow: 0 4px 12px rgba(0,0,0,0.1); border-radius: 6px; display: none; z-index: 100; flex-direction: column; min-width: 150px; }
        .ctx-item { padding: 8px 15px; cursor: pointer; font-size: 13px; display: flex; gap: 10px; align-items: center; }
        .ctx-item:hover { background: #f8f9fa; color: var(--accent); }
        .ctx-item.del:hover { color: var(--danger); background: #fff5f5; }
        .modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.4); z-index: 200; display: none; justify-content: center; align-items: center; }
        .modal { background: white; padding: 25px; border-radius: 8px; width: 350px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); max-height: 80vh; display: flex; flex-direction: column; }
        .modal h3 { margin-top: 0; }
        .modal input { width: 100%; padding: 10px; border: 1px solid #ced4da; border-radius: 4px; box-sizing: border-box; margin: 15px 0; }
        .modal-footer { text-align: right; margin-top: 15px; }
        #toast { position: fixed; bottom: 20px; right: 20px; padding: 12px 20px; border-radius: 6px; background: #333; color: white; font-size: 14px; display: none; z-index: 300; }
        #drop-zone { position: fixed; top:0; left:0; width:100%; height:100%; background: rgba(13, 110, 253, 0.1); border: 4px dashed var(--accent); z-index: 500; display: none; pointer-events: none; justify-content: center; align-items: center; font-size: 24px; color: var(--accent); font-weight: bold; }

        /* Image Picker Styles */
        .img-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; overflow-y: auto; max-height: 300px; border: 1px solid var(--border); padding: 10px; border-radius: 4px; margin-bottom: 10px; }
        .img-card { border: 1px solid var(--border); border-radius: 4px; padding: 5px; cursor: pointer; text-align: center; }
        .img-card:hover { border-color: var(--accent); background: #f8f9fa; }
        .img-card.selected { border-color: var(--accent); background: #e7f1ff; box-shadow: 0 0 0 2px rgba(13,110,253,0.3); }
        .img-card img { max-width: 100%; height: 60px; object-fit: contain; display: block; margin: 0 auto; }
        .img-card span { display: block; font-size: 11px; margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .img-upload-area { border: 2px dashed var(--border); padding: 20px; text-align: center; color: #6c757d; border-radius: 4px; cursor: pointer; transition: 0.2s; }
        .img-upload-area:hover { border-color: var(--accent); color: var(--accent); }
        .warn-msg { font-size: 12px; color: #ff9800; margin-top: 5px; display: none; }
    </style>
</head>
<body ondragover="showDrop(event)" ondragleave="hideDrop(event)" ondrop="handleDrop(event)">

<div id="sidebar">
    <div class="sb-header">
        NanoCMS Ultimate
        <i class="fas fa-cog tool-btn" onclick="showSettings()" title="Settings"></i>
    </div>
    <div class="sb-tools">
        <button class="tool-btn" onclick="promptCreate('file')" title="New File"><i class="fas fa-file-plus"></i></button>
        <button class="tool-btn" onclick="promptCreate('folder')" title="New Folder"><i class="fas fa-folder-plus"></i></button>
        <button class="tool-btn" onclick="refreshTree()" title="Refresh"><i class="fas fa-sync-alt"></i></button>
        <div style="flex:1"></div>
        <button class="tool-btn" onclick="location.href='/logout'" title="Logout"><i class="fas fa-sign-out-alt"></i></button>
    </div>
    <div id="tree">Loading...</div>
</div>

<div id="main">
    <div id="toolbar">
        <div class="path-crumbs" id="current-path">/</div>
        <div style="display:flex; gap:10px; align-items:center">
            <div id="mode-switch" style="display:none; background:#e9ecef; border-radius:4px; padding:2px;">
                <button class="tool-btn" id="btn-code" onclick="setMode('code')">Code</button>
                <button class="tool-btn" id="btn-vis" onclick="setMode('visual')">Visual</button>
            </div>
            <button class="btn" id="btn-save" onclick="saveCurrent()" disabled>Save (Ctrl+S)</button>
        </div>
    </div>
    <div id="editors">
        <div id="ace-editor"></div>
        <iframe id="visual-editor"></iframe>
    </div>
</div>

<div id="ctx-menu">
    <div class="ctx-item" onclick="ctxRename()"><i class="fas fa-edit"></i> Rename</div>
    <div class="ctx-item del" onclick="ctxDelete()"><i class="fas fa-trash"></i> Delete</div>
</div>

<!-- Standard Modal -->
<div class="modal-overlay" id="modal-wrap">
    <div class="modal">
        <h3 id="modal-title">Title</h3>
        <input type="text" id="modal-input" onkeyup="if(event.key==='Enter') modalOk()">
        <div class="modal-footer">
            <button class="tool-btn" onclick="closeModal()">Cancel</button>
            <button class="btn" onclick="modalOk()">OK</button>
        </div>
    </div>
</div>

<!-- Image Picker Modal -->
<div class="modal-overlay" id="img-modal-wrap">
    <div class="modal" style="width: 500px;">
        <h3>Media Library</h3>
        <div class="img-upload-area" onclick="document.getElementById('img-upload-input').click()">
            <i class="fas fa-cloud-upload-alt"></i> Click to Upload (to /resources)
        </div>
        <input type="file" id="img-upload-input" style="display:none" onchange="handleImgUpload(this.files)" accept="image/*">
        <div style="margin: 10px 0; font-size: 13px; font-weight: bold;">Select Image:</div>
        <div class="img-grid" id="img-list"></div>
        <input type="text" id="img-url-input" placeholder="Or enter URL..." oninput="checkImgPath(this.value)">
        <div id="path-warning" class="warn-msg"><i class="fas fa-exclamation-triangle"></i> Not in 'resources' folder</div>
        <div class="modal-footer">
            <button class="tool-btn" onclick="closeImgModal()">Cancel</button>
            <button class="btn" onclick="applyImg()">Update Image</button>
        </div>
    </div>
</div>

<div id="toast">Notification</div>
<div id="drop-zone">Drop files here to upload</div>

<script>
    let currentFile = null;
    let currentCtxItem = null;
    let mode = 'code';
    let editor = ace.edit("ace-editor");
    editor.setTheme("ace/theme/chrome");
    editor.session.setMode("ace/mode/html");
    editor.setFontSize(14);

    // --- API & TREE ---
    async function api(ep, d) {
        try {
            let r=await fetch('/api/'+ep,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});
            return await r.json();
        } catch(e){return{status:'error',message:e.message};}
    }
    let treeData = [];
    async function refreshTree() {
        let r=await fetch('/api/list'); let j=await r.json();
        if(j.status==='success'){ treeData=j.data; renderTree(); }
    }
    function renderTree() {
        let h='';
        function b(items,l){
            items.forEach(i=>{
                let p=l*20; let ic=i.type==='folder'?'fa-folder':'fa-file-code';
                if(i.name.match(/\.(jpg|png|gif|svg|webp)$/i)) ic='fa-image';
                h+=`<div class="t-item ${i.type}" data-path="${i.path}" data-type="${i.type}" style="padding-left:${15+p}px" onclick="itemClick(this)" oncontextmenu="openCtx(event,'${i.path}','${i.type}','${i.name}')"><i class="fas ${ic}"></i> ${i.name}</div>`;
                if(i.children) b(i.children,l+1);
            });
        }
        b(treeData,0); document.getElementById('tree').innerHTML=h;
        if(currentFile) { let el=document.querySelector(`.t-item[data-path="${currentFile}"]`); if(el) el.classList.add('active'); }
    }
    function itemClick(el){
        let type=el.dataset.type; let path=el.dataset.path;
        document.querySelectorAll('.t-item').forEach(e=>e.classList.remove('active')); el.classList.add('active');
        if(type==='file') loadFile(path);
        else { currentFile=null; document.getElementById('current-path').innerText=path; }
    }

    // --- EDITOR ---
    async function loadFile(path){
        if(currentFile===path)return;
        currentFile=path; document.getElementById('current-path').innerText=path;
        document.getElementById('btn-save').disabled=true;
        let ext=path.split('.').pop().toLowerCase();
        let isVis=['html','htm','php'].includes(ext);
        document.getElementById('mode-switch').style.display=isVis?'block':'none';
        setMode('code',true);
        let r=await fetch('/api/load?file='+encodeURIComponent(path));
        if(r.ok){
            let t=await r.text(); editor.setValue(t,-1);
            let m='ace/mode/text';
            if(ext==='js')m='ace/mode/javascript'; if(ext==='css')m='ace/mode/css'; if(ext==='php')m='ace/mode/php'; if(isVis)m='ace/mode/html';
            editor.session.setMode(m);
            document.getElementById('btn-save').disabled=false;
        }
    }
    function setMode(m, force){
        if(mode===m && !force) return;
        let cD=document.getElementById('ace-editor'); let vF=document.getElementById('visual-editor');
        let bC=document.getElementById('btn-code'); let bV=document.getElementById('btn-vis');
        if(m==='code'){
            if(mode==='visual' && !force){
                try{
                    let h=vF.contentDocument.documentElement.outerHTML;
                    h=h.replace(/<base href=".*?">/i,''); editor.setValue(h,-1);
                }catch(e){}
            }
            vF.style.display='none'; cD.style.display='block';
            bC.style.background='white'; bC.style.fontWeight='bold'; bV.style.background='transparent'; bV.style.fontWeight='normal';
        } else {
            let val=editor.getValue(); let doc=vF.contentDocument||vF.contentWindow.document;
            doc.open(); val=val.replace('<head>',`<head><base href="${location.origin}/">`);
            doc.write(val);
            // Inject Script for Image Handling
            let s=doc.createElement('script');
            s.textContent=`
                document.addEventListener('mouseover', e=>{
                    if(e.target.tagName==='IMG') {
                        e.target.style.outline='3px solid #0d6efd';
                        e.target.style.cursor='pointer';
                    }
                });
                document.addEventListener('mouseout', e=>{
                    if(e.target.tagName==='IMG') e.target.style.outline='';
                });
                document.addEventListener('click', e=>{
                    if(e.target.tagName==='IMG'){
                        e.preventDefault(); e.stopPropagation();
                        // Store ref to image using a unique ID approach or just pass message to parent
                        // Simple: Pass message, parent opens modal, parent sends message back.
                        // We need to know WHICH image. Let's add a temp ID.
                        let tmpId = 'img-edit-' + Math.random().toString(36).substr(2,9);
                        e.target.setAttribute('data-cms-id', tmpId);
                        window.parent.postMessage({action:'edit_image', src: e.target.getAttribute('src'), id: tmpId}, '*');
                    }
                }, true);
                window.addEventListener('message', e=>{
                    if(e.data.action==='update_image'){
                        let img = document.querySelector('img[data-cms-id="'+e.data.id+'"]');
                        if(img) {
                            img.src = e.data.src;
                            img.removeAttribute('data-cms-id'); // cleanup
                        }
                    }
                });
            `;
            doc.head.appendChild(s);
            doc.close(); doc.designMode='on';
            cD.style.display='none'; vF.style.display='block';
            bV.style.background='white'; bV.style.fontWeight='bold'; bC.style.background='transparent'; bC.style.fontWeight='normal';
        }
        mode=m;
    }
    async function saveCurrent(){
        if(!currentFile)return;
        let c='';
        if(mode==='code') c=editor.getValue();
        else {
            let doc=document.getElementById('visual-editor').contentDocument;
            // Clean temp attributes
            doc.querySelectorAll('img[data-cms-id]').forEach(i=>i.removeAttribute('data-cms-id'));
            c=doc.documentElement.outerHTML; c=c.replace(/<base href=".*?">/i,'');
            editor.setValue(c,-1);
        }
        let r=await api('save',{file:currentFile,content:c});
        if(r.status==='success') showToast('Saved!'); else showToast('Error: '+r.message);
    }

    // --- IMAGE MODAL LOGIC ---
    let editingImgId = null;
    window.addEventListener('message', e=>{
        if(e.data.action === 'edit_image') {
            editingImgId = e.data.id;
            openImgModal(e.data.src);
        }
    });

    function openImgModal(currentSrc) {
        document.getElementById('img-modal-wrap').style.display='flex';
        document.getElementById('img-url-input').value = currentSrc;
        checkImgPath(currentSrc);
        loadGallery();
    }

    function closeImgModal() { document.getElementById('img-modal-wrap').style.display='none'; }

    async function loadGallery() {
        // Flatten tree to find images
        let images = [];
        function find(items) {
            items.forEach(i=>{
                if(i.type==='file' && i.name.match(/\.(jpg|png|gif|svg|webp|jpeg)$/i)) images.push(i);
                if(i.children) find(i.children);
            });
        }
        find(treeData);

        let html = '';
        images.forEach(img => {
            html += `<div class="img-card" onclick="selectImg('${img.path}')">
                <img src="${img.path}">
                <span>${img.name}</span>
            </div>`;
        });
        document.getElementById('img-list').innerHTML = html;
    }

    function selectImg(path) {
        let els = document.querySelectorAll('.img-card');
        els.forEach(e=>e.classList.remove('selected'));
        // Highlight clicked (visually tricky without ID, but simple match works)
        event.currentTarget.classList.add('selected');
        document.getElementById('img-url-input').value = path;
        checkImgPath(path);
    }

    function checkImgPath(val) {
        let warn = document.getElementById('path-warning');
        if(val && !val.startsWith('http') && !val.startsWith('resources/')) {
            warn.style.display = 'block';
        } else {
            warn.style.display = 'none';
        }
    }

    function applyImg() {
        let val = document.getElementById('img-url-input').value;
        document.getElementById('visual-editor').contentWindow.postMessage({action: 'update_image', id: editingImgId, src: val}, '*');
        closeImgModal();
    }

    async function handleImgUpload(files) {
        if(!files.length) return;
        let fd = new FormData();
        fd.append('file', files[0]);
        fd.append('path', 'resources'); // Force resources for this specific modal

        let r = await fetch('/api/upload', {method:'POST', body: fd});
        let j = await r.json();
        if(j.status === 'success') {
            refreshTree().then(() => {
                loadGallery(); // Reload gallery
                // Auto select uploaded
                document.getElementById('img-url-input').value = 'resources/' + files[0].name;
                checkImgPath('resources/' + files[0].name);
            });
        } else {
            showToast('Upload failed: ' + j.message);
        }
    }

    // --- STANDARD MODALS ---
    let modalAction=null;
    function promptCreate(t){
        modalAction=t; document.getElementById('modal-title').innerText=t==='file'?'New File Name':'New Folder Name';
        document.getElementById('modal-wrap').style.display='flex'; document.getElementById('modal-input').focus();
    }
    function showSettings(){
        modalAction='settings'; document.getElementById('modal-title').innerText='Change Password';
        document.getElementById('modal-input').placeholder='New Password'; document.getElementById('modal-wrap').style.display='flex';
    }
    function closeModal(){ document.getElementById('modal-wrap').style.display='none'; document.getElementById('modal-input').value=''; }
    function modalOk(){
        let v=document.getElementById('modal-input').value; if(!v)return;
        if(modalAction==='settings'){ api('change_password',{password:v}).then(r=>{if(r.status==='success')showToast('Password changed');else showToast(r.message);closeModal();}); return; }
        let ep=modalAction==='file'?'create_file':'create_folder';
        api(ep,{path:v}).then(r=>{if(r.status==='success'){refreshTree();closeModal();}else showToast(r.message);});
    }

    // --- CTX & DND ---
    function openCtx(e,p,t,n){ e.preventDefault();e.stopPropagation(); currentCtxItem={path:p,type:t,name:n}; let m=document.getElementById('ctx-menu'); m.style.display='flex'; m.style.top=e.clientY+'px'; m.style.left=e.clientX+'px'; }
    document.addEventListener('click',()=>document.getElementById('ctx-menu').style.display='none');
    function ctxDelete(){
        if(!currentCtxItem)return; if(confirm(`Delete ${currentCtxItem.name}?`)){
            api('delete',{path:currentCtxItem.path}).then(r=>{if(r.status==='success'){if(currentFile===currentCtxItem.path){currentFile=null;editor.setValue('');}refreshTree();}else showToast(r.message);});
        }
    }
    function ctxRename(){
        if(!currentCtxItem)return; let n=prompt("New name:",currentCtxItem.name);
        if(n&&n!==currentCtxItem.name) api('rename',{old_path:currentCtxItem.path,new_name:n}).then(r=>{if(r.status==='success')refreshTree();else showToast(r.message);});
    }
    function showDrop(e){e.preventDefault();document.getElementById('drop-zone').style.display='flex';}
    function hideDrop(e){e.preventDefault();document.getElementById('drop-zone').style.display='none';}
    function handleDrop(e){
        e.preventDefault(); document.getElementById('drop-zone').style.display='none';
        let f=e.dataTransfer.files; if(f.length>0) uploadFiles(f);
    }
    async function uploadFiles(files){
        let tp=''; if(currentCtxItem&&currentCtxItem.type==='folder') tp=currentCtxItem.path;
        for(let i=0;i<files.length;i++){
            let fd=new FormData(); fd.append('file',files[i]); fd.append('path',tp);
            await fetch('/api/upload',{method:'POST',body:fd});
        }
        refreshTree(); showToast('Upload finished');
    }
    function showToast(m){let t=document.getElementById('toast');t.innerText=m;t.style.display='block';setTimeout(()=>t.style.display='none',3000);}
    document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key==='s'){e.preventDefault();saveCurrent();}});
    refreshTree();
</script>
</body>
</html>
        """
        self.wfile.write(html.encode('utf-8'))

if __name__ == "__main__":
    os.chdir(ROOT_DIR)
    if not os.path.exists(CONFIG_FILE): security.load_config()
    with socketserver.TCPServer(("", PORT), CMSHandler) as httpd:
        try: httpd.serve_forever()
        except KeyboardInterrupt: pass