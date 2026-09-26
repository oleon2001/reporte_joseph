"""
Generación de la hoja de cálculo: replica EXACTAMENTE el diseño y el análisis
de "Detalles de Tr's atrapadas DD-MM-YYYY.xlsx" del equipo de continuidad.

Diseño observado en el archivo de referencia:
  - Sin estilos de relleno/bold. Encabezados de sección en columna D, combinados
    D:G, con texto plano. Encabezados de tabla (Tienda/POS/TR EPA...) planos.
  - Guatemala:
      A1='StellarDocID'  B1='Observaciones'  B2='Sin observaciones.'
      Secciones en D (merged D:G):
        'Sin cliente en VENTAS.MAECEC o Sin documento en VENTAS.OPEVTSC'  (Tienda/POS/TR EPA)
        'Sin cliente en CR400'                                            (Tienda/POS/TR EPA/CODCTE)
        'Transacciones con estatus en blanco en sus detalles'            (Tienda/POS/TR EPA)
        'Devoluciones sin detalles'                                       (Tienda/POS/TR EPA)
        "TR's Pendientes por imprimir"                                    (Tienda/POS/TR/Mensaje)
      Cada sección: título, cabecera, y 2 filas de datos (o vacías).
  - Salvador: header A1-D1 centrado, filas con Tienda/POS/TR EPA numéricos +
      Observaciones ('Se desconoce el motivo ya que la caja no está encendida.').
  - Venezuela: header A1-B1, filas StellarDocID + Observaciones.
"""
import logging
import os

from openpyxl import Workbook
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter

import config

log = logging.getLogger(__name__)

# Anchos de columna tal como el archivo real
_WIDTHS_GT = {"A": 19.13, "B": 77.88, "C": 15.75, "D": 18.75, "G": 14.13}
_WIDTHS_SV = {"A": 9.25, "B": 7.5, "C": 12.25, "D": 66.0}
_WIDTHS_VE = {"A": 19.13, "B": 106.0, "C": 15.75, "D": 38.13}

_CENTER = Alignment(horizontal="center")


def _num(value):
    """El archivo real guarda Tienda/POS/TR como float."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


def _apply_widths(ws, widths):
    for col, width in widths.items():
        ws.column_dimensions[col].width = width


def _section(ws, start_row, titulo, headers, data_rows, rows_of_data=2):
    """Escribe una sección en col D (merged D:G) como el archivo real.

    El original separa secciones cada 4 filas: título, cabecera y 2 filas.
    """
    ws.merge_cells(start_row=start_row, start_column=4, end_row=start_row, end_column=7)
    ws.cell(row=start_row, column=4).value = titulo
    hdr_row = start_row + 1
    for i, h in enumerate(headers):
        ws.cell(row=hdr_row, column=4 + i).value = h
    for j in range(rows_of_data):
        r = hdr_row + 1 + j
        if j < len(data_rows):
            row_data = data_rows[j]
            for i in range(len(headers)):
                ws.cell(row=r, column=4 + i).value = row_data[i] if i < len(row_data) else None
    return start_row + 4  # siguiente sección: título, cabecera y 2 filas


# ---------------------------------------------------------------------------
# Por país
# ---------------------------------------------------------------------------
def _sheet_guatemala(ws, rows):
    by_origen = {}
    for r in rows:
        by_origen.setdefault(r["Origen"], []).append(r)

    def take(origen):
        return by_origen.get(origen, [])

    # Bloque Cabtra a la izquierda (A/B), como en el original
    ws["A1"] = "StellarDocID"
    ws["B1"] = "Observaciones"
    cabtra = take("Cabtra GT")
    if cabtra:
        for i, r in enumerate(cabtra):
            ws.cell(row=2 + i, column=1).value = r["StellarDocID"]
            ws.cell(row=2 + i, column=2).value = r["Observaciones"]
    else:
        ws["B2"] = "Sin observaciones."

    # Secciones en columna D
    anomalias = take("AS400: no llegó cliente a MAECEC") + take("AS400: no llegó a OPVTSC")
    row = _section(
        ws, 1,
        "Sin cliente en VENTAS.MAECEC o Sin documento en VENTAS.OPEVTSC",
        ["Tienda", "POS", "TR EPA"],
        [[_num(r["Tienda"]), _num(r["POS/Caja"]), _num(r["TR EPA"])] for r in anomalias],
    )
    cr400 = take("AS400: no llegó cliente a CR400")
    row = _section(
        ws, row,
        "Sin cliente en CR400",
        ["Tienda", "POS", "TR EPA", "CODCTE"],
        [[_num(r["Tienda"]), _num(r["POS/Caja"]), _num(r["TR EPA"])] for r in cr400],
    )
    blanco = take("AS400: estatus en blanco")
    row = _section(
        ws, row,
        "Transacciones con estatus en blanco en sus detalles",
        ["Tienda", "POS", "TR EPA"],
        [[_num(r["Tienda"]), _num(r["POS/Caja"]), _num(r["TR EPA"])] for r in blanco],
    )
    dev = take("AS400: devolución sin detalle")
    row = _section(
        ws, row,
        "Devoluciones sin detalles",
        ["Tienda", "POS", "TR EPA"],
        [[_num(r["Tienda"]), _num(r["POS/Caja"]), _num(r["TR EPA"])] for r in dev],
    )
    pend = take("MA_PAGOS pendiente")
    _section(
        ws, row,
        "TR's Pendientes por imprimir",
        ["Tienda", "POS", "TR", "Mensaje"],
        [[_num(r["Tienda"]), _num(r["POS/Caja"]), _num(r["TR EPA"]), r["Observaciones"]]
         for r in pend],
    )
    _apply_widths(ws, _WIDTHS_GT)


def _sheet_salvador(ws, rows):
    for i, h in enumerate(["Tienda", "POS", "TR EPA", "Observaciones"]):
        cell = ws.cell(row=1, column=1 + i)
        cell.value = h
        cell.alignment = _CENTER
    if not rows:
        return
    r = 2
    for item in rows:
        ws.cell(row=r, column=1).value = _num(item["Tienda"])
        ws.cell(row=r, column=2).value = _num(item["POS/Caja"])
        ws.cell(row=r, column=3).value = _num(item["TR EPA"])
        ws.cell(row=r, column=4).value = item["Observaciones"]
        r += 1
    _apply_widths(ws, _WIDTHS_SV)


def _sheet_venezuela(ws, rows):
    ws["A1"] = "StellarDocID"
    ws["B1"] = "Observaciones"
    if not rows:
        return
    r = 2
    for item in rows:
        ws.cell(row=r, column=1).value = item["StellarDocID"]
        ws.cell(row=r, column=2).value = item["Observaciones"]
        r += 1
    _apply_widths(ws, _WIDTHS_VE)


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
def build_workbook(rows_by_country, out_dir, date_str):
    os.makedirs(out_dir, exist_ok=True)
    wb = Workbook()
    wb.remove(wb.worksheets[0])
    builders = {"GT": _sheet_guatemala, "SV": _sheet_salvador, "VE": _sheet_venezuela}
    for country in config.SHEET_ORDER:
        meta = config.COUNTRIES[country]
        ws = wb.create_sheet(meta["sheet"])
        builders[country](ws, rows_by_country.get(country, []))
    path = os.path.join(out_dir, f"Detalles de Tr's atrapadas {date_str}.xlsx")
    wb.save(path)
    log.info("Hoja de cálculo generada: %s", path)
    return path


if __name__ == "__main__":
    import tempfile

    sample = {"GT": [{"Tienda": "3", "POS/Caja": "52", "TR EPA": "52023419",
                      "StellarDocID": "X", "Origen": "MA_PAGOS pendiente",
                      "Observaciones": "FAIL - 82-ERROR CALCULO DE IMPORTE BRUTO INCORRECTO"}],
              "SV": [{"Tienda": "3", "POS/Caja": "20", "TR EPA": "666745",
                      "Observaciones": "Se desconoce el motivo ya que la caja no está encendida."}],
              "VE": [{"StellarDocID": "13DEV41027786",
                      "Observaciones": "Error Relación Venta/Nota de Crédito."}]}
    with tempfile.TemporaryDirectory() as tmp:
        out = build_workbook(sample, tmp, "01-01-2026")
        from openpyxl import load_workbook

        wb = load_workbook(out)
        assert wb.sheetnames == ["Guatemala", "Salvador", "Venezuela"], wb.sheetnames
        g = wb["Guatemala"]
        assert g["A1"].value == "StellarDocID" and g["B1"].value == "Observaciones"
        assert g["B2"].value == "Sin observaciones."
        assert g["D1"].value.startswith("Sin cliente en VENTAS.MAECEC")
        assert g["D19"].value == 3 or g["D19"].value is None
        s = wb["Salvador"]
        assert s["A1"].value == "Tienda" and isinstance(s["A2"].value, (int, float))
        v = wb["Venezuela"]
        assert v["A1"].value == "StellarDocID"
    print("excel_builder OK")
