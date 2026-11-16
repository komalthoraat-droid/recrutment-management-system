from rpms.exception.exceptions import CompanyNotFoundError
from rpms.model.company import Company
from rpms.util.validation import is_valid_email


class CompanyService:

    def __init__(self, company_dao):
        self.company_dao = company_dao

    def add_company(self, company: Company) -> int:
        company.company_code = company.company_code.strip().upper()
        company.company_name = company.company_name.strip()
        company.hr_email = company.hr_email.strip().lower()
        company.status = company.status.strip().upper()
        if not company.company_code or not company.company_name:
            raise ValueError("Company code and company name are required")
        if company.hr_email and not is_valid_email(company.hr_email):
            raise ValueError("Invalid HR email")
        if company.status not in {"ACTIVE", "INACTIVE"}:
            raise ValueError("Company status must be ACTIVE or INACTIVE")
        return self.company_dao.save(company)

    def get_company(self, company_id: int):
        company = self.company_dao.find_by_id(company_id)
        if not company:
            raise CompanyNotFoundError(f"Company ID {company_id} not found")
        return company

    def get_companies(self, search: str = "", active_only: bool = False):
        return self.company_dao.find_all(search, active_only)

    def update_status(self, company_id: int, status: str) -> None:
        target = status.strip().upper()
        if target not in {"ACTIVE", "INACTIVE"}:
            raise ValueError("Company status must be ACTIVE or INACTIVE")
        if not self.company_dao.set_status(company_id, target):
            raise CompanyNotFoundError(f"Company ID {company_id} not found")
