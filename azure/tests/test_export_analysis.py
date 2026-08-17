"""Notebook'u arayüzün okuyabileceği bir yapıya çeviren dışa aktarım.

Testler gerçek `notebooks/analiz_full.ipynb` üzerinde çalışır — uydurma bir
fixture, notebook'un biçimi değiştiğinde sessizce geçmeye devam ederdi.
Ölçülmüş yapı: 60 hücre, 21 markdown, 39 kod, 10 PNG, 20 tablo, 6 akış çıktısı.
"""

import json
from pathlib import Path

import pytest

from azure.scripts.export_analysis import (
    build_document,
    parse_table_html,
    split_into_sections,
)

NOTEBOOK = Path("notebooks/analiz_full.ipynb")


@pytest.fixture(scope="module")
def notebook():
    if not NOTEBOOK.exists():
        pytest.skip("analiz_full.ipynb bu ortamda yok")
    return json.loads(NOTEBOOK.read_text(encoding="utf-8"))


# --- bölümleme ---------------------------------------------------------------


def test_sections_are_split_on_markdown_headings(notebook):
    """Her `## ` başlığı yeni bir bölüm açar."""
    sections = split_into_sections(notebook["cells"])

    titles = [section["title"] for section in sections]
    assert "A1 — Son 2 yılın satış performansı ve ürün kırılımı" in titles
    assert "A7 — Bir sonraki ay talep tahmini" in titles


def test_every_section_has_a_stable_anchor_id(notebook):
    """Kenar çubuğu bağlantıları bu kimliklere dayanıyor; benzersiz olmalı."""
    sections = split_into_sections(notebook["cells"])

    ids = [section["id"] for section in sections]
    assert len(ids) == len(set(ids))
    assert all(id_ and " " not in id_ for id_ in ids)


def test_no_cell_is_lost_during_splitting(notebook):
    """Her hücre tam olarak bir bölüme girer — sessiz kayıp olmamalı."""
    sections = split_into_sections(notebook["cells"])

    counted = sum(len(section["blocks"]) for section in sections)
    narrative = sum(1 for c in notebook["cells"] if c["cell_type"] == "markdown")
    code = sum(1 for c in notebook["cells"] if c["cell_type"] == "code")
    assert counted == narrative + code


# --- tablolar ----------------------------------------------------------------


def test_a_pandas_table_becomes_headers_and_rows():
    """Pandas HTML'i ham enjekte edilmez; başlık + satır verisine çevrilir."""
    html = """
    <table border="1" class="dataframe">
      <thead><tr><th>pazar</th><th>brut_kutu</th></tr></thead>
      <tbody>
        <tr><td>A Pazarı</td><td>1.234</td></tr>
        <tr><td>B Pazarı</td><td>5.678</td></tr>
      </tbody>
    </table>
    """

    table = parse_table_html(html)

    assert table["headers"] == ["pazar", "brut_kutu"]
    assert table["rows"] == [["A Pazarı", "1.234"], ["B Pazarı", "5.678"]]


def test_a_table_with_an_index_column_keeps_its_row_labels():
    """Pandas satır etiketlerini <th> ile yazar; kaybolmamalılar."""
    html = """
    <table class="dataframe">
      <thead><tr><th></th><th>mae</th></tr></thead>
      <tbody>
        <tr><th>Naive</th><td>12,3</td></tr>
      </tbody>
    </table>
    """

    table = parse_table_html(html)

    assert table["rows"] == [["Naive", "12,3"]]


# --- belge -------------------------------------------------------------------


def test_figures_are_extracted_as_files_not_inline_base64(notebook, tmp_path):
    """10 PNG figür ayrı dosya olur; JSON'a gömülürse yüzlerce KB şişer."""
    document = build_document(notebook, tmp_path)

    figures = [
        block
        for section in document["sections"]
        for block in section["blocks"]
        if block["type"] == "figure"
    ]
    assert len(figures) == 10
    for figure in figures:
        assert (tmp_path / Path(figure["src"]).name).exists()
        assert "base64" not in json.dumps(figure)


def test_code_blocks_keep_their_source(notebook, tmp_path):
    """Değerlendiren kodu doğrulayabilmeli — katlanabilir ama mevcut."""
    document = build_document(notebook, tmp_path)

    code_blocks = [
        block
        for section in document["sections"]
        for block in section["blocks"]
        if block["type"] == "code"
    ]
    assert len(code_blocks) == 39
    assert any("def " in block["source"] for block in code_blocks)


def test_the_document_carries_every_measured_output(notebook, tmp_path):
    """Ölçülmüş sayılar: 20 tablo, 6 akış çıktısı."""
    document = build_document(notebook, tmp_path)

    kinds = [block["type"] for section in document["sections"] for block in section["blocks"]]
    assert kinds.count("table") == 20
    assert kinds.count("stream") == 6


def test_the_document_is_json_serialisable(notebook, tmp_path):
    """Çıktı doğrudan `analysis.json` olarak yazılıyor."""
    document = build_document(notebook, tmp_path)

    assert json.loads(json.dumps(document, ensure_ascii=False))["sections"]
