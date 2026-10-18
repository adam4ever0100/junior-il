"""HTML -> plain text, without pulling in a parser dependency.

Job descriptions arrive as ATS-authored HTML. We only need readable text with
line structure preserved, because the normalizer looks for phrases like
"3+ years" that must not get glued to the previous sentence.
"""
import re
from html.parser import HTMLParser

_BLOCK = {
    "p", "div", "br", "li", "ul", "ol", "tr", "table",
    "h1", "h2", "h3", "h4", "h5", "h6", "section", "article",
}
_SKIP = {"script", "style"}


class _Extractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skipping = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in _SKIP:
            self._skipping += 1
        elif tag in _BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP and self._skipping:
            self._skipping -= 1
        elif tag in _BLOCK:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skipping:
            self.parts.append(data)


# Tag-shaped text left over after a pass, e.g. "<li>" surviving as literal
# characters. Deliberately narrow: a description legitimately containing
# "a < b" or "<24h response" must not be mistaken for markup.
_RESIDUAL_TAG = re.compile(r"</?[a-zA-Z][a-zA-Z0-9]{0,14}(\s[^<>]{0,200})?/?>")

# Two passes, no more. Greenhouse double-encodes — it sends "&lt;li&gt;", so
# one pass only turns the entities into literal "<li>" text instead of a line
# break — while other boards send plain HTML and need exactly one pass. A small
# fixed bound beats looping: text that still looks like markup after two passes
# is far likelier to be prose about markup than a third layer of encoding.
_MAX_PASSES = 2


def _strip_once(html: str) -> str:
    parser = _Extractor()
    parser.feed(html)
    parser.close()
    return "".join(parser.parts)


def html_to_text(html: str) -> str:
    """Flatten ATS-authored HTML to readable text, keeping line structure.

    Handles both plain and HTML-escaped HTML, because an ATS that escapes its
    own markup would otherwise hand the normalizer one unbroken wall of text,
    and "5+ years" glued to the end of the previous bullet is invisible to it.
    """
    if not html:
        return ""
    text = _strip_once(html)
    for _ in range(_MAX_PASSES - 1):
        if not _RESIDUAL_TAG.search(text):
            break
        text = _strip_once(text)
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
