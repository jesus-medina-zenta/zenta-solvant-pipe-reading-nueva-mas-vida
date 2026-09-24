"""
Normalización del archivo de deudores que envía Nueva Masvida.

Formato del piloto ("piloto Zenta Llamadas virtual.csv"):
- Codificación cp1252 (latin-1), separador ';'.
- Encabezados en español (RUTDeudor, Nombre / Razón Social  Deudor, Mail Deudor, ...).
- Nombre con apellidos primero: "SAAVEDRA TABILO JUAN EDUARDO".
- Montos con coma de miles: "73,611".
- Periodos como MM-YYYY: "07-2026".
- La última columna no tiene encabezado y trae el teléfono de gestión ya normalizado.
"""
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

# Partículas que forman parte de un apellido compuesto (ej. "MAC DONALD", "GARREAUD DE MAINVILL")
SURNAME_PARTICLES = {
    "DE", "DEL", "LA", "LAS", "LOS", "SAN", "SANTA", "MAC", "MC", "VON", "VAN", "DA", "DI", "DOS", "DAS", "Y",
}

# Encabezado sin nombre de la última columna del archivo (teléfono de gestión)
PHONE_COLUMN_WITHOUT_HEADER = ""

CLIENT_FORMAT_MARKER = "rutdeudor"

# "Tipo Deudor" de las empresas (razón social en vez de nombre de persona)
EMPLOYER_DEBTOR_TYPE = "empleador"


def normalize_key(key: Optional[str]) -> str:
    """Convierte un encabezado a snake_case ASCII: 'Mayor período de Deuda' -> 'mayor_periodo_de_deuda'."""
    text = unicodedata.normalize("NFKD", str(key or ""))
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def decode_content(raw: bytes) -> str:
    """Decodifica el archivo probando UTF-8 y, si falla, cp1252 (formato del cliente)."""
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1")


def detect_delimiter(content: str) -> str:
    """Detecta ';' o ',' mirando la línea de encabezados."""
    header = content.split("\n", 1)[0]
    return ";" if header.count(";") > header.count(",") else ","


def is_client_format(row: Dict[str, Any]) -> bool:
    return CLIENT_FORMAT_MARKER in {normalize_key(k) for k in row.keys() if k is not None}


def is_employer(row: Dict[str, Any]) -> bool:
    """True si la fila del archivo del cliente es una empresa (Tipo Deudor = Empleador)."""
    for key, value in row.items():
        if normalize_key(key) == "tipo_deudor":
            return str(value or "").strip().lower() == EMPLOYER_DEBTOR_TYPE
    return False


def _title(text: str) -> str:
    """Capitaliza respetando partículas: 'GARREAUD DE MAINVILL' -> 'Garreaud de Mainvill'."""
    words = []
    for word in text.split():
        words.append(word.lower() if word.upper() in SURNAME_PARTICLES and words else word.capitalize())
    return " ".join(words)


def _take_surname(tokens: List[str], start: int) -> Tuple[str, int]:
    """
    Toma un apellido desde tokens[start] y devuelve (apellido, siguiente índice).
    Incluye partículas al inicio ("MAC DONALD") o entre medio ("GARREAUD DE MAINVILL").
    """
    def is_particle(i: int) -> bool:
        return tokens[i].upper() in SURNAME_PARTICLES

    i = start
    while i < len(tokens) and is_particle(i):
        i += 1
    i += 1  # la palabra principal del apellido
    while i < len(tokens) and is_particle(i):
        j = i
        while j < len(tokens) and is_particle(j):
            j += 1
        if j >= len(tokens):
            break
        i = j + 1
    i = min(i, len(tokens))
    return " ".join(tokens[start:i]), i


def split_full_name(full_name: str) -> Dict[str, str]:
    """
    Separa "APELLIDO_PATERNO APELLIDO_MATERNO NOMBRES" en sus partes.
    Con solo dos palabras ("LUO JIAXING") se asume apellido + nombre.
    """
    tokens = (full_name or "").split()
    if not tokens:
        return {"primer_nombre": "", "nombres": "", "apellido_paterno": "", "apellido_materno": ""}
    if len(tokens) == 1:
        nombre = _title(tokens[0])
        return {"primer_nombre": nombre, "nombres": nombre, "apellido_paterno": "", "apellido_materno": ""}

    paterno, i = _take_surname(tokens, 0)
    if len(tokens) - i <= 1:
        nombres = tokens[i:]
        materno = ""
    else:
        materno, j = _take_surname(tokens, i)
        nombres = tokens[j:]
        if not nombres:
            # "PEREZ GONZALEZ" sin nombres: el segundo término es el nombre
            nombres, materno = materno.split(), ""

    nombres_text = _title(" ".join(nombres))
    return {
        "primer_nombre": nombres_text.split()[0] if nombres_text else "",
        "nombres": nombres_text,
        "apellido_paterno": _title(paterno),
        "apellido_materno": _title(materno),
    }


def normalize_phone(value: Any, allow_missing_nine: bool = False) -> str:
    """
    Normaliza un teléfono chileno a 9 dígitos sin +56. Devuelve "" si no es válido.
    allow_missing_nine: los celulares antiguos de 8 dígitos se completan con el 9 inicial.
    """
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) == 11 and digits.startswith("56"):
        digits = digits[2:]
    if len(digits) == 10 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) == 8 and allow_missing_nine:
        digits = "9" + digits
    if len(digits) != 9 or digits[0] in "01":
        return ""
    if set(digits[1:]) == {"0"}:
        # Relleno del cliente, ej. 900000000
        return ""
    return digits


def normalize_amount(value: Any) -> str:
    """'73,611' / '$ 73.611' -> '73611'."""
    return re.sub(r"\D", "", str(value or ""))


def normalize_email(value: Any) -> str:
    email = str(value or "").strip().lower()
    return email if "@" in email and " " not in email else ""


def parse_client_row(row: Dict[str, Any]) -> Dict[str, str]:
    """Convierte una fila del archivo del cliente a los campos que usa el pipeline."""
    values = {normalize_key(k): str(v or "").strip() for k, v in row.items() if k is not None}

    rut = values.get("rutdeudor", "").upper().replace(".", "").replace("-", "")
    nombre_deudor = " ".join(values.get("nombre_razon_social_deudor", "").split())
    tipo_deudor = values.get("tipo_deudor", "")

    if tipo_deudor.lower() == EMPLOYER_DEBTOR_TYPE:
        # Razón social de una empresa: no tiene nombre ni apellidos que separar
        razon_social = _title(nombre_deudor)
        nombre = {"primer_nombre": "", "apellido_paterno": "", "apellido_materno": ""}
        nombre_llamada = razon_social
    else:
        nombre = split_full_name(nombre_deudor)
        nombre_llamada = " ".join(p for p in (nombre["primer_nombre"], nombre["apellido_paterno"]) if p)

    phone_candidates = [
        # v2 del archivo: una sola columna "Numero Telefonico"
        normalize_phone(values.get("numero_telefonico"), allow_missing_nine=True),
        # v1 del archivo: última columna sin encabezado + columnas de teléfonos del deudor
        normalize_phone(values.get(PHONE_COLUMN_WITHOUT_HEADER), allow_missing_nine=True),
        normalize_phone(values.get("celular_deudor"), allow_missing_nine=True),
        normalize_phone(values.get("fono_de_contacto_back_cobranzas_1")),
        normalize_phone(values.get("fono_de_contacto_back_cobranzas_2")),
        normalize_phone(values.get("fono_particular_deudor")),
    ]
    phones: List[str] = []
    for phone in phone_candidates:
        if phone and phone not in phones:
            phones.append(phone)

    return {
        "rut_deudor": rut,
        "rut_number": rut[:-1],
        "rut_digit": rut[-1:],
        "nombre_deudor": nombre_deudor,
        "nombre_llamada": nombre_llamada,
        "primer_nombre": nombre["primer_nombre"],
        "apellido_paterno": nombre["apellido_paterno"],
        "apellido_materno": nombre["apellido_materno"],
        "email": normalize_email(values.get("mail_deudor")),
        "fono_contacto": phones[0] if phones else "",
        "fono_secundario": phones[1] if len(phones) > 1 else "",
        "deuda_cotizaciones": normalize_amount(values.get("monto_deuda")),
        "menor_per_deuda": values.get("menor_periodo_de_deuda", ""),
        "mayor_per_deuda": values.get("mayor_periodo_de_deuda", ""),
        "n_periodos": values.get("n_periodos", ""),
        "ciudad": values.get("ciudad_residencia_asignada_deudor", ""),
        "clasificacion_deudor": values.get("deudor_definido_segun_criterio_dado", ""),
        "tipo_deudor": tipo_deudor,
        "url_link": values.get("pago_link", ""),
        "estado_vigencia": values.get("estado_de_vigencia_del_contrato_deudor", ""),
        "fin_vigencia": values.get("fin_de_vigencia_deudor", ""),
        "tramo_deuda": values.get("tramo_menor_periodo_de_deuda", ""),
        "tipo_cartera": values.get("tipo_de_cartera", ""),
    }
