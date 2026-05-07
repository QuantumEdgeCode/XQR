# -*- coding: utf-8 -*-
"""
XQR Web 应用 —— 二维码生成与扫码识别

一个单文件 Flask Web 应用，支持：
  • 输入任意文本生成二维码（实时预览）
  • 上传图片识别二维码内容（拖拽 / 点击上传）
  • 纠错等级 / 颜色 / 大小自由调节

启动::

    pip install flask          # 首次使用需安装
    python examples/app.py

然后浏览器打开 http://localhost:5000
"""

import io
import sys
import os

# ── 确保能找到 xqr ─────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, render_template_string, jsonify

from xqr import XQR, encode, decode

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8MB

# ── 页面模板 ────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>&#x25A3;</text></svg>">
<title>XQR · 二维码工具</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, 'Microsoft YaHei', sans-serif; background: linear-gradient(135deg, #f0f4f8 0%, #e8edf4 100%); color: #1a1a2e; min-height: 100vh; padding: 30px 16px; display: flex; flex-direction: column; align-items: center; }
.container { max-width: 960px; width: 100%; }
header { text-align: center; margin-bottom: 30px; }
header h1 { font-size: 28px; font-weight: 700; background: linear-gradient(135deg, #2c3e50, #3498db); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
header p { color: #7a8a9a; font-size: 14px; margin-top: 4px; }
.panels { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
@media (max-width: 700px) { .panels { grid-template-columns: 1fr; } }
.panel { background: rgba(255,255,255,0.85); backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px); border: 1px solid rgba(255,255,255,0.6); border-radius: 20px; padding: 28px; box-shadow: 0 8px 32px rgba(0,0,0,0.05); }
.panel h2 { font-size: 17px; margin-bottom: 18px; color: #2c3e50; display: flex; align-items: center; gap: 8px; }
.panel h2 span { background: #eef3f8; border-radius: 8px; padding: 2px 10px; font-size: 20px; }
label { display: block; font-size: 13px; color: #4a5a6a; margin-bottom: 5px; font-weight: 500; }
input, select, textarea { width: 100%; padding: 10px 14px; border: 1.5px solid #e2e8f0; border-radius: 10px; font-size: 14px; font-family: inherit; background: rgba(255,255,255,0.7); transition: border-color 0.2s, box-shadow 0.2s; outline: none; }
input:focus, select:focus, textarea:focus { border-color: #3498db; box-shadow: 0 0 0 3px rgba(52,152,219,0.12); }
textarea { resize: vertical; min-height: 70px; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px; }
.btn { display: inline-flex; align-items: center; justify-content: center; gap: 6px; padding: 10px 22px; border: none; border-radius: 10px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.2s; width: 100%; margin-top: 14px; }
.btn-primary { background: linear-gradient(135deg, #3498db, #2980b9); color: #fff; }
.btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 16px rgba(52,152,219,0.3); }
.btn-primary:active { transform: translateY(0); }
.btn-success { background: linear-gradient(135deg, #27ae60, #1e8449); color: #fff; }
.btn-success:hover { transform: translateY(-1px); box-shadow: 0 4px 16px rgba(39,174,96,0.3); }
.btn-success:active { transform: translateY(0); }
.result-box { margin-top: 16px; padding: 14px; border-radius: 12px; background: #f7fafc; border: 1px solid #e8edf4; min-height: 60px; word-break: break-all; font-size: 13px; display: none; }
.result-box.show { display: block; }
.result-box img { display: block; max-width: 200px; margin: 0 auto; }
.result-box .text-result { text-align: center; color: #2c3e50; font-weight: 500; }
.result-box .error { color: #e74c3c; text-align: center; }
.drop-zone { border: 2px dashed #d0d8e0; border-radius: 12px; padding: 30px 20px; text-align: center; cursor: pointer; transition: all 0.2s; background: rgba(255,255,255,0.4); margin-top: 10px; }
.drop-zone:hover, .drop-zone.dragover { border-color: #3498db; background: rgba(52,152,219,0.06); }
.drop-zone p { color: #8a9aa8; font-size: 13px; }
.drop-zone .icon { font-size: 36px; margin-bottom: 8px; }
#fileInput { display: none; }
.spinner { display: none; text-align: center; padding: 10px; }
.spinner.show { display: block; }
.spinner::after { content: ''; display: inline-block; width: 20px; height: 20px; border: 2px solid #e2e8f0; border-top-color: #3498db; border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
footer { margin-top: 30px; text-align: center; color: #8a9aa8; font-size: 12px; }
</style>
</head>
<body>
<div class="container">
<header>
  <h1>&#x25A3; XQR · 二维码工具箱</h1>
  <p>纯自研 QR 编码引擎 · 无需外部二维码库</p>
</header>

<div class="panels">

<!------------------- 左：生成 ------------------->
<div class="panel">
  <h2><span>&#x1F4DD;</span> 生成二维码</h2>
  <form id="genForm" onsubmit="generateQR(event)">
    <label for="data">输入内容</label>
    <textarea id="data" placeholder="输入文本、URL、WiFi 配置…" required>Hello 你好 XQR</textarea>

    <div class="form-row">
      <div><label for="level">纠错等级</label>
        <select id="level">
          <option value="L">L ~7%</option>
          <option value="M" selected>M ~15%</option>
          <option value="Q">Q ~25%</option>
          <option value="H">H ~30%</option>
        </select>
      </div>
      <div><label for="size">模块尺寸</label>
        <select id="size">
          <option value="6">小</option>
          <option value="10" selected>中</option>
          <option value="16">大</option>
          <option value="24">超大</option>
        </select>
      </div>
    </div>

    <div class="form-row">
      <div><label for="fg">前景色</label>
        <input type="color" id="fg" value="#000000">
      </div>
      <div><label for="bg">背景色</label>
        <input type="color" id="bg" value="#ffffff">
      </div>
    </div>

    <button type="submit" class="btn btn-primary">&#x25A3; 生成二维码</button>
  </form>
  <div class="result-box" id="genResult"></div>
</div>

<!------------------- 右：解码 ------------------->
<div class="panel">
  <h2><span>&#x1F50D;</span> 扫码识别</h2>
  <form id="decForm" onsubmit="decodeQR(event)">
    <div class="drop-zone" id="dropZone" onclick="document.getElementById('fileInput').click()">
      <div class="icon" id="dzIcon">&#x1F4F7;</div>
      <p id="dzText">点击上传 或 拖拽二维码图片到这里</p>
    </div>
    <input type="file" id="fileInput" accept="image/*" onchange="onFileSelect(event)" style="display:none">
    <button type="submit" class="btn btn-success">&#x1F50D; 识别二维码</button>
  </form>
  <div class="spinner" id="decSpinner"></div>
  <div class="result-box" id="decResult"></div>
</div>

</div>

<footer>XQR v1.0.0 · 由自研 QR 编码引擎驱动</footer>
</div>

<script>
var _droppedFile = null;
var _genTimer = null;

// ── 自动生成（防抖） ─────────────────────────────────
function autoGen() {
  if (_genTimer) clearTimeout(_genTimer);
  _genTimer = setTimeout(function() { generateQR(null); }, 300);
}

// ── 生成二维码 ────────────────────────────────────────
async function generateQR(e) {
  if (e) e.preventDefault();
  var box = document.getElementById('genResult');
  box.classList.remove('show');
  box.innerHTML = '<div class="spinner show"></div>';
  box.classList.add('show');

  try {
    var r = await fetch('/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        data: document.getElementById('data').value,
        level: document.getElementById('level').value,
        box_size: parseInt(document.getElementById('size').value),
        fill_color: document.getElementById('fg').value,
        back_color: document.getElementById('bg').value,
      })
    });
    var j = await r.json();
    box.innerHTML = j.ok
      ? '<img src="' + j.image + '" alt="二维码">'
      : '<div class="error">\u274C ' + j.error + '</div>';
  } catch(err) {
    box.innerHTML = '<div class="error">\u274C 请求失败: ' + err.message + '</div>';
  }
}

// ── 自动解码（文件选择/拖拽后触发） ──────────────────
async function doDecode(file) {
  var box = document.getElementById('decResult');
  var spinner = document.getElementById('decSpinner');
  if (!file) return;
  spinner.classList.add('show');
  box.classList.remove('show');
  var fd = new FormData();
  fd.append('image', file);
  try {
    var r = await fetch('/decode', { method: 'POST', body: fd });
    var j = await r.json();
    spinner.classList.remove('show');
    box.innerHTML = j.ok
      ? '<div class="text-result">\u2705 识别结果:<br><span style="font-size:18px">' + escHtml(j.text) + '</span></div>'
      : '<div class="error">\u274C ' + j.error + '</div>';
    box.classList.add('show');
  } catch(err) {
    spinner.classList.remove('show');
    box.innerHTML = '<div class="error">\u274C 请求失败: ' + err.message + '</div>';
    box.classList.add('show');
  }
}

// ── 文件选择（点击上传） ──────────────────────────────
function onFileSelect(e) {
  var file = e.target.files[0];
  if (!file) return;
  _droppedFile = file;
  updateDropZone(file);
  doDecode(file);
}

// ── 手动解码按钮 ──────────────────────────────────────
async function decodeQR(e) {
  e.preventDefault();
  var fileInput = document.getElementById('fileInput');
  var file = _droppedFile || (fileInput.files && fileInput.files[0]);
  if (!file) {
    var box = document.getElementById('decResult');
    box.innerHTML = '<div class="error">\u274C 请先选择一张二维码图片</div>';
    box.classList.add('show');
    return;
  }
  doDecode(file);
}

function updateDropZone(file) {
  document.getElementById('dzIcon').textContent = '\u2705';
  document.getElementById('dzText').innerHTML = '<span style="color:#27ae60;font-weight:500">已选择: ' + file.name + '</span>';
}

function escHtml(s) {
  var d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

// ── 绑定自动生成事件 ──────────────────────────────────
(function() {
  document.getElementById('data').addEventListener('input', autoGen);
  document.getElementById('level').addEventListener('change', autoGen);
  document.getElementById('size').addEventListener('change', autoGen);
  document.getElementById('fg').addEventListener('input', autoGen);
  document.getElementById('bg').addEventListener('input', autoGen);

  // ── 拖拽支持 ────────────────────────────────────────
  var dz = document.getElementById('dropZone');
  dz.addEventListener('dragover', function(e) { e.preventDefault(); this.classList.add('dragover'); });
  dz.addEventListener('dragleave', function(e) { this.classList.remove('dragover'); });
  dz.addEventListener('drop', function(e) {
    e.preventDefault();
    this.classList.remove('dragover');
    var file = e.dataTransfer.files[0];
    if (file) {
      _droppedFile = file;
      updateDropZone(file);
      doDecode(file);
    }
  });

  // 页面加载后自动生成一次
  autoGen();
})();
</script>
</body>
</html>"""

# ── 路由 ─────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/favicon.ico")
def favicon():
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">\u25a3</text></svg>'
    return svg, 200, {"Content-Type": "image/svg+xml"}


@app.route("/generate", methods=["POST"])
def generate():
    """接收 JSON，返回 base64 二维码图片。"""
    body = request.get_json(silent=True)
    if not body or "data" not in body:
        return jsonify(ok=False, error="缺少 data 参数")

    data = body["data"]
    if not data or not data.strip():
        return jsonify(ok=False, error="内容不能为空")

    try:
        qr = XQR(
            data=data,
            level=body.get("level", "M"),
            box_size=body.get("box_size", 10),
            mask_pattern=body.get("mask_pattern"),
        )
        qr.make()
        b64 = qr.to_base64(
            fill_color=body.get("fill_color", "black"),
            back_color=body.get("back_color", "white"),
        )
        return jsonify(ok=True, image=b64)
    except Exception as e:
        return jsonify(ok=False, error=str(e))


@app.route("/decode", methods=["POST"])
def decode_qr():
    """上传图片，返回解码文本。"""
    if "image" not in request.files:
        return jsonify(ok=False, error="未收到图片文件")

    f = request.files["image"]
    if not f or not f.filename:
        return jsonify(ok=False, error="无效的文件")

    try:
        from PIL import Image
        img = Image.open(f.stream).convert("RGB")
        result = decode(img)
        if result:
            return jsonify(ok=True, text=result)
        else:
            return jsonify(ok=False, error="未在图片中识别到二维码")
    except Exception as e:
        return jsonify(ok=False, error=str(e))


# ── 启动 ─────────────────────────────────────────────────────

if __name__ == "__main__":
    # 避免 debug 重启时重复打印 banner
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        pass
    else:
        print("""
  ╔══════════════════════════════════════╗
  ║   XQR · 二维码工具箱                ║
  ║                                      ║
  ║   生成  →  http://localhost:5000     ║
  ║   解码  →  同上页面上传图片          ║
  ╚══════════════════════════════════════╝
        """)
    app.run(host="0.0.0.0", port=5000, debug=True)
