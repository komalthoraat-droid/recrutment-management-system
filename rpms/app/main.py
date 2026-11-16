from datetime import date

from mysql.connector import Error as MySQLError

from rpms.dao.application_dao import ApplicationDAO
from rpms.dao.candidate_dao import CandidateDAO
from rpms.dao.company_dao import CompanyDAO
from rpms.dao.interview_dao import InterviewDAO
from rpms.dao.job_dao import JobDAO
from rpms.dao.offer_dao import OfferDAO
from rpms.dao.placement_dao import PlacementDAO
from rpms.exception.exceptions import RPMSException
from rpms.model.candidate import Candidate
from rpms.model.company import Company
from rpms.model.interview import Interview
from rpms.model.interview_feedback import InterviewFeedback
from rpms.model.job import Job
from rpms.service.activity_log_service import ActivityLogService
from rpms.service.application_service import ApplicationService
from rpms.service.candidate_service import CandidateService
from rpms.service.company_service import CompanyService
from rpms.service.eligibility_service import EligibilityService
from rpms.service.interview_service import InterviewService
from rpms.service.job_service import JobService
from rpms.service.offer_service import OfferService
from rpms.service.placement_service import PlacementService
from rpms.service.report_service import ReportService


def _read_date(prompt: str, required: bool = False) -> date | None:
    value = input(prompt).strip()
    if not value and not required:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Enter a date in YYYY-MM-DD format") from exc


def _read_optional_rating(prompt: str) -> float | None:
    value = input(prompt).strip()
    return float(value) if value else None


def print_menu() -> None:
    print(
        "\n==================================\n"
        "RECRUITMENT & PLACEMENT SYSTEM\n"
        "==================================\n"
        "1. Candidate management\n"
        "2. Company management\n"
        "3. Job management\n"
        "4. Applications and shortlisting\n"
        "5. Interviews (schedule/status)\n"
        "6. Record interview feedback\n"
        "7. Offers\n"
        "8. Placements and joining\n"
        "9. Reports\n"
        "0. Exit"
    )


def _candidate_menu(service: CandidateService) -> None:
    action = input("Add, list, or change status? (a/l/u): ").strip().lower()
    if action == "l":
        search = input("Search text (optional): ").strip()
        for candidate in service.get_all_candidates(search=search):
            print(candidate)
        return
    if action == "u":
        service.update_profile_status(
            int(input("Candidate ID: ")),
            input("Profile status (ACTIVE/INACTIVE/ON_HOLD/BLACKLISTED): ")
        )
        print("Candidate status updated.")
        return
    if action != "a":
        raise ValueError("Choose 'a' to add, 'l' to list, or 'u' to change status")
    candidate = Candidate(
        candidate_code=input("Candidate code: "),
        full_name=input("Full name: "),
        email=input("Email: "),
        mobile=input("Mobile (10 digits): "),
        qualification=input("Qualification: "),
        passing_year=int(input("Passing year: ")),
        percentage=float(input("Percentage: ")),
        backlog_count=int(input("Active backlogs: ")),
        primary_technology=input("Primary technology: "),
        skills=[
            item.strip() for item in input("Other skills (comma separated): ").split(",")
            if item.strip()
        ],
    )
    candidate_id = service.add_candidate(candidate)
    print(f"Candidate created. ID = {candidate_id}")


def _company_menu(service: CompanyService) -> None:
    action = input("Add, list, or change status? (a/l/u): ").strip().lower()
    if action == "l":
        for company in service.get_companies(input("Search text (optional): ").strip()):
            print(company)
        return
    if action == "u":
        service.update_status(
            int(input("Company ID: ")),
            input("New status (ACTIVE/INACTIVE): ")
        )
        print("Company status updated.")
        return
    if action != "a":
        raise ValueError("Choose 'a' to add, 'l' to list, or 'u' to change status")
    company = Company(
        company_code=input("Company code: "),
        company_name=input("Company name: "),
        industry=input("Industry: "),
        location=input("Location: "),
        hr_name=input("HR contact name: "),
        hr_email=input("HR email: "),
    )
    print(f"Company created. ID = {service.add_company(company)}")


def _job_menu(service: JobService) -> None:
    action = input("Add, list, or change status? (a/l/u): ").strip().lower()
    if action == "l":
        status = input("Status filter (blank for all): ").strip().upper() or None
        for job in service.get_jobs(status=status):
            print(job)
        return
    if action == "u":
        service.update_status(
            int(input("Job ID: ")),
            input("New status (OPEN/CLOSED/CANCELLED): ")
        )
        print("Job status updated.")
        return
    if action != "a":
        raise ValueError("Choose 'a' to add, 'l' to list, or 'u' to change status")
    job = Job(
        job_code=input("Job code: "),
        company_id=int(input("Company ID: ")),
        job_title=input("Job title: "),
        location=input("Location: "),
        openings=int(input("Number of openings: ")),
        min_package_lpa=float(input("Minimum package (LPA): ") or "0"),
        max_package_lpa=float(input("Maximum package (LPA): ") or "0"),
        min_percentage=float(input("Minimum percentage: ") or "0"),
        min_passing_year=int(input("Minimum passing year (0 for none): ") or "0"),
        max_passing_year=int(input("Maximum passing year (0 for none): ") or "0"),
        max_backlogs=int(input("Maximum active backlogs: ") or "0"),
        qualification_rule=input("Allowed qualifications (comma separated, blank for any): "),
        application_deadline=_read_date("Application deadline (YYYY-MM-DD): ", required=True),
        status=input("Status (OPEN/DRAFT) [OPEN]: ").strip().upper() or "OPEN",
        required_skills=[
            item.strip() for item in input("Required skills (comma separated): ").split(",")
            if item.strip()
        ],
    )
    print(f"Job created. ID = {service.add_job(job)}")


def _application_menu(service: ApplicationService, application_dao: ApplicationDAO) -> None:
    action = input("Apply, list, shortlist, or update status? (a/l/s/u): ").strip().lower()
    if action == "a":
        candidate_id = int(input("Candidate ID: "))
        job_id = int(input("Job ID: "))
        application_id = service.apply_for_job(candidate_id, job_id)
        print(f"Application created. ID = {application_id}")
        return
    if action == "l":
        status = input("Status filter (blank for all): ").strip() or None
        for application in application_dao.find_all(status):
            print(application)
        return
    if action == "s":
        application_id = int(input("Application ID: "))
        service.shortlist(application_id, input("Shortlisting notes: ").strip())
        print("Application shortlisted.")
        return
    if action == "u":
        application_id = int(input("Application ID: "))
        status = input("New status: ")
        remarks = input("Status notes: ")
        service.transition(application_id, status, remarks)
        print("Application status updated.")
        return
    raise ValueError("Choose 'a', 'l', 's', or 'u'")


def _interview_menu(service: InterviewService) -> None:
    action = input("Schedule or update interview status? (s/u): ").strip().lower()
    if action == "u":
        interview_id = int(input("Interview ID: "))
        status = input("New status (RESCHEDULED/CANCELLED/NO_SHOW): ")
        scheduled_date = None
        if status.strip().upper() == "RESCHEDULED":
            scheduled_date = _read_date("New date (YYYY-MM-DD): ", required=True)
        service.update_status(interview_id, status, scheduled_date)
        print("Interview status updated.")
        return
    if action != "s":
        raise ValueError("Choose 's' to schedule or 'u' to update")
    interview = Interview(
        application_id=int(input("Application ID: ")),
        round_type=input("Round type (e.g. TECHNICAL): "),
        mode=input("Mode (ONLINE/OFFLINE/TELEPHONIC): "),
        scheduled_date=_read_date("Interview date (YYYY-MM-DD): ", required=True),
        interviewer_name=input("Interviewer name: "),
        meeting_or_location=input("Meeting link or location: "),
    )
    print(f"Interview scheduled. ID = {service.schedule(interview)}")


def _feedback_menu(service: InterviewService) -> None:
    feedback = InterviewFeedback(
        interview_id=int(input("Interview ID: ")),
        technical_rating=_read_optional_rating("Technical rating (0-5, optional): "),
        communication_rating=_read_optional_rating("Communication rating (0-5, optional): "),
        problem_solving_rating=_read_optional_rating("Problem-solving rating (0-5, optional): "),
        overall_rating=_read_optional_rating("Overall rating (0-5, optional): "),
        recommendation=input("Recommendation (NEXT_ROUND/SELECTED/REJECTED/ON_HOLD): "),
        remarks=input("Feedback notes: "),
    )
    service.submit_feedback(feedback)
    print("Interview feedback recorded.")


def _offer_menu(service: OfferService, offer_dao: OfferDAO) -> None:
    action = input("Create, update status, or list offers? (c/u/l): ").strip().lower()
    if action == "c":
        application_id = int(input("Selected application ID: "))
        designation = input("Designation: ")
        package = float(input("Offered package (LPA): "))
        joining_date = _read_date("Expected joining date (YYYY-MM-DD, optional): ")
        print(
            "Offer created. ID = "
            f"{service.create_offer(application_id, designation, package, joining_date)}"
        )
        return
    if action == "u":
        service.update_status(
            int(input("Offer ID: ")),
            input("New status (ACCEPTED/REJECTED/EXPIRED/WITHDRAWN): ")
        )
        print("Offer status updated.")
        return
    if action == "l":
        for offer in offer_dao.find_all():
            print(offer)
        return
    raise ValueError("Choose 'c' to create, 'u' to update, or 'l' to list")


def _placement_menu(service: PlacementService, placement_dao: PlacementDAO) -> None:
    action = input("Register accepted offer, update joining, or list placements? (r/u/l): ")
    action = action.strip().lower()
    if action == "r":
        offer_id = int(input("Accepted offer ID: "))
        print(f"Placement created. ID = {service.register_accepted_offer(offer_id)}")
        return
    if action == "u":
        placement_id = int(input("Placement ID: "))
        status = input("Joining status (JOINED/NOT_JOINED/DEFERRED/NO_SHOW): ")
        joined_date = _read_date("Actual joining date (YYYY-MM-DD, optional): ")
        service.update_joining_status(placement_id, status, joined_date)
        print("Joining status updated.")
        return
    if action == "l":
        for placement in placement_dao.find_all():
            print(placement)
        return
    raise ValueError("Choose 'r' to register, 'u' to update, or 'l' to list")


def _print_reports(service: ReportService) -> None:
    reports = (
        ("Candidates by technology", service.candidate_count_by_technology()),
        ("Application status summary", service.application_status_summary()),
        ("Placement summary by company", service.placement_summary_by_company()),
        ("Applications by job", service.job_application_summary()),
    )
    for title, rows in reports:
        print(f"\n{title}")
        for row in rows:
            print(row)


def main() -> None:
    candidate_dao = CandidateDAO()
    company_dao = CompanyDAO()
    job_dao = JobDAO()
    application_dao = ApplicationDAO()
    interview_dao = InterviewDAO()
    offer_dao = OfferDAO()
    placement_dao = PlacementDAO()

    candidate_service = CandidateService(candidate_dao)
    company_service = CompanyService(company_dao)
    job_service = JobService(job_dao, company_service)
    application_service = ApplicationService(
        candidate_dao,
        job_dao,
        application_dao,
        EligibilityService()
    )
    interview_service = InterviewService(interview_dao, application_dao)
    offer_service = OfferService(offer_dao, application_dao)
    placement_service = PlacementService(
        placement_dao,
        offer_dao,
        application_dao,
        job_dao
    )
    report_service = ReportService()
    log_service = ActivityLogService()

    actions = {
        "1": lambda: _candidate_menu(candidate_service),
        "2": lambda: _company_menu(company_service),
        "3": lambda: _job_menu(job_service),
        "4": lambda: _application_menu(application_service, application_dao),
        "5": lambda: _interview_menu(interview_service),
        "6": lambda: _feedback_menu(interview_service),
        "7": lambda: _offer_menu(offer_service, offer_dao),
        "8": lambda: _placement_menu(placement_service, placement_dao),
        "9": lambda: _print_reports(report_service),
    }

    while True:
        print_menu()
        choice = input("Enter choice: ").strip()
        if choice == "0":
            print("Application closed.")
            return
        action = actions.get(choice)
        if action is None:
            print("Invalid choice.")
            continue
        try:
            action()
            log_service.log(f"Completed menu action {choice}")
        except (RPMSException, ValueError, RuntimeError, MySQLError, OSError) as exc:
            print(f"ERROR: {exc}")


if __name__ == "__main__":
    main()
