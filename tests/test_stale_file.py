"""
Tests de la protección contra archivos antiguos: el cliente sube siempre el mismo
nombre y, si no sube uno nuevo, no se debe volver a llamar a las mismas personas.
"""
import asyncio
import os
from datetime import datetime, timedelta, timezone

import pytest

os.environ.setdefault("SFTP_HOST", "sftp.test")
os.environ.setdefault("SFTP_PORT", "22")
os.environ.setdefault("SFTP_USERNAME", "user")
os.environ.setdefault("SFTP_PASSWORD", "secret")
os.environ.setdefault("FIRESTORE_PROJECT_ID", "test")

from src.pipeline import CHILE_TZ, Pipeline  # noqa: E402


class FakeSftp:
    def __init__(self, modified=None, connects=True, stat_error=None):
        self.modified = modified
        self.connects = connects
        self.stat_error = stat_error
        self.is_connected = False
        self.extracted = False

    def connect(self):
        self.is_connected = self.connects
        return self.connects

    def get_modified_time(self, path):
        if self.stat_error:
            raise self.stat_error
        return self.modified

    def extract(self, path):
        self.extracted = True
        return []

    def disconnect(self):
        pass


def _pipeline(sftp):
    pipeline = Pipeline.__new__(Pipeline)
    pipeline.sftp_service = sftp
    pipeline.file_url = "/zentagrp/NMV-COBRANZA.csv"
    pipeline.errors = []
    return pipeline


def _chile_today_at(hour, minute=0):
    now = datetime.now(CHILE_TZ)
    return now.replace(hour=hour, minute=minute, second=0, microsecond=0).astimezone(timezone.utc)


def _yesterday_at(hour, minute=0):
    return _chile_today_at(hour, minute) - timedelta(days=1)


def test_archivo_subido_hoy_se_procesa():
    assert _pipeline(FakeSftp(_chile_today_at(0, 5)))._stale_file_reason() is None
    assert _pipeline(FakeSftp(_chile_today_at(11, 0)))._stale_file_reason() is None


def test_archivo_subido_ayer_no_se_procesa_aunque_sea_reciente():
    # Ayer a las 23:55 puede tener pocas horas de antigüedad, pero no es de hoy
    reason = _pipeline(FakeSftp(_yesterday_at(23, 55)))._stale_file_reason()
    assert reason.startswith("ARCHIVO ANTIGUO")
    assert "NMV-COBRANZA.csv" in reason


def test_archivo_de_varios_dias_atras_no_se_procesa():
    assert _pipeline(FakeSftp(_chile_today_at(11) - timedelta(days=5)))._stale_file_reason()


def test_se_puede_desactivar_para_una_ejecucion_manual(monkeypatch):
    monkeypatch.setenv("PIPELINE_REQUIRE_TODAY_FILE", "false")
    assert _pipeline(FakeSftp(_chile_today_at(11) - timedelta(days=30)))._stale_file_reason() is None


def test_si_no_se_puede_leer_la_fecha_no_bloquea_y_extract_informa():
    assert _pipeline(FakeSftp(stat_error=FileNotFoundError("no existe")))._stale_file_reason() is None
    assert _pipeline(FakeSftp(connects=False))._stale_file_reason() is None


def test_run_con_archivo_antiguo_no_extrae_ni_dispara_nada():
    sftp = FakeSftp(_yesterday_at(23, 55))
    pipeline = _pipeline(sftp)
    saved = []

    async def fake_log(id, status, extracted, processed, errors, fecha_utc, csv_location):
        saved.append((status, extracted, errors))

    pipeline._save_extraction_log = fake_log
    pipeline.firestore_service = type("F", (), {"disconnect": lambda self: None})()
    pipeline.gcs_service = type("G", (), {"disconnect": lambda self: asyncio.sleep(0)})()
    pipeline.cloud_run_service = type("C", (), {"disconnect": lambda self: None})()

    assert asyncio.run(pipeline.run()) is True
    assert sftp.extracted is False
    assert saved[0][0] == "NO_DATA" and saved[0][1] == 0
    assert saved[0][2][0].startswith("ARCHIVO ANTIGUO")
