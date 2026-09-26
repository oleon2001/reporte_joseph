"""
Reporte de transacciones atrapadas EPA (VE, SV y GT).

Uso:
    python main.py                 # corrida real (pide Gmail + confirmación S/N)
    python main.py --mock          # sin red: web y BD simuladas
    python main.py --dry-run       # genera todo pero NO envía
    python main.py --inspect       # vuelca HTML/capturas para calibrar selectores
    python main.py --only VE,GT    # procesa solo esos países
    python main.py --export out.json
    python main.py --only GT --merge server.json   # combina corridas local/servidor
"""
import argparse
import datetime
import getpass
import json
import logging
import os
import sys

import config
import db_validator
import entregables
import excel_builder
import mailer
import web_extractor

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("main")

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
         "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args():
    p = argparse.ArgumentParser(description="Reporte de transacciones atrapadas EPA")
    p.add_argument("--mock", action="store_true", help="web y BD simuladas (sin red)")
    p.add_argument("--dry-run", action="store_true", help="genera todo pero no envía")
    p.add_argument("--no-confirm", action="store_true", help="no pide confirmación S/N")
    p.add_argument("--inspect", action="store_true", help="volcar HTML/capturas de las webs")
    p.add_argument("--only", default="", help="países a procesar, ej: VE,GT")
    p.add_argument("--export", default="", help="guarda resultados en un JSON")
    p.add_argument("--merge", default="", help="combina resultados de otro JSON")
    p.add_argument("--days-back", type=int, default=config.REPORT_WEB_DAYS_BACK,
                   help="días hacia atrás para el Reporte Web / BD")
    p.add_argument("--test-recipient", default="",
                   help="envía solo a este correo (prueba), ej: oleon@intelix.biz")
    return p.parse_args()


def load_apagadas():
    if not os.path.exists(config.APAGADAS_FILE):
        return {c: [] for c in config.COUNTRIES}
    with open(config.APAGADAS_FILE, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return {c: data.get(c, []) for c in config.COUNTRIES}


def get_credentials(dry_run):
    user = config.GMAIL_USER
    password = config.GMAIL_APP_PASSWORD
    if dry_run:
        return user, password
    if not user:
        user = input("Correo de Gmail: ").strip()
    if not password:
        password = getpass.getpass("Contraseña de aplicación de Google: ")
    return user, password


# ---------------------------------------------------------------------------
# Métricas
# ---------------------------------------------------------------------------
def _db_count(db_results, country, name_contains):
    total = 0
    for source in db_results.get(country, []):
        if name_contains.lower() in source.name.lower():
            total += source.count
    return total


def metrics_for(country, web, db_results):
    w = web.get(country)
    report_total = w.report_total if w else 0
    monitor_total = w.monitor_total if w else 0
    data = {"report": report_total, "monitor": monitor_total}
    if country == "GT":
        data["legacy_stellar"] = (
            _db_count(db_results, "GT", "Cabtra") + _db_count(db_results, "GT", "VAD20")
        )
        data["pendientes"] = _db_count(db_results, "GT", "Pendientes por imprimir")
    return data


def build_subject(today):
    return f"Reporte de transacciones atrapadas EPA {today.strftime('%d-%m-%Y')}"


def build_body(today, metrics, apagadas, errors):
    fecha = f"{today.day} de {MESES[today.month - 1]} de {today.year}"
    ve, sv, gt = metrics["VE"], metrics["SV"], metrics["GT"]
    lines = [
        "Buenos días, adjunto los reportes de transacciones atrapadas y diferencias de las "
        f"tiendas de Ferretería EPA hasta el día {fecha}, los reportes presentan:",
        "",
        f"VE: {ve['report']} en el Reporte Web y {ve['monitor']} en el Monitor.",
        f"SV: {sv['report']} en el Reporte Web y {sv['monitor']} en el Monitor.",
        f"GT: {gt['report']} en el Reporte Web, {gt['monitor']} en el Monitor, "
        f"{gt['legacy_stellar']} diferencias entre Legacy y Stellar y "
        f"{gt['pendientes']} pendientes por imprimir.",
        "",
        "Observaciones:",
        "• Detalles adjuntos en la hoja de cálculo.",
        "• Algunas de las diferencias detectadas en SV por parte del Monitor es debido a que "
        "aún no han encendido todas las cajas, por ende, si se detectó diferencias en el "
        "Reporte Web, es probable que provenga de las mismas.",
    ]
    for country, meta in config.COUNTRIES.items():
        apagadas_pais = apagadas.get(country) or []
        if apagadas_pais:
            lines.append(
                f"• En {country}, las tiendas {', '.join(apagadas_pais)} están apagadas; "
                "por eso no se reflejan datos de Stellar en el Monitor."
            )
    lines += ["", "Saludos cordiales."]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Serialización (para --export / --merge)
# ---------------------------------------------------------------------------
def export_results(path, web, db_results, attachments):
    data = {
        "date": datetime.date.today().isoformat(),
        "web": {c: vars(w) for c, w in web.items()},
        "db": {c: [{"name": s.name, "ok": s.ok, "error": s.error, "rows": s.rows}
                   for s in sources] for c, sources in db_results.items()},
        "attachments": attachments,
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    log.info("Resultados exportados a %s", path)


def merge_results(path, web, db_results, attachments):
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    for country, wdata in data.get("web", {}).items():
        if country not in web:
            web[country] = web_extractor.WebResult(country)
            for key, value in wdata.items():
                setattr(web[country], key, value)
    for country, sources in data.get("db", {}).items():
        if country not in db_results:
            db_results[country] = []
            for s in sources:
                src = db_validator.SourceResult(s["name"], country)
                src.ok = s.get("ok", True)
                src.error = s.get("error", "")
                src.rows = s.get("rows", [])
                db_results[country].append(src)
    for path_ in data.get("attachments", []):
        if path_ not in attachments:
            attachments.append(path_)
    log.info("Resultados combinados desde %s", path)


# ---------------------------------------------------------------------------
# Flujo principal
# ---------------------------------------------------------------------------
def collect_attachments(web, excel_path):
    files = []
    for country in config.COUNTRIES:
        w = web.get(country)
        if w and w.report_pdf:
            files.append(w.report_pdf)
    for country in config.COUNTRIES:
        w = web.get(country)
        if w and w.monitor_pdf:
            files.append(w.monitor_pdf)
    files.append(excel_path)
    return files


def main():
    args = parse_args()
    today = datetime.date.today()
    date_str = today.strftime("%d-%m-%Y")
    out_dir = os.path.join(config.OUTPUT_DIR, date_str)
    os.makedirs(out_dir, exist_ok=True)
    only = [c.strip().upper() for c in args.only.split(",") if c.strip()] or None
    apagadas = load_apagadas()

    # 1) Extracción web
    log.info("Extrayendo reportes web%s...", " (mock)" if args.mock else "")
    web = web_extractor.extract_all(
        args.days_back, out_dir, mock=args.mock, inspect=args.inspect,
        apagadas=apagadas, only=only,
    )

    # 2) Validación en BD
    log.info("Validando BD%s...", " (mock)" if args.mock else "")
    sv_web = web["SV"].report_rows if web.get("SV") else []
    db_results = db_validator.validate_all(args.days_back, mock=args.mock, sv_web_rows=sv_web)

    attachments = []
    if args.merge:
        merge_results(args.merge, web, db_results, attachments)

    # 3) Hoja de cálculo (con todos los países combinados)
    rows_by_country = db_validator.flatten_rows(db_results)
    for country in config.COUNTRIES:
        rows_by_country.setdefault(country, [])
    excel_path = excel_builder.build_workbook(rows_by_country, out_dir, date_str)

    # 4) Métricas + cuerpo
    metrics = {c: metrics_for(c, web, db_results) for c in config.COUNTRIES}
    errors = [f"[{c}] {w.error}" for c, w in web.items() if w.error]
    for c, sources in db_results.items():
        for s in sources:
            if not s.ok:
                errors.append(f"[{c}] {s.name} no disponible")
    subject = build_subject(today)
    body = build_body(today, metrics, apagadas, errors)

    files = collect_attachments(web, excel_path)
    files = list(dict.fromkeys(attachments + files))  # sin duplicados, orden estable

    # 5) Resumen y confirmación
    print("\n" + "=" * 70)
    print(f"ASUNTO: {subject}")
    print("=" * 70)
    print(body)
    print("=" * 70)
    print(f"ADJUNTOS ({len(files)}):")
    for f in files:
        print(f"  - {f}")
    if errors:
        print("AVISOS:")
        for e in errors:
            print(f"  ! {e}")
    print("=" * 70)

    # Entregables por versión (documentos + mensaje + destinatarios)
    version = entregables.next_version()
    dest = args.test_recipient or config.RECIPIENTS
    root = entregables.build_deliverable(
        version, date_str, web, db_results, metrics, subject, body, dest, files, errors,
        mock=args.mock,
    )
    print(f"ENTREGABLE: {root}")

    if args.export:
        export_results(args.export, web, db_results, files)

    if args.dry_run:
        log.info("DRY-RUN: no se envía el correo.")
        return 0

    if not args.no_confirm:
        answer = input("¿Enviar el correo? (S/N): ").strip().upper()
        if answer != "S":
            log.info("Envío cancelado por el usuario.")
            return 0

    recipients = [args.test_recipient] if args.test_recipient else None
    if recipients:
        subject = f"[PRUEBA] {subject}"
        log.info("MODO PRUEBA: se envía solo a %s", args.test_recipient)

    user, password = get_credentials(dry_run=False)
    if not user or not password:
        log.error("Faltan credenciales de Gmail (correo o contraseña de aplicación).")
        return 2
    try:
        mailer.send_email(user, password, subject, body, files, recipients=recipients)
    except mailer.MailError as exc:
        log.error("No se pudo enviar el correo: %s", exc)
        return 1
    log.info("Listo. Correo enviado correctamente.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
