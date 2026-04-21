import math
import uuid
from pathlib import Path

import numpy as np
from flask import Flask, render_template_string, request
from PIL import Image, ImageOps, ImageDraw

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "static" / "output"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

STATE = {
    "session_id": None,
    "items": [],
    "defaults": {
        "image_k": 20,
        "album_k": 25,
        "image_mode": "compress",
        "album_mode": "compress",
        "layout": "grid",
    },
}


HTML = """
<!doctype html>
<html>
<head>
  <title>SVD Combined Album Studio</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    body {
      margin: 0;
      font-family: Arial, sans-serif;
      background: linear-gradient(135deg, #eef4ff, #fff6eb);
      color: #142033;
    }
    .container {
      width: min(1200px, calc(100% - 32px));
      margin: 24px auto;
    }
    .card {
      background: white;
      border-radius: 18px;
      padding: 20px;
      box-shadow: 0 10px 24px rgba(0,0,0,0.08);
      margin-bottom: 20px;
    }
    .controls {
      display: grid;
      grid-template-columns: 2fr 1fr 1fr 1fr 1fr;
      gap: 16px;
    }
    .controls2 {
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 16px;
      margin-top: 16px;
    }
    input, select, button, a.btn {
      width: 100%;
      padding: 12px;
      border-radius: 12px;
      border: 1px solid #d0d9e5;
      font: inherit;
      box-sizing: border-box;
    }
    button, a.btn {
      background: linear-gradient(135deg, #ff9d36, #ff6b45);
      color: white;
      border: none;
      font-weight: bold;
      cursor: pointer;
      text-decoration: none;
      display: inline-block;
      text-align: center;
    }
    .secondary {
      background: #1f3b5b;
    }
    .danger {
      background: #b83a3a;
    }
    .download {
      background: #1c8c5e;
    }
    .grid {
      display: grid;
      gap: 18px;
    }
    .compare {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }
    .compare img, .album-preview img {
      width: 100%;
      border-radius: 14px;
      display: block;
    }
    .small {
      color: #57708c;
    }
    h1, h2, h3 {
      margin-top: 0;
    }
    .thumb-card {
      background: #f8fbff;
      border: 1px solid #e1e9f2;
      border-radius: 14px;
      padding: 16px;
    }
    .pill-list {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }
    .pill {
      background: #eef4ff;
      color: #23415f;
      padding: 8px 12px;
      border-radius: 999px;
      font-weight: 600;
    }
    .download-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
      margin-top: 16px;
    }
    @media (max-width: 900px) {
      .controls, .controls2, .compare, .download-row {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="card">
      <h1>SVD Combined Album Studio</h1>
      <p class="small">
        Upload images one by one or many together. Each image is processed individually.
        Then all processed images are combined into one album, and that album is also processed by SVD.
      </p>
    </div>

    <form class="card" method="POST" enctype="multipart/form-data">
      <input type="hidden" name="action" value="add">

      <div class="controls">
        <div>
          <label>Choose images</label>
          <input type="file" name="images" multiple required>
        </div>
        <div>
          <label>Image mode</label>
          <select name="image_mode">
            <option value="compress" {% if defaults.image_mode == "compress" %}selected{% endif %}>Compress</option>
            <option value="quality" {% if defaults.image_mode == "quality" %}selected{% endif %}>High quality</option>
          </select>
        </div>
        <div>
          <label>Image k</label>
          <input type="number" name="image_k" min="1" value="{{ defaults.image_k }}" required>
        </div>
        <div>
          <label>Album mode</label>
          <select name="album_mode">
            <option value="compress" {% if defaults.album_mode == "compress" %}selected{% endif %}>Compress</option>
            <option value="quality" {% if defaults.album_mode == "quality" %}selected{% endif %}>High quality</option>
          </select>
        </div>
        <div>
          <label>Album k</label>
          <input type="number" name="album_k" min="1" value="{{ defaults.album_k }}" required>
        </div>
      </div>

      <div class="controls2">
        <div>
          <label>Album layout</label>
          <select name="layout">
            <option value="grid" {% if defaults.layout == "grid" %}selected{% endif %}>Grid</option>
            <option value="vertical" {% if defaults.layout == "vertical" %}selected{% endif %}>Vertical</option>
            <option value="horizontal" {% if defaults.layout == "horizontal" %}selected{% endif %}>Horizontal</option>
          </select>
        </div>
        <div style="display:flex;align-items:end;">
          <button class="secondary" type="submit">Add Images And Rebuild Album</button>
        </div>
        <div style="display:flex;align-items:end;">
          <button class="danger" type="submit" formaction="/" formmethod="POST" name="action" value="reset">Reset All</button>
        </div>
      </div>
    </form>

    <div class="card">
      <h2>Current Uploaded Images</h2>
      {% if items %}
        <div class="pill-list">
          {% for item in items %}
            <div class="pill">{{ item.display_name }}</div>
          {% endfor %}
        </div>
      {% else %}
        <p class="small">No images uploaded yet.</p>
      {% endif %}
    </div>

    {% if items %}
      <div class="card">
        <h2>Individual Image Results</h2>
        <div class="grid">
          {% for item in items %}
            <div class="thumb-card">
              <h3>{{ item.display_name }}</h3>
              <p class="small">Mode: {{ item.image_mode }} | k = {{ item.image_k }}</p>
              <div class="compare">
                <div>
                  <p><strong>Original</strong></p>
                  <img src="{{ item.original_url }}" alt="original">
                </div>
                <div>
                  <p><strong>Processed</strong></p>
                  <img src="{{ item.processed_url }}" alt="processed">
                </div>
              </div>
            </div>
          {% endfor %}
        </div>
      </div>

      <div class="card">
        <h2>Combined Album</h2>
        <p class="small">All processed images are attached together into one album.</p>

        <div class="album-preview">
          <h3>Combined Album Before Album-SVD</h3>
          <img src="{{ album_base_url }}" alt="combined album">
        </div>

        <div class="album-preview" style="margin-top:20px;">
          <h3>Combined Album After Album-SVD</h3>
          <p class="small">Mode: {{ album_mode }} | k = {{ album_k }}</p>
          <img src="{{ album_svd_url }}" alt="combined album svd">
        </div>

        <div class="download-row">
          <a class="btn download" href="{{ album_base_url }}" download="combined_album.png">Download Combined Album</a>
          <a class="btn download" href="{{ album_svd_url }}" download="combined_album_svd.png">Download SVD Album</a>
        </div>
      </div>
    {% endif %}
  </div>
</body>
</html>
"""


def load_image(path):
    img = Image.open(path).convert("RGB")
    return np.array(img, dtype=np.float32) / 255.0


def save_array_image(img_array, path):
    img = Image.fromarray((img_array * 255).astype(np.uint8))
    img.save(path)


def make_preview(input_path, output_path, size=(420, 320)):
    img = Image.open(input_path).convert("RGB")
    img = ImageOps.fit(img, size)
    img.save(output_path)


def compress_channel(channel, k):
    u, s, vt = np.linalg.svd(channel, full_matrices=False)
    k = max(1, min(k, len(s)))
    return u[:, :k] @ np.diag(s[:k]) @ vt[:k, :]


def svd_compress_image(img_array, k):
    r = compress_channel(img_array[:, :, 0], k)
    g = compress_channel(img_array[:, :, 1], k)
    b = compress_channel(img_array[:, :, 2], k)
    output = np.stack([r, g, b], axis=2)
    return np.clip(output, 0, 1)


def choose_k(mode, user_k, max_rank):
    user_k = max(1, min(user_k, max_rank))
    if mode == "quality":
        return max(user_k, int(max_rank * 0.75))
    return user_k


def create_album_from_paths(image_paths, output_path, layout="grid", thumb_size=(220, 220), padding=20):
    thumbs = []
    labels = []

    for path in image_paths:
        img = Image.open(path).convert("RGB")
        img = ImageOps.fit(img, thumb_size)
        thumbs.append(img)
        labels.append(Path(path).stem[:24])

    if not thumbs:
        return

    label_height = 28

    if layout == "vertical":
        cols = 1
        rows = len(thumbs)
    elif layout == "horizontal":
        cols = len(thumbs)
        rows = 1
    else:
        cols = 3
        rows = math.ceil(len(thumbs) / cols)

    canvas_width = cols * (thumb_size[0] + padding) + padding
    canvas_height = rows * (thumb_size[1] + label_height + padding) + padding

    album = Image.new("RGB", (canvas_width, canvas_height), "white")
    draw = ImageDraw.Draw(album)

    for i, thumb in enumerate(thumbs):
        row = i // cols
        col = i % cols
        x = padding + col * (thumb_size[0] + padding)
        y = padding + row * (thumb_size[1] + label_height + padding)

        album.paste(thumb, (x, y))
        draw.text((x, y + thumb_size[1] + 4), labels[i], fill="black")

    album.save(output_path)


def ensure_session():
    if not STATE["session_id"]:
        STATE["session_id"] = str(uuid.uuid4())
        STATE["items"] = []
        session_output = OUTPUT_DIR / STATE["session_id"]
        session_output.mkdir(parents=True, exist_ok=True)


def rebuild_album(album_mode, album_k_input, layout):
    session_id = STATE["session_id"]
    session_output = OUTPUT_DIR / session_id

    processed_paths = [Path(item["processed_path"]) for item in STATE["items"]]

    album_base_path = session_output / "album_base.png"
    album_svd_path = session_output / "album_svd.png"

    create_album_from_paths(processed_paths, album_base_path, layout=layout)

    album_array = load_image(album_base_path)
    max_album_rank = min(album_array.shape[0], album_array.shape[1])
    final_album_k = choose_k(album_mode, album_k_input, max_album_rank)

    album_processed = svd_compress_image(album_array, final_album_k)
    save_array_image(album_processed, album_svd_path)

    return {
        "album_base_url": f"/static/output/{session_id}/album_base.png",
        "album_svd_url": f"/static/output/{session_id}/album_svd.png",
        "album_mode": album_mode,
        "album_k": final_album_k,
    }


@app.route("/", methods=["GET", "POST"])
def index():
    album_data = None

    if request.method == "POST":
        action = request.form.get("action")

        if action == "reset":
            STATE["session_id"] = None
            STATE["items"] = []
            STATE["defaults"] = {
                "image_k": 20,
                "album_k": 25,
                "image_mode": "compress",
                "album_mode": "compress",
                "layout": "grid",
            }
        else:
            ensure_session()

            image_mode = request.form.get("image_mode", "compress")
            album_mode = request.form.get("album_mode", "compress")
            image_k_input = int(request.form.get("image_k", 20))
            album_k_input = int(request.form.get("album_k", 25))
            layout = request.form.get("layout", "grid")

            STATE["defaults"] = {
                "image_k": image_k_input,
                "album_k": album_k_input,
                "image_mode": image_mode,
                "album_mode": album_mode,
                "layout": layout,
            }

            files = request.files.getlist("images")

            session_id = STATE["session_id"]
            session_output = OUTPUT_DIR / session_id

            for file in files:
                if not file.filename:
                    continue

                original_name = Path(file.filename).stem
                suffix = Path(file.filename).suffix or ".png"
                unique_name = f"{len(STATE['items'])}_{uuid.uuid4().hex}_{original_name}{suffix}"

                upload_path = UPLOAD_DIR / unique_name
                file.save(upload_path)

                preview_original_path = session_output / f"original_{unique_name}.png"
                processed_path = session_output / f"processed_{unique_name}.png"

                img_array = load_image(upload_path)
                max_rank = min(img_array.shape[0], img_array.shape[1])
                final_image_k = choose_k(image_mode, image_k_input, max_rank)

                processed_array = svd_compress_image(img_array, final_image_k)
                save_array_image(processed_array, processed_path)
                make_preview(upload_path, preview_original_path)

                STATE["items"].append({
                    "display_name": Path(file.filename).name,
                    "image_mode": image_mode,
                    "image_k": final_image_k,
                    "original_url": f"/static/output/{session_id}/{preview_original_path.name}",
                    "processed_url": f"/static/output/{session_id}/{processed_path.name}",
                    "processed_path": str(processed_path),
                })

            if STATE["items"]:
                album_data = rebuild_album(album_mode, album_k_input, layout)

    if STATE["session_id"] and STATE["items"] and not album_data:
        defaults = STATE["defaults"]
        album_data = rebuild_album(defaults["album_mode"], defaults["album_k"], defaults["layout"])

    return render_template_string(
        HTML,
        items=STATE["items"],
        album_base_url=album_data["album_base_url"] if album_data else None,
        album_svd_url=album_data["album_svd_url"] if album_data else None,
        album_mode=album_data["album_mode"] if album_data else None,
        album_k=album_data["album_k"] if album_data else None,
        defaults=STATE["defaults"],
    )


if __name__ == "__main__":
    app.run(debug=True)

