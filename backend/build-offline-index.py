#!/usr/bin/env python3
"""
Build offline AI search index for Lensora Gallery.
Pre-computes CLIP embeddings for images + search vocabulary.
Output goes to frontend/public/ for static bundling.
"""

import os
import sys
import json
import math
import base64
import struct
from pathlib import Path

import numpy as np
from PIL import Image

# Try loading CLIP
try:
    import clip
    import torch
    HAS_CLIP = True
except ImportError:
    HAS_CLIP = False
    print("WARNING: CLIP not available. Install with: pip install git+https://github.com/openai/CLIP.git")

# ── config ───────────────────────────────────────────
IMAGES_DIR = "/home/daniel/Desktop/AI Gallery/Lensora/Images"
OUTPUT_DIR = Path(__file__).parent.parent / "frontend" / "public"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")
MODEL_NAME = "ViT-B/32"
EMBEDDING_DIM = 512

# Search vocabulary — common photo terms + words from filenames
SEARCH_TERMS = [
    # scene types
    "beach", "ocean", "sea", "sand", "waves", "coast", "shore",
    "family", "people", "person", "kids", "children", "baby",
    "party", "celebration", "birthday", "event", "gathering",
    "park", "nature", "trees", "forest", "garden", "outdoors",
    "sunset", "sunrise", "sky", "clouds", "sun", "light",
    "water", "river", "lake", "pool", "swimming",
    "food", "meal", "dinner", "lunch", "breakfast",
    "building", "house", "home", "architecture", "city",
    "mountain", "hill", "valley", "landscape", "scenery",
    "animal", "dog", "cat", "pet", "bird",
    "flower", "plant", "tree", "grass", "green",
    "night", "evening", "day", "morning", "afternoon",
    "winter", "summer", "spring", "fall", "autumn",
    "snow", "rain", "storm", "fog", "mist",
    # emotions / vibes
    "happy", "joy", "fun", "smile", "laugh", "love",
    "relax", "calm", "peaceful", "beautiful", "pretty",
    # actions
    "playing", "running", "walking", "sitting", "standing",
    "eating", "drinking", "dancing", "singing", "talking",
    # colors
    "blue", "green", "red", "yellow", "orange", "pink", "purple",
    "white", "black", "brown", "gray", "golden",
    # photo style
    "portrait", "selfie", "group photo", "candid", "posed",
    "close up", "wide shot", "panorama", "detail",
]

# ── helpers ──────────────────────────────────────────

def find_images(folder):
    paths = []
    for root, _, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(EXTENSIONS):
                paths.append(os.path.join(root, f))
    return sorted(paths)

def encode_floats(arr):
    """Encode float32 array to compact base64 string."""
    packed = struct.pack(f"<{len(arr)}f", *arr)
    return base64.b64encode(packed).decode("ascii")

def decode_floats(b64, dim):
    """Decode base64 string back to float32 array."""
    packed = base64.b64decode(b64)
    return struct.unpack(f"<{dim}f", packed)

def cosine_similarity(a, b):
    """Dot product of two normalized vectors."""
    return sum(x * y for x, y in zip(a, b))

# ── build index ──────────────────────────────────────

def build():
    if not HAS_CLIP:
        print("CLIP not available. Generating metadata-only index.")
        build_metadata_only()
        return

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading CLIP {MODEL_NAME} on {device}...")
    model, preprocess = clip.load(MODEL_NAME, device=device)
    model.eval()
    print("CLIP ready\n")

    image_paths = find_images(IMAGES_DIR)
    print(f"Found {len(image_paths)} images")

    # ── encode images ────────────────────────────────
    print("Encoding images...")
    image_embeddings = []
    image_meta = []

    for p in image_paths:
        try:
            img = preprocess(Image.open(p).convert("RGB")).unsqueeze(0).to(device)
            with torch.no_grad():
                feat = model.encode_image(img)
                feat /= feat.norm(dim=-1, keepdim=True)
            emb = feat.cpu().numpy().flatten().tolist()
            image_embeddings.append(encode_floats(emb))

            with Image.open(p) as im:
                w, h = im.size
            image_meta.append({
                "name": os.path.basename(p),
                "src": f"/images/{os.path.basename(p)}",
                "alt": os.path.splitext(os.path.basename(p))[0],
                "width": w,
                "height": h,
            })
        except Exception as e:
            print(f"  skip {p}: {e}")

    # ── encode search terms ──────────────────────────
    # Extract unique words from filenames
    filename_words = set()
    for m in image_meta:
        words = m["alt"].replace("_", " ").replace("-", " ").split()
        for w in words:
            w = w.lower().strip()
            if len(w) > 2:
                filename_words.add(w)

    all_terms = sorted(set(SEARCH_TERMS) | filename_words)
    print(f"\nEncoding {len(all_terms)} search terms...")

    text_embeddings = {}
    batch_size = 64
    for i in range(0, len(all_terms), batch_size):
        batch = all_terms[i:i + batch_size]
        with torch.no_grad():
            tokens = clip.tokenize(batch, truncate=True).to(device)
            feats = model.encode_text(tokens)
            feats /= feats.norm(dim=-1, keepdim=True)
        for term, feat in zip(batch, feats):
            text_embeddings[term] = encode_floats(feat.cpu().numpy().flatten().tolist())

    # ── save outputs ─────────────────────────────────
    with open(OUTPUT_DIR / "images.json", "w") as f:
        json.dump({"images": image_meta}, f, indent=2)

    with open(OUTPUT_DIR / "image-embeddings.json", "w") as f:
        json.dump({"embeddings": image_embeddings, "dim": EMBEDDING_DIM}, f)

    with open(OUTPUT_DIR / "text-embeddings.json", "w") as f:
        json.dump({"embeddings": text_embeddings, "dim": EMBEDDING_DIM}, f)

    print(f"\nSaved to {OUTPUT_DIR}:")
    print(f"  images.json            - {len(image_meta)} images")
    print(f"  image-embeddings.json  - {len(image_embeddings)} embeddings")
    print(f"  text-embeddings.json   - {len(text_embeddings)} terms")

    # ── verify sample search ─────────────────────────
    print("\nSample search 'beach':")
    test_emb = decode_floats(text_embeddings["beach"], EMBEDDING_DIM)
    scores = []
    for i, emb_b64 in enumerate(image_embeddings):
        img_emb = decode_floats(emb_b64, EMBEDDING_DIM)
        scores.append((cosine_similarity(test_emb, img_emb), image_meta[i]["name"]))
    scores.sort(reverse=True)
    for score, name in scores[:5]:
        print(f"  {score:.3f}  {name}")

def build_metadata_only():
    """Fallback: build only images.json without CLIP embeddings."""
    image_paths = find_images(IMAGES_DIR)
    image_meta = []
    for p in image_paths:
        try:
            with Image.open(p) as im:
                w, h = im.size
            image_meta.append({
                "name": os.path.basename(p),
                "src": f"/images/{os.path.basename(p)}",
                "alt": os.path.splitext(os.path.basename(p))[0],
                "width": w,
                "height": h,
            })
        except:
            pass

    with open(OUTPUT_DIR / "images.json", "w") as f:
        json.dump({"images": image_meta}, f, indent=2)
    print(f"Saved images.json with {len(image_meta)} images (no AI search)")

if __name__ == "__main__":
    build()
