# -*- coding: utf-8 -*-
"""
XQR Web 应用 v2 —— 二维码 & 条形码生成与识别

与 app.py（仅 QR 码）不同，v2 版本同时支持：
  • 生成二维码或 Code128 条形码
  • 上传图片自动识别二维码/条形码
  • QR 纠错等级 / 颜色 / 大小 / 条宽 / 条高自由调节

启动::

    pip install flask
    python examples/app_v2.py

然后浏览器打开 http://localhost:5000
"""

import io
import sys
import os
import base64

# ── 确保能找到 xqr ─────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, render_template_string, jsonify

from xqr import XQR, encode, decode
from xqr.barcode import encode as bar_encode, decode as bar_decode

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8MB

# ── 页面模板 ────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>&#x25A3;</text></svg>">
<title>XQR v2·码图工具箱</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, 'Microsoft YaHei', sans-serif; background: linear-gradient(135deg, #f0f4f8 0%, #e8edf4 100%); color: #1a1a2e; min-height: 100vh; padding: 30px 16px; display: flex; flex-direction: column; align-items: center; }
.container { max-width: 960px; width: 100%; }
header { text-align: center; margin-bottom: 30px; }
header h1 { font-size: 28px; font-weight: 700; background: linear-gradient(135deg, #2c3e50, #3498db); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
header p { color: #7a8a9a; font-size: 14px; margin-top: 4px; }
.panels { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
@media (max-width: 700px) { .panels { grid-template-columns: 1fr; } }
@media (max-width: 500px) { .form-row { grid-template-columns: 1fr; } .form-row-3 { grid-template-columns: 1fr; } .gen-actions { flex-direction: column; } }
.panel { background: rgba(255,255,255,0.85); backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px); border: 1px solid rgba(255,255,255,0.6); border-radius: 20px; padding: 28px; box-shadow: 0 8px 32px rgba(0,0,0,0.05); }
.panel h2 { font-size: 17px; margin-bottom: 18px; color: #2c3e50; display: flex; align-items: center; gap: 8px; }
.panel h2 span { background: #eef3f8; border-radius: 8px; padding: 2px 10px; font-size: 20px; }
label { display: block; font-size: 13px; color: #4a5a6a; margin-bottom: 5px; font-weight: 500; }
input, select, textarea { width: 100%; padding: 10px 14px; border: 1.5px solid #e2e8f0; border-radius: 10px; font-size: 14px; font-family: inherit; background: rgba(255,255,255,0.7); transition: border-color 0.2s, box-shadow 0.2s; outline: none; }
input:focus, select:focus, textarea:focus { border-color: #3498db; box-shadow: 0 0 0 3px rgba(52,152,219,0.12); }
input[type="color"] { width: 100%; min-height: 20px; padding: 2px 4px; cursor: pointer; }
input[type="checkbox"] { width: auto; margin-right: 6px; transform: scale(1.1); }
textarea { resize: vertical; min-height: 70px; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px; }
.form-row-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; }
.opt-group { display: none; margin-top: 6px; }
.opt-group.show { display: block; }
.qr-only { display: block; }
.qr-only.hide { display: none; }
.btn { display: inline-flex; align-items: center; justify-content: center; gap: 6px; padding: 10px 22px; border: none; border-radius: 10px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.2s; width: 100%; margin-top: 14px; }
.btn-primary { background: linear-gradient(135deg, #3498db, #2980b9); color: #fff; }
.btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 16px rgba(52,152,219,0.3); }
.btn-primary:active { transform: translateY(0); }
.btn-success { background: linear-gradient(135deg, #27ae60, #1e8449); color: #fff; }
.btn-success:hover { transform: translateY(-1px); box-shadow: 0 4px 16px rgba(39,174,96,0.3); }
.btn-success:active { transform: translateY(0); }
/* 左侧生成按钮行 — 独立隔离，不影响右侧 */
.gen-actions { display: flex; gap: 10px; margin-top: 14px; }
.gen-actions .btn { margin-top: 0; }
.gen-save { background: #eef3f8; color: #2c3e50; }
.gen-save:hover { background: #dce5ed; transform: translateY(-1px); }
.gen-save:active { transform: translateY(0); }
.hidden { display: none !important; }
.result-box { margin-top: 16px; padding: 14px; border-radius: 12px; background: #f7fafc; border: 1px solid #e8edf4; min-height: 60px; word-break: break-all; font-size: 13px; display: none; text-align: center; }
.result-box.show { display: block; }
.result-box img { display: block; max-width: 200px; margin: 0 auto; }
.result-box .code-type-badge { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; margin-bottom: 10px; }
.result-box .badge-qr { background: #e8f4fd; color: #1677FF; }
.result-box .badge-bar { background: #fef3e2; color: #d48806; }
.result-box .text-result { margin-top: 6px; color: #2c3e50; font-weight: 500; font-size: 16px; }
.result-box .error { color: #e74c3c; }
.drop-zone { border: 2px dashed #d0d8e0; border-radius: 12px; padding: 30px 20px; text-align: center; cursor: pointer; transition: all 0.2s; background: rgba(255,255,255,0.4); margin-top: 10px; }
.drop-zone:hover, .drop-zone.dragover { border-color: #3498db; background: rgba(52,152,219,0.06); }
.drop-zone p { color: #8a9aa8; font-size: 13px; }
.drop-zone .icon { font-size: 36px; margin-bottom: 8px; }
#fileInput { display: none; }
.spinner { display: none; text-align: center; padding: 10px; }
.spinner.show { display: block; }
.spinner::after { content: ''; display: inline-block; width: 20px; height: 20px; border: 2px solid #e2e8f0; border-top-color: #3498db; border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.badge-v2 { display: inline-block; background: #e8f4fd; color: #1677FF; font-size: 10px; font-weight: 700; padding: 1px 8px; border-radius: 20px; margin-left: 6px; vertical-align: middle; }
footer { margin-top: 30px; text-align: center; color: #8a9aa8; font-size: 12px; }
</style>
</head>
<body>
<div class="container">
<header>
  <p>QR 码 + Code128 条形码 · 纯自研引擎</p>
</header>

<div class="panels">

<!------------------- 左：生成 ------------------->
<div class="panel">
  <h2><span>&#x1F4DD;</span> 生成码图 <span class="badge-v2">v2</span></h2>
  <form id="genForm" onsubmit="generateCode(event)">

    <label for="data">输入内容</label>
    <textarea id="data" placeholder="输入文本、URL…" required>Hello 你好 XQR</textarea>

    <!-- 类型 + 前景色 + 背景色 紧凑一行 -->
    <div class="form-row-3" style="margin-top:10px">
      <div><label for="codeType">类型</label>
        <select id="codeType" onchange="toggleCodeType()">
          <option value="qr">QR 二维码</option>
          <option value="barcode">条形码 (Code128)</option>
        </select>
      </div>
      <div class="qr-only"><label for="fg">前景色</label>
        <input type="color" id="fg" value="#000000">
      </div>
      <div class="qr-only"><label for="bg">背景色</label>
        <input type="color" id="bg" value="#ffffff">
      </div>
    </div>

    <!-- QR 专属选项 -->
    <div class="opt-group show" id="qrOpts">
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
    </div>

    <!-- 条形码专属选项 -->
    <div class="opt-group" id="barOpts">
      <div class="form-row">
        <div><label for="barWidth">条宽（像素）</label>
          <input type="text" id="barWidth" value="3" placeholder="默认 3">
        </div>
        <div><label for="barHeight">条高（像素）</label>
          <input type="text" id="barHeight" value="80" placeholder="默认 80">
        </div>
      </div>
      <div style="margin-top:10px">
        <label><input type="checkbox" id="barText" checked> 显示下方文字</label>
      </div>
    </div>

    <div class="gen-actions">
      <button type="submit" class="btn btn-primary" id="genBtn">&#x25A3; 生成二维码</button>
      <a class="btn gen-save hidden" id="saveBtn" href="#" download="qrcode.png">&#x1F4E5; 保存图片</a>
    </div>
  </form>
  <div class="result-box" id="genResult"></div>
</div>

<!------------------- 右：解码 ------------------->
<div class="panel">
  <h2><span>&#x1F50D;</span> 扫码识别 <span class="badge-v2">v2</span></h2>
  <form id="decForm" onsubmit="decodeImage(event)">
    <div class="drop-zone" id="dropZone" onclick="document.getElementById('fileInput').click()">
      <div class="icon" id="dzIcon">&#x1F4F7;</div>
      <p id="dzText">点击上传 或 拖拽二维码/条形码图片到这里</p>
    </div>
    <input type="file" id="fileInput" accept="image/*" onchange="onFileSelect(event)" style="display:none">
    <button type="submit" class="btn btn-success">&#x1F50D; 识别码图</button>
  </form>
  <div class="spinner" id="decSpinner"></div>
  <div class="result-box" id="decResult"></div>
</div>

</div>

<footer>XQR v1.0.1 · 自研 QR 编码 + Code128 条形码引擎</footer>
</div>

<script>
var _droppedFile = null;
var _genTimer = null;

// ── 类型切换 ─────────────────────────────────────────────
function toggleCodeType() {
  var t = document.getElementById('codeType').value;
  document.getElementById('qrOpts').classList.toggle('show', t === 'qr');
  document.getElementById('barOpts').classList.toggle('show', t === 'barcode');
  document.getElementById('genBtn').textContent =
    t === 'qr' ? '\u25A3 生成二维码' : '\u25A3 生成条形码';
  document.getElementById('saveBtn').classList.add('hidden');
  // 切换类型时显示/隐藏前景色背景色
  document.querySelectorAll('.qr-only').forEach(function(el) {
    el.classList.toggle('hide', t !== 'qr');
  });
  // 切换类型时清空输入内容和结果
  document.getElementById('data').value = '';
  var box = document.getElementById('genResult');
  box.classList.remove('show');
  box.innerHTML = '';
}

// ── 自动生成（防抖） ─────────────────────────────────
function autoGen() {
  if (_genTimer) clearTimeout(_genTimer);
  _genTimer = setTimeout(function() { generateCode(null); }, 300);
}

// ── 生成 ────────────────────────────────────────────────
async function generateCode(e) {
  if (e) e.preventDefault();
  document.getElementById('saveBtn').classList.add('hidden');
  var box = document.getElementById('genResult');
  box.classList.remove('show');
  box.innerHTML = '<div class="spinner show"></div>';
  box.classList.add('show');

  var codeType = document.getElementById('codeType').value;
  var payload = {
    type: codeType,
    data: document.getElementById('data').value,
  };

  if (codeType === 'qr') {
    payload.level = document.getElementById('level').value;
    payload.box_size = parseInt(document.getElementById('size').value);
    payload.fill_color = document.getElementById('fg').value;
    payload.back_color = document.getElementById('bg').value;
  } else {
    payload.module_width = parseInt(document.getElementById('barWidth').value) || 3;
    payload.module_height = parseInt(document.getElementById('barHeight').value) || 80;
    payload.write_text = document.getElementById('barText').checked;
  }

  try {
    var r = await fetch('/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    var j = await r.json();
    if (j.ok) {
      var badge = codeType === 'qr'
        ? '<span class="code-type-badge badge-qr">QR 二维码</span>'
        : '<span class="code-type-badge badge-bar">Code128 条形码</span>';
      box.innerHTML = badge + '<br><img src="' + j.image + '" alt="码图">';
      var saveBtn = document.getElementById('saveBtn');
      saveBtn.href = j.image;
      saveBtn.download = codeType === 'qr' ? 'qrcode.png' : 'barcode.png';
      saveBtn.classList.remove('hidden');
    } else {
      box.innerHTML = '<div class="error">\u274C ' + j.error + '</div>';
    }
  } catch(err) {
    box.innerHTML = '<div class="error">\u274C 请求失败: ' + err.message + '</div>';
  }
}

// ── 自动解码 ────────────────────────────────────────────
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
    if (j.ok) {
      var badge = j.code_type === 'barcode'
        ? '<span class="code-type-badge badge-bar">条形码</span>'
        : '<span class="code-type-badge badge-qr">QR 二维码</span>';
      box.innerHTML = badge + '<div class="text-result">\u2705 ' + escHtml(j.text) + '</div>';
    } else {
      box.innerHTML = '<div class="error">\u274C ' + j.error + '</div>';
    }
    box.classList.add('show');
  } catch(err) {
    spinner.classList.remove('show');
    box.innerHTML = '<div class="error">\u274C 请求失败: ' + err.message + '</div>';
    box.classList.add('show');
  }
}

// ── 文件选择 ────────────────────────────────────────────
function onFileSelect(e) {
  var file = e.target.files[0];
  if (!file) return;
  _droppedFile = file;
  updateDropZone(file);
  doDecode(file);
}

// ── 手动解码 ────────────────────────────────────────────
async function decodeImage(e) {
  e.preventDefault();
  var fileInput = document.getElementById('fileInput');
  var file = _droppedFile || (fileInput.files && fileInput.files[0]);
  if (!file) {
    var box = document.getElementById('decResult');
    box.innerHTML = '<div class="error">\u274C 请先选择一张图片</div>';
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

// ── 绑定事件 ────────────────────────────────────────────
(function() {
  document.getElementById('data').addEventListener('input', autoGen);
  document.getElementById('codeType').addEventListener('change', autoGen);
  document.getElementById('level').addEventListener('change', autoGen);
  document.getElementById('size').addEventListener('change', autoGen);
  document.getElementById('fg').addEventListener('input', autoGen);
  document.getElementById('bg').addEventListener('input', autoGen);
  document.getElementById('barWidth').addEventListener('input', autoGen);
  document.getElementById('barHeight').addEventListener('input', autoGen);
  document.getElementById('barText').addEventListener('change', autoGen);

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
    """接收 JSON，返回 base64 图片（二维码或条形码）。"""
    body = request.get_json(silent=True)
    if not body or "data" not in body:
        return jsonify(ok=False, error="缺少 data 参数")

    data = body["data"]
    if not data or not data.strip():
        return jsonify(ok=False, error="内容不能为空")

    code_type = body.get("type", "qr")

    try:
        if code_type == "barcode":
            bar_width = body.get("module_width", 3)
            bar_height = body.get("module_height", 80)
            write_text = body.get("write_text", True)

            png_bytes = bar_encode(
                data,
                module_width=bar_width,
                module_height=bar_height,
                write_text=write_text,
            )
            b64 = "data:image/png;base64," + base64.b64encode(png_bytes).decode()
            return jsonify(ok=True, image=b64)
        else:
            qr = XQR(
                data=data,
                level=body.get("level", "M"),
                box_size=body.get("box_size", 10),
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
def decode_image():
    """上传图片，自动检测并解码二维码或条形码。"""
    if "image" not in request.files:
        return jsonify(ok=False, error="未收到图片文件")

    f = request.files["image"]
    if not f or not f.filename:
        return jsonify(ok=False, error="无效的文件")

    try:
        from PIL import Image
        img = Image.open(f.stream).convert("RGB")

        qr_result = decode(img)
        if qr_result:
            return jsonify(ok=True, text=qr_result, code_type="qr")

        bar_result = bar_decode(img)
        if bar_result:
            return jsonify(ok=True, text=bar_result, code_type="barcode")

        return jsonify(ok=False, error="未识别到二维码或条形码")

    except Exception as e:
        return jsonify(ok=False, error=str(e))


# ── 启动 ─────────────────────────────────────────────────────

if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        pass
    else:
        print("""
  ╔══════════════════════════════════════╗
  ║   XQR v2 · 码图工具箱               ║
  ║                                      ║
  ║   生成  →  http://localhost:5000     ║
  ║   解码  →  同上页面上传图片          ║
  ║   支持 QR 码 + Code128 条形码        ║
  ╚══════════════════════════════════════╝
        """)
    app.run(host="0.0.0.0", port=5000, debug=True)
