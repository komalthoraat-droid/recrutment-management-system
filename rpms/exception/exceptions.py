class RPMSException(Exception):
    """Base class for expected recruitment workflow errors."""


class CandidateNotFoundError(RPMSException):
    pass

class JobNotFoundError(RPMSException):
    pass

class CompanyNotFoundError(RPMSException):
    pass

class ApplicationNotFoundError(RPMSException):
    pass

class DuplicateApplicationError(RPMSException):
    pass

class CandidateNotEligibleError(RPMSException):
    pass

class InvalidStatusTransitionError(RPMSException):
    pass

class InterviewNotFoundError(RPMSException):
    pass

class OfferNotFoundError(RPMSException):
    pass

class PlacementNotFoundError(RPMSException):
    pass
    pass
