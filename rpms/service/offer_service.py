import uuid
from datetime import date

from rpms.exception.exceptions import (
    ApplicationNotFoundError,
    InvalidStatusTransitionError,
    OfferNotFoundError,
)
from rpms.model.offer import Offer


class OfferService:

    def __init__(self, offer_dao, application_dao):
        self.offer_dao = offer_dao
        self.application_dao = application_dao

    def create_offer(
        self,
        application_id: int,
        designation: str,
        package_lpa: float,
        expected_joining_date: date | None = None
    ) -> int:
        application = self.application_dao.find_by_id(application_id)
        if not application:
            raise ApplicationNotFoundError(f"Application ID {application_id} not found")
        if application["application_status"] != "SELECTED":
            raise InvalidStatusTransitionError("An offer can only be created for a selected application")
        if self.offer_dao.find_by_application(application_id):
            raise InvalidStatusTransitionError("An offer already exists for this application")
        designation = designation.strip()
        if not designation:
            raise ValueError("Designation is required")
        if package_lpa < 0:
            raise ValueError("Offered package cannot be negative")
        if expected_joining_date and expected_joining_date < date.today():
            raise ValueError("Expected joining date cannot be in the past")
        offer = Offer(
            offer_code="OFF-" + uuid.uuid4().hex[:8].upper(),
            application_id=application_id,
            designation=designation,
            offered_package_lpa=package_lpa,
            offer_date=date.today(),
            expected_joining_date=expected_joining_date
        )
        return self.offer_dao.save(offer)

    def update_status(self, offer_id: int, status: str) -> None:
        offer = self.offer_dao.find_by_id(offer_id)
        if not offer:
            raise OfferNotFoundError(f"Offer ID {offer_id} not found")
        target = status.strip().upper()
        if offer["offer_status"] != "OFFERED" or target not in {
            "ACCEPTED", "REJECTED", "EXPIRED", "WITHDRAWN"
        }:
            raise InvalidStatusTransitionError(
                f"Cannot move offer from {offer['offer_status']} to {target}"
            )
        self.offer_dao.set_status(offer_id, target)
