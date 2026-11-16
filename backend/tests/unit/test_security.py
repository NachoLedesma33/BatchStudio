from __future__ import annotations

import time
from pathlib import Path

import pytest

from app.core.errors import ApiError


def test_reveal_allows_job_output(services, tmp_path: Path) -> None:
    output = tmp_path / "salida" / "unido.pdf"
    output.parent.mkdir(parents=True)
    output.write_bytes(b"%PDF-1.4")
    services.jobs.create(
        kind="merge",
        session_id="local",
        params={"output_path": str(output)},
        total_items=1,
    )
    job = services.jobs.claim_next()
    assert job is not None
    services.jobs.finish(job["id"], status="completed", output={"output_path": str(output)})

    assert services.path_policy.assert_revealable(output) == output.resolve()


def test_reveal_denies_unrelated_path(services, tmp_path: Path) -> None:
    unrelated = tmp_path / "secreto.txt"
    unrelated.write_text("no")
    with pytest.raises(ApiError) as exc:
        services.path_policy.assert_revealable(unrelated)
    assert exc.value.status_code == 403
    assert exc.value.code == "PATH_NOT_ALLOWED"


def test_reveal_allows_dialog_path(services, tmp_path: Path) -> None:
    chosen = tmp_path / "elegido.pdf"
    chosen.write_bytes(b"%PDF-1.4")
    services.path_policy.approve_dialog_path(chosen)
    assert services.path_policy.assert_revealable(chosen) == chosen.resolve()


def test_validate_import(services, tmp_path: Path) -> None:
    pdf = tmp_path / "ok.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    assert services.path_policy.validate_import(pdf) == pdf
    with pytest.raises(ApiError):
        services.path_policy.validate_import(tmp_path / "missing.pdf")
    text = tmp_path / "no.txt"
    text.write_text("x")
    with pytest.raises(ApiError):
        services.path_policy.validate_import(text)


def test_capabilities_report_real_absence(services) -> None:
    started = time.perf_counter()
    payload = services.capabilities.detect(force=True)
    elapsed = time.perf_counter() - started
    assert elapsed < 3.0
    assert payload["pdf_engine"]["name"] == "PyMuPDF"
    assert payload["pdf_engine"]["available"] is True
    assert set(payload["tools"]) == {"tesseract", "libreoffice", "qpdf", "ghostscript"}
    for tool in payload["tools"].values():
        assert {"available", "path", "version", "note"} <= set(tool)
