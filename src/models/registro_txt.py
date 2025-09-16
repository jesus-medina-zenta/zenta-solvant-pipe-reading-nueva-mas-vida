from pydantic import BaseModel, Field

from src.models.metadata_user import MetadataUser

class RegistroTxt(BaseModel):
    id: str = Field(..., description="ID de la carga")
    phone_number: str = Field(..., description="Teléfono principal")
    phone_number_2: str = Field(..., description="Teléfono secundario")
    metadata_user: MetadataUser = Field(..., description="Datos del usuario agrupados")

    @classmethod
    def from_line(cls, line: str, id: str) -> "RegistroTxt":

        metadata_user = MetadataUser(
            queue=line[0:4].strip(),
            queue_id_cyber=line[0:4].strip(),
            rut=line[4:12].strip() + line[12:13].strip(),
            name=line[48:128].strip(),
            paternal_surname=line[128:208].strip(),
            maternal_surname=line[208:212].strip(),
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

        return cls(
            id=id,
            phone_number=line[377:392].strip(),
            phone_number_2=line[397:412].strip(),
            metadata_user=metadata_user
        )