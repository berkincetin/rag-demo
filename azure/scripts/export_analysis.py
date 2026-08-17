"""`notebooks/analiz_full.ipynb` → arayüzün render ettiği JSON + PNG dosyaları.

Neden derleme anında dışa aktarım: notebook'u tarayıcıda çalıştırmak pandas,
statsmodels ve LightGBM'i istemciye taşımak demekti. Analiz zaten yapılmış;
sayfanın işi onu göstermek.

Tablolar ham HTML olarak enjekte edilmez. Pandas'ın ürettiği `<style scoped>`
bloğu koyu temada okunmaz metin üretir ve ham HTML enjeksiyonu gereksiz bir
saldırı yüzeyidir. Bunun yerine başlık + satır verisine çevrilip uygulamanın
kendi tablo bileşeniyle çizilir.

Çalıştırma:
    PYTHONIOENCODING=utf-8 python -m azure.scripts.export_analysis
"""

import argparse
import base64
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

# Bölüm ayırıcı: markdown hücresindeki ilk `## ` başlığı.
_HEADING = re.compile(r"^##\s+(.+?)\s*$", re.M)
_NON_WORD = re.compile(r"[^a-z0-9]+")

# Türkçe harfleri ASCII'ye indirger. `casefold()` öncesi uygulanır: Python'un
# varsayılan küçültmesi `İ` harfini iki kod noktasına açar ve çapa kimlikleri
# tarayıcıda eşleşmez olur.
_TR_MAP = str.maketrans(
    {
        "İ": "I",
        "I": "I",
        "ı": "i",
        "Ş": "S",
        "ş": "s",
        "Ğ": "G",
        "ğ": "g",
        "Ç": "C",
        "ç": "c",
        "Ö": "O",
        "ö": "o",
        "Ü": "U",
        "ü": "u",
    }
)


def slugify(text: str) -> str:
    """Başlıktan kararlı bir çapa kimliği üretir."""
    folded = text.translate(_TR_MAP).casefold()
    return _NON_WORD.sub("-", folded).strip("-")[:60]


class _TableParser(HTMLParser):
    """Pandas'ın `to_html` çıktısından başlık ve satırları toplar.

    Yalnızca `<th>`/`<td>` metnini alır; stil bloğu ve öznitelikler atılır.
    `<th>` hem başlık satırında hem de satır etiketi olarak geçtiği için
    ayrım `<thead>` içinde olup olmamasına göre yapılır.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.headers: list[str] = []
        self.rows: list[list[str]] = []
        self._in_head = False
        self._in_cell = False
        self._row: list[str] = []
        self._cell: list[str] = []

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        if tag == "thead":
            self._in_head = True
        elif tag == "tr":
            self._row = []
        elif tag in ("th", "td"):
            self._in_cell = True
            self._cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "thead":
            self._in_head = False
        elif tag in ("th", "td"):
            self._in_cell = False
            self._row.append("".join(self._cell).strip())
        elif tag == "tr":
            if self._in_head:
                self.headers = self._row
            elif self._row:
                self.rows.append(self._row)
            self._row = []

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell.append(data)


def parse_table_html(html: str) -> dict[str, Any]:
    """Pandas HTML tablosunu `{headers, rows}` yapısına çevirir."""
    parser = _TableParser()
    parser.feed(html)
    return {"headers": parser.headers, "rows": parser.rows}


def _text(source: Any) -> str:
    """Notebook kaynakları satır listesi ya da tek dize olabilir."""
    return "".join(source) if isinstance(source, list) else str(source)


def _outputs_to_blocks(
    outputs: list[dict[str, Any]], figures_dir: Path, counter: list[int]
) -> list[dict[str, Any]]:
    """Bir kod hücresinin çıktılarını bloklara çevirir."""
    blocks: list[dict[str, Any]] = []
    for output in outputs:
        kind = output.get("output_type")
        data = output.get("data", {})

        if "image/png" in data:
            counter[0] += 1
            name = f"figur-{counter[0]:02d}.png"
            payload = _text(data["image/png"])
            figures_dir.mkdir(parents=True, exist_ok=True)
            (figures_dir / name).write_bytes(base64.b64decode(payload))
            blocks.append(
                {
                    "type": "figure",
                    "src": f"/analiz/{name}",
                    "alt": _text(data.get("text/plain", "")).strip() or "Analiz figürü",
                }
            )
        elif "text/html" in data:
            table = parse_table_html(_text(data["text/html"]))
            if table["headers"] or table["rows"]:
                blocks.append({"type": "table", **table})
        elif kind == "stream":
            text = _text(output.get("text", "")).rstrip()
            if text:
                blocks.append({"type": "stream", "text": text})
        elif "text/plain" in data:
            text = _text(data["text/plain"]).rstrip()
            if text:
                blocks.append({"type": "stream", "text": text})
    return blocks


def split_into_sections(cells: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Hücreleri `## ` başlıklarına göre bölümlere ayırır.

    Başlıktan önceki hücreler (notebook'un ana başlığı) ilk bölüme girer, ki
    hiçbir hücre kaybolmasın.
    """
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for cell in cells:
        source = _text(cell["source"])
        heading = _HEADING.search(source) if cell["cell_type"] == "markdown" else None

        if heading:
            title = heading.group(1).strip()
            current = {"id": slugify(title), "title": title, "blocks": []}
            sections.append(current)
        elif current is None:
            current = {"id": "giris", "title": "Giriş", "blocks": []}
            sections.append(current)

        current["blocks"].append(cell)

    return sections


def build_document(notebook: dict[str, Any], figures_dir: Path) -> dict[str, Any]:
    """Notebook'u arayüzün render ettiği belgeye çevirir.

    Figürler `figures_dir` altına PNG olarak yazılır ve JSON'da yalnızca yolları
    taşınır — base64 gömülü olsaydı `analysis.json` megabaytlara çıkardı.
    """
    counter = [0]
    sections: list[dict[str, Any]] = []

    for raw in split_into_sections(notebook["cells"]):
        blocks: list[dict[str, Any]] = []

        for cell in raw["blocks"]:
            source = _text(cell["source"])

            if cell["cell_type"] == "markdown":
                # Bölümü açan `## ` satırı başlığa taşındı; gövdede tekrarlanmaz.
                body = _HEADING.sub("", source, count=1).strip()
                blocks.append({"type": "narrative", "markdown": body})
                continue

            blocks.append({"type": "code", "source": source.rstrip()})
            blocks.extend(_outputs_to_blocks(cell.get("outputs", []), figures_dir, counter))

        sections.append({"id": raw["id"], "title": raw["title"], "blocks": blocks})

    return {"sections": sections, "figureCount": counter[0]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--notebook", default="notebooks/analiz_full.ipynb")
    parser.add_argument("--out", default="azure/web/lib/analysis.json")
    parser.add_argument("--figures", default="azure/web/public/analiz")
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")  # konsol cp1252 (CLAUDE.md §7)

    notebook = json.loads(Path(args.notebook).read_text(encoding="utf-8"))
    document = build_document(notebook, Path(args.figures))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    blocks = sum(len(section["blocks"]) for section in document["sections"])
    print(f"{len(document['sections'])} bölüm, {blocks} blok, {document['figureCount']} figür")
    print(f"→ {out} ({out.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
