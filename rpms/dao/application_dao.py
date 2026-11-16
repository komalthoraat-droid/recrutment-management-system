from rpms.model.application import Application
from rpms.exception.exceptions import InvalidStatusTransitionError
from rpms.util.db_connection import ACTOR_USER_ID, get_connection

class ApplicationDAO:

    def save(self, app: Application, changed_by: int = ACTOR_USER_ID) -> int:
        sql = '''
            INSERT INTO applications
            (application_code,candidate_id,job_id,eligibility_status,
             eligibility_reason,application_status)
            VALUES (%s,%s,%s,%s,%s,%s)
        '''
        con = get_connection()
        try:
            cur = con.cursor()
            cur.execute(sql, (
                app.application_code,
                app.candidate_id,
                app.job_id,
                app.eligibility_status,
                app.eligibility_reason,
                app.application_status
            ))
            application_id = cur.lastrowid
            cur.execute(
                """
                INSERT INTO application_history
                (application_id, old_status, new_status, remarks, changed_by)
                VALUES (%s, NULL, %s, %s, %s)
                """,
                (application_id, app.application_status, "Application submitted", changed_by)
            )
            con.commit()
            return application_id
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def exists(self, candidate_id: int, job_id: int) -> bool:
        con = get_connection()
        try:
            cur = con.cursor()
            cur.execute(
                "SELECT 1 FROM applications WHERE candidate_id=%s AND job_id=%s",
                (candidate_id, job_id)
            )
            return cur.fetchone() is not None
        finally:
            con.close()

    def find_by_candidate(self, candidate_id: int):
        con = get_connection()
        try:
            cur = con.cursor(dictionary=True)
            cur.execute(
                "SELECT * FROM applications WHERE candidate_id=%s ORDER BY application_id DESC",
                (candidate_id,)
            )
            return cur.fetchall()
        finally:
            con.close()

    def find_by_id(self, application_id: int):
        con = get_connection()
        try:
            cur = con.cursor(dictionary=True)
            cur.execute("SELECT * FROM applications WHERE application_id=%s", (application_id,))
            return cur.fetchone()
        finally:
            con.close()

    def find_all(self, status: str | None = None):
        con = get_connection()
        try:
            cur = con.cursor(dictionary=True)
            if status:
                cur.execute(
                    """
                    SELECT a.*, c.full_name, j.job_title, co.company_name
                    FROM applications a
                    JOIN candidates c ON c.candidate_id=a.candidate_id
                    JOIN jobs j ON j.job_id=a.job_id
                    JOIN companies co ON co.company_id=j.company_id
                    WHERE a.application_status=%s
                    ORDER BY a.applied_at DESC
                    """,
                    (status.upper(),)
                )
            else:
                cur.execute(
                    """
                    SELECT a.*, c.full_name, j.job_title, co.company_name
                    FROM applications a
                    JOIN candidates c ON c.candidate_id=a.candidate_id
                    JOIN jobs j ON j.job_id=a.job_id
                    JOIN companies co ON co.company_id=j.company_id
                    ORDER BY a.applied_at DESC
                    """
                )
            return cur.fetchall()
        finally:
            con.close()

    def set_status(
        self,
        application_id: int,
        status: str,
        remarks: str,
        changed_by: int = ACTOR_USER_ID,
        expected_status: str | None = None
    ) -> None:
        con = get_connection()
        try:
            cur = con.cursor(dictionary=True)
            cur.execute(
                "SELECT application_status FROM applications WHERE application_id=%s FOR UPDATE",
                (application_id,)
            )
            row = cur.fetchone()
            if not row:
                raise LookupError(f"Application ID {application_id} not found")
            old_status = row["application_status"]
            if expected_status and old_status != expected_status:
                raise InvalidStatusTransitionError(
                    f"Application status changed from {expected_status} to {old_status}"
                )
            cur.execute(
                "UPDATE applications SET application_status=%s WHERE application_id=%s",
                (status, application_id)
            )
            cur.execute(
                """
                INSERT INTO application_history
                (application_id, old_status, new_status, remarks, changed_by)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (application_id, old_status, status, remarks, changed_by)
            )
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()
