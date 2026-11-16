from __future__ import annotations

import hashlib
from pathlib import Path

import pymupdf
import pytest
from fastapi.testclient import TestClient


def _import_paths(client: TestClient, paths: list[Path]) -> list[dict]:
    response = client.post("/api/files/import", json={"paths": [str(path) for path in paths]})
    assert response.status_code == 200, response.text
    return response.json()["documents"]


def _preview(client: TestClient, params: dict) -> dict:
    response = client.post("/api/operations/preview", json={"kind": "split", "params": params})
    assert response.status_code == 200, response.text
    return response.json()


def _run_job(client: TestClient, services, params: dict) -> tuple[str, dict]:
    response = client.post("/api/jobs", json={"kind": "split", "params": params})
    assert response.status_code == 202, response.text
    job_id = response.json()["job_id"]
    assert services.worker.run_once() is True
    report = client.get(f"/api/jobs/{job_id}/report")
    assert report.status_code == 200, report.text
    return job_id, report.json()


def _fingerprint(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest, path.stat().st_mtime_ns


def _page_counts(paths: list[str]) -> list[int]:
    counts = []
    for raw in paths:
        with pymupdf.open(raw) as doc:
            counts.append(doc.page_count)
    return counts


def test_split_preview_y_job_coinciden(
    client: TestClient, services, ten_page_pdf: Path, tmp_path: Path
) -> None:
    _import_paths(client, [ten_page_pdf])
    out_dir = tmp_path / "salida"
    params = {
        "mode": "ranges",
        "ranges": "1-3, 4, 5-10",
        "output_dir": str(out_dir),
        "name_template": "parte_{index:02}",
    }

    preview = _preview(client, params)
    assert preview["errors"] == [], preview
    assert preview["summary"]["total_files"] == 3
    assert preview["summary"]["total_pages"] == 10
    assert [len(item["pages"]) for item in preview["items"]] == [3, 1, 6]
    assert not out_dir.exists()

    before = _fingerprint(ten_page_pdf)
    _, report = _run_job(client, services, params)
    assert report["status"] == "completed", report
    assert report["result"]["total_files"] == 3
    assert report["result"]["total_pages"] == 10

    outputs = [item["output_path"] for item in report["items"]]
    assert [Path(path).name for path in outputs] == ["parte_01.pdf", "parte_02.pdf", "parte_03.pdf"]
    assert _page_counts(outputs) == [3, 1, 6]
    assert len(preview["items"]) == len(report["items"])

    after = _fingerprint(ten_page_pdf)
    assert before == after, "el original no debe cambiar (contenido ni mtime)"


def test_split_una_pagina_por_archivo(
    client: TestClient, services, tmp_path: Path
) -> None:
    source = tmp_path / "cinco.pdf"
    doc = pymupdf.open()
    for index in range(5):
        page = doc.new_page()
        page.insert_text((72, 72), f"Página {index + 1}")
    doc.save(source)
    doc.close()

    _import_paths(client, [source])
    out_dir = tmp_path / "por-pagina"
    params = {"mode": "single", "output_dir": str(out_dir), "name_template": "p{index}"}

    _, report = _run_job(client, services, params)
    assert report["status"] == "completed", report
    assert report["result"]["total_files"] == 5
    outputs = sorted(item["output_path"] for item in report["items"])
    assert _page_counts(outputs) == [1, 1, 1, 1, 1]


def test_split_every_n_paginas(client: TestClient, services, ten_page_pdf: Path, tmp_path: Path) -> None:
    _import_paths(client, [ten_page_pdf])
    params = {
        "mode": "every",
        "every": 4,
        "output_dir": str(tmp_path / "cada4"),
    }
    _, report = _run_job(client, services, params)
    assert report["status"] == "completed", report
    outputs = [item["output_path"] for item in report["items"]]
    assert _page_counts(outputs) == [4, 4, 2]


def test_split_politica_suffix_no_pisa(
    client: TestClient, services, ten_page_pdf: Path, tmp_path: Path
) -> None:
    _import_paths(client, [ten_page_pdf])
    out_dir = tmp_path / "sufijo"
    params = {
        "mode": "ranges",
        "ranges": "1-3",
        "output_dir": str(out_dir),
        "name_template": "parte",
    }

    _, first = _run_job(client, services, params)
    assert first["status"] == "completed", first
    _, second = _run_job(client, services, params)
    assert second["status"] == "completed", second

    names = sorted(Path(item["output_path"]).name for item in second["items"])
    assert names == ["parte_2.pdf"]
    assert sorted(path.name for path in out_dir.glob("*.pdf")) == ["parte.pdf", "parte_2.pdf"]
    assert _page_counts([str(out_dir / "parte.pdf"), str(out_dir / "parte_2.pdf")]) == [3, 3]


def test_split_politica_fail_detecta_colision(
    client: TestClient, services, ten_page_pdf: Path, tmp_path: Path
) -> None:
    _import_paths(client, [ten_page_pdf])
    out_dir = tmp_path / "falla"
    out_dir.mkdir(parents=True)
    (out_dir / "parte.pdf").write_bytes(b"%PDF-1.4 existente")

    params = {
        "mode": "ranges",
        "ranges": "1-3",
        "output_dir": str(out_dir),
        "name_template": "parte",
        "collision_policy": "fail",
    }
    preview = _preview(client, params)
    assert preview["items"] == []
    assert [error["code"] for error in preview["errors"]] == ["OUTPUT_EXISTS"]

    _, report = _run_job(client, services, params)
    assert report["status"] == "failed"
    assert report["errors"][0]["code"] == "OUTPUT_EXISTS"
    assert (out_dir / "parte.pdf").read_bytes() == b"%PDF-1.4 existente"


def test_split_politica_overwrite(
    client: TestClient, services, ten_page_pdf: Path, tmp_path: Path
) -> None:
    _import_paths(client, [ten_page_pdf])
    out_dir = tmp_path / "sobrescribe"
    out_dir.mkdir(parents=True)
    target = out_dir / "parte.pdf"
    target.write_bytes(b"%PDF-1.4 viejo")

    params = {
        "mode": "ranges",
        "ranges": "1-3",
        "output_dir": str(out_dir),
        "name_template": "parte",
        "collision_policy": "overwrite",
    }
    _, report = _run_job(client, services, params)
    assert report["status"] == "completed", report
    assert _page_counts([str(target)]) == [3]


def test_split_rechaza_rangos_invalidos(client: TestClient, ten_page_pdf: Path, tmp_path: Path) -> None:
    _import_paths(client, [ten_page_pdf])
    preview = _preview(
        client,
        {"mode": "ranges", "ranges": "2-4, 30", "output_dir": str(tmp_path / "malo")},
    )
    assert preview["items"] == []
    assert preview["errors"][0]["code"] == "PAGE_OUT_OF_RANGE"
    assert "10 página" in preview["errors"][0]["message"]


def test_split_pdf_protegido_no_aborta_el_resto(
    client: TestClient, services, ten_page_pdf: Path, tmp_path: Path
) -> None:
    protected = tmp_path / "protegido.pdf"
    doc = pymupdf.open()
    doc.new_page()
    doc.save(
        protected,
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        owner_pw="duenio",
        user_pw="clave",
    )
    doc.close()

    _import_paths(client, [protected, ten_page_pdf])
    params = {
        "mode": "ranges",
        "ranges": "1-2",
        "output_dir": str(tmp_path / "protegido-salida"),
    }
    preview = _preview(client, params)
    assert preview["summary"]["total_files"] == 1
    codes = [warning["code"] for warning in preview["warnings"]]
    assert "SKIPPED_SOURCE" in codes

    _, report = _run_job(client, services, params)
    assert report["status"] == "completed_with_errors", report
    assert report["result"]["total_files"] == 1
    assert any(
        "protegido.pdf" in (error.get("message") or "") for error in report["errors"]
    )


def test_split_cancelado_no_publica_archivos(
    client: TestClient, services, ten_page_pdf: Path, tmp_path: Path
) -> None:
    _import_paths(client, [ten_page_pdf])
    out_dir = tmp_path / "cancelado"
    params = {"mode": "single", "output_dir": str(out_dir)}

    response = client.post("/api/jobs", json={"kind": "split", "params": params})
    job_id = response.json()["job_id"]
    assert client.post(f"/api/jobs/{job_id}/cancel").status_code == 200
    assert services.worker.run_once() is True

    report = client.get(f"/api/jobs/{job_id}/report").json()
    assert report["status"] == "cancelled"
    assert not any(out_dir.glob("*.pdf")) if out_dir.exists() else True


def test_split_sin_documentos(client: TestClient) -> None:
    preview = _preview(client, {"mode": "ranges", "ranges": "1-3"})
    assert preview["errors"][0]["code"] == "NO_DOCUMENTS"
