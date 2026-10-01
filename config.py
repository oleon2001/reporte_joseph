"""
Configuración central del reporte de transacciones atrapadas EPA (VE, SV, GT).

Los valores sensibles se pueden sobreescribir con variables de entorno (.env).
Los valores por defecto provienen de reporteDeVentas/config.py y de la
documentación operativa del reporte.
"""
import os
import platform

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))


def _env(name, default=None):
    return os.getenv(name, default)


# =========================================================================
# GENERAL
# =========================================================================
TIMEZONE = _env("TIMEZONE", "America/Caracas")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQL_DIR = os.path.join(BASE_DIR, "sql")
OUTPUT_DIR = os.path.join(BASE_DIR, "salidas")
APAGADAS_FILE = os.path.join(BASE_DIR, "tiendas_apagadas.json")

# Rangos de fecha (días)
REPORT_WEB_DAYS_BACK = 5  # Reporte Web: últimos 5 días hasta hoy
MONITOR_ONLY_TODAY = True  # Monitor: solo el día actual


# =========================================================================
# DESTINATARIOS (lista fija)
# =========================================================================
RECIPIENTS = [
    "Leon Cuello <lcuello@intelix.biz>",
    "Maribel Sanchez <isanchez@intelix.biz>",
    "Marling Gonzalez <mgonzalez@intelix.biz>",
    "Omar Castillo <ocastillo@intelix.biz>",
    "Gusvia Gómez <ggomez@intelix.biz>",
    "Romel Flores <raflores@intelix.biz>",
    "EPA - Soporte Caja Registradora <epa-cajaregistradora@intelix.biz>",
    "Maria Duarte <mduarte@intelix.biz>",
    "Rashel Álvarez <ralvarez@intelix.biz>",
    "Eliana Alarcón <continuidad@epa.biz>",
    "continuidad1@epa.biz",
    "Katherine Torrealba <continuidad2@epa.biz>",
    "Gabriel Pinto <continuidad3@epa.biz>",
    "Rafael Hernandez <continuidad4@epa.biz>",
    "Shirley Parra <procesos6@epa.biz>",
]


# =========================================================================
# WEBS
# =========================================================================
REPORT_WEB_URL = _env(
    "REPORT_WEB_URL",
    "http://10.48.12.89:28083/ReportesWeb/frameset?"
    "__report=reportes/sistemas/VentasAtrapadas/TransaccionesFaltantes.rptdesign",
)
MONITOR_BASE_URL = _env("MONITOR_BASE_URL", "http://10.48.12.77:3500")

# API REST del Monitor (el frontend React la consume en el puerto 3010).
MONITOR_API_URL = _env("MONITOR_API_URL", "http://10.48.12.77:3010")
MONITOR_API_USER = _env("MONITOR_API_USER", "EpaSupport2023")
MONITOR_API_PASS = _env("MONITOR_API_PASS", "vJ69@GP8PSlapqh@JCXDbz!U8iE5VV%@o5")

# Valor del <select id="DNS_selection"> del Reporte Web por país.
REPORT_SERVER_VALUES = {"VE": "EPA", "SV": "EPASV", "GT": "EPAGT"}

# Selectores del Reporte Web (BIRT) y del Monitor (calibrados contra el sitio).
SELECTORS = {
    # Reporte Web
    "report_server": "#DNS_selection",
    "report_date_from": "[id='Fecha Inicio']",
    "report_date_to": "[id='Fecha Final']",
    "report_ok": "input[value='OK']:visible",
    "report_export": "input[name='exportReport']",
    "report_export_format": "#exportFormat",
    "report_metric_re": r"Total Trx no actualizadas[^0-9]*([\d.,]+)",
    # Monitor (UI para el PDF)
    "monitor_date_from": "input[placeholder='DD/MM/YYYY']",
    "monitor_date_to": "input[placeholder='DD/MM/YYYY']",
    "monitor_refresh": "button:has-text('Actualizar')",
    "monitor_down": "button.MuiFab-root",
}

MONITOR_PDF_SCALE = 0.6  # escala solicitada (60%)
REPORT_DATE_FORMAT = "%Y-%m-%d"  # el reporte BIRT usa yyyy-mm-dd
MONITOR_DATE_FORMAT = "%d/%m/%Y"  # la UI del Monitor usa DD/MM/YYYY


# =========================================================================
# PAÍSES
# =========================================================================
COUNTRIES = {
    "VE": {
        "name": "Venezuela",
        "sheet": "Venezuela",
        "report_server": "EPA Central Venezuela",
        "monitor_path": "/ve",
        # Tiendas Stellar VE: t2..t17
        "stellar_stores": {str(i): f"stellardb.t{i}.ve.epa.com" for i in range(2, 18)},
        "has_store_pagination": True,  # VE y GT paginan de 4 en 4
    },
    "SV": {
        "name": "El Salvador",
        "sheet": "Salvador",
        "report_server": "EPASV El Salvador",
        "monitor_path": "/sv",
        "stellar_stores": {str(i): f"stellardb.t{i}.sv.epa.com" for i in range(1, 5)},
        "has_store_pagination": False,
    },
    "GT": {
        "name": "Guatemala",
        "sheet": "Guatemala",
        "report_server": "EPAGT Guatemala",
        "monitor_path": "/gt",
        "stellar_stores": {str(i): f"stellardb.t{i}.gt.epa.com" for i in range(2, 7)},
        "has_store_pagination": True,
    },
}


# =========================================================================
# DRIVERS
# =========================================================================
if platform.system() == "Windows":
    SQL_SERVER_DRIVER = _env("SQL_SERVER_DRIVER", "{SQL Server}")
else:
    SQL_SERVER_DRIVER = _env("SQL_SERVER_DRIVER", "{ODBC Driver 17 for SQL Server}")


def _find_jt400():
    """Localiza el jar de JDBC de AS400 (local o dentro de Docker)."""
    candidates = [
        _env("JT400_JAR"),
        os.path.join(BASE_DIR, "jt400.jar"),
        os.path.join(os.path.dirname(BASE_DIR), "reporteDeVentas", "jt400.jar"),
        "/app/jt400.jar",
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None


JT400_JAR = _find_jt400()


# =========================================================================
# SQL SERVER (Stellar)
# =========================================================================
STELLAR_STORE_USER = _env("STELLAR_STORE_USER", "oZkbrCFK")
STELLAR_STORE_PASS = _env("STELLAR_STORE_PASS", "+8Rd4G*FZ0")

CENTRAL_STELLAR_VE = {
    "host": _env("CENTRAL_STELLAR_VE_HOST", "10.57.113.191"),
    "user": _env("CENTRAL_STELLAR_VE_USER", "INT0000545"),
    "pass": _env("CENTRAL_STELLAR_VE_PASS", "2aJG6rSYOpTlX7ny"),
}

CENTRAL_STELLAR_GT = {
    "host": _env(
        "CENTRAL_STELLAR_GT_HOST",
        "epagt-prod-stellar-rdssqlser-dbinstancesqlserver01-ym7id5i9opmc."
        "cknssci6uzuz.us-east-1.rds.amazonaws.com",
    ),
    "user": _env("CENTRAL_STELLAR_GT_USER", "INT0000545"),
    "pass": _env("CENTRAL_STELLAR_GT_PASS", "Vgwv2gRyDxIh617hzHyT"),
}


# =========================================================================
# AS400 / DB2 (Central Legacy)
# =========================================================================
AS400_VE_CENTRAL = {
    "host": _env("AS400_VE_CENTRAL_HOST", "192.168.118.91"),
    "user": _env("AS400_VE_CENTRAL_USER", "userdb2"),
    "pass": _env("AS400_VE_CENTRAL_PASS", "userdb2"),
}

AS400_SV_CENTRAL = {
    "host": _env("AS400_SV_CENTRAL_HOST", "10.48.11.22"),
    "user": _env("AS400_SV_CENTRAL_USER", "userdb2"),
    "pass": _env("AS400_SV_CENTRAL_PASS", "userdb2"),
}


# =========================================================================
# GMAIL (se pueden pasar por CLI o por .env cuando no hay TTY)
# =========================================================================
GMAIL_USER = _env("GMAIL_USER")
GMAIL_APP_PASSWORD = _env("GMAIL_APP_PASSWORD")
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465


# =========================================================================
# HOJA DE CÁLCULO
# =========================================================================
EXCEL_COLUMNS = ["Tienda", "POS/Caja", "TR EPA", "StellarDocID", "Origen", "Observaciones"]

# Orden de pestañas en la hoja de cálculo
SHEET_ORDER = ["GT", "SV", "VE"]

# Listas desplegables de Observaciones (idénticas al Excel real del equipo).
OBSERVACIONES_GT = [
    "Falta de Donación por falta de Detalle Donación en el momento de su envío.",
    "Artículos con descuentos repetidos en el detalle.",
    "Falta en VENTASSTORE pero si se encuentra en VAD20.",
    "Sin observaciones.",
    "El campo CUSTOMERID posee un valor no permitido.",
    "Existen códigos artículos que no tienen los 7 dígitos que les corresponden.",
    "Existen artículos que tienen codigo o porcentaje de descuento pero no guardaron rebaja.",
]
OBSERVACIONES_SV = [
    "Venta con diferencias en montos.",
    "Anulación no sube ya que su venta asociada no tiene campos asignados en caja.",
    "Se desconoce el motivo ya que la caja no está encendida.",
    "Devolución con diferencias en montos.",
    "Venta no tiene campos asignados en caja.",
    "Venta en estado I.",
    "Devolución en estado I.",
    "Anulación en estado I.",
]
OBSERVACIONES_VE = [
    "Falta de Donación por falta de Detalle Donación en el momento de su envío.",
    "Artículos con descuentos repetidos en el detalle.",
    "Falta en VENTASSTORE pero si se encuentra en VAD20.",
    "Sin observaciones.",
    "El campo CASHIER posee un valor no permitido.",
    "El campo CUSTOMERID posee un valor no permitido.",
    "Error Descuento Detalle - Existen artículos que tienen código o porcentaje de descuento pero no guardaron rebaja.",
    "Error Cálculo Detalle - Total Artículo Incorrecto.",
    "Error Cálculo Cabecera Detalle - Rebaja Incorrecta.",
    "Error Relación Venta/Nota de Crédito.",
]

# Columnas de la hoja (celda donde vive el desplegable por país)
DROPDOWN = {
    "GT": {"col": 1, "start_row": 2},   # B2
    "SV": {"col": 3, "start_row": 2},   # D2
    "VE": {"col": 1, "start_row": 2},   # B2
}
OBSERVACIONES = {"GT": OBSERVACIONES_GT, "SV": OBSERVACIONES_SV, "VE": OBSERVACIONES_VE}
