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


def html_to_text(html: str) -> str:
    if not html:
        return ""
    parser = _Extractor()
    parser.feed(html)
    parser.close()
    text = "".join(parser.parts)
    text = text.replace(" ", " ")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
