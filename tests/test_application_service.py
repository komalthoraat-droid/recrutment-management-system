import unittest
from datetime import date, timedelta

from rpms.exception.exceptions import InvalidStatusTransitionError
from rpms.model.candidate import Candidate
from rpms.model.job import Job
from rpms.service.application_service import ApplicationService
from rpms.service.eligibility_service import EligibilityService


class FakeCandidateDAO:
    def find_by_id(self, candidate_id):
        return Candidate(
            candidate_id=candidate_id,
            candidate_code="CAN-1",
            full_name="Test Candidate",
            email="test@example.com",
            mobile="1234567890",
            qualification="BE",
            passing_year=date.today().year,
            percentage=80,
            backlog_count=0,
            primary_technology="Python",
            skills=["Python"],
        )


class FakeJobDAO:
    def find_by_id(self, job_id):
        return Job(
            job_id=job_id,
            company_id=1,
            job_title="Developer",
            min_percentage=70,
            max_backlogs=0,
            application_deadline=date.today() + timedelta(days=1),
            required_skills=["Python"],
        )


class FakeApplicationDAO:
    def __init__(self):
        self.saved = []
        self.rows = {}
        self.remarks = {}

    def exists(self, candidate_id, job_id):
        return any(
            app.candidate_id == candidate_id and app.job_id == job_id
            for app in self.saved
        )

    def save(self, application):
        application_id = len(self.saved) + 1
        self.saved.append(application)
        self.rows[application_id] = {"application_status": application.application_status}
        return application_id

    def find_by_id(self, application_id):
        return self.rows.get(application_id)

    def set_status(self, application_id, status, remarks, expected_status=None):
        if expected_status:
            self.assert_current_status(application_id, expected_status)
        self.rows[application_id]["application_status"] = status
        self.remarks[application_id] = remarks

    def assert_current_status(self, application_id, expected_status):
        if self.rows[application_id]["application_status"] != expected_status:
            raise AssertionError("Unexpected application status")


class ApplicationServiceTests(unittest.TestCase):

    def setUp(self):
        self.application_dao = FakeApplicationDAO()
        self.service = ApplicationService(
            FakeCandidateDAO(),
            FakeJobDAO(),
            self.application_dao,
            EligibilityService(),
        )

    def test_application_is_saved_after_eligibility_passes(self):
        application_id = self.service.apply_for_job(1, 2)
        self.assertEqual(application_id, 1)
        self.assertEqual(self.application_dao.saved[0].eligibility_status, "ELIGIBLE")

    def test_shortlisting_advances_status(self):
        application_id = self.service.apply_for_job(1, 2)
        self.service.shortlist(application_id)
        self.assertEqual(
            self.application_dao.rows[application_id]["application_status"],
            "SHORTLISTED",
        )

    def test_invalid_status_transition_is_rejected(self):
        application_id = self.service.apply_for_job(1, 2)
        with self.assertRaises(InvalidStatusTransitionError):
            self.service.transition(application_id, "JOINED")


if __name__ == "__main__":
    unittest.main()
