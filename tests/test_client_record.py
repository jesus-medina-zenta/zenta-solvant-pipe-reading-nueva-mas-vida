"""
Tests del formato del archivo de deudores de Nueva Masvida (cp1252, separador ';',
encabezados en español, nombre con apellidos primero). Los datos son ficticios.
"""
import csv
import io

import pytest

from src.utils.client_record import (
    decode_content,
    detect_delimiter,
    is_client_format,
    normalize_phone,
    parse_client_row,
    split_full_name,
)

HEADER = (
    "RUTDeudor;Nombre / Razón Social  Deudor;Ciudad Residencia / Asignada  Deudor;"
    "Deudor (definido según criterio dado);Fin de Vigencia  Deudor;Mail Deudor;Fono particular Deudor;"
    "Celular Deudor;Estado de Vigencia del Contrato  Deudor;Tipo Deudor;Fono de Contacto BACK COBRANZAS (1);"
    "Fono de Contacto BACK COBRANZAS (2);N° períodos;Monto Deuda ($);Menor período de Deuda;"
    "Mayor período de Deuda;Tramo menor período de deuda;Tipo de Cartera;"
)
ROWS = [
    "11111111K;PÉREZ MUÑOZ JUAN ANDRÉS;SANTIAGO;Dependiente;;Juan.Perez@Correo.CL;;912345678;Vigente;Afiliado;;;2;"
    "84,249;06-2026;07-2026;Tramos 1 a 2;2;912345678",
    "222222222;SOTO ROJAS MARÍA;VALPARAISO;Pensionado;;maria@correo.cl;-;87654321;Vigente;Afiliado;322241711;;1;"
    "149,247;07-2026;07-2026;Tramos 1 a 2;2;900000000",
]


def _rows():
    raw = ("\r\n".join([HEADER] + ROWS) + "\r\n").encode("cp1252")
    content = decode_content(raw)
    return list(csv.DictReader(io.StringIO(content), delimiter=detect_delimiter(content)))


def test_lee_archivo_cp1252_con_punto_y_coma():
    rows = _rows()
    assert len(rows) == 2
    assert is_client_format(rows[0])


def test_mapea_la_fila_del_cliente():
    record = parse_client_row(_rows()[0])

    assert record["rut_deudor"] == "11111111K"
    assert record["nombre_deudor"] == "PÉREZ MUÑOZ JUAN ANDRÉS"
    assert record["nombre_llamada"] == "Juan Pérez"
    assert record["primer_nombre"] == "Juan"
    assert record["email"] == "juan.perez@correo.cl"
    assert record["fono_contacto"] == "912345678"
    assert record["deuda_cotizaciones"] == "84249"
    assert record["menor_per_deuda"] == "06-2026"
    assert record["mayor_per_deuda"] == "07-2026"
    assert record["n_periodos"] == "2"
    assert record["ciudad"] == "SANTIAGO"
    assert record["tipo_cartera"] == "2"


def test_telefono_de_relleno_se_reemplaza_por_el_celular():
    record = parse_client_row(_rows()[1])

    # La última columna trae 900000000: se usa el celular de 8 dígitos completado con 9
    assert record["fono_contacto"] == "987654321"
    assert record["fono_secundario"] == "322241711"


HEADER_V2 = (
    "RUTDeudor;Nombre / Razón Social  Deudor;Ciudad Residencia / Asignada  Deudor;"
    "Deudor (definido según criterio dado);Fin de Vigencia  Deudor;Mail Deudor;"
    "Estado de Vigencia del Contrato  Deudor;Tipo Deudor;N° períodos;Monto Deuda ($);Menor período de Deuda;"
    "Mayor período de Deuda;Tramo menor período de deuda;Tipo de Cartera;Numero Telefonico;Pago Link"
)
ROWS_V2 = [
    "11111111K;PÉREZ MUÑOZ JUAN ANDRÉS;SANTIAGO;Dependiente;;juan@correo.cl;Vigente;Afiliado;1;73,611;"
    "07-2026;07-2026;Tramos 1 a 2;2;912345678;https://pagos.ejemplo.cl/?id=abc123",
    "765432109;GRISO SPA;SANTIAGO;Empleador;;;;Empleador;1;150,000;07-2026;07-2026;Tramos 1 a 2;3;"
    "224567890;https://pagos.ejemplo.cl/?id=def456",
]


def _rows_v2():
    raw = ("\r\n".join([HEADER_V2] + ROWS_V2) + "\r\n").encode("cp1252")
    content = decode_content(raw)
    return list(csv.DictReader(io.StringIO(content), delimiter=detect_delimiter(content)))


def test_v2_usa_numero_telefonico_y_pago_link():
    record = parse_client_row(_rows_v2()[0])

    assert record["fono_contacto"] == "912345678"
    assert record["url_link"] == "https://pagos.ejemplo.cl/?id=abc123"
    assert record["nombre_llamada"] == "Juan Pérez"
    assert record["deuda_cotizaciones"] == "73611"


def test_v2_empleador_conserva_la_razon_social():
    record = parse_client_row(_rows_v2()[1])

    assert record["tipo_deudor"] == "Empleador"
    assert record["nombre_llamada"] == "Griso Spa"
    assert record["primer_nombre"] == ""
    assert record["fono_contacto"] == "224567890"
    assert record["email"] == ""


def test_excluye_empresas_y_deja_afiliados():
    from src.pipeline import Pipeline

    kept = Pipeline._exclude_employers(_rows_v2())

    assert len(kept) == 1
    assert kept[0]["Tipo Deudor"] == "Afiliado"


@pytest.mark.parametrize("full_name, primer_nombre, paterno, materno", [
    ("SAAVEDRA TABILO JUAN EDUARDO", "Juan", "Saavedra", "Tabilo"),
    ("ORREGO TOLEDO MAGALI", "Magali", "Orrego", "Toledo"),
    ("MAC DONALD SIRONVALLE FRANCISCO JAVIER", "Francisco", "Mac Donald", "Sironvalle"),
    ("GOSTLING GARREAUD DE MAINVILL CONSTANZA MARGARITA", "Constanza", "Gostling", "Garreaud de Mainvill"),
    ("RAMIREZ LABARCA FABIOLA DEL CARMEN", "Fabiola", "Ramirez", "Labarca"),
    ("LUO  JIAXING", "Jiaxing", "Luo", ""),
])
def test_separa_apellidos_y_nombres(full_name, primer_nombre, paterno, materno):
    parts = split_full_name(full_name)
    assert parts["primer_nombre"] == primer_nombre
    assert parts["apellido_paterno"] == paterno
    assert parts["apellido_materno"] == materno


@pytest.mark.parametrize("value, allow_missing_nine, expected", [
    ("973788338", True, "973788338"),
    (" 96806013", True, "996806013"),
    ("56954586160", True, "954586160"),
    ("02-28819648", False, "228819648"),
    ("900000000", True, ""),
    ("51/219617", False, ""),
    ("-", False, ""),
])
def test_normaliza_telefonos(value, allow_missing_nine, expected):
    assert normalize_phone(value, allow_missing_nine=allow_missing_nine) == expected
