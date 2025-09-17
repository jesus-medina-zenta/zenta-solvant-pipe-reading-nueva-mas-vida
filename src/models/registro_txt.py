from pydantic import BaseModel, Field

class RegistroTxt(BaseModel):
    queue: str
    queue_id_cyber: str
    rut: str
    name: str
    paternal_surname: str
    maternal_surname: str
    personal_area_code: str
    personal_phone: str
    personal_cell_area_code: str
    personal_cell_phone: str
    cell_area_code: str
    cell_phone: str
    reference_area_code: str
    reference_phone: str
    days_overdue: str
    monthly_payment: str
    down_payment_option1: str
    process_date: str
    overdue_date1: str
    overdue_amount1: str
    email: str
    card: str
    expiration_date: str

    @classmethod
    def from_line(cls, line: str) -> "RegistroTxt":
        return cls(
            queue=line[0:4].strip(),
            queue_id_cyber=line[0:4].strip(),
            rut=line[4:12].strip() + line[12:13].strip(),
            name=line[48:128].strip(),
            paternal_surname=line[128:208].strip(),
            maternal_surname=line[208:212].strip(),
            personal_area_code=line[372:377].strip(),
            personal_phone=line[377:392].strip(),
            personal_cell_area_code=line[392:397].strip(),
            personal_cell_phone=line[397:412].strip(),
            cell_area_code=line[412:417].strip(),
            cell_phone=line[417:432].strip(),
            reference_area_code=line[432:437].strip(),
            reference_phone=line[437:452].strip(),
            days_overdue=line[473:478].strip(),
            monthly_payment=line[478:493].strip(),
            down_payment_option1=line[508:523].strip(),
            process_date=line[572:582].strip(),
            overdue_date1=line[586:596].strip(),
            overdue_amount1=line[596:611].strip(),
            email=line[822:882].strip(),
            card=line[902:908].strip(),
            expiration_date=line[1008:1018].strip(),
        )