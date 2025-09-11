from pydantic import BaseModel

class RegistroTxtFull(BaseModel):
    cola: str
    cola_id_cyber: str
    rut: str
    dv: str
    sucursal: str
    nombre_sucursal: str
    nombre: str
    ap_paterno: str
    ap_materno: str
    calle_part: str
    nro_part: str
    dpto_part: str
    villa_part: str
    comuna_part: str
    region_part: str
    cod_fono_part: str
    fono_part: str
    cod_fono_part_cel: str
    fono_part_cel: str
    cod_fono_cel: str
    fono_cel: str
    cod_fono_ref: str
    fono_ref: str
    estado: str
    fono_lab: str
    anexo: str
    dias_mora: str
    apagar_mes: str
    total_deuda: str
    pie_pm_op1: str
    nro_cuotas_pm_op1: str
    cuotas_pm_op1: str
    pie_pm_op2: str
    nro_cuotas_pm_op2: str
    cuotas_pm_op2: str
    fecha_proceso: str
    sin_dato: str
    fecha_mora1: str
    monto_mora1: str
    fecha_fut1: str
    monto_fut1: str
    fecha_fut2: str
    monto_fut2: str
    fecha_fut3: str
    monto_fut3: str
    fecha_fut4: str
    monto_fut4: str
    fecha_fut5: str
    monto_fut5: str
    fecha_fut6: str
    monto_fut6: str
    fecha_compromiso: str
    fecha_compromiso_futuro: str
    compromisos_vencidos: str
    cant_rep: str
    rep_vig: str
    cant_pm: str
    vig_pm: str
    deuda_gasto: str
    deuda_capital: str
    deuda_honorarios: str
    deuda_intereses: str
    dscto_capital: str
    dscto_gasto: str
    mail: str
    fecha_nacimiento: str
    fecha_cast_t1: str
    tarjeta: str
    pie_min: str
    monto_rene: str
    max_cuo: str
    cuota1: str
    valor_cuo1: str
    cuota2: str
    valor_cuo2: str
    cuota3: str
    valor_cuo3: str
    tasa: str
    cae: str
    fec_venc: str

    @classmethod
    def from_line(cls, line: str) -> "RegistroTxtFull":
        return cls(
            cola=line[0:4].strip(),
            cola_id_cyber=line[0:4].strip(),
            rut=line[4:12].strip(),
            dv=line[12:13].strip(),
            sucursal=line[13:18].strip(),
            nombre_sucursal=line[18:48].strip(),
            nombre=line[48:128].strip(),
            ap_paterno=line[128:208].strip(),
            ap_materno=line[208:212].strip(),
            calle_part=line[212:292].strip(),
            nro_part=line[292:297].strip(),
            dpto_part=line[297:312].strip(),
            villa_part=line[312:327].strip(),
            comuna_part=line[327:367].strip(),
            region_part=line[367:372].strip(),
            cod_fono_part=line[372:377].strip(),
            fono_part=line[377:392].strip(),
            cod_fono_part_cel=line[392:397].strip(),
            fono_part_cel=line[397:412].strip(),
            cod_fono_cel=line[412:417].strip(),
            fono_cel=line[417:432].strip(),
            cod_fono_ref=line[432:437].strip(),
            fono_ref=line[437:452].strip(),
            estado=line[452:453].strip(),
            fono_lab=line[453:458].strip(),
            anexo=line[458:473].strip(),
            dias_mora=line[473:478].strip(),
            apagar_mes=line[478:493].strip(),
            total_deuda=line[493:508].strip(),
            pie_pm_op1=line[508:523].strip(),
            nro_cuotas_pm_op1=line[523:525].strip(),
            cuotas_pm_op1=line[525:540].strip(),
            pie_pm_op2=line[540:555].strip(),
            nro_cuotas_pm_op2=line[555:557].strip(),
            cuotas_pm_op2=line[557:572].strip(),
            fecha_proceso=line[572:582].strip(),
            sin_dato=line[583:586].strip(),
            fecha_mora1=line[586:596].strip(),
            monto_mora1=line[596:611].strip(),
            fecha_fut1=line[611:621].strip(),
            monto_fut1=line[621:630].strip(),
            fecha_fut2=line[630:640].strip(),
            monto_fut2=line[640:649].strip(),
            fecha_fut3=line[649:659].strip(),
            monto_fut3=line[659:668].strip(),
            fecha_fut4=line[668:678].strip(),
            monto_fut4=line[678:687].strip(),
            fecha_fut5=line[687:697].strip(),
            monto_fut5=line[697:706].strip(),
            fecha_fut6=line[706:716].strip(),
            monto_fut6=line[716:725].strip(),
            fecha_compromiso=line[725:735].strip(),
            fecha_compromiso_futuro=line[735:745].strip(),
            compromisos_vencidos=line[745:748].strip(),
            cant_rep=line[748:751].strip(),
            rep_vig=line[751:752].strip(),
            cant_pm=line[752:755].strip(),
            vig_pm=line[755:756].strip(),
            deuda_gasto=line[756:765].strip(),
            deuda_capital=line[765:774].strip(),
            deuda_honorarios=line[774:783].strip(),
            deuda_intereses=line[783:792].strip(),
            dscto_capital=line[792:807].strip(),
            dscto_gasto=line[807:822].strip(),
            mail=line[822:882].strip(),
            fecha_nacimiento=line[882:892].strip(),
            fecha_cast_t1=line[892:902].strip(),
            tarjeta=line[902:908].strip(),
            pie_min=line[908:918].strip(),
            monto_rene=line[918:928].strip(),
            max_cuo=line[928:938].strip(),
            cuota1=line[938:948].strip(),
            valor_cuo1=line[948:958].strip(),
            cuota2=line[958:968].strip(),
            valor_cuo2=line[968:978].strip(),
            cuota3=line[978:988].strip(),
            valor_cuo3=line[988:998].strip(),
            tasa=line[998:1003].strip(),
            cae=line[1003:1008].strip(),
            fec_venc=line[1008:1018].strip(),
        )