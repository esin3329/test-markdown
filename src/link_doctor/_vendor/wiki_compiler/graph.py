"""Upstream wiki-compiler graph.py, adapted for Unicode and alias matching.

Upstream: https://github.com/Emmimal/wiki-compiler
Pinned revision: b2b2b0ecf5f32d69e1cf6d9254216ab902f3d188
Copyright (c) 2026 Emmimal P Alexander; MIT License.
"""
import re

_WORD_RE = re.compile(r"[^\W_]+(?:['’][^\W_]+)*", re.UNICODE)


def _build_phrase_index(entities: dict) -> dict:
    index = {}
    for eid, ent in entities.items():
        phrases = [ent.name, *getattr(ent, "aliases", [])]
        for phrase in phrases:
            words = tuple(w.casefold() for w in _WORD_RE.findall(phrase))
            if words:
                index.setdefault(words[0], []).append((words, eid))
    for first_word in index:
        # Longest alias/name wins. Entity id breaks ties deterministically.
        index[first_word].sort(key=lambda pair: (-len(pair[0]), pair[1], pair[0]))
    return index


def build_graph(entities: dict) -> dict:
    """Build bidirectional whole-token mention edges, including aliases."""
    graph = {eid: {"outgoing": set(), "incoming": set()} for eid in entities}
    if not entities:
        return graph
    phrase_index = _build_phrase_index(entities)
    for eid, ent in entities.items():
        tokens = [w.casefold() for w in _WORD_RE.findall(ent.body)]
        seen_targets = set()
        for i, word in enumerate(tokens):
            candidates = phrase_index.get(word, ())
            for phrase, target_id in candidates:
                end = i + len(phrase)
                if end <= len(tokens) and tuple(tokens[i:end]) == phrase:
                    matches = {candidate_id for candidate_phrase, candidate_id in candidates if candidate_phrase == phrase}
                    if len(matches) == 1:
                        matched_id = next(iter(matches))
                        if matched_id != eid:
                            seen_targets.add(matched_id)
                    break
        for target_id in sorted(seen_targets):
            graph[eid]["outgoing"].add(target_id)
            graph[target_id]["incoming"].add(eid)
    return graph


def orphan_ids(graph: dict) -> list:
    return sorted(eid for eid, edges in graph.items() if not edges["incoming"])
