import re
from datetime import datetime

ETIQUETAS = "[TDC][SCB]"


def extraer_fechas(linea):
    patron = r'\d{2}-[a-zA-Z]{3}-\d{4}'
    fechas = re.findall(patron, linea)
    return fechas[0], fechas[1]   # fecha_operacion, fecha_cargo


def extraer_monto_gbp(linea):
    match = re.search(r'(\d+\.?\d*)GBP', linea)
    return float(match.group(1)) if match else None


def extraer_monto_mxn(linea):
    match = re.search(r'\$(\d+\.?\d*)', linea)
    return float(match.group(1)) if match else None


def extraer_descripcion(linea, fecha_cargo):
    # Todo lo que viene después de la segunda fecha...
    despues = linea.split(fecha_cargo)[1].strip()
    # ...hasta donde aparece el primer monto
    sin_montos = re.split(r'\d+\.?\d*GBP|\$\d+\.?\d*', despues)
    return sin_montos[0].strip().rstrip('+').strip()


def parsear_linea(linea):
    fecha_op, fecha_cargo = extraer_fechas(linea)
    return {
        "fecha_op":    fecha_op,
        "fecha_cargo": fecha_cargo,
        "descripcion": extraer_descripcion(linea, fecha_cargo),
        "monto_gbp":   extraer_monto_gbp(linea),
        "monto_mxn":   extraer_monto_mxn(linea),
    }


# ---  TRANSFORMAR AL FORMATO DE EXCEL --- #
def fromatear_fecha(fecha_str):
    # "08-may-2026" -> "08-May-26"
    fecha = datetime.strptime(fecha_str, "%d-%b-%Y")
    return fecha.strftime("%d-%b-%y")


def convertir_a_fila(linea):
    datos = parsear_linea(linea)

    date = fromatear_fecha(datos["fecha_op"])
    type_ = ""
    category = ""
    amount = datos["monto_mxn"]
    amount_gbp = datos["monto_gbp"]
    details = f"{ETIQUETAS} {datos['descripcion']}"

    return [date, type_, category, amount, amount_gbp, details]


# Prueba
linea = "08-may-2026 11-may-2026 SumUp *MukjaLtdOxford 6.50GBP + $153.58"
fila = convertir_a_fila(linea)
print(fila)
print("--- hello ---")
