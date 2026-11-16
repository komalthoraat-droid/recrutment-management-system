from rpms.model.company import Company
from rpms.util.db_connection import get_connection


class CompanyDAO:

    def save(self, company: Company) -> int:
        con = get_connection()
        try:
            cur = con.cursor()
            cur.execute(
                """
                INSERT INTO companies
                (company_code, company_name, industry, location, hr_name, hr_email, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    company.company_code,
                    company.company_name,
                    company.industry or None,
                    company.location or None,
                    company.hr_name or None,
                    company.hr_email or None,
                    company.status
                )
            )
            con.commit()
            return cur.lastrowid
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def find_by_id(self, company_id: int):
        return self._query(
            "SELECT * FROM companies WHERE company_id=%s",
            (company_id,),
            one=True
        )

    def find_all(self, search: str = "", active_only: bool = False):
        clauses = []
        params = []
        if search:
            clauses.append("(company_name LIKE %s OR company_code LIKE %s OR industry LIKE %s)")
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
        if active_only:
            clauses.append("status='ACTIVE'")
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        return self._query(
            f"SELECT * FROM companies{where} ORDER BY company_name",
            tuple(params)
        )

    def set_status(self, company_id: int, status: str) -> bool:
        con = get_connection()
        try:
            cur = con.cursor()
            cur.execute("SELECT 1 FROM companies WHERE company_id=%s", (company_id,))
            if cur.fetchone() is None:
                return False
            cur.execute(
                "UPDATE companies SET status=%s WHERE company_id=%s",
                (status, company_id)
            )
            con.commit()
            return True
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    @staticmethod
    def _query(sql: str, params: tuple = (), one: bool = False):
        con = get_connection()
        try:
            cur = con.cursor(dictionary=True)
            cur.execute(sql, params)
            rows = cur.fetchone() if one else cur.fetchall()
            if one:
                return CompanyDAO._map(rows) if rows else None
            return [CompanyDAO._map(row) for row in rows]
        finally:
            con.close()

    @staticmethod
    def _map(row):
        return Company(
            company_id=row["company_id"],
            company_code=row["company_code"],
            company_name=row["company_name"],
            industry=row["industry"] or "",
            location=row["location"] or "",
            hr_name=row["hr_name"] or "",
            hr_email=row["hr_email"] or "",
            status=row["status"]
        )
