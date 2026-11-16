from datetime import date

from rpms.model.job import Job
from rpms.util.db_connection import ACTOR_USER_ID, get_connection

class JobDAO:

    def save(self, job: Job, created_by: int = ACTOR_USER_ID) -> int:
        con = get_connection()
        try:
            cur = con.cursor()
            cur.execute(
                """
                INSERT INTO jobs
                (job_code, company_id, job_title, location, openings, min_package_lpa,
                 max_package_lpa, min_percentage, min_passing_year, max_passing_year,
                 max_backlogs, qualification_rule, posted_date, application_deadline,
                 status, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    job.job_code,
                    job.company_id,
                    job.job_title,
                    job.location,
                    job.openings,
                    job.min_package_lpa or None,
                    job.max_package_lpa or None,
                    job.min_percentage,
                    job.min_passing_year or None,
                    job.max_passing_year or None,
                    job.max_backlogs,
                    job.qualification_rule or None,
                    date.today(),
                    job.application_deadline,
                    job.status,
                    created_by
                )
            )
            job_id = cur.lastrowid
            self._save_skills(cur, job_id, job.required_skills)
            con.commit()
            return job_id
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def find_by_id(self, job_id: int):
        con = get_connection()
        try:
            cur = con.cursor(dictionary=True)
            cur.execute(
                """
                SELECT j.*, c.status AS company_status
                FROM jobs j
                JOIN companies c ON c.company_id=j.company_id
                WHERE j.job_id=%s
                """,
                (job_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            job = self._map(row)
            job.required_skills = self._find_skills(cur, job_id)
            return job
        finally:
            con.close()

    def find_open_jobs(self, search: str = ""):
        params = []
        where = "WHERE j.status='OPEN'"
        if search:
            where += " AND (j.job_title LIKE %s OR j.job_code LIKE %s OR j.location LIKE %s)"
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
        con = get_connection()
        try:
            cur = con.cursor(dictionary=True)
            cur.execute(
                f"""
                SELECT j.*, c.status AS company_status
                FROM jobs j
                JOIN companies c ON c.company_id=j.company_id
                {where}
                ORDER BY j.job_id
                """,
                tuple(params)
            )
            jobs = [self._map(row) for row in cur.fetchall()]
            self._attach_skills(cur, jobs)
            return jobs
        finally:
            con.close()

    def find_all(self, search: str = "", status: str | None = None):
        clauses = []
        params = []
        if search:
            clauses.append("(j.job_title LIKE %s OR j.job_code LIKE %s OR j.location LIKE %s)")
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
        if status:
            clauses.append("j.status=%s")
            params.append(status.upper())
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        con = get_connection()
        try:
            cur = con.cursor(dictionary=True)
            cur.execute(
                f"""
                SELECT j.*, c.status AS company_status
                FROM jobs j
                JOIN companies c ON c.company_id=j.company_id
                {where}
                ORDER BY j.job_id
                """,
                tuple(params)
            )
            jobs = [self._map(row) for row in cur.fetchall()]
            self._attach_skills(cur, jobs)
            return jobs
        finally:
            con.close()

    def set_status(self, job_id: int, status: str) -> bool:
        con = get_connection()
        try:
            cur = con.cursor()
            cur.execute("SELECT 1 FROM jobs WHERE job_id=%s", (job_id,))
            if cur.fetchone() is None:
                return False
            cur.execute(
                "UPDATE jobs SET status=%s WHERE job_id=%s",
                (status, job_id)
            )
            con.commit()
            return True
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    @staticmethod
    def _save_skills(cur, job_id: int, skills: list[str]) -> None:
        for skill in dict.fromkeys(name.strip() for name in skills if name.strip()):
            cur.execute(
                """
                INSERT INTO skills (skill_name)
                VALUES (%s)
                ON DUPLICATE KEY UPDATE skill_id=LAST_INSERT_ID(skill_id)
                """,
                (skill,)
            )
            cur.execute(
                "INSERT INTO job_skills (job_id, skill_id, mandatory_flag) VALUES (%s, %s, 1)",
                (job_id, cur.lastrowid)
            )

    @staticmethod
    def _find_skills(cur, job_id: int) -> list[str]:
        cur.execute(
            """
            SELECT s.skill_name
            FROM job_skills js
            JOIN skills s ON s.skill_id=js.skill_id
            WHERE js.job_id=%s AND js.mandatory_flag=1
            ORDER BY s.skill_name
            """,
            (job_id,)
        )
        return [row["skill_name"] for row in cur.fetchall()]

    @classmethod
    def _attach_skills(cls, cur, jobs: list[Job]) -> None:
        if not jobs:
            return
        ids = [job.job_id for job in jobs]
        placeholders = ",".join(["%s"] * len(ids))
        cur.execute(
            f"""
            SELECT js.job_id, s.skill_name
            FROM job_skills js
            JOIN skills s ON s.skill_id=js.skill_id
            WHERE js.job_id IN ({placeholders}) AND js.mandatory_flag=1
            ORDER BY s.skill_name
            """,
            tuple(ids)
        )
        skills_by_job: dict[int, list[str]] = {}
        for row in cur.fetchall():
            skills_by_job.setdefault(row["job_id"], []).append(row["skill_name"])
        for job in jobs:
            job.required_skills = skills_by_job.get(job.job_id, [])

    @staticmethod
    def _map(row):
        return Job(
            job_id=row["job_id"],
            job_code=row["job_code"],
            company_id=row["company_id"],
            job_title=row["job_title"],
            location=row["location"],
            openings=row["openings"],
            min_package_lpa=float(row["min_package_lpa"] or 0),
            max_package_lpa=float(row["max_package_lpa"] or 0),
            min_percentage=float(row["min_percentage"] or 0),
            min_passing_year=row["min_passing_year"] or 0,
            max_passing_year=row["max_passing_year"] or 0,
            max_backlogs=row["max_backlogs"],
            application_deadline=row["application_deadline"],
            status=row["status"],
            qualification_rule=row["qualification_rule"] or "",
            company_status=row.get("company_status", "ACTIVE")
        )
