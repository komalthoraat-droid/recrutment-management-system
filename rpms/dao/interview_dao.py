from rpms.model.interview import Interview
from rpms.model.interview_feedback import InterviewFeedback
from rpms.exception.exceptions import InvalidStatusTransitionError
from rpms.util.db_connection import ACTOR_USER_ID, get_connection


class InterviewDAO:

    def find_by_id(self, interview_id: int):
        con = get_connection()
        try:
            cur = con.cursor(dictionary=True)
            cur.execute(
                "SELECT * FROM interview_rounds WHERE interview_id=%s",
                (interview_id,)
            )
            return cur.fetchone()
        finally:
            con.close()

    def find_by_application(self, application_id: int):
        con = get_connection()
        try:
            cur = con.cursor(dictionary=True)
            cur.execute(
                """
                SELECT ir.*, f.recommendation, f.overall_rating, f.remarks
                FROM interview_rounds ir
                LEFT JOIN interview_feedback f ON f.interview_id=ir.interview_id
                WHERE ir.application_id=%s
                ORDER BY ir.round_number
                """,
                (application_id,)
            )
            return cur.fetchall()
        finally:
            con.close()

    def next_round_number(self, application_id: int) -> int:
        con = get_connection()
        try:
            cur = con.cursor()
            cur.execute(
                "SELECT COALESCE(MAX(round_number), 0) + 1 FROM interview_rounds WHERE application_id=%s",
                (application_id,)
            )
            return int(cur.fetchone()[0])
        finally:
            con.close()

    def save(self, interview: Interview, changed_by: int = ACTOR_USER_ID) -> int:
        con = get_connection()
        try:
            cur = con.cursor(dictionary=True)
            cur.execute(
                "SELECT application_status FROM applications WHERE application_id=%s FOR UPDATE",
                (interview.application_id,)
            )
            application = cur.fetchone()
            if not application:
                raise LookupError(f"Application ID {interview.application_id} not found")
            old_status = application["application_status"]
            if old_status not in {"SHORTLISTED", "INTERVIEWED"}:
                raise InvalidStatusTransitionError(
                    f"Cannot schedule an interview for application status {old_status}"
                )
            cur.execute(
                """
                INSERT INTO interview_rounds
                (application_id, round_number, round_type, scheduled_date, scheduled_time,
                 mode, interviewer_name, meeting_or_location, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    interview.application_id,
                    interview.round_number,
                    interview.round_type,
                    interview.scheduled_date,
                    interview.scheduled_time,
                    interview.mode,
                    interview.interviewer_name or None,
                    interview.meeting_or_location or None,
                    interview.status
                )
            )
            interview_id = cur.lastrowid
            if old_status != "INTERVIEW_SCHEDULED":
                cur.execute(
                    "UPDATE applications SET application_status='INTERVIEW_SCHEDULED' WHERE application_id=%s",
                    (interview.application_id,)
                )
                cur.execute(
                    """
                    INSERT INTO application_history
                    (application_id, old_status, new_status, remarks, changed_by)
                    VALUES (%s, %s, 'INTERVIEW_SCHEDULED', %s, %s)
                    """,
                    (
                        interview.application_id,
                        old_status,
                        f"Interview round {interview.round_number} scheduled",
                        changed_by
                    )
                )
            con.commit()
            return interview_id
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def save_feedback(
        self,
        feedback: InterviewFeedback,
        changed_by: int = ACTOR_USER_ID
    ) -> None:
        next_status = {
            "NEXT_ROUND": "INTERVIEWED",
            "SELECTED": "SELECTED",
            "REJECTED": "REJECTED",
            "ON_HOLD": "INTERVIEWED",
        }[feedback.recommendation]
        con = get_connection()
        try:
            cur = con.cursor(dictionary=True)
            cur.execute(
                """
                SELECT application_id, status
                FROM interview_rounds
                WHERE interview_id=%s
                FOR UPDATE
                """,
                (feedback.interview_id,)
            )
            interview = cur.fetchone()
            if not interview:
                raise LookupError(f"Interview ID {feedback.interview_id} not found")
            if interview["status"] not in {"SCHEDULED", "RESCHEDULED"}:
                raise InvalidStatusTransitionError("Interview is no longer open for feedback")
            cur.execute(
                "SELECT application_status FROM applications WHERE application_id=%s FOR UPDATE",
                (interview["application_id"],)
            )
            application = cur.fetchone()
            if not application or application["application_status"] != "INTERVIEW_SCHEDULED":
                raise InvalidStatusTransitionError(
                    "Application is no longer in the interview stage"
                )
            cur.execute(
                """
                INSERT INTO interview_feedback
                (interview_id, technical_rating, communication_rating,
                 problem_solving_rating, overall_rating, recommendation, remarks, submitted_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    feedback.interview_id,
                    feedback.technical_rating,
                    feedback.communication_rating,
                    feedback.problem_solving_rating,
                    feedback.overall_rating,
                    feedback.recommendation,
                    feedback.remarks or None,
                    changed_by
                )
            )
            cur.execute(
                "UPDATE interview_rounds SET status='COMPLETED' WHERE interview_id=%s",
                (feedback.interview_id,)
            )
            old_status = application["application_status"]
            cur.execute(
                "UPDATE applications SET application_status=%s WHERE application_id=%s",
                (next_status, interview["application_id"])
            )
            cur.execute(
                """
                INSERT INTO application_history
                (application_id, old_status, new_status, remarks, changed_by)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    interview["application_id"],
                    old_status,
                    next_status,
                    f"Interview feedback: {feedback.recommendation}",
                    changed_by
                )
            )
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def set_status(
        self,
        interview_id: int,
        status: str,
        scheduled_date=None,
        scheduled_time=None
    ) -> None:
        con = get_connection()
        try:
            cur = con.cursor(dictionary=True)
            cur.execute(
                """
                SELECT application_id
                FROM interview_rounds
                WHERE interview_id=%s
                FOR UPDATE
                """,
                (interview_id,)
            )
            interview = cur.fetchone()
            if not interview:
                raise LookupError(f"Interview ID {interview_id} not found")
            cur.execute(
                """
                UPDATE interview_rounds
                SET status=%s,
                    scheduled_date=COALESCE(%s, scheduled_date),
                    scheduled_time=COALESCE(%s, scheduled_time)
                WHERE interview_id=%s
                """,
                (status, scheduled_date, scheduled_time, interview_id)
            )
            if status in {"CANCELLED", "NO_SHOW"}:
                cur.execute(
                    """
                    SELECT COUNT(*) AS completed
                    FROM interview_rounds
                    WHERE application_id=%s AND status='COMPLETED'
                    """,
                    (interview["application_id"],)
                )
                completed = cur.fetchone()["completed"]
                restored_status = "INTERVIEWED" if completed else "SHORTLISTED"
                cur.execute(
                    "SELECT application_status FROM applications WHERE application_id=%s FOR UPDATE",
                    (interview["application_id"],)
                )
                old_status = cur.fetchone()["application_status"]
                cur.execute(
                    "UPDATE applications SET application_status=%s WHERE application_id=%s",
                    (restored_status, interview["application_id"])
                )
                cur.execute(
                    """
                    INSERT INTO application_history
                    (application_id, old_status, new_status, remarks, changed_by)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        interview["application_id"],
                        old_status,
                        restored_status,
                        f"Interview marked {status.lower().replace('_', ' ')}",
                        ACTOR_USER_ID
                    )
                )
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()
