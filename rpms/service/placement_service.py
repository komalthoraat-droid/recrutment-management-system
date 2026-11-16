from datetime import date

from rpms.exception.exceptions import (
    ApplicationNotFoundError,
    InvalidStatusTransitionError,
    JobNotFoundError,
    OfferNotFoundError,
    PlacementNotFoundError,
)
from rpms.model.placement import Placement


class PlacementService:

    def __init__(self, placement_dao, offer_dao, application_dao, job_dao):
        self.placement_dao = placement_dao
        self.offer_dao = offer_dao
        self.application_dao = application_dao
        self.job_dao = job_dao

    def register_accepted_offer(self, offer_id: int) -> int:
        offer = self.offer_dao.find_by_id(offer_id)
        if not offer:
            raise OfferNotFoundError(f"Offer ID {offer_id} not found")
        if offer["offer_status"] != "ACCEPTED":
            raise InvalidStatusTransitionError("A placement requires an accepted offer")
        if self.placement_dao.find_by_offer(offer_id):
            raise InvalidStatusTransitionError("This offer already has a placement record")
        application = self.application_dao.find_by_id(offer["application_id"])
        if not application:
            raise ApplicationNotFoundError(
                f"Application ID {offer['application_id']} not found"
            )
        job = self.job_dao.find_by_id(application["job_id"])
        if not job:
            raise JobNotFoundError(f"Job ID {application['job_id']} not found")
        placement = Placement(
            candidate_id=application["candidate_id"],
            company_id=job.company_id,
            job_id=job.job_id,
            offer_id=offer_id,
            designation=offer["designation"],
            final_package_lpa=float(offer["offered_package_lpa"]),
            expected_joining_date=offer["expected_joining_date"]
        )
        return self.placement_dao.create(placement)

    def update_joining_status(
        self,
        placement_id: int,
        status: str,
        actual_joining_date: date | None = None
    ) -> None:
        placement = self.placement_dao.find_by_id(placement_id)
        if not placement:
            raise PlacementNotFoundError(f"Placement ID {placement_id} not found")
        target = status.strip().upper()
        allowed = {
            "PENDING": {"JOINED", "NOT_JOINED", "DEFERRED", "NO_SHOW"},
            "DEFERRED": {"JOINED", "NOT_JOINED", "NO_SHOW"},
        }
        if target not in allowed.get(placement["joining_status"], set()):
            raise InvalidStatusTransitionError(
                f"Cannot move placement from {placement['joining_status']} to {target}"
            )
        if target == "JOINED" and actual_joining_date is None:
            actual_joining_date = date.today()
        if target != "JOINED" and actual_joining_date is not None:
            raise ValueError("Actual joining date is only valid when status is JOINED")
        self.placement_dao.update_joining(placement_id, target, actual_joining_date)
