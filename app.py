"""QR・画像変換ミニツール qrimage

テキスト/URL から QR コード PNG を生成し、画像ファイルの
PNG/JPEG 変換を行う、広告なし・登録不要の小さな道具。
ファイルはサーバーに保存しない。単一ファイル Flask（DB なし）。
"""
import base64
import io
import os

import qrcode
from PIL import Image
from flask import Flask, jsonify, render_template_string, request, send_file

app = Flask(__name__)
MAX_UPLOAD = 5 * 1024 * 1024  # 5MB
ALLOWED_FORMATS = {"PNG", "JPEG", "WEBP"}

PAGE = """<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>QR・画像変換ミニツール</title>
<style>body{font-family:sans-serif;max-width:640px;margin:2em auto;padding:0 1em}
section{border:1px solid #ccc;border-radius:8px;padding:1em;margin:1em 0}
.err{color:#b00}</style>
</head><body>
<h1>QR・画像変換ミニツール</h1>
<p>広告なし・登録不要。アップロードしたファイルはサーバーに保存しません。</p>

<section>
<h2>QRコード生成</h2>
<form method="post" action="{{ url_for('make_qr') }}">
  <input type="text" name="text" size="40" placeholder="URL やテキスト" value="{{ qr_text or '' }}">
  <button type="submit">QRコードを作る</button>
</form>
{% if qr_b64 %}
<p><img src="data:image/png;base64,{{ qr_b64 }}" alt="QRコード" width="240"></p>
<p><a href="data:image/png;base64,{{ qr_b64 }}" download="qr.png">PNG をダウンロード</a></p>
{% endif %}
</section>

<section>
<h2>画像変換（PNG / JPEG / WebP → PNG または JPEG、5MBまで）</h2>
<form method="post" action="{{ url_for('convert') }}" enctype="multipart/form-data">
  <input type="file" name="file" accept=".png,.jpg,.jpeg,.webp">
  <label>変換先
    <select name="target"><option value="png">PNG</option><option value="jpeg">JPEG</option></select></label>
  <button type="submit">変換してダウンロード</button>
</form>
{% if error %}<p class="err">{{ error }}</p>{% endif %}
</section>
</body></html>"""


def make_qr_png(text):
    img = qrcode.make(text)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})


@app.route("/")
def index():
    return render_template_string(PAGE, qr_text=None, qr_b64=None, error=None)


@app.route("/qr", methods=["POST"])
def make_qr():
    text = (request.form.get("text") or "").strip()
    if not text:
        return render_template_string(PAGE, qr_text="", qr_b64=None, error=None)
    buf = make_qr_png(text)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return render_template_string(PAGE, qr_text=text, qr_b64=b64, error=None)


@app.route("/api/qr")
def api_qr():
    text = request.args.get("text", "")
    if not text:
        return jsonify({"error": "text is required"}), 400
    return send_file(make_qr_png(text), mimetype="image/png", download_name="qr.png", as_attachment=False)


@app.route("/convert", methods=["POST"])
def convert():
    f = request.files.get("file")
    target = request.form.get("target", "png")
    if target not in ("png", "jpeg"):
        target = "png"
    if f is None or f.filename == "":
        return render_template_string(PAGE, qr_text=None, qr_b64=None, error="ファイルを選んでください。"), 400
    data = f.read()
    if len(data) > MAX_UPLOAD:
        return render_template_string(PAGE, qr_text=None, qr_b64=None, error="ファイルが大きすぎます（5MBまで）。"), 400
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception:
        return render_template_string(PAGE, qr_text=None, qr_b64=None, error="画像として読み込めませんでした。"), 400
    if img.format not in ALLOWED_FORMATS:
        return render_template_string(
            PAGE, qr_text=None, qr_b64=None,
            error=f"対応形式は PNG / JPEG / WebP です（これは {img.format} でした）。"), 400
    out = io.BytesIO()
    if target == "jpeg":
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1])
            img = bg
        else:
            img = img.convert("RGB")
        img.save(out, format="JPEG", quality=90)
        mimetype, filename = "image/jpeg", "converted.jpg"
    else:
        img.save(out, format="PNG")
        mimetype, filename = "image/png", "converted.png"
    out.seek(0)
    return send_file(out, mimetype=mimetype, download_name=filename, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
