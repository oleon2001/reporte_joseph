"""
Generación de entregables por versión.

Crea:  entregables/<VERSION>/
         reportes/        -> 6 PDFs (Reporte Web + Monitor)
         Detalles de Tr's atrapadas DD-MM-YYYY.xlsx
         MENSAJE.txt      -> asunto + cuerpo del correo
         DESTINATARIOS.txt-> lista de correos a adjuntar/enviar
         README.txt       -> resumen (métricas, fuentes, fecha)
         envio_adjuntos/  -> copia plana de los 7 adjuntos lista para adjuntar

La versión se autoincrementa: v1, v2, v3...
"""
import datetime
import glob
import json
import logging
import os
import re
import shutil

import config

log = logging.getLogger(__name__)

ENTREGABLES_DIR = os.path.join(config.BASE_DIR, "entregables")


def next_version():
    """Devuelve el siguiente número de versión (v1, v2, ...)."""
    os.makedirs(ENTREGABLES_DIR, exist_ok=True)
    versions = []
    for name in os.listdir(ENTREGABLES_DIR):
        m = re.fullmatch(r"v(\d+)", name)
        if m:
            versions.append(int(m.group(1)))
    return f"v{max(versions, default=0) + 1}"


def _write(path, text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def build_deliverable(version, date_str, web, db_results, metrics, subject, body,
                      recipients, attachments, errors, mock=False):
    """Crea la carpeta de entregables y devuelve su ruta."""
    root = os.path.join(ENTREGABLES_DIR, version)
    reportes_dir = os.path.join(root, "reportes")
    envio_dir = os.path.join(root, "envio_adjuntos")
    os.makedirs(reportes_dir, exist_ok=True)
    os.makedirs(envio_dir, exist_ok=True)

    # 1) Copiar los 7 adjuntos (planos, listos para adjuntar)
    for path in attachments:
        if os.path.exists(path):
            shutil.copy2(path, os.path.join(envio_dir, os.path.basename(path)))

    # 2) Copiar los PDFs del reporte web y monitor a reportes/
    for path in attachments:
        if path.lower().endswith(".pdf"):
            shutil.copy2(path, os.path.join(reportes_dir, os.path.basename(path)))

    # 2b) Validar que los PDFs tengan contenido real (no vacíos ni mock)
    bad_pdfs = []
    for path in attachments:
        if path.lower().endswith(".pdf"):
            size = os.path.getsize(path) if os.path.exists(path) else 0
            if size < 2000:
                bad_pdfs.append(f"{os.path.basename(path)} ({size} bytes)")
    if bad_pdfs:
        with open(os.path.join(root, "ADVERTENCIA_PDFS.txt"), "w", encoding="utf-8") as fh:
            fh.write(
                "ATENCIÓN: los siguientes PDFs no tienen contenido válido "
                "(posible corrida --mock o fallo de red):\n" + "\n".join(f"  - {b}" for b in bad_pdfs)
            )
        if mock:
            with open(os.path.join(root, "NO_ENVIAR_ES_MOCK.txt"), "w", encoding="utf-8") as fh:
                fh.write("Este entregable se generó con --mock. NO enviar.\n")
        else:
            raise RuntimeError(
                "PDFs inválidos en el entregable: " + ", ".join(bad_pdfs)
            )

    # 3) Mensaje del correo
    _write(
        os.path.join(root, "MENSAJE.txt"),
        f"Asunto: {subject}\n\n{'=' * 60}\n{body}\n",
    )

    # 4) Destinatarios
    _write(
        os.path.join(root, "DESTINATARIOS.txt"),
        "Para:\n" + "\n".join(recipients) + "\n\n"
        "CC:\n(ninguno)\n\n"
        f"Total: {len(recipients)} destinatarios\n",
    )

    # 5) README con el resumen
    lines = [
        f"ENTREGABLE {version} - Reporte de transacciones atrapadas EPA",
        f"Fecha: {date_str}",
        f"Generado: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "MÉTRICAS",
        f"  VE: Reporte Web={metrics['VE']['report']}  Monitor={metrics['VE']['monitor']}",
        f"  SV: Reporte Web={metrics['SV']['report']}  Monitor={metrics['SV']['monitor']}",
        f"  GT: Reporte Web={metrics['GT']['report']}  Monitor={metrics['GT']['monitor']}"
        f"  Legacy/Stellar={metrics['GT'].get('legacy_stellar', 0)}"
        f"  Pendientes={metrics['GT'].get('pendientes', 0)}",
        "",
        "FUENTES",
    ]
    for country, sources in db_results.items():
        for s in sources:
            state = f"{s.count} filas" if s.ok else f"N/D ({s.error[:60]})"
            lines.append(f"  [{country}] {s.name}: {state}")
    lines += [
        "",
        "ADJUNTOS",
    ]
    for path in attachments:
        lines.append(f"  - {os.path.basename(path)}")
    if errors:
        lines += ["", "AVISOS"] + [f"  ! {e}" for e in errors]
    _write(os.path.join(root, "README.txt"), "\n".join(lines) + "\n")

    # 6) Manifiesto legible por máquina
    with open(os.path.join(root, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump({
            "version": version,
            "date": date_str,
            "subject": subject,
            "recipients": recipients,
            "metrics": metrics,
            "attachments": [os.path.basename(a) for a in attachments],
            "errors": errors,
        }, fh, ensure_ascii=False, indent=2)

    log.info("Entregable creado: %s", root)
    return root


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        ENTREGABLES_DIR = tmp
        assert next_version() == "v1"
        assert next_version() == "v1"
        os.makedirs(os.path.join(tmp, "v1"))
        assert next_version() == "v2"
        with open(os.path.join(tmp, "v1", "x.pdf"), "wb") as fh:
            fh.write(b"%PDF-1.4 mock")
        # PDF inválido en modo no-mock debe fallar
        try:
            build_deliverable("v1", "01-01-2026", {}, {}, {"VE": {"report": 0, "monitor": 0},
                              "SV": {"report": 0, "monitor": 0},
                              "GT": {"report": 0, "monitor": 0}}, "s", "b", ["a@b.c"],
                              [os.path.join(tmp, "v1", "x.pdf")], [])
            raise AssertionError("debía fallar con PDF inválido")
        except RuntimeError:
            pass
    print("entregables OK")
