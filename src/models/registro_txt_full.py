from pydantic import BaseModel

class RegistroTxtFull(BaseModel):
    queue: str
    queue_id_cyber: str
    rut: str  # Combined RUT + DV
    branch: str
    branch_name: str
    name: str
    paternal_surname: str
    maternal_surname: str
    personal_address: str
    personal_number: str
    apartment: str
    neighborhood: str
    commune: str
    region: str
    personal_area_code: str
    personal_phone: str
    personal_cell_area_code: str
    personal_cell_phone: str
    cell_area_code: str
    cell_phone: str
    reference_area_code: str
    reference_phone: str
    status: str
    work_phone: str
    extension: str
    days_overdue: str
    monthly_payment: str
    total_debt: str
    down_payment_option1: str
    installments_option1: str
    installment_amount_option1: str
    down_payment_option2: str
    installments_option2: str
    installment_amount_option2: str
    process_date: str
    no_data: str
    overdue_date1: str
    overdue_amount1: str
    future_date1: str
    future_amount1: str
    future_date2: str
    future_amount2: str
    future_date3: str
    future_amount3: str
    future_date4: str
    future_amount4: str
    future_date5: str
    future_amount5: str
    future_date6: str
    future_amount6: str
    commitment_date: str
    future_commitment_date: str
    expired_commitments: str
    reprogramming_count: str
    active_reprogramming: str
    payment_plan_count: str
    active_payment_plan: str
    expense_debt: str
    capital_debt: str
    fees_debt: str
    interest_debt: str
    capital_discount: str
    expense_discount: str
    email: str
    birth_date: str
    tier1_cast_date: str
    card: str
    minimum_down_payment: str
    renewal_amount: str
    max_installments: str
    installment1: str
    installment1_value: str
    installment2: str
    installment2_value: str
    installment3: str
    installment3_value: str
    rate: str
    cae: str
    expiration_date: str

    @classmethod
    def from_line(cls, line: str) -> "RegistroTxtFull":
        return cls(
            queue=line[0:4].strip(),
            queue_id_cyber=line[0:4].strip(),
            rut=line[4:12].strip() + line[12:13].strip(),
            branch=line[13:18].strip(),
            branch_name=line[18:48].strip(),
            name=line[48:128].strip().split()[0],
            paternal_surname=line[128:208].strip(),
            maternal_surname=line[208:212].strip(),
            personal_address=line[212:292].strip(),
            personal_number=line[292:297].strip(),
            apartment=line[297:312].strip(),
            neighborhood=line[312:327].strip(),
            commune=line[327:367].strip(),
            region=line[367:372].strip(),
            personal_area_code=line[372:377].strip(),
            personal_phone=line[377:392].strip(),
            personal_cell_area_code=line[392:397].strip(),
            personal_cell_phone=line[397:412].strip(),
            cell_area_code=line[412:417].strip(),
            cell_phone=line[417:432].strip(),
            reference_area_code=line[432:437].strip(),
            reference_phone=line[437:452].strip(),
            status=line[452:453].strip(),
            work_phone=line[453:458].strip(),
            extension=line[458:473].strip(),
            days_overdue=line[473:478].strip(),
            monthly_payment=line[478:493].strip(),
            total_debt=line[493:508].strip(),
            down_payment_option1=line[508:523].strip(),
            installments_option1=line[523:525].strip(),
            installment_amount_option1=line[525:540].strip(),
            down_payment_option2=line[540:555].strip(),
            installments_option2=line[555:557].strip(),
            installment_amount_option2=line[557:572].strip(),
            process_date=line[572:583].strip(),
            no_data=line[583:586].strip(),
            overdue_date1=line[586:596].strip(),
            overdue_amount1=line[596:611].strip(),
            future_date1=line[611:621].strip(),
            future_amount1=line[621:630].strip(),
            future_date2=line[630:640].strip(),
            future_amount2=line[640:649].strip(),
            future_date3=line[649:659].strip(),
            future_amount3=line[659:668].strip(),
            future_date4=line[668:678].strip(),
            future_amount4=line[678:687].strip(),
            future_date5=line[687:697].strip(),
            future_amount5=line[697:706].strip(),
            future_date6=line[706:716].strip(),
            future_amount6=line[716:725].strip(),
            commitment_date=line[725:735].strip(),
            future_commitment_date=line[735:745].strip(),
            expired_commitments=line[745:748].strip(),
            reprogramming_count=line[748:751].strip(),
            active_reprogramming=line[751:752].strip(),
            payment_plan_count=line[752:755].strip(),
            active_payment_plan=line[755:756].strip(),
            expense_debt=line[756:765].strip(),
            capital_debt=line[765:774].strip(),
            fees_debt=line[774:783].strip(),
            interest_debt=line[783:792].strip(),
            capital_discount=line[792:807].strip(),
            expense_discount=line[807:822].strip(),
            email=line[822:882].strip(),
            birth_date=line[882:892].strip(),
            tier1_cast_date=line[892:902].strip(),
            card=line[902:908].strip(),
            minimum_down_payment=line[908:918].strip(),
            renewal_amount=line[918:928].strip(),
            max_installments=line[928:938].strip(),
            installment1=line[938:948].strip(),
            installment1_value=line[948:958].strip(),
            installment2=line[958:968].strip(),
            installment2_value=line[968:978].strip(),
            installment3=line[978:988].strip(),
            installment3_value=line[988:998].strip(),
            rate=line[998:1003].strip(),
            cae=line[1003:1008].strip(),
            expiration_date=line[1008:1018].strip(),
        )