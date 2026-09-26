"""
Tests locales (sin framework): lógica + pipeline mock + conectividad real.

    python test_local.py

La conectividad es de solo lectura (SELECT / HTTP GET). Las fuentes que
requieren VPN o credenciales pendientes se reportan como AVISO, no como fallo.
"""
import datetime
import os
import subprocess
import sys
import urllib.request

import config
import db_validator
import excel_builder
import mailer
import web_extractor

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# Lógica
# ---------------------------------------------------------------------------
def test_logic():
    # Rango de fechas
    from_date, to_date = db_validator.date_range(5)
    today = datetime.date.today()
    assert to_date == today.isoformat()
    assert from_date == (today - datetime.timedelta(days=5)).isoformat()

    # Asunto y cuerpo
    subject = main_subject(today)
    assert subject == f"Reporte de transacciones atrapadas EPA {today.strftime('%d-%m-%Y')}"

    metrics = {"VE": {"report": 0, "monitor": 0},
               "SV": {"report": 2, "monitor": 0},
               "GT": {"report": 0, "monitor": 2, "legacy_stellar": 0, "pendientes": 2}}
    body = main_body(today, metrics, {"VE": ["12"], "SV": [], "GT": []}, [])
    assert "SV: 2 en el Reporte Web y 0 en el Monitor." in body
    assert "GT: 0 en el Reporte Web, 2 en el Monitor, 0 diferencias entre Legacy y Stellar y 2 pendientes por imprimir." in body
    assert "tiendas 12 están apagadas" in body
    assert "Saludos cordiales." in body

    # Adjuntos del correo
    msg = mailer.build_message("x@gmail.com", subject, body, [])
    assert msg["To"].count("@") == len(config.RECIPIENTS) == 15

    # Columnas del Excel
    assert config.EXCEL_COLUMNS == ["Tienda", "POS/Caja", "TR EPA", "StellarDocID", "Origen", "Observaciones"]
    print("[OK] Lógica (fechas, asunto, cuerpo, destinatarios, columnas)")


def test_mock_pipeline():
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        web = web_extractor.extract_all(5, tmp, mock=True)
        assert set(web) == {"VE", "SV", "GT"}
        assert all(w.report_pdf and w.monitor_pdf for w in web.values())
        files = [w.report_pdf or "" for w in web.values()] + [w.monitor_pdf or "" for w in web.values()]
        assert len(files) == 6 and all(files)

    db = db_validator.validate_all(5, mock=True)
    assert set(db) == {"VE", "SV", "GT"}
    assert db["GT"][2].count == 1  # pendientes por imprimir

    # CLI end-to-end sin red ni envío
    proc = subprocess.run(
        [sys.executable, "main.py", "--mock", "--dry-run", "--no-confirm"],
        capture_output=True, text=True, cwd=BASE_DIR,
    )
    assert proc.returncode == 0, proc.stderr
    assert "ASUNTO:" in proc.stdout
    assert "ADJUNTOS (7)" in proc.stdout, proc.stdout[-800:]
    print("[OK] Pipeline mock end-to-end (7 adjuntos, sin envío)")


# ---------------------------------------------------------------------------
# Conectividad real (solo lectura)
# ---------------------------------------------------------------------------
def _port(host, port, timeout=5):
    import socket
    try:
        with socket.create_connection((host, port), timeout):
            return True
    except Exception:  # noqa: BLE001
        return False


def _http(url, timeout=8):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status
    except Exception as exc:  # noqa: BLE001
        return f"ERR {str(exc)[:40]}"


def test_connectivity():
    print("\n--- Conectividad (solo lectura) ---")
    hard_fail = []

    # AS400 / DB2
    for name, cfg, tables in [
        ("AS400 Central VE", config.AS400_VE_CENTRAL, [("ventas", "trcmov"), ("cr", "DEVOLUCIONVENTA")]),
        ("AS400 Central SV", config.AS400_SV_CENTRAL, [("ventas", "trcmov")]),
    ]:
        try:
            conn = db_validator.connect_db2(cfg)
            cur = conn.cursor()
            for sch, tbl in tables:
                cur.execute(f"SELECT * FROM {sch}.{tbl} FETCH FIRST 1 ROW ONLY")
                cur.fetchall()
            conn.close()
            print(f"  [OK] {name}")
        except Exception as exc:  # noqa: BLE001
            print(f"  [FAIL] {name}: {str(exc)[:70]}")
            hard_fail.append(name)

    # SQL Server tienda Stellar
    store_cfg = {"host": None, "user": config.STELLAR_STORE_USER, "pass": config.STELLAR_STORE_PASS}
    for name, host in [("Stellar VE t2", "stellardb.t2.ve.epa.com"),
                       ("Stellar GT t3", "stellardb.t3.gt.epa.com")]:
        store_cfg["host"] = host
        try:
            conn = db_validator.connect_mssql(store_cfg)
            cur = conn.cursor()
            cur.execute("SELECT TOP 0 * FROM VAD20.dbo.MA_PAGOS")
            cur.fetchall()
            conn.close()
            print(f"  [OK] {name} (VAD20.dbo.MA_PAGOS)")
        except Exception as exc:  # noqa: BLE001
            print(f"  [FAIL] {name}: {str(exc)[:70]}")
            hard_fail.append(name)

    # Central Stellar GT (requiere VPN)
    try:
        conn = db_validator.connect_mssql(config.CENTRAL_STELLAR_GT, database="VENTASSTORE")
        cur = conn.cursor()
        cur.execute("SELECT TOP 0 * FROM VENTASSTORE.dbo.TICKET")
        cur.fetchall()
        conn.close()
        print("  [OK] Central Stellar GT (VENTASSTORE.dbo.TICKET)")
    except Exception as exc:  # noqa: BLE001
        print(f"  [AVISO] Central Stellar GT: {str(exc)[:70]} (¿VPN activa?)")

    # Central Stellar VE
    try:
        conn = db_validator.connect_mssql(config.CENTRAL_STELLAR_VE, database="VENTASSTORE")
        cur = conn.cursor()
        cur.execute("SELECT TOP 0 * FROM VENTASSTORE.dbo.TICKET")
        cur.fetchall()
        conn.close()
        print("  [OK] Central Stellar VE (VENTASSTORE.dbo.TICKET)")
    except Exception as exc:  # noqa: BLE001
        print(f"  [FAIL] Central Stellar VE: {str(exc)[:70]}")
        hard_fail.append("Central Stellar VE")

    # Webs
    for name, url in [("Reporte Web", config.REPORT_WEB_URL),
                      ("Monitor VE", config.MONITOR_BASE_URL + "/ve"),
                      ("Monitor SV", config.MONITOR_BASE_URL + "/sv"),
                      ("Monitor GT", config.MONITOR_BASE_URL + "/gt")]:
        status = _http(url)
        if status == 200:
            print(f"  [OK] {name} (200)")
        else:
            print(f"  [FAIL] {name}: {status}")
            hard_fail.append(name)

    return hard_fail


# ---------------------------------------------------------------------------
# Helpers (importan de main sin ejecutar su CLI)
# ---------------------------------------------------------------------------
def _load_main():
    import importlib
    return importlib.import_module("main")


_main = _load_main()
main_subject = _main.build_subject
main_body = _main.build_body


if __name__ == "__main__":
    test_logic()
    test_mock_pipeline()
    fails = test_connectivity()
    print("\n" + "=" * 50)
    if fails:
        print(f"RESULTADO: fallos en {len(fails)} fuente(s): {', '.join(fails)}")
        sys.exit(1)
    print("RESULTADO: lógica y pipeline OK. Conectividad OK (avisos no bloqueantes).")
