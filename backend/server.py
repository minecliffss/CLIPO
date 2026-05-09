#!/usr/bin/env python3
"""
Lensora AI Photo Search Backend
Uses CLIP + FAISS for semantic image search.
"""

import os
import sys
import json
import time
import threading
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

import torch
import clip
import numpy as np
import faiss
from PIL import Image

# ── config ───────────────────────────────────────────
# Use relative path to frontend/public/images
BASE_DIR = Path(__file__).parent.parent
IMAGES_DIR = str(BASE_DIR / "frontend" / "public" / "images")
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

FAISS_FILE = DATA_DIR / "faiss_index.bin"
PATHS_FILE = DATA_DIR / "image_paths.json"
META_FILE = DATA_DIR / "image_meta.json"

EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")
MODEL_NAME = "ViT-B/32"
TOP_K = 24

# ── Flask app ────────────────────────────────────────
app = Flask(__name__)
CORS(app)

# ── globals (loaded on startup) ──────────────────────
model = None
preprocess = None
device = None
faiss_index = None
image_paths = []
image_meta = []
index_lock = threading.Lock()

# ── helpers ──────────────────────────────────────────
def find_images(folder):
    paths = []
    for root, _, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(EXTENSIONS):
                paths.append(os.path.join(root, f))
    return sorted(paths)

def build_index():
    """Build CLIP embeddings + FAISS index from scratch."""
    global faiss_index, image_paths, image_meta

    print(f"\nScanning: {IMAGES_DIR}")
    paths = find_images(IMAGES_DIR)
    if not paths:
        print("No images found!")
        return False

    print(f"Found {len(paths)} images")
    print("Encoding with CLIP... this may take a few minutes\n")

    embeddings = []
    valid_paths = []
    valid_meta = []

    for p in paths:
        try:
            img = preprocess(Image.open(p).convert("RGB")).unsqueeze(0).to(device)
            with torch.no_grad():
                feat = model.encode_image(img)
                feat /= feat.norm(dim=-1, keepdim=True)
            embeddings.append(feat.cpu().numpy())
            valid_paths.append(p)

            # get dimensions
            with Image.open(p) as im:
                w, h = im.size
            valid_meta.append({"width": w, "height": h, "name": os.path.basename(p)})
        except Exception as e:
            print(f"  skip {p}: {e}")

    dim = embeddings[0].shape[1]
    matrix = np.vstack(embeddings).astype("float32")

    faiss_index = faiss.IndexFlatIP(dim)
    faiss_index.add(matrix)

    faiss.write_index(faiss_index, str(FAISS_FILE))
    with open(PATHS_FILE, "w") as f:
        json.dump(valid_paths, f)
    with open(META_FILE, "w") as f:
        json.dump(valid_meta, f)

    image_paths = valid_paths
    image_meta = valid_meta
    print(f"\nIndexed {len(valid_paths)} photos")
    return True

def load_index():
    """Load existing FAISS index."""
    global faiss_index, image_paths, image_meta

    faiss_index = faiss.read_index(str(FAISS_FILE))
    with open(PATHS_FILE) as f:
        image_paths = json.load(f)
    with open(META_FILE) as f:
        image_meta = json.load(f)
    print(f"Loaded index: {len(image_paths)} photos")

def check_and_update_index():
    """Add any new photos since last index."""
    global faiss_index, image_paths, image_meta

    all_paths = set(find_images(IMAGES_DIR))
    existing = set(image_paths)
    new_paths = [p for p in all_paths if p not in existing]

    if not new_paths:
        return

    print(f"\nFound {len(new_paths)} new photos, updating index...")
    new_embeddings = []
    valid_new = []
    valid_meta_new = []

    for p in new_paths:
        try:
            img = preprocess(Image.open(p).convert("RGB")).unsqueeze(0).to(device)
            with torch.no_grad():
                feat = model.encode_image(img)
                feat /= feat.norm(dim=-1, keepdim=True)
            new_embeddings.append(feat.cpu().numpy())
            valid_new.append(p)

            with Image.open(p) as im:
                w, h = im.size
            valid_meta_new.append({"width": w, "height": h, "name": os.path.basename(p)})
        except Exception as e:
            print(f"  skip {p}: {e}")

    if valid_new:
        matrix = np.vstack(new_embeddings).astype("float32")
        faiss_index.add(matrix)
        image_paths += valid_new
        image_meta += valid_meta_new

        faiss.write_index(faiss_index, str(FAISS_FILE))
        with open(PATHS_FILE, "w") as f:
            json.dump(image_paths, f)
        with open(META_FILE, "w") as f:
            json.dump(image_meta, f)
        print(f"Updated: {len(image_paths)} total photos")

# ── API routes ───────────────────────────────────────

@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "indexed": len(image_paths)})

@app.route("/api/images")
def list_images():
    """Return all images with metadata."""
    images = []
    for i, p in enumerate(image_paths):
        meta = image_meta[i] if i < len(image_meta) else {"width": 400, "height": 300}
        images.append({
            "name": meta.get("name", os.path.basename(p)),
            "src": f"/images/{os.path.basename(p)}",
            "alt": os.path.splitext(os.path.basename(p))[0],
            "width": meta.get("width", 400),
            "height": meta.get("height", 300),
        })
    return jsonify({"images": images})

@app.route("/api/search")
def search():
    """AI semantic search using CLIP + FAISS."""
    query = request.args.get("q", "").strip()
    top_k = int(request.args.get("k", TOP_K))

    if not query:
        return jsonify({"images": [], "query": query})

    if faiss_index is None or len(image_paths) == 0:
        return jsonify({"images": [], "query": query, "error": "Index not ready"})

    start = time.time()
    with torch.no_grad():
        text = clip.tokenize([query], truncate=True).to(device)
        tfeat = model.encode_text(text)
        tfeat /= tfeat.norm(dim=-1, keepdim=True)

    query_vec = tfeat.cpu().numpy().astype("float32")
    k = min(top_k, len(image_paths))
    scores, indices = faiss_index.search(query_vec, k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < len(image_paths):
            p = image_paths[idx]
            meta = image_meta[idx] if idx < len(image_meta) else {"width": 400, "height": 300}
            results.append({
                "name": meta.get("name", os.path.basename(p)),
                "src": f"/images/{os.path.basename(p)}",
                "alt": os.path.splitext(os.path.basename(p))[0],
                "width": meta.get("width", 400),
                "height": meta.get("height", 300),
                "score": float(score),
            })

    elapsed = time.time() - start
    return jsonify({
        "images": results,
        "query": query,
        "time_ms": round(elapsed * 1000, 1),
    })

@app.route("/images/<path:filename>")
def serve_image(filename):
    """Serve actual image files."""
    return send_from_directory(IMAGES_DIR, filename)

# ── startup ──────────────────────────────────────────
def init():
    global model, preprocess, device

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading CLIP {MODEL_NAME} on {device}...")
    model, preprocess = clip.load(MODEL_NAME, device=device)
    model.eval()
    print("CLIP ready")

    if FAISS_FILE.exists() and PATHS_FILE.exists():
        load_index()
        check_and_update_index()
    else:
        build_index()

    print(f"\nServer ready: {len(image_paths)} photos indexed")

if __name__ == "__main__":
    init()
    app.run(host="0.0.0.0", port=3001, threaded=True)
