from rpms.util.db_connection import ACTOR_USER_ID, get_connection
from rpms.exception.exceptions import InvalidStatusTransitionError


class PlacementDAO:

    def find_by_id(self, placement_id: int):
        con = get_connection()
        try:
            cur = con.cursor(dictionary=True)
            cur.execute(
                "SELECT * FROM placements WHERE placement_id=%s",
                (placement_id,)
            )
            return cur.fetchone()
        finally:
            con.close()

    def find_by_offer(self, offer_id: int):
        con = get_connection()
        try:
            cur = con.cursor(dictionary=True)
            cur.execute("SELECT * FROM placements WHERE offer_id=%s", (offer_id,))
            return cur.fetchone()
        finally:
            con.close()

    def find_all(self):
        con = get_connection()
        try:
            cur = con.cursor(dictionary=True)
            cur.execute(
                """
                SELECT p.*, c.full_name, co.company_name, j.job_title
                FROM placements p
                JOIN candidates c ON c.candidate_id=p.candidate_id
                JOIN companies co ON co.company_id=p.company_id
                JOIN jobs j ON j.job_id=p.job_id
                ORDER BY p.created_at DESC
                """
            )
            return cur.fetchall()
        finally:
            con.close()

    def create(self, placement) -> int:
        con = get_connection()
        try:
            cur = con.cursor()
            cur.execute(
                """
                INSERT INTO placements
                (candidate_id, company_id, job_id, offer_id, designation,
                 final_package_lpa, expected_joining_date, joining_status, placement_status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'PENDING', 'ACTIVE')
                """,
                (
                    placement.candidate_id,
                    placement.company_id,
                    placement.job_id,
                    placement.offer_id,
                    placement.designation,
                    placement.final_package_lpa,
                    placement.expected_joining_date
                )
            )
            con.commit()
            return cur.lastrowid
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def update_joining(
        self,
        placement_id: int,
        status: str,
        actual_date,
        changed_by: int = ACTOR_USER_ID
    ) -> None:
        con = get_connection()
        try:
            cur = con.cursor(dictionary=True)
            cur.execute(
                """
                SELECT candidate_id, joining_status, offer_id
                FROM placements
                WHERE placement_id=%s
                FOR UPDATE
                """,
                (placement_id,)
            )
            placement = cur.fetchone()
            if not placement:
                raise LookupError(f"Placement ID {placement_id} not found")
            allowed = {
                "PENDING": {"JOINED", "NOT_JOINED", "DEFERRED", "NO_SHOW"},
                "DEFERRED": {"JOINED", "NOT_JOINED", "NO_SHOW"},
            }
            if status not in allowed.get(placement["joining_status"], set()):
                raise InvalidStatusTransitionError(
                    f"Cannot move placement from {placement['joining_status']} to {status}"
                )
            cur.execute(
                """
                UPDATE placements
                SET joining_status=%s, actual_joining_date=%s
                WHERE placement_id=%s
                """,
                (status, actual_date, placement_id)
            )
            if status == "JOINED":
                cur.execute(
                    "UPDATE candidates SET placement_status='PLACED' WHERE candidate_id=%s",
                    (placement["candidate_id"],)
                )
                cur.execute(
                    "SELECT application_id FROM offers WHERE offer_id=%s",
                    (placement["offer_id"],)
                )
                application_id = cur.fetchone()["application_id"]
                cur.execute(
                    "UPDATE applications SET application_status='JOINED' WHERE application_id=%s",
                    (application_id,)
                )
                cur.execute(
                    """
                    INSERT INTO application_history
                    (application_id, old_status, new_status, remarks, changed_by)
                    VALUES (%s, 'OFFERED', 'JOINED', 'Candidate joined placement', %s)
                    """,
                    (application_id, changed_by)
                )
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()
