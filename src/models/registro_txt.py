from pydantic import BaseModel, Field

class RegistroTxt(BaseModel):
    cola: str
    cola_id_cyber: str
    rut: str
    dv: str
    nombre: str
    ap_paterno: str
    ap_materno: str
    cod_fono_part: str
    fono_part: str
    cod_fono_part_cel: str
    fono_part_cel: str
    cod_fono_cel: str
    fono_cel: str
    cod_fono_ref: str
    fono_ref: str
    dias_mora: str
    apagar_mes: str
    pie_pm_op1: str
    fecha_proceso: str
    fecha_mora1: str
    monto_mora1: str
    mail: str
    tarjeta: str
    fec_venc: str

    @classmethod
    def from_line(cls, line: str) -> "RegistroTxt":
        return cls(
            cola=line[0:4].strip(),
            cola_id_cyber=line[0:4].strip(),
            rut=line[4:12].strip(),
            dv=line[12:13].strip(),
            nombre=line[48:128].strip(),
            ap_paterno=line[128:208].strip(),
            ap_materno=line[208:212].strip(),
            cod_fono_part=line[372:377].strip(),
            fono_part=line[377:392].strip(),
            cod_fono_part_cel=line[392:397].strip(),
            fono_part_cel=line[397:412].strip(),
            cod_fono_cel=line[412:417].strip(),
            fono_cel=line[417:432].strip(),
            cod_fono_ref=line[432:437].strip(),
            fono_ref=line[437:452].strip(),
            dias_mora=line[473:478].strip(),
            apagar_mes=line[478:493].strip(),
            pie_pm_op1=line[508:523].strip(),
            fecha_proceso=line[572:582].strip(),
            fecha_mora1=line[586:596].strip(),
            monto_mora1=line[596:611].strip(),
            mail=line[822:882].strip(),
            tarjeta=line[902:908].strip(),
            fec_venc=line[1008:1018].strip(),
        )
