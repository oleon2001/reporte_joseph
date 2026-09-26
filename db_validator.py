"""
Validación en BD de las transacciones atrapadas.

Fuentes (cada una se intenta de forma aislada; si no hay red o credenciales
se marca como no disponible sin romper el flujo):

  - AS400 / DB2 (Central VE/SV)      -> jaydebeapi + jt400.jar
  - SQL Server (Stellar tienda/central) -> pyodbc

Devuelve, por país, una lista de "discrepancias" normalizadas listas para la
hoja de cálculo: Tienda, POS/Caja, TR EPA, StellarDocID, Origen, Observaciones.
"""
import datetime
import logging
import os

import config

log = logging.getLogger(__name__)


class SourceResult:
    """Resultado de una fuente de datos (una conexión/consulta)."""

    def __init__(self, name, country):
        self.name = name
        self.country = country
        self.rows = []
        self.ok = False
        self.error = ""
        self.note = ""

    @property
    def count(self):
        return len(self.rows)

    def __repr__(self):
        state = "OK" if self.ok else "N/D"
        return f"<{self.country}:{self.name} {state} rows={self.count}>"


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def date_range(days_back):
    today = datetime.date.today()
    return (today - datetime.timedelta(days=days_back)).isoformat(), today.isoformat()


def read_sql(filename):
    """Lee un archivo SQL. Devuelve None si no existe, es solo comentarios o es STUB."""
    path = os.path.join(config.SQL_DIR, filename)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        sql = fh.read().strip().rstrip(";").strip()
    lines = [l.strip() for l in sql.splitlines() if l.strip()]
    if not lines or all(l.startswith("--") for l in lines):
        return None
    if lines[0].startswith("-- STUB"):
        return None  # marcada como no configurada: no debe alimentar el reporte
    return sql


def _named_to_qmark(sql, names):
    """Convierte parámetros nombrados (ej. :Fi, :Ff) a marcadores posicionales."""
    for name in names:
        sql = sql.replace(name, "?")
    return sql


def _fetch(conn, sql, params=None):
    """Ejecuta una consulta y devuelve lista de dicts."""
    cur = conn.cursor()
    try:
        if params:
            cur.execute(sql, params)
        else:
            cur.execute(sql)
        cols = [d[0] for d in cur.description] if cur.description else []
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        cur.close()


def _pick(row, *keys):
    for key in keys:
        for row_key in row:
            if row_key.lower() == key.lower() and row[row_key] is not None:
                return row[row_key]
    return ""


def _clean_obs(text):
    """Colapsa saltos/espacios del diagnóstico en una sola línea."""
    import re

    return re.sub(r"\s+", " ", str(text or "")).strip()


def normalize(row, origen, obs=""):
    """Normaliza una fila cruda a las columnas de la hoja de cálculo."""
    observacion = obs or _clean_obs(_pick(row, "Observaciones", "Motivo", "c_MotivoContingencia"))
    if not observacion:
        # Cabtra: si no hay diagnóstico de error, se usa el contexto disponible.
        partes = [
            _clean_obs(_pick(row, "ORIGEN_DEVOLUCION")),
            _clean_obs(_pick(row, "Marca_Integracion")),
        ]
        observacion = " | ".join(p for p in partes if p and p not in (" ", "Pendiente"))
    return {
        "Tienda": _pick(row, "Tienda", "STORE", "TDACMV", "c_Sucursal", "NUMTIENDA"),
        "POS/Caja": _pick(row, "Caja", "POS/Caja", "CAJCMV", "c_Caja", "CAJA", "NUMCAJA"),
        "TR EPA": _pick(row, "TR_EPA", "TR EPA", "TRSCMV", "c_Numero", "DOCUMENTUID"),
        "StellarDocID": _pick(row, "StellarDocID", "DocumentUID", "DOCUMENTUID"),
        "Origen": origen,
        "Observaciones": observacion,
    }


# ---------------------------------------------------------------------------
# Conexiones
# ---------------------------------------------------------------------------
def connect_mssql(cfg, database="master"):
    import pyodbc

    cs = (
        f"DRIVER={config.SQL_SERVER_DRIVER};SERVER={cfg['host']},1433;"
        f"DATABASE={database};UID={cfg['user']};PWD={cfg['pass']};"
        "TrustServerCertificate=yes;Connection Timeout=15;"
    )
    return pyodbc.connect(cs, timeout=15)


def connect_db2(cfg):
    import jaydebeapi

    if not config.JT400_JAR:
        raise RuntimeError("jt400.jar no encontrado (define JT400_JAR o colócalo en ./jt400.jar)")
    url = (
        f"jdbc:as400://{cfg['host']};login timeout=10;"
        "socket timeout=20000;thread used=false;"
    )
    return jaydebeapi.connect(
        "com.ibm.as400.access.AS400JDBCDriver", url, [cfg["user"], cfg["pass"]], config.JT400_JAR
    )


# ---------------------------------------------------------------------------
# Ejecución aislada de cada fuente
# ---------------------------------------------------------------------------
def _run(name, country, fn):
    result = SourceResult(name, country)
    try:
        rows = fn()
        result.rows = rows or []
        result.ok = True
    except Exception as exc:  # noqa: BLE001 - queremos aislar cualquier fallo de fuente
        result.error = str(exc)[:200]
        log.warning("Fuente '%s' (%s) no disponible: %s", name, country, result.error)
    return result


def _central_stellar_query(cfg, sql_file, days_back, origen, database="VENTASSTORE"):
    sql = read_sql(sql_file)
    if not sql:
        raise RuntimeError(f"SQL no configurado: {sql_file}")
    sql = _named_to_qmark(sql, [":Fi", ":Ff"])
    from_date, to_date = date_range(days_back)
    conn = connect_mssql(cfg, database=database)
    try:
        rows = _fetch(conn, sql, [from_date, to_date])
    finally:
        conn.close()
    return [normalize(r, origen) for r in rows]


def _ma_pagos_stores(stores, days_back, origen):
    """Pendientes por imprimir desde el Stellar de cada tienda."""
    sql = read_sql("MA_PAGOS_pendientes.sql")
    if not sql:
        raise RuntimeError("SQL no configurado: MA_PAGOS_pendientes.sql")
    store_cfg = {"host": None, "user": config.STELLAR_STORE_USER, "pass": config.STELLAR_STORE_PASS}
    collected, errors, ok_stores = [], [], 0
    for store_id, host in stores.items():
        store_cfg["host"] = host
        try:
            conn = connect_mssql(store_cfg, database="master")
            try:
                rows = _fetch(conn, sql)
            finally:
                conn.close()
            ok_stores += 1
            for r in rows:
                row = normalize(r, f"{origen} tienda {store_id}")
                if not row["Tienda"]:
                    row["Tienda"] = store_id
                collected.append(row)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"t{store_id}:{str(exc)[:60]}")
    # Solo se considera fuente no disponible si NINGUNA tienda respondió.
    if ok_stores == 0 and errors:
        raise RuntimeError("; ".join(errors[:3]))
    if errors:
        log.warning("MA_PAGOS: tiendas sin respuesta: %s", "; ".join(errors))
    return collected


def _as400_anomalies(cfg, days_back):
    """Ejecuta las 5 anomalías AS400 (GT) y normaliza cada una."""
    days = days_back or 5
    files = [
        ("as400_anomalias_1.sql", "AS400: no llegó cliente a MAECEC"),
        ("as400_anomalias_2.sql", "AS400: no llegó a OPVTSC"),
        ("as400_anomalias_3.sql", "AS400: no llegó cliente a CR400"),
        ("as400_anomalias_4.sql", "AS400: estatus en blanco"),
        ("as400_anomalias_5.sql", "AS400: devolución sin detalle"),
    ]
    conn = connect_db2(cfg)
    collected, errors = [], []
    try:
        for filename, origen in files:
            sql = read_sql(filename)
            if not sql:
                continue
            try:
                rows = _fetch(conn, sql, [days])
                collected += [normalize(r, origen) for r in rows]
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{filename}:{str(exc)[:60]}")
    finally:
        conn.close()
    if not collected and errors:
        raise RuntimeError("; ".join(errors[:3]))
    return collected


# ---------------------------------------------------------------------------
# Validación por país
# ---------------------------------------------------------------------------
def validate_ve(days_back):
    return [
        _run("Reporte/Cabtra VE", "VE",
             lambda: _central_stellar_query(config.CENTRAL_STELLAR_VE, "Cabtra VE.sql",
                                            days_back, "Cabtra VE")),
        _run("Falta en VENTASSTORE/VAD20", "VE",
             lambda: _central_stellar_query(config.CENTRAL_STELLAR_VE, "VentaStore-VAD20.sql",
                                            days_back, "VentaStore/VAD20")),
    ]


def _sv_itr(days_back):
    """ITR de SV (AS400 Central SV): transacciones atrapadas vía CR400."""
    sql = read_sql("itr.sql")
    if not sql:
        raise RuntimeError("SQL no configurado: itr.sql")
    from_date, to_date = date_range(days_back)
    # DB2 exige DATE(...) en el BETWEEN date(A.FECHA); se usan literales.
    sql = sql.replace(":FechaInicial", f"DATE('{from_date}')")
    sql = sql.replace(":FechaFinal", f"DATE('{to_date}')")
    conn = connect_db2(config.AS400_SV_CENTRAL)
    try:
        rows = _fetch(conn, sql)
    finally:
        conn.close()
    return [_sv_normalize(r) for r in rows]


def _sv_normalize(row):
    """Parsea "TIENDA: 003 CAJA: 26 TR: 964762" a las columnas de la hoja."""
    import re

    datos = str(_pick(row, "DATOS_DE_LA_TRANSACCION"))
    tienda = caja = tr = ""
    m = re.search(r"TIENDA:\s*(\S+)", datos)
    if m:
        tienda = m.group(1)
    m = re.search(r"CAJA:\s*(\S+)", datos)
    if m:
        caja = m.group(1)
    m = re.search(r"TR:\s*(\S+)", datos)
    if m:
        tr = m.group(1)
    obs = " | ".join(
        s for s in (
            _clean_obs(_pick(row, "ANALISTA_MOV_TR")),
            _clean_obs(_pick(row, "PIN_EMERGENCIA_TR")),
        ) if s
    )
    return {
        "Tienda": tienda,
        "POS/Caja": caja,
        "TR EPA": tr,
        "StellarDocID": _pick(row, "ID_TRANSACCION"),
        "Origen": "ITR SV",
        "Observaciones": obs,
    }


def validate_sv(days_back):
    return [
        _run("ITR SV", "SV", lambda: _sv_itr(days_back)),
    ]


def validate_gt(days_back):
    return [
        _run("Reporte/Cabtra GT", "GT",
             lambda: _central_stellar_query(config.CENTRAL_STELLAR_GT, "Cabtra GT.sql",
                                            days_back, "Cabtra GT")),
        _run("Falta en VENTASSTORE/VAD20", "GT",
             lambda: _central_stellar_query(config.CENTRAL_STELLAR_GT, "VentaStore-VAD20.sql",
                                            days_back, "VentaStore/VAD20")),
        _run("Pendientes por imprimir (Stellar)", "GT",
             lambda: _ma_pagos_stores(config.COUNTRIES["GT"]["stellar_stores"], days_back,
                                      "MA_PAGOS pendiente")),
        _run("Anomalías AS400", "GT",
             lambda: _as400_anomalies(config.AS400_VE_CENTRAL, days_back)),
    ]


def validate_all(days_back, mock=False):
    """Devuelve {pais: [SourceResult, ...]}."""
    if mock:
        return _mock_results()
    results = {"VE": validate_ve(days_back), "SV": validate_sv(days_back), "GT": validate_gt(days_back)}
    return results


# ---------------------------------------------------------------------------
# Mock (para tests locales end-to-end sin red)
# ---------------------------------------------------------------------------
def _mock_results():
    def src(name, country, rows):
        r = SourceResult(name, country)
        r.ok = True
        r.rows = rows
        return r

    return {
        "VE": [
            src("Reporte/Cabtra VE", "VE", []),
            src("Falta en VENTASSTORE/VAD20", "VE", []),
        ],
        "SV": [
            src("Validación SV", "SV", [
                normalize({"Tienda": "3", "Caja": "21", "TR_EPA": "045812"}, "SV"),
            ]),
        ],
        "GT": [
            src("Reporte/Cabtra GT", "GT", []),
            src("Falta en VENTASSTORE/VAD20", "GT", []),
            src("Pendientes por imprimir (Stellar)", "GT", [
                normalize({"Tienda": "5", "Caja": "12", "TR_EPA": "009912",
                           "Motivo": "Pendiente de imprimir"}, "MA_PAGOS pendiente"),
            ]),
            src("Anomalías AS400", "GT", [
                normalize({"Tienda": "4", "Caja": "8", "TR_EPA": "001234"},
                          "AS400: estatus en blanco"),
            ]),
        ],
    }


def flatten_rows(results):
    """Aplana {pais: [SourceResult]} a {pais: [filas]}, sin duplicar."""
    flat = {}
    for country, sources in results.items():
        rows = []
        for source in sources:
            rows += source.rows
        flat[country] = rows
    return flat


def source_counts(results):
    """Conteo por país y por nombre de fuente (para el cuerpo del correo)."""
    counts = {}
    for country, sources in results.items():
        counts[country] = {s.name: s.count for s in sources}
    return counts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    res = validate_all(days_back=5, mock=True)
    for country, sources in res.items():
        for s in sources:
            print(s)
    assert res["GT"][2].count == 1
    print("db_validator OK")
