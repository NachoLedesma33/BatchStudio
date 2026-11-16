from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.operations.split import (
    PageRange,
    SplitSpecError,
    ensure_pdf_suffix,
    every_ranges,
    find_overlaps,
    parse_ranges,
    render_template,
    sanitize_filename,
    unique_output_path,
)


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        ("1-3", [(1, 3)]),
        ("1-3, 5, 8-10", [(1, 3), (5, 5), (8, 10)]),
        ("3", [(3, 3)]),
        ("7-", [(7, 10)]),
        ("-3", [(1, 3)]),
        (" -3 , 5-6 ", [(1, 3), (5, 6)]),
        ("1-1", [(1, 1)]),
    ],
)
def test_parse_ranges_validos(spec: str, expected: list[tuple[int, int]]) -> None:
    assert [(item.start, item.end) for item in parse_ranges(spec, 10)] == expected


@pytest.mark.parametrize(
    ("spec", "code"),
    [
        ("", "EMPTY_RANGES"),
        ("   ", "EMPTY_RANGES"),
        ("1-3,,5", "EMPTY_GROUP"),
        ("1,,3", "EMPTY_GROUP"),
        ("1-3-5", "INVALID_RANGE"),
        ("a-b", "INVALID_RANGE"),
        ("1-a", "INVALID_RANGE"),
        ("0", "PAGE_OUT_OF_RANGE"),
        ("0-3", "PAGE_OUT_OF_RANGE"),
        ("11", "PAGE_OUT_OF_RANGE"),
        ("5-11", "PAGE_OUT_OF_RANGE"),
        ("5-2", "RANGE_REVERSED"),
    ],
)
def test_parse_ranges_invalidos(spec: str, code: str) -> None:
    with pytest.raises(SplitSpecError) as exc:
        parse_ranges(spec, 10)
    assert exc.value.code == code


def test_parse_ranges_sin_paginas() -> None:
    with pytest.raises(SplitSpecError) as exc:
        parse_ranges("1", 0)
    assert exc.value.code == "NO_PAGES"


def test_every_ranges() -> None:
    assert [(r.start, r.end) for r in every_ranges(10, 3)] == [(1, 3), (4, 6), (7, 9), (10, 10)]
    assert [(r.start, r.end) for r in every_ranges(5, 1)] == [(1, 1), (2, 2), (3, 3), (4, 4), (5, 5)]
    with pytest.raises(SplitSpecError):
        every_ranges(10, 0)


def test_find_overlaps_solo_avisa_de_repetidas() -> None:
    assert find_overlaps([PageRange(1, 3), PageRange(4, 4), PageRange(5, 10)]) == []
    assert find_overlaps([PageRange(1, 3), PageRange(3, 5)]) == [3]
    assert find_overlaps([PageRange(1, 2), PageRange(2, 3), PageRange(2, 2)]) == [2]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("parte 1.pdf", "parte 1.pdf"),
        ('a<b>c:d"e/f\\g|h?i*j.pdf', "a_b_c_d_e_f_g_h_i_j.pdf"),
        ("CON.pdf", "_CON.pdf"),
        ("con", "_con"),
        ("reporte. ", "reporte"),
        ("", "documento"),
        ("...", "documento"),
    ],
)
def test_sanitize_filename(raw: str, expected: str) -> None:
    cleaned, changed = sanitize_filename(raw)
    assert cleaned == expected
    assert changed is (cleaned != raw)


def test_sanitize_recorta_nombres_largos() -> None:
    cleaned, changed = sanitize_filename("x" * 400 + ".pdf")
    assert changed is True
    assert len(cleaned) <= 120
    assert cleaned.endswith(".pdf")


def test_render_template_tokens_y_formato() -> None:
    rendered = render_template(
        "{name}_p{index:02}_{start}-{end}_{pages}_{date}",
        name="informe",
        index=2,
        start=4,
        end=6,
        pages=3,
        today=date(2026, 11, 16),
    )
    assert rendered == "informe_p02_4-6_3_20261116"


def test_render_template_default_y_extension() -> None:
    assert render_template("", name="acta", index=1, start=1, end=1, pages=1) == "acta_parte_01"
    assert ensure_pdf_suffix("acta_parte_01") == "acta_parte_01.pdf"
    assert ensure_pdf_suffix("acta.PDF") == "acta.PDF"


def test_render_template_rechaza_tokens_y_formatos_invalidos() -> None:
    with pytest.raises(SplitSpecError) as exc:
        render_template("{nombre}", name="a", index=1, start=1, end=1, pages=1)
    assert exc.value.code == "INVALID_TEMPLATE"

    with pytest.raises(SplitSpecError) as exc:
        render_template("{index:zz}", name="a", index=1, start=1, end=1, pages=1)
    assert exc.value.code == "INVALID_TEMPLATE"


def test_unique_output_path_no_pisa_archivos(tmp_path: Path) -> None:
    first = tmp_path / "parte.pdf"
    first.write_bytes(b"%PDF-1.4")
    used: set[str] = set()
    second = unique_output_path(first, used)
    third = unique_output_path(first, used)
    assert second.name == "parte_2.pdf"
    assert third.name == "parte_3.pdf"
    assert first.read_bytes() == b"%PDF-1.4"
