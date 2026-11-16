from datetime import date

from rpms.exception.exceptions import InvalidStatusTransitionError
from rpms.util.db_connection import ACTOR_USER_ID, get_connection


class OfferDAO:

    def find_by_id(self, offer_id: int):
        con = get_connection()
        try:
            cur = con.cursor(dictionary=True)
            cur.execute("SELECT * FROM offers WHERE offer_id=%s", (offer_id,))
            return cur.fetchone()
        finally:
            con.close()

    def find_by_application(self, application_id: int):
        con = get_connection()
        try:
            cur = con.cursor(dictionary=True)
            cur.execute(
                "SELECT * FROM offers WHERE application_id=%s",
                (application_id,)
            )
            return cur.fetchone()
        finally:
            con.close()

    def find_all(self):
        con = get_connection()
        try:
            cur = con.cursor(dictionary=True)
            cur.execute(
                """
                SELECT o.*, a.application_code, c.full_name, co.company_name
                FROM offers o
                JOIN applications a ON a.application_id=o.application_id
                JOIN candidates c ON c.candidate_id=a.candidate_id
                JOIN jobs j ON j.job_id=a.job_id
                JOIN companies co ON co.company_id=j.company_id
                ORDER BY o.offer_date DESC, o.offer_id DESC
                """
            )
            return cur.fetchall()
        finally:
            con.close()

    def save(self, offer, changed_by: int = ACTOR_USER_ID) -> int:
        con = get_connection()
        try:
            cur = con.cursor(dictionary=True)
            cur.execute(
                "SELECT application_status FROM applications WHERE application_id=%s FOR UPDATE",
                (offer.application_id,)
            )
            application = cur.fetchone()
            if not application:
                raise LookupError(f"Application ID {offer.application_id} not found")
            if application["application_status"] != "SELECTED":
                raise InvalidStatusTransitionError(
                    "An offer can only be created for a selected application"
                )
            cur.execute(
                """
                INSERT INTO offers
                (offer_code, application_id, designation, offered_package_lpa,
                 offer_date, expected_joining_date, offer_status)
                VALUES (%s, %s, %s, %s, %s, %s, 'OFFERED')
                """,
                (
                    offer.offer_code,
                    offer.application_id,
                    offer.designation,
                    offer.offered_package_lpa,
                    offer.offer_date or date.today(),
                    offer.expected_joining_date
                )
            )
            offer_id = cur.lastrowid
            cur.execute(
                "UPDATE applications SET application_status='OFFERED' WHERE application_id=%s",
                (offer.application_id,)
            )
            cur.execute(
                """
                INSERT INTO application_history
                (application_id, old_status, new_status, remarks, changed_by)
                VALUES (%s, 'SELECTED', 'OFFERED', 'Offer created', %s)
                """,
                (offer.application_id, changed_by)
            )
            con.commit()
            return offer_id
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def set_status(self, offer_id: int, status: str) -> None:
        con = get_connection()
        try:
            cur = con.cursor(dictionary=True)
            cur.execute(
                "SELECT application_id, offer_status FROM offers WHERE offer_id=%s FOR UPDATE",
                (offer_id,)
            )
            offer = cur.fetchone()
            if not offer:
                raise LookupError(f"Offer ID {offer_id} not found")
            if offer["offer_status"] != "OFFERED" or status not in {
                "ACCEPTED", "REJECTED", "EXPIRED", "WITHDRAWN"
            }:
                raise InvalidStatusTransitionError(
                    f"Cannot move offer from {offer['offer_status']} to {status}"
                )
            cur.execute(
                "UPDATE offers SET offer_status=%s WHERE offer_id=%s",
                (status, offer_id)
            )
            application_status = {
                "REJECTED": "REJECTED",
                "WITHDRAWN": "WITHDRAWN",
                "EXPIRED": "REJECTED",
            }.get(status)
            if application_status:
                cur.execute(
                    "SELECT application_status FROM applications WHERE application_id=%s FOR UPDATE",
                    (offer["application_id"],)
                )
                old_status = cur.fetchone()["application_status"]
                cur.execute(
                    "UPDATE applications SET application_status=%s WHERE application_id=%s",
                    (application_status, offer["application_id"])
                )
                cur.execute(
                    """
                    INSERT INTO application_history
                    (application_id, old_status, new_status, remarks, changed_by)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        offer["application_id"],
                        old_status,
                        application_status,
                        f"Offer status changed to {status}",
                        ACTOR_USER_ID
                    )
                )
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()
