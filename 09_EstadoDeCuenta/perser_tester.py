import re
from datetime import datetime

# --- INSTRUCCIONES --- #
# 1. Copiar y pegar estado de cuenta en un archivo txt
# 2. Limpiar archivo txt eliminando lineas no deseadas.
# Solo deven de estar la tabla
# 3. Modificar la variable ARCHIVO_INPUT para leer el archivo txt correcto
# 4. Ejecutar perser_tester.py
# 5. Copiar y pegar output en excel.
# 6. En excel, ajustar el formato en Data> text to column.


# ---  CONFIGURACION --- #
ETIQUETAS = "[TDC][SCB]"
ARCHIVO_INPUT = "estado_de_cuenta_07.txt"

# --- FUNCIONES PARSER --- #


def extraer_fechas(linea):
    patron = r'\d{2}-[a-zA-Z]{3}-\d{4}'
    fechas = re.findall(patron, linea)
    return fechas[0], fechas[1]   # fecha_operacion, fecha_cargo


def extraer_monto_gbp(linea):
    match = re.search(r'([\d,]+\.?\d*)GBP', linea)
    if not match:
        return None
    # Quitar las comas antes de convertir a float
    monto_str = match.group(1).replace(",", "")
    return float(monto_str)


def extraer_monto_mxn(linea):
    match = re.search(r'\$([\d,]+\.?\d*)', linea)
    if not match:
        return None
    # Quitar las comas antes de convertir a float
    monto_str = match.group(1).replace(",", "")
    return float(monto_str)


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

# --- LEER Y PROCESAR ---#


filas = []
errores = []

with open(ARCHIVO_INPUT, "r", encoding="utf-8") as f:
    for numero, linea in enumerate(f, start=1):
        linea = linea.strip()
        if not linea:
            continue
        try:
            fila = convertir_a_fila(linea)
            filas.append(fila)

        except Exception as e:
            errores.append(f" Linea {numero}: {linea[:50]}... -> {e}")

# Prueba
""" linea = "08-may-2026 11-may-2026 SumUp *MukjaLtdOxford 6.50GBP + $153.58"
fila = convertir_a_fila(linea)
print(fila) """

# --- MOSTRAR RESULTADO --- #
print("Date\t\tType\tCategory\tAmount\t\tAmount(GBP)\tDetails")
print("-" * 90)
for fila in filas:
    print("\t".join(str(c) if c is not None else "" for c in fila))

if errores:
    print(f"\n⚠️ {len(errores)} linea(s) con error:")
    for e in errores:
        print(e)
