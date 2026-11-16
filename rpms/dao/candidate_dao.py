from rpms.model.candidate import Candidate
from rpms.util.db_connection import get_connection


class CandidateDAO:

    def save(self, candidate: Candidate) -> int:
        sql = '''
            INSERT INTO candidates
            (candidate_code, full_name, email, mobile, qualification, passing_year,
             percentage, backlog_count, primary_technology, profile_status, placement_status)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'ACTIVE','NOT_PLACED')
        '''
        con = get_connection()
        try:
            cur = con.cursor()
            cur.execute(sql, (
                candidate.candidate_code,
                candidate.full_name,
                candidate.email,
                candidate.mobile,
                candidate.qualification,
                candidate.passing_year,
                candidate.percentage,
                candidate.backlog_count,
                candidate.primary_technology
            ))
            candidate_id = cur.lastrowid
            self._save_skills(
                cur,
                candidate_id,
                candidate.skills,
                candidate.primary_technology
            )
            con.commit()
            return candidate_id
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def find_by_id(self, candidate_id: int):
        con = get_connection()
        try:
            cur = con.cursor(dictionary=True)
            cur.execute("SELECT * FROM candidates WHERE candidate_id=%s", (candidate_id,))
            row = cur.fetchone()
            if not row:
                return None
            candidate = self._map(row)
            candidate.skills = self._find_skills(cur, candidate_id)
            return candidate
        finally:
            con.close()

    def find_by_email(self, email: str):
        return self._find_one("SELECT * FROM candidates WHERE email=%s", email)

    def find_by_mobile(self, mobile: str):
        return self._find_one("SELECT * FROM candidates WHERE mobile=%s", mobile)

    def _find_one(self, sql: str, value: str):
        con = get_connection()
        try:
            cur = con.cursor(dictionary=True)
            cur.execute(sql, (value,))
            row = cur.fetchone()
            return self._map(row) if row else None
        finally:
            con.close()

    def find_all(self, search: str = "", status: str | None = None):
        clauses = []
        params = []
        if search:
            clauses.append("(full_name LIKE %s OR candidate_code LIKE %s OR email LIKE %s)")
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
        if status:
            clauses.append("profile_status=%s")
            params.append(status.upper())
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        con = get_connection()
        try:
            cur = con.cursor(dictionary=True)
            cur.execute(f"SELECT * FROM candidates{where} ORDER BY candidate_id", tuple(params))
            candidates = [self._map(row) for row in cur.fetchall()]
            self._attach_skills(cur, candidates)
            return candidates
        finally:
            con.close()

    def find_by_technology(self, technology: str):
        con = get_connection()
        try:
            cur = con.cursor(dictionary=True)
            cur.execute(
                "SELECT * FROM candidates WHERE primary_technology=%s ORDER BY full_name",
                (technology,)
            )
            candidates = [self._map(row) for row in cur.fetchall()]
            self._attach_skills(cur, candidates)
            return candidates
        finally:
            con.close()

    def set_profile_status(self, candidate_id: int, status: str) -> bool:
        con = get_connection()
        try:
            cur = con.cursor()
            cur.execute(
                "SELECT 1 FROM candidates WHERE candidate_id=%s",
                (candidate_id,)
            )
            if cur.fetchone() is None:
                return False
            cur.execute(
                "UPDATE candidates SET profile_status=%s WHERE candidate_id=%s",
                (status, candidate_id)
            )
            con.commit()
            return True
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    @staticmethod
    def _save_skills(
        cur,
        candidate_id: int,
        skills: list[str],
        primary_technology: str
    ) -> None:
        for skill in dict.fromkeys(name.strip() for name in skills if name.strip()):
            cur.execute(
                """
                INSERT INTO skills (skill_name)
                VALUES (%s)
                ON DUPLICATE KEY UPDATE skill_id=LAST_INSERT_ID(skill_id)
                """,
                (skill,)
            )
            skill_id = cur.lastrowid
            cur.execute(
                """
                INSERT INTO candidate_skills (candidate_id, skill_id, is_primary)
                VALUES (%s, %s, %s)
                """,
                (candidate_id, skill_id, int(skill.casefold() == primary_technology.casefold()))
            )

    @staticmethod
    def _find_skills(cur, candidate_id: int) -> list[str]:
        cur.execute(
            """
            SELECT s.skill_name
            FROM candidate_skills cs
            JOIN skills s ON s.skill_id=cs.skill_id
            WHERE cs.candidate_id=%s
            ORDER BY s.skill_name
            """,
            (candidate_id,)
        )
        return [row["skill_name"] for row in cur.fetchall()]

    @classmethod
    def _attach_skills(cls, cur, candidates: list[Candidate]) -> None:
        if not candidates:
            return
        ids = [candidate.candidate_id for candidate in candidates]
        placeholders = ",".join(["%s"] * len(ids))
        cur.execute(
            f"""
            SELECT cs.candidate_id, s.skill_name
            FROM candidate_skills cs
            JOIN skills s ON s.skill_id=cs.skill_id
            WHERE cs.candidate_id IN ({placeholders})
            ORDER BY s.skill_name
            """,
            tuple(ids)
        )
        skills_by_candidate: dict[int, list[str]] = {}
        for row in cur.fetchall():
            skills_by_candidate.setdefault(row["candidate_id"], []).append(row["skill_name"])
        for candidate in candidates:
            candidate.skills = skills_by_candidate.get(candidate.candidate_id, [])

    @staticmethod
    def _map(row):
        return Candidate(
            candidate_id=row["candidate_id"],
            candidate_code=row["candidate_code"],
            full_name=row["full_name"],
            email=row["email"],
            mobile=row["mobile"],
            qualification=row["qualification"],
            passing_year=row["passing_year"],
            percentage=float(row["percentage"] or 0),
            backlog_count=row["backlog_count"],
            primary_technology=row["primary_technology"] or "",
            profile_status=row["profile_status"],
            placement_status=row["placement_status"]
        )
