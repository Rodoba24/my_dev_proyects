import re
import os
from datetime import datetime


# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PATRON_MONEDA = re.compile(r'^(GBP|EUR|MXP)\s*\$')
ARCHIVO_INPUT = [
    "estado_de_cuenta_07.txt",
    "estado_de_cuenta_BBVA.txt"
]
ETIQUETAS = {
    "1": "[TDC][SCB]",
    "2": "[TDC][BBV]"
    }

MESES_ES = {
    "ene": "jan", "feb": "feb", "mar": "mar", "abr": "apr",
    "may": "may", "jun": "jun", "jul": "jul", "ago": "aug",
    "sep": "sep", "oct": "oct", "nov": "nov", "dic": "dec"
}


# =============================================================
# FUNCIONES COMPARTIDAS
# =============================================================


def traducir_fecha(fecha_str):
    # 02-abr-2026 -> "02-apr-2026"
    for es, en in MESES_ES.items():
        fecha_str = fecha_str.replace(es, en)
    return fecha_str


def formatear_fecha(fecha_str):
    fecha_str = traducir_fecha(fecha_str.lower())
    fecha = datetime.strptime(fecha_str, "%d-%b-%Y")
    return fecha.strftime("%d-%b-%y")


def extraer_fechas(linea):
    patron = r'\d{2}-[a-zA-Z]{3}-\d{4}'
    fechas = re.findall(patron, linea)
    return fechas[0], fechas[1]


def extraer_monto_mxn(texto):
    match = re.search(r'\$([\d,]+\.?\d*)', texto)
    if not match:
        return None
    return float(match.group(1).replace(",", ""))


def extraer_monto_gbp(texto):
    match = re.search(r'(\d+\.?\d*)GBP', texto)
    return float(match.group(1)) if match else None


# =============================================================
# BANCO 1 — una línea por entrada
# =============================================================


def extraer_descripcion_b1(linea, fecha_cargo):
    despues = linea.split(fecha_cargo)[1].strip()
    sin_montos = re.split(r'\d+\.?\d*GBP|\$[\d,]+\.?\d*', despues)
    return sin_montos[0].strip().rstrip('+').strip()


def parsear_banco1(linea):
    fecha_op, fecha_cargo = extraer_fechas(linea)
    descripcion = extraer_descripcion_b1(linea, fecha_cargo)
    return {
        "fecha_op":    fecha_op,
        "descripcion": descripcion,
        "monto_mxn":   extraer_monto_mxn(linea),
        "monto_gbp":   extraer_monto_gbp(linea),
    }

# =============================================================
# BANCO 2 — una o dos líneas por entrada
# =============================================================


def limpiar_descripcion_b2(texto):
    # Quitar info de tarjeta: "; Tarjeta Digital ***1234"
    texto = re.sub(r';.*$', '', texto)
    return texto.strip()


def extraer_descripcion_b2(linea, fecha_cargo):
    despues = linea.split(fecha_cargo)[1].strip()
    # Quitar el monto del final (viene después de +)
    sin_monto = re.split(r'\+\s*\$[\d,]+\.?\d*', despues)[0]
    return limpiar_descripcion_b2(sin_monto)


def agrupar_lineas_banco2(lineas):
    grupos = []
    i = 0
    while i < len(lineas):
        linea_actual = lineas[i]
        if i + 1 < len(lineas) and PATRON_MONEDA.match(lineas[i + 1].strip()):
            grupos.append((linea_actual, lineas[i + 1]))
            i += 2
        else:
            grupos.append((linea_actual, None))
            i += 1
    return grupos


def parsear_banco2(linea_principal, linea_secundaria=None):
    fecha_op, fecha_cargo = extraer_fechas(linea_principal)
    descripcion = extraer_descripcion_b2(linea_principal, fecha_cargo)

    # Monto MXN siempre viene en la línea principal
    monto_mxn = extraer_monto_mxn(linea_principal)

    # Monto GBP viene en la segunda línea si existe
    monto_gbp = None
    if linea_secundaria:
        match = re.search(r'GBP\s*\$([\d,]+\.?\d*)', linea_secundaria)
        if match:
            monto_gbp = float(match.group(1).replace(",", ""))

    return {
        "fecha_op":    fecha_op,
        "descripcion": descripcion,
        "monto_mxn":   monto_mxn,
        "monto_gbp":   monto_gbp,
    }

# =============================================================
# CONVERTIR A FILA EXCEL
# =============================================================


def convertir_a_fila(datos, banco):
    date = formatear_fecha(datos["fecha_op"])
    amount = datos["monto_mxn"]
    amount_gbp = datos["monto_gbp"]
    details = f"{ETIQUETAS[banco]} {datos['descripcion']}"
    return [date, "", "", amount, amount_gbp, details]

# =============================================================
# MAIN
# =============================================================


def procesar_banco1():
    archivo = os.path.join(BASE_DIR, ARCHIVO_INPUT[0])
    filas, errores = [], []

    with open(archivo, "r", encoding="utf-8") as f:
        for numero, linea in enumerate(f, start=1):
            linea = linea.strip()
            if not linea:
                continue
            try:
                filas.append(convertir_a_fila(parsear_banco1(linea), "1"))
            except Exception as e:
                errores.append(f"  Línea {numero}: {linea[:50]} → {e}")

    return filas, errores


def procesar_banco2():
    archivo = os.path.join(BASE_DIR, ARCHIVO_INPUT[1])
    filas, errores = [], []

    with open(archivo, "r", encoding="utf-8") as f:
        lineas = [ln.strip() for ln in f if ln.strip()]

    grupos = agrupar_lineas_banco2(lineas)

    for i, (principal, secundaria) in enumerate(grupos, start=1):
        try:
            filas.append(convertir_a_fila(parsear_banco2(principal,
                                                         secundaria), "2"))
        except Exception as e:
            errores.append(f"  Entrada {i}: {principal[:50]} → {e}")

    return filas, errores


def mostrar_resultado(filas, errores):
    print("\nDate\t\tType\tCategory\tAmount\t\tAmount(GBP)\tDetails")
    print("-" * 90)
    for fila in filas:
        print("\t".join(str(c) if c is not None else "" for c in fila))

    if errores:
        print(f"\n⚠️  {len(errores)} línea(s) con error:")
        for e in errores:
            print(e)


def main():
    print("¿Qué banco quieres procesar?")
    print("  1 — Banco 1 (Scot)")
    print("  2 — Banco 2 (BBVA)")
    opcion = input("\nOpción: ").strip()

    if opcion == "1":
        filas, errores = procesar_banco1()
    elif opcion == "2":
        filas, errores = procesar_banco2()
    else:
        print("Opción no válida.")
        return

    mostrar_resultado(filas, errores)


main()
