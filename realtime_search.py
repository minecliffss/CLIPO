import os
import sys
import clip
import torch
import pickle
import json
import time
import threading
import faiss
import numpy as np
from PIL import Image
from tqdm import tqdm
import readchar
import face_recognition
import sqlite3

# ── config ───────────────────────────────────────────
MODEL_NAME   = "ViT-B/32"
TOP_K        = 5
SEARCH_DELAY = 0.4
FAISS_FILE   = "faiss_index.bin"
PATHS_FILE   = "image_paths.json"
MATRIX_FILE  = "embeddings.npy"          # ← NEW: store raw matrix
CONFIG_FILE  = "config.json"
FACES_DB     = "faces.db"
EXTENSIONS   = (".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff")

# ── global scan-status so UI can poll it ─────────────
_scan_status = {
    "running":  False,
    "matched":  0,
    "total":    0,
    "done":     False,
    "message":  "",
}
_scan_lock = threading.Lock()

# ── faces database ────────────────────────────────────
def init_faces_db():
    conn = sqlite3.connect(FACES_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS known_faces (
            id       INTEGER PRIMARY KEY,
            name     TEXT    NOT NULL,
            encoding BLOB    NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS photo_faces (
            photo_path TEXT NOT NULL,
            name       TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_photo_faces_unique
        ON photo_faces(photo_path, name)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_photo_faces_name
        ON photo_faces(name)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_photo_faces_path
        ON photo_faces(photo_path)
    """)
    conn.commit()
    conn.close()

def save_known_face(name, encoding):
    conn = sqlite3.connect(FACES_DB)
    blob = encoding.tobytes()
    conn.execute(
        "INSERT INTO known_faces (name, encoding) VALUES (?, ?)",
        (name, blob)
    )
    conn.commit()
    conn.close()

def load_known_faces():
    conn  = sqlite3.connect(FACES_DB)
    rows  = conn.execute(
        "SELECT name, encoding FROM known_faces"
    ).fetchall()
    conn.close()
    names, encodings = [], []
    for name, blob in rows:
        enc = np.frombuffer(blob, dtype=np.float64).copy()  # ← .copy() so array is writable
        names.append(name)
        encodings.append(enc)
    return names, encodings

def save_photo_face(photo_path, name):
    """
    Insert row — silently skip if the unique index blocks it.
    Uses INSERT OR IGNORE so we never get duplicate rows.
    """
    conn = sqlite3.connect(FACES_DB)
    conn.execute(
        "INSERT OR IGNORE INTO photo_faces (photo_path, name) VALUES (?, ?)",
        (photo_path, name)
    )
    conn.commit()
    conn.close()

def get_photos_by_name(name):
    """
    Case-insensitive exact name match first;
    fall back to LIKE if no rows found.
    """
    conn = sqlite3.connect(FACES_DB)

    # exact match (case-insensitive via COLLATE NOCASE)
    rows = conn.execute(
        "SELECT photo_path FROM photo_faces "
        "WHERE name = ? COLLATE NOCASE",
        (name,)
    ).fetchall()

    # fuzzy fallback
    if not rows:
        rows = conn.execute(
            "SELECT photo_path FROM photo_faces WHERE name LIKE ?",
            (f"%{name}%",)
        ).fetchall()

    conn.close()
    # filter to paths that still exist on disk
    return [r[0] for r in rows if os.path.exists(r[0])]

def get_all_known_names():
    conn  = sqlite3.connect(FACES_DB)
    rows  = conn.execute(
        "SELECT DISTINCT name FROM known_faces ORDER BY name"
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_face_scan_status():
    conn    = sqlite3.connect(FACES_DB)
    scanned = conn.execute(
        "SELECT COUNT(DISTINCT photo_path) FROM photo_faces"
    ).fetchone()[0]
    conn.close()
    return scanned

# ── config / folder ───────────────────────────────────
def save_config(folder):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"image_folder": folder}, f, indent=2)

def get_image_folder():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            config = json.load(f)
        folder = config.get("image_folder", "")
        if folder and os.path.exists(folder):
            print(f"✓ Saved folder: {folder}")
            ans = input("  Use this folder? (y/n): ").strip().lower()
            if ans == "y":
                return folder

    defaults = [
        os.path.expanduser("~/Pictures"),
        os.path.expanduser("~/Desktop/Images"),
        os.path.expanduser("~/Images"),
        os.path.expanduser("~/Photos"),
    ]
    for folder in defaults:
        if os.path.exists(folder):
            print(f"✓ Found folder: {folder}")
            ans = input("  Use this folder? (y/n): ").strip().lower()
            if ans == "y":
                save_config(folder)
                return folder

    print("\nNo image folder found. Tip: drag folder into terminal\n")
    while True:
        folder = input("Image folder path: ").strip().strip("'\"")
        folder = os.path.expanduser(folder)
        if os.path.exists(folder):
            save_config(folder)
            print("✓ Saved!\n")
            return folder
        print("  ✗ Not found — try again\n")

# ── load CLIP ─────────────────────────────────────────
device = "cuda" if torch.cuda.is_available() else "cpu"

def load_model():
    print("Loading CLIP model...")
    model, preprocess = clip.load(MODEL_NAME, device=device)
    if os.path.exists("clip_finetuned.pt"):
        model.load_state_dict(
            torch.load("clip_finetuned.pt", map_location=device)
        )
        print("✓ Fine-tuned weights loaded")
    model.eval()
    with torch.no_grad():
        dummy = clip.tokenize(["warmup"], truncate=True).to(device)
        _ = model.encode_text(dummy)
    print(f"✓ CLIP ready on {device}")
    return model, preprocess

# ── find images ───────────────────────────────────────
def find_images(folder):
    paths = []
    for root, _, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(EXTENSIONS):
                paths.append(os.path.join(root, f))
    return sorted(paths)

# ── build FAISS index ─────────────────────────────────
def build_index(model, preprocess, image_folder):
    print(f"\nScanning: {image_folder}")
    image_paths = find_images(image_folder)

    if not image_paths:
        print("No images found!")
        return None, None, None

    print(f"Found {len(image_paths)} images — indexing now...\n")

    embeddings  = []
    valid_paths = []

    for path in tqdm(image_paths, desc="Indexing"):
        try:
            img = preprocess(
                Image.open(path).convert("RGB")
            ).unsqueeze(0).to(device)
            with torch.no_grad():
                feat = model.encode_image(img)
                feat /= feat.norm(dim=-1, keepdim=True)
            embeddings.append(feat.cpu().numpy())
            valid_paths.append(path)
        except Exception:
            pass

    matrix = np.vstack(embeddings).astype("float32")
    dim    = matrix.shape[1]
    index  = faiss.IndexFlatIP(dim)
    index.add(matrix)

    faiss.write_index(index, FAISS_FILE)
    np.save(MATRIX_FILE, matrix)          # ← save raw matrix
    with open(PATHS_FILE, "w") as f:
        json.dump(valid_paths, f)

    print(f"\n✓ Indexed {len(valid_paths)} photos\n")
    return index, valid_paths, matrix

def load_index():
    index  = faiss.read_index(FAISS_FILE)
    with open(PATHS_FILE) as f:
        paths = json.load(f)
    # load raw matrix (needed for per-vector dot-product in smart_search)
    matrix = np.load(MATRIX_FILE) if os.path.exists(MATRIX_FILE) else None
    return index, paths, matrix

def check_new_photos(existing_paths, image_folder):
    all_paths = find_images(image_folder)
    existing  = set(existing_paths)
    return [p for p in all_paths if p not in existing]

def update_index(new_paths, existing_paths,
                 faiss_index, matrix, model, preprocess):
    print(f"\nAdding {len(new_paths)} new photos...")
    new_embeddings = []
    valid_new      = []

    for path in tqdm(new_paths, desc="Indexing new"):
        try:
            img = preprocess(
                Image.open(path).convert("RGB")
            ).unsqueeze(0).to(device)
            with torch.no_grad():
                feat = model.encode_image(img)
                feat /= feat.norm(dim=-1, keepdim=True)
            new_embeddings.append(feat.cpu().numpy())
            valid_new.append(path)
        except Exception:
            pass

    if valid_new:
        new_matrix  = np.vstack(new_embeddings).astype("float32")
        faiss_index.add(new_matrix)
        all_paths   = existing_paths + valid_new
        full_matrix = np.vstack([matrix, new_matrix]) if matrix is not None else new_matrix

        faiss.write_index(faiss_index, FAISS_FILE)
        np.save(MATRIX_FILE, full_matrix)
        with open(PATHS_FILE, "w") as f:
            json.dump(all_paths, f)

        print(f"✓ Updated — {len(all_paths)} total\n")
        return faiss_index, all_paths, full_matrix

    return faiss_index, existing_paths, matrix

# ── face registration ─────────────────────────────────
def register_face(image_path, name):
    """
    Returns (success: bool, message: str)
    """
    print(f"\n  Loading: {os.path.basename(image_path)}")
    try:
        img = face_recognition.load_image_file(image_path)
    except Exception as e:
        return False, f"Cannot open image: {e}"

    # use CNN model if available for better accuracy; hog is faster
    locations = face_recognition.face_locations(img, model="hog")

    if not locations:
        return False, (
            "No face found — try a clearer, "
            "front-facing photo with good lighting"
        )

    if len(locations) > 1:
        print(f"  ⚠ {len(locations)} faces found — using the largest one")
        # pick largest bounding box
        locations = [
            max(locations,
                key=lambda loc: (loc[2] - loc[0]) * (loc[1] - loc[3]))
        ]

    try:
        encodings = face_recognition.face_encodings(
            img, locations, num_jitters=2   # ← more jitters = more accurate
        )
    except Exception as e:
        return False, f"Encoding failed: {e}"

    if not encodings:
        return False, "Could not encode face — try another photo"

    save_known_face(name, encodings[0])
    return True, f"'{name}' registered successfully"

# ── face scan (threaded) ──────────────────────────────
def scan_faces_in_gallery(image_folder):
    """
    Runs in a daemon thread.
    Updates _scan_status dict so the UI can poll it.
    """
    global _scan_status

    known_names, known_encodings = load_known_faces()
    if not known_encodings:
        with _scan_lock:
            _scan_status.update({
                "running": False,
                "done":    True,
                "message": "No registered faces — press F to add one",
            })
        return

    image_paths = find_images(image_folder)
    total       = len(image_paths)

    with _scan_lock:
        _scan_status.update({
            "running": True,
            "matched": 0,
            "total":   total,
            "done":    False,
            "message": f"Scanning {total} photos...",
        })

    matched = 0
    for i, path in enumerate(image_paths):
        # update progress every 10 photos
        if i % 10 == 0:
            with _scan_lock:
                _scan_status["message"] = (
                    f"Scanning {i}/{total}  "
                    f"matches so far: {matched}"
                )

        try:
            img       = face_recognition.load_image_file(path)
            locations = face_recognition.face_locations(img, model="hog")
            if not locations:
                continue

            encodings = face_recognition.face_encodings(img, locations)
            for enc in encodings:
                matches   = face_recognition.compare_faces(
                    known_encodings, enc, tolerance=0.5
                )
                distances = face_recognition.face_distance(
                    known_encodings, enc
                )
                if True in matches:
                    best_idx = int(np.argmin(distances))
                    save_photo_face(path, known_names[best_idx])
                    matched += 1

        except Exception:
            pass

    with _scan_lock:
        _scan_status.update({
            "running": False,
            "matched": matched,
            "done":    True,
            "message": (
                f"✓ Scan complete! "
                f"{matched} matches in {total} photos"
            ),
        })

def start_face_scan(image_folder):
    """Start background scan and return immediately."""
    global _scan_status
    with _scan_lock:
        if _scan_status["running"]:
            return False   # already running
    t = threading.Thread(
        target=scan_faces_in_gallery,
        args=(image_folder,),
        daemon=True
    )
    t.start()
    return True

# ── search ────────────────────────────────────────────
def search_clips(query, paths, faiss_index, model, top_k=TOP_K):
    with torch.no_grad():
        text  = clip.tokenize([query], truncate=True).to(device)
        tfeat = model.encode_text(text)
        tfeat /= tfeat.norm(dim=-1, keepdim=True)

    query_vec       = tfeat.cpu().numpy().astype("float32")
    k               = min(top_k, len(paths))
    scores, indices = faiss_index.search(query_vec, k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if 0 <= idx < len(paths):
            results.append({
                "path":  paths[idx],
                "score": float(score),
                "name":  os.path.basename(paths[idx]),
                "type":  "clip",
            })
    return results

def smart_search(query, paths, faiss_index, matrix, model):
    """
    1. Check if query contains a known person name.
    2. If yes  → fetch face-matched photos from DB.
    3. If remaining query text exists → score those photos with CLIP.
    4. Otherwise → pure CLIP search.
    """
    if not query.strip():
        return []

    known_names  = get_all_known_names()
    face_results = []
    remaining_q  = query.strip()
    matched_name = None

    # longest-match first so "John Smith" beats "John"
    for name in sorted(known_names, key=len, reverse=True):
        if name.lower() in query.lower():
            face_paths = get_photos_by_name(name)
            if face_paths:
                matched_name = name
                remaining_q  = query.lower().replace(
                    name.lower(), ""
                ).strip()
                face_results = [{
                    "path":  p,
                    "score": 1.0,
                    "name":  os.path.basename(p),
                    "type":  "face",
                } for p in face_paths]
            break   # use first (longest) match

    # face + CLIP hybrid
    if face_results and remaining_q and matrix is not None:
        face_path_set = {r["path"] for r in face_results}
        face_indices  = [
            i for i, p in enumerate(paths) if p in face_path_set
        ]

        if face_indices:
            with torch.no_grad():
                text  = clip.tokenize([remaining_q], truncate=True).to(device)
                tfeat = model.encode_text(text)
                tfeat /= tfeat.norm(dim=-1, keepdim=True)
            query_vec = tfeat.cpu().numpy().astype("float32").flatten()

            scored = []
            for idx in face_indices:
                img_vec = matrix[idx]                          # ← use saved matrix
                score   = float(np.dot(query_vec, img_vec))
                scored.append({
                    "path":  paths[idx],
                    "score": score,
                    "name":  os.path.basename(paths[idx]),
                    "type":  "face+clip",
                })

            scored.sort(key=lambda x: -x["score"])
            return scored[:TOP_K]

    # face only
    if face_results:
        return face_results[:TOP_K]

    # pure CLIP
    return search_clips(query, paths, faiss_index, model)

# ── UI ────────────────────────────────────────────────
def clear_screen():
    os.system("clear")

def get_scan_message():
    """Return a one-line status string for the face scanner."""
    with _scan_lock:
        s = dict(_scan_status)
    if s["running"]:
        return f"⏳ {s['message']}"
    if s["done"] and s["message"]:
        return f"✓  {s['message']}"
    return ""

def draw_ui(query, results, status, search_time,
            total_photos, message="", mode="search"):
    clear_screen()
    W = 62

    def row(content=""):
        content = str(content)
        # truncate so the box never breaks
        if len(content) > W - 4:
            content = content[: W - 7] + "..."
        return f"║  {content:<{W-4}}  ║"

    def divider():
        return "╠" + "═" * W + "╣"

    known_names   = get_all_known_names()
    scanned_count = get_face_scan_status()
    scan_msg      = get_scan_message()

    print("╔" + "═" * W + "╗")
    print(row("🔍 AI Photo Search"))
    print(row(
        f"📁 {total_photos} photos  "
        f"👤 {len(known_names)} people  "
        f"🔎 {scanned_count} scanned"
    ))
    if scan_msg:
        print(row(scan_msg))
    print(divider())

    if mode == "search":
        cursor    = "█" if int(time.time() * 2) % 2 == 0 else " "
        q_display = query[-(W - 14):] if len(query) > W - 14 else query
        print(row(f"Search: {q_display}{cursor}"))
        print(divider())

        if status == "empty":
            print(row("  Type to search your photos..."))
            print(row())
            print(row("  Examples:"))
            print(row("    family birthday"))
            print(row("    sunset on beach"))
            print(row("    Daniel at beach    ← combines face + scene"))
            print(row("    children playing"))
            if known_names:
                print(row())
                print(row(f"  Known people: {', '.join(known_names)}"))
            for _ in range(2):
                print(row())

        elif status == "searching":
            print(row("  Searching..."))
            for _ in range(TOP_K * 2 + 2):
                print(row())

        elif status == "results":
            t = f"{search_time * 1000:.0f}ms"
            print(row(f"  {len(results)} results  ({t})"))
            print(divider())
            if results:
                for r in results:
                    name  = r["name"]
                    score = r["score"]
                    rtype = r.get("type", "clip")
                    tag   = "👤" if "face" in rtype else "🖼"
                    type_label = f"[{rtype}]"
                    print(row(
                        f"{tag}  {name}  {score:.3f}  {type_label}"
                    ))
                    short_path = r["path"]
                    if len(short_path) > W - 8:
                        short_path = "..." + short_path[-(W - 11):]
                    print(row(f"    {short_path}"))
            else:
                print(row("  No results — try different keywords"))
                for _ in range(TOP_K * 2 - 1):
                    print(row())

    elif mode == "register":
        print(row("  👤 REGISTER FACE"))
        print(divider())
        print(row(message))
        for _ in range(8):
            print(row())

    print(divider())
    if mode == "search":
        print(row(
            "F=add face  S=scan gallery  "
            "Enter=search  Ctrl+C=quit"
        ))
    else:
        print(row("  Follow prompts above  |  Ctrl+C = cancel"))
    print("╚" + "═" * W + "╝")

# ── face registration flow ────────────────────────────
def face_registration_flow(image_folder):
    clear_screen()

    print("╔" + "═" * 60 + "╗")
    print("║  👤 Register a Face                                      ║")
    print("╠" + "═" * 60 + "╣")
    print("║  Step 1: person's name                                   ║")
    print("║  Step 2: path to a clear front-facing photo of them      ║")
    print("║  Tip: drag the photo into the terminal to paste its path ║")
    print("╚" + "═" * 60 + "╝\n")

    name = input("  Person's name: ").strip()
    if not name:
        print("  ✗ No name entered.")
        input("  Press Enter to go back...")
        return

    print(f"\n  Now give a clear photo of {name}")
    path = input("  Photo path: ").strip().strip("'\"")
    path = os.path.expanduser(path)

    if not os.path.exists(path):
        print(f"\n  ✗ File not found: {path}")
        input("\n  Press Enter to go back...")
        return

    success, msg = register_face(path, name)
    print(f"\n  {'✓' if success else '✗'}  {msg}")

    if success:
        print(f"\n  Starting background scan for {name} in gallery...")
        started = start_face_scan(image_folder)
        if started:
            print("  Scan running — you can search while it works.")
        else:
            print("  A scan is already running.")

    input("\n  Press Enter to continue...")

# ── main ──────────────────────────────────────────────
def main():
    print("=" * 62)
    print("  AI Photo Gallery Search")
    print("=" * 62 + "\n")

    init_faces_db()
    image_folder      = get_image_folder()
    model, preprocess = load_model()

    # load or build FAISS index
    if os.path.exists(FAISS_FILE) and os.path.exists(PATHS_FILE):
        print("\nLoading index...")
        faiss_index, paths, matrix = load_index()
        print(f"✓ {len(paths)} photos ready\n")

        new = check_new_photos(paths, image_folder)
        if new:
            print(f"Found {len(new)} new photos!")
            ans = input("  Add to index? (y/n): ").strip().lower()
            if ans == "y":
                faiss_index, paths, matrix = update_index(
                    new, paths, faiss_index, matrix, model, preprocess
                )
    else:
        print("\nNo index found — building now...")
        faiss_index, paths, matrix = build_index(
            model, preprocess, image_folder
        )
        if faiss_index is None:
            return

    # ── search state ──────────────────────────────────
    query       = ""
    results     = []
    status      = "empty"
    search_time = 0.0
    timer       = None

    def do_search():
        nonlocal results, status, search_time
        if not query.strip():
            status  = "empty"
            results = []
            draw_ui(query, results, status, search_time, len(paths))
            return
        start       = time.time()
        results     = smart_search(query, paths, faiss_index, matrix, model)
        search_time = time.time() - start
        status      = "results"
        draw_ui(query, results, status, search_time, len(paths))

    draw_ui(query, results, status, search_time, len(paths))

    try:
        while True:
            key = readchar.readkey()

            # ── quit ──────────────────────────────────
            if key == readchar.key.CTRL_C:
                clear_screen()
                print("Bye!")
                sys.exit(0)

            # ── register face ─────────────────────────
            elif key.lower() == "f":
                face_registration_flow(image_folder)
                draw_ui(query, results, status, search_time, len(paths))

            # ── scan gallery ──────────────────────────
            elif key.lower() == "s":
                known_names = get_all_known_names()
                if not known_names:
                    draw_ui(
                        query, results, status, search_time, len(paths),
                        message="No faces registered yet! Press F first.",
                        mode="register",
                    )
                    time.sleep(2)
                else:
                    started = start_face_scan(image_folder)
                    msg = (
                        f"Scanning for {', '.join(known_names)} — running in background!"
                        if started else
                        "Scan already running..."
                    )
                    draw_ui(
                        query, results, status, search_time, len(paths),
                        message=msg, mode="register",
                    )
                    time.sleep(2)
                draw_ui(query, results, status, search_time, len(paths))

            # ── backspace ─────────────────────────────
            elif key in (readchar.key.BACKSPACE, "\x7f", "\x08"):
                if query:
                    query = query[:-1]
                    if timer:
                        timer.cancel()
                    if query:
                        status = "searching"
                        draw_ui(query, results, status,
                                search_time, len(paths))
                        timer = threading.Timer(SEARCH_DELAY, do_search)
                        timer.start()
                    else:
                        results = []
                        status  = "empty"
                        draw_ui(query, results, status,
                                search_time, len(paths))

            # ── enter = immediate search ───────────────
            elif key == readchar.key.ENTER:
                if query.strip():
                    if timer:
                        timer.cancel()
                    status = "searching"
                    draw_ui(query, results, status,
                            search_time, len(paths))
                    do_search()

            # ── normal typing ─────────────────────────
            elif len(key) == 1 and key.isprintable():
                query += key
                status = "searching"
                if timer:
                    timer.cancel()
                draw_ui(query, results, status, search_time, len(paths))
                timer = threading.Timer(SEARCH_DELAY, do_search)
                timer.start()

    except (KeyboardInterrupt, SystemExit):
        clear_screen()
        print("Bye!")

if __name__ == "__main__":
    main()
