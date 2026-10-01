"""
Extracción web (Playwright headless + API) de:

  1. Reporte Web (BIRT) -> 1 PDF por país + métrica "Total Trx no actualizadas".
  2. Monitor           -> 1 PDF por país (escala 60%) + total de diferencias.

El conteo del Monitor se obtiene de su API REST (robusto, sin scraping); el PDF
se genera desde la UI con la escala solicitada. Los selectores del Reporte Web
están calibrados contra el sitio real.
"""
import datetime
import logging
import os
import re

import config

log = logging.getLogger(__name__)


class WebResult:
    def __init__(self, country):
        self.country = country
        self.report_pdf = None
        self.monitor_pdf = None
        self.report_total = 0
        self.report_rows = []
        self.monitor_total = 0
        self.monitor_rows = []
        self.error = ""

    def __repr__(self):
        return (f"<{self.country} web={self.report_total} monitor={self.monitor_total} "
                f"err={bool(self.error)}>")


def _to_int(value):
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    digits = re.sub(r"[^\d]", "", str(value))
    return int(digits) if digits else 0


def _all_text(page):
    chunks = []
    for frame in page.frames:
        try:
            chunks.append(frame.inner_text("body"))
        except Exception:  # noqa: BLE001
            pass
    return "\n".join(chunks)


def _param_frame(page, timeout=30000):
    """Espera a que el frame de parámetros del Reporte Web esté visible."""
    deadline = datetime.datetime.now() + datetime.timedelta(milliseconds=timeout)
    while datetime.datetime.now() < deadline:
        for frame in page.frames:
            try:
                loc = frame.locator(config.SELECTORS["report_server"])
                if loc.count() and loc.first.is_visible():
                    return frame
            except Exception:  # noqa: BLE001
                continue
        page.wait_for_timeout(1000)
    raise RuntimeError("No se encontró el frame de parámetros del Reporte Web")


def _extract_report_rows(page):
    """Extrae las filas de la tabla de resultados del Reporte Web.

    Columnas reales: Tienda | Caja | Transacción Inicial | Transacción Final |
    Cantidad Trx | Transacciones Faltantes. La TR EPA es "Transacción Inicial".
    """
    rows = []
    for frame in page.frames:
        try:
            tables = frame.locator("table")
            for t in range(tables.count()):
                table = tables.nth(t)
                trs = table.locator("tr").all()
                header_idx = None
                for i, tr in enumerate(trs):
                    cells = [c.inner_text().strip() for c in tr.locator("td,th").all()]
                    joined = " ".join(cells)
                    if "Tienda" in joined and "Caja" in joined and "Transacci" in joined:
                        header_idx = i
                        break
                if header_idx is None:
                    continue
                for tr in trs[header_idx + 1:]:
                    cells = [c.inner_text().strip() for c in tr.locator("td").all()]
                    nums = [c for c in cells if re.fullmatch(r"\d{1,9}", c)]
                    if len(nums) < 3:
                        continue
                    tienda, caja, tr_epa = nums[0], nums[1], nums[2]
                    # Filtro de sanidad: tienda<=99, caja<=99, TR EPA 4-7 dígitos.
                    if len(tienda) > 3 or len(caja) > 3 or not (3 <= len(tr_epa) <= 8):
                        continue
                    # Descartar la fila de fecha (Día=25, Mes=9, Año=2026).
                    if re.fullmatch(r"20\d{2}", tr_epa) and len(caja) <= 2 and len(tienda) <= 2:
                        continue
                    rows.append({"Tienda": tienda, "POS/Caja": caja, "TR EPA": tr_epa})
        except Exception:  # noqa: BLE001
            continue
    # Deduplicar manteniendo orden
    seen, unique = set(), []
    for r in rows:
        key = (r["Tienda"], r["POS/Caja"], r["TR EPA"])
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


def _dump_inspect(page, name, out_dir):
    try:
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, f"inspect_{name}.html"), "w", encoding="utf-8") as fh:
            fh.write(page.content())
        page.screenshot(path=os.path.join(out_dir, f"inspect_{name}.png"), full_page=True)
    except Exception as exc:  # noqa: BLE001
        log.warning("No se pudo volcar inspect %s: %s", name, exc)


# ---------------------------------------------------------------------------
# Reporte Web (BIRT)
# ---------------------------------------------------------------------------
def _extract_report(context, page, country, result, days_back, out_dir, inspect):
    meta = config.COUNTRIES[country]
    sel = config.SELECTORS
    today = datetime.date.today()
    from_date = today - datetime.timedelta(days=days_back)

    page.goto(config.REPORT_WEB_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(4000)
    frame = _param_frame(page)

    frame.select_option(sel["report_server"], config.REPORT_SERVER_VALUES[country])
    frame.fill(sel["report_date_from"], from_date.strftime(config.REPORT_DATE_FORMAT))
    frame.fill(sel["report_date_to"], today.strftime(config.REPORT_DATE_FORMAT))
    frame.locator(sel["report_ok"]).first.click(timeout=10000)
    page.wait_for_timeout(10000)

    if inspect:
        _dump_inspect(page, f"report_{country}", out_dir)

    match = re.search(sel["report_metric_re"], _all_text(page), re.IGNORECASE)
    result.report_total = _to_int(match.group(1)) if match else 0
    result.report_rows = _extract_report_rows(page)

    # Exportar a PDF (diálogo "Export report" -> formato PDF -> OK -> descarga).
    path = os.path.join(out_dir, f"Reporte Web {meta['name']}.pdf")
    frame.locator(sel["report_export"]).click(timeout=10000)
    page.wait_for_timeout(1500)
    frame.select_option(sel["report_export_format"], label="PDF")
    with page.expect_download(timeout=60000) as download_info:
        frame.locator(sel["report_ok"]).last.click(timeout=10000)
    download_info.value.save_as(path)
    result.report_pdf = path


# ---------------------------------------------------------------------------
# Monitor
# ---------------------------------------------------------------------------
def _monitor_api(country, from_date, to_date, apagadas):
    """Conteo del Monitor vía API REST. Devuelve (total_diferencias, filas).

    El Monitor compara por tienda las fuentes POS/CRPOS (caja) contra
    CR400 / Legacy (AS400 Central) / Ventas. La diferencia es POS vs esas
    fuentes; se reporta la mayor discrepancia por tienda.
    """
    import requests

    base = config.MONITOR_API_URL
    cc = country.lower()
    session = requests.Session()
    login = session.post(
        f"{base}/v1/auth/login",
        json={"username": config.MONITOR_API_USER, "password": config.MONITOR_API_PASS},
        timeout=20,
    )
    login.raise_for_status()
    token = login.json().get("token")
    headers = {"Authorization": token}  # el frontend envía el token crudo (sin "Bearer")
    params = {"startDate": from_date, "endDate": to_date, "page": 1, "limit": 200}

    def counts(path):
        resp = session.get(f"{base}/v1/transactions/{path}/{cc}", params=params,
                           headers=headers, timeout=45)
        resp.raise_for_status()
        flat = []
        for item in resp.json().get("results", []):
            flat += item if isinstance(item, list) else [item]
        return {str(x.get("store")): _to_int(x.get("count")) for x in flat if x.get("store")}

    # Fuentes del Monitor. En SV la caja es CRPOS (db2); en VE/GT es Stellar.
    if country == "SV":
        pos_ep = "transaction-crpos-front-count"
    else:
        pos_ep = "transaction-stellar-front-count"
    pos = counts(pos_ep)
    cr400 = counts("transaction-cr400-front-count")
    legacy = counts("transaction-AS400-central-count")
    ventas = counts("transaction-ventas-front-count")
    pos_central = counts("transaction-stellar-central-count")

    apagadas = set(apagadas or [])
    stores = set(pos) | set(legacy) | set(ventas)
    rows, total = [], 0
    for store in sorted(stores, key=lambda s: int(s) if s.isdigit() else s):
        if store in apagadas:
            continue
        # Compara la caja (POS) contra las fuentes de destino.
        fuentes = [legacy.get(store, 0), ventas.get(store, 0)]
        if country == "SV":
            fuentes.append(cr400.get(store, 0))
        base = pos.get(store, 0)
        diff = max(abs(base - f) for f in fuentes)
        total += diff
        rows.append({
            "tienda": store, "diff": diff, "pos": base,
            "legacy": legacy.get(store, 0), "ventas": ventas.get(store, 0),
            "cr400": cr400.get(store, 0), "stellar_central": pos_central.get(store, 0),
        })
    return total, rows


def _monitor_pdf(page, country, result, out_dir, inspect):
    meta = config.COUNTRIES[country]
    sel = config.SELECTORS
    today = datetime.date.today()
    date_from = (today - datetime.timedelta(days=1)).strftime(config.MONITOR_DATE_FORMAT)
    date_to = today.strftime(config.MONITOR_DATE_FORMAT)

    page.goto(config.MONITOR_BASE_URL + meta["monitor_path"],
              wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(6000)

    dates = page.locator(sel["monitor_date_from"])
    if dates.count() >= 2:
        dates.nth(0).fill(date_from)
        dates.nth(1).fill(date_to)
    if page.locator(sel["monitor_refresh"]).count():
        page.locator(sel["monitor_refresh"]).first.click()
        page.wait_for_timeout(5000)

    if meta["has_store_pagination"]:
        _paginate_down(page, sel["monitor_down"])

    if inspect:
        _dump_inspect(page, f"monitor_{country}", out_dir)

    path = os.path.join(out_dir, f"Monitor {meta['name']}.pdf")
    page.pdf(path=path, print_background=True, scale=config.MONITOR_PDF_SCALE)
    result.monitor_pdf = path


def _paginate_down(page, down_selector, max_pages=12):
    """Pulsa la flecha hacia abajo esperando a que cambie el contenido (best-effort)."""
    for _ in range(max_pages):
        if not page.locator(down_selector).count():
            return
        before = page.content()
        try:
            page.locator(down_selector).last.click(timeout=8000)
        except Exception:  # noqa: BLE001
            return
        page.wait_for_timeout(2000)
        try:
            page.wait_for_function("prev => document.body.innerHTML !== prev",
                                   arg=before, timeout=8000)
        except Exception:  # noqa: BLE001
            return


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
def extract_all(days_back, out_dir, mock=False, inspect=False, apagadas=None, only=None):
    countries = list(config.COUNTRIES)
    if only:
        countries = [c for c in countries if c in only]
    results = {c: WebResult(c) for c in countries}

    if mock:
        _fill_mock(results, out_dir)
        return results

    from playwright.sync_api import sync_playwright

    today = datetime.date.today()
    # El Monitor cubre ayer y hoy (si no, faltan transacciones del día anterior).
    monitor_from = (today - datetime.timedelta(days=1)).isoformat()
    monitor_to = today.isoformat()

    with sync_playwright() as p:
        log.info("Iniciando navegador Playwright (Chromium headless)...")
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        try:
            for country, result in results.items():
                log.info("[%s] 1/3 Extrayendo Reporte Web (BIRT)...", country)
                try:
                    _extract_report(context, page, country, result, days_back, out_dir, inspect)
                    log.info("[%s] Reporte Web OK (total: %s, filas: %s)", country, result.report_total, len(result.report_rows))
                except Exception as exc:  # noqa: BLE001
                    result.error += f"Reporte Web: {str(exc)[:150]}"
                    log.warning("[%s] Reporte Web falló: %s", country, exc)

                log.info("[%s] 2/3 Consultando API del Monitor...", country)
                apagadas_pais = (apagadas or {}).get(country, [])
                try:
                    result.monitor_total, result.monitor_rows = _monitor_api(
                        country, monitor_from, monitor_to, apagadas_pais
                    )
                    log.info("[%s] API Monitor OK (diferencias: %s)", country, result.monitor_total)
                except Exception as exc:  # noqa: BLE001
                    result.error += f" | API Monitor: {str(exc)[:120]}"
                    log.warning("[%s] API Monitor falló: %s", country, exc)

                log.info("[%s] 3/3 Generando PDF del Monitor...", country)
                try:
                    _monitor_pdf(page, country, result, out_dir, inspect)
                    log.info("[%s] PDF Monitor OK", country)
                except Exception as exc:  # noqa: BLE001
                    result.error += f" | PDF Monitor: {str(exc)[:100]}"
                    log.warning("[%s] PDF Monitor falló: %s", country, exc)
        finally:
            browser.close()
    return results


def _fill_mock(results, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for country, result in results.items():
        meta = config.COUNTRIES[country]
        for label, attr in (("Reporte Web", "report_pdf"), ("Monitor", "monitor_pdf")):
            path = os.path.join(out_dir, f"{label} {meta['name']}.pdf")
            with open(path, "wb") as fh:
                fh.write(b"%PDF-1.4\n% mock\n")
            setattr(result, attr, path)
        result.report_total = 0
        result.monitor_total = 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        res = extract_all(5, tmp, mock=True)
        assert set(res) == {"VE", "SV", "GT"}
        assert all(r.report_pdf and r.monitor_pdf for r in res.values())
    print("web_extractor OK")
