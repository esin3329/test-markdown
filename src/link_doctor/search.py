"""SentenceTransformers-backed local semantic search with provenance cache."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

MODEL_ID = "google/embeddinggemma-2"
MODEL_REVISION = "914f7f89142e33e77833254d9c9b90c3cef7303b"
DEFAULT_DIMENSION = 256
CHUNK_WORDS = 420
RELATION_SIMILARITY_THRESHOLD = 0.55
CACHE_SCHEMA = 1


def _chunks(root: Path) -> list[dict]:
    result = []
    for path in sorted(p for p in root.rglob("*") if p.suffix.casefold() == ".md"):
        if not path.is_file() or path.is_symlink() or any(part in {".git", ".link-doctor", "node_modules", ".venv"} for part in path.parts):
            continue
        title = path.stem
        section = title
        current: list[tuple[int, str]] = []
        chunk_number = 0
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("#"):
                if current:
                    pieces = _split_chunk(path.relative_to(root).as_posix(), title, section, current, chunk_number)
                    result.extend(pieces)
                    chunk_number += len(pieces)
                    current = []
                section = line.lstrip("# ").strip() or title
            elif line.strip():
                current.append((number, line))
        if current:
            result.extend(_split_chunk(path.relative_to(root).as_posix(), title, section, current, chunk_number))
    return result


def _split_chunk(source: str, title: str, section: str, lines: list[tuple[int, str]], offset: int) -> list[dict]:
    words: list[str] = []
    word_lines: list[int] = []
    for number, text in lines:
        line_words = text.split()
        words.extend(line_words)
        word_lines.extend([number] * len(line_words))
    chunks = []
    for start in range(0, len(words), CHUNK_WORDS):
        content = " ".join(words[start:start + CHUNK_WORDS])
        if content:
            chunks.append({"source": source, "title": title, "section": section, "line": word_lines[start], "text": content, "chunk": offset + len(chunks)})
    return chunks


def _content_hash(chunks: list[dict]) -> str:
    content = [(c["source"], c["title"], c["section"], c["line"], c["text"]) for c in chunks]
    return hashlib.sha256(json.dumps(content, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def _cache_identity(chunks: list[dict], dimension: int, task: str) -> str:
    payload = {"schema": CACHE_SCHEMA, "model": MODEL_ID, "revision": MODEL_REVISION, "dimension": dimension, "task": task, "chunk_words": CHUNK_WORDS, "content_hash": _content_hash(chunks)}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def _load_model(device: str | None):
    try:
        import torch
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError("Semantic search requires the search extra; install with `pip install -e '.[search]'`.") from exc
    if device and device.startswith("cuda") and torch.cuda.is_available() and torch.cuda.is_bf16_supported():
        dtype = torch.bfloat16
    elif device and device.startswith("mps"):
        dtype = torch.float32
    elif device is None and torch.cuda.is_available() and torch.cuda.is_bf16_supported():
        dtype = torch.bfloat16
    else:
        dtype = torch.float32
    try:
        return SentenceTransformer(MODEL_ID, revision=MODEL_REVISION, device=device, model_kwargs={"torch_dtype": dtype}, config_kwargs={"vision_config": None, "audio_config": None})
    except Exception as exc:
        raise RuntimeError(f"Unable to load {MODEL_ID}@{MODEL_REVISION}; check model access and compatible Transformers dependencies: {exc}") from exc


def _encode(model, texts: list[str], task: str, dimension: int):
    import numpy as np
    if task == "SearchQuery":
        embeddings = model.encode_query(texts, truncate_dim=dimension, normalize_embeddings=True, convert_to_numpy=True)
    elif task == "SearchDocument":
        # Inputs already use the model-card's `title: … | text: …` document format.
        embeddings = model.encode(texts, truncate_dim=dimension, normalize_embeddings=True, convert_to_numpy=True)
    elif task == "SentenceSimilarity":
        embeddings = model.encode(texts, prompt_name="SentenceSimilarity", truncate_dim=dimension, normalize_embeddings=True, convert_to_numpy=True)
    else:
        raise ValueError(f"Unsupported EmbeddingGemma2 task: {task}")
    matrix = np.asarray(embeddings, dtype=np.float32)
    if matrix.ndim != 2 or matrix.shape[1] != dimension or not np.isfinite(matrix).all():
        raise RuntimeError(f"Model returned invalid {task} embeddings: shape={matrix.shape}")
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if not np.isfinite(norms).all() or np.any(norms <= 1e-12):
        raise RuntimeError(f"Model returned a zero or invalid {task} embedding")
    # Truncating an already-normalized Matryoshka vector changes its norm.
    matrix /= norms
    return matrix


def search(root_path: str | Path, query: str, top_k: int = 5, index_dir: str | Path | None = None, dimension: int = DEFAULT_DIMENSION, device: str | None = None, related: bool = True) -> dict:
    if not query.strip():
        raise ValueError("Search query must not be empty")
    if top_k < 1:
        raise ValueError("top-k must be positive")
    if dimension not in {128, 256, 512, 768}:
        raise ValueError("dimension must be one of 128, 256, 512, 768")
    root = Path(root_path).resolve(strict=True)
    if not root.is_dir():
        raise ValueError(f"Search root is not a directory: {root_path}")
    chunks = _chunks(root)
    if not chunks:
        return {"model": MODEL_ID, "revision": MODEL_REVISION, "dimension": dimension, "query": query, "results": [], "relation_candidates": []}
    cache_root = Path(index_dir) if index_dir else root / ".link-doctor" / "index"
    cache_root.mkdir(parents=True, exist_ok=True)
    model = _load_model(device)
    cache_reused = True
    vectors_by_task = {}
    content_hash = _content_hash(chunks)
    for task in (["SearchDocument", "SentenceSimilarity"] if related else ["SearchDocument"]):
        identity = _cache_identity(chunks, dimension, task)
        meta_path = cache_root / f"{identity}.json"
        vector_path = cache_root / f"{identity}.npy"
        if meta_path.exists() and vector_path.exists():
            try:
                import numpy as np
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                vectors = np.load(vector_path, allow_pickle=False)
                if meta.get("identity") == identity and meta.get("content_hash") == content_hash and vectors.shape == (len(chunks), dimension) and np.isfinite(vectors).all():
                    vectors_by_task[task] = vectors.astype(np.float32, copy=False)
                    continue
            except (OSError, ValueError, json.JSONDecodeError):
                pass
        cache_reused = False
        texts = [f"title: {chunk['title']} | text: {chunk['text']}" for chunk in chunks]
        vectors = _encode(model, texts, task, dimension)
        import numpy as np
        temp_vector = vector_path.with_suffix(".npy.tmp")
        with temp_vector.open("wb") as stream:
            np.save(stream, vectors, allow_pickle=False)
        temp_vector.replace(vector_path)
        meta_path.write_text(json.dumps({"identity": identity, "content_hash": content_hash, "model": MODEL_ID, "revision": MODEL_REVISION, "dimension": dimension, "task": task, "chunk_words": CHUNK_WORDS, "chunks": chunks}, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        vectors_by_task[task] = vectors
    query_vector = _encode(model, [query], "SearchQuery", dimension)[0]
    scores = vectors_by_task["SearchDocument"] @ query_vector
    order = sorted(range(len(chunks)), key=lambda i: (-float(scores[i]), chunks[i]["source"], chunks[i]["line"]))[:top_k]
    results = [{**{key: chunks[i][key] for key in ("source", "title", "section", "line", "chunk")}, "score": float(scores[i]), "text": chunks[i]["text"]} for i in order]
    candidates = []
    if related and len(chunks) > 1:
        matrix = vectors_by_task["SentenceSimilarity"]
        seen = set()
        for i in order:
            sims = matrix @ matrix[i]
            for relative, score in enumerate(sims):
                if relative <= i or score < RELATION_SIMILARITY_THRESHOLD:
                    continue
                left, right = chunks[i], chunks[relative]
                pair = ((left["source"], left["chunk"]), (right["source"], right["chunk"]))
                seen.add((float(score), pair, i, relative))
        for score, _, i, j in sorted(seen, key=lambda item: (-item[0], item[1]))[:top_k]:
            candidates.append({"source": chunks[i]["source"], "section": chunks[i]["section"], "line": chunks[i]["line"], "candidate": chunks[j]["source"], "candidate_section": chunks[j]["section"], "candidate_line": chunks[j]["line"], "score": score, "status": "unverified semantic relation candidate"})
    return {"model": MODEL_ID, "revision": MODEL_REVISION, "dimension": dimension, "query": query, "results": results, "relation_candidates": candidates, "cache_reused": cache_reused}
