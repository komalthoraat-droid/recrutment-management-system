from rpms.util.db_connection import get_connection

class ReportService:

    def candidate_count_by_technology(self):
        con = get_connection()
        try:
            cur = con.cursor()
            cur.execute(
                '''
                SELECT primary_technology, COUNT(*) AS total
                FROM candidates
                GROUP BY primary_technology
                ORDER BY total DESC
                '''
            )
            return cur.fetchall()
        finally:
            con.close()

    def application_status_summary(self):
        return self._fetch_all(
            """
            SELECT application_status, COUNT(*) AS total
            FROM applications
            GROUP BY application_status
            ORDER BY application_status
            """
        )

    def placement_summary_by_company(self):
        return self._fetch_all(
            """
            SELECT co.company_name, COUNT(p.placement_id) AS placements,
                   ROUND(AVG(p.final_package_lpa), 2) AS average_package_lpa
            FROM companies co
            LEFT JOIN placements p ON p.company_id=co.company_id
                AND p.placement_status='ACTIVE'
            GROUP BY co.company_id, co.company_name
            ORDER BY placements DESC, co.company_name
            """
        )

    def job_application_summary(self):
        return self._fetch_all(
            """
            SELECT j.job_code, j.job_title, co.company_name, j.status,
                   COUNT(a.application_id) AS applications,
                   COALESCE(SUM(a.application_status='SELECTED'), 0) AS selected
            FROM jobs j
            JOIN companies co ON co.company_id=j.company_id
            LEFT JOIN applications a ON a.job_id=j.job_id
            GROUP BY j.job_id, j.job_code, j.job_title, co.company_name, j.status
            ORDER BY applications DESC, j.job_title
            """
        )

    @staticmethod
    def _fetch_all(sql: str):
        con = get_connection()
        try:
            cur = con.cursor(dictionary=True)
            cur.execute(sql)
            return cur.fetchall()
        finally:
            con.close()
