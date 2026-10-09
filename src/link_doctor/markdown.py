"""Small deterministic Markdown indexer for links and document structure."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

FENCE = re.compile(r"^\s{0,3}(```+|~~~+)")
HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
WIKILINK = re.compile(r"\[\[([^\]]+)\]\]")
MDLINK = re.compile(r"!?\[[^\]]*\]\((<[^>]+>|[^)]+)\)")
REFDEF = re.compile(r"^\s{0,3}\[([^\]]+)\]:\s*(\S+)")


@dataclass(frozen=True)
class Link:
    target: str
    line: int
    kind: str
    label: str | None = None


@dataclass(frozen=True)
class Heading:
    title: str
    anchor: str
    level: int
    line: int


@dataclass(frozen=True)
class MarkdownIndex:
    links: tuple[Link, ...]
    headings: tuple[Heading, ...]
    aliases: tuple[str, ...]
    title: str
    body: str


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).strip().lower()
    value = re.sub(r"[^\w\-\s]", "", value, flags=re.UNICODE)
    return re.sub(r"[\s_-]+", "-", value).strip("-") or "section"


def index_markdown(text: str, source_name: str = "") -> MarkdownIndex:
    links: list[Link] = []
    headings: list[Heading] = []
    aliases: list[str] = []
    refdefs: dict[str, str] = {}
    ref_uses: list[tuple[str, int]] = []
    slug_counts: dict[str, int] = {}
    fence_char = ""
    fence_size = 0
    first_title = ""
    body_lines: list[str] = []

    for number, line in enumerate(text.splitlines(), 1):
        marker = FENCE.match(line)
        if marker:
            mark = marker.group(1)
            char = mark[0]
            if not fence_char:
                fence_char, fence_size = char, len(mark)
            elif char == fence_char and len(mark) >= fence_size:
                fence_char, fence_size = "", 0
            body_lines.append(line)
            continue
        if fence_char:
            body_lines.append(line)
            continue
        heading_match = HEADING.match(line)
        if heading_match:
            title = re.sub(r"`+([^`]+)`+", r"\1", heading_match.group(2)).strip()
            if not first_title:
                first_title = title
            base = slugify(title)
            count = slug_counts.get(base, 0)
            slug_counts[base] = count + 1
            headings.append(Heading(title, base if count == 0 else f"{base}-{count}", len(heading_match.group(1)), number))
        alias_match = re.match(r"^\s{0,3}aliases\s*:\s*(.+)$", line, re.IGNORECASE)
        if alias_match:
            aliases.extend(x.strip().strip("[]'\" ") for x in re.split(r",|;", alias_match.group(1)) if x.strip())
        definition = REFDEF.match(line)
        if definition:
            refdefs[definition.group(1).strip().casefold()] = definition.group(2)
        masked = re.sub(r"(`+)(.*?)\1", lambda match: " " * len(match.group(0)), line)
        for match in WIKILINK.finditer(masked):
            raw = match.group(1).strip()
            target, sep, label = raw.partition("|")
            links.append(Link(target.strip(), number, "wiki", label.strip() if sep else None))
        for match in MDLINK.finditer(masked):
            target = match.group(1).strip().strip("<>").split(maxsplit=1)[0]
            links.append(Link(target, number, "markdown"))
        if not definition:
            for match in re.finditer(r"(?<!!)\[([^\]]+)\](?!\()", masked):
                ref_uses.append((match.group(1).strip().casefold(), number))
        body_lines.append(line)
    for identifier, number in ref_uses:
        if identifier in refdefs:
            links.append(Link(refdefs[identifier], number, "markdown"))
    return MarkdownIndex(tuple(links), tuple(headings), tuple(aliases), first_title or source_name, "\n".join(body_lines))


def text_without_code(text: str) -> str:
    """Mask fenced and inline code before lexical relationship matching."""
    output = []
    fence_char = ""
    fence_size = 0
    for line in text.splitlines():
        marker = FENCE.match(line)
        if marker:
            mark = marker.group(1)
            char = mark[0]
            if not fence_char:
                fence_char, fence_size = char, len(mark)
            elif char == fence_char and len(mark) >= fence_size:
                fence_char, fence_size = "", 0
            output.append("")
        elif fence_char:
            output.append("")
        else:
            output.append(re.sub(r"(`+)(.*?)\1", lambda match: " " * len(match.group(0)), line))
    return "\n".join(output)
