"""Domain exceptions: all carry messages that are safe to show to the user."""


class PlaceTrackError(Exception):
    pass


class ValidationError(PlaceTrackError):
    def __init__(self, errors):
        self.errors = [errors] if isinstance(errors, str) else list(errors)
        super().__init__("; ".join(self.errors))


class AuthenticationError(PlaceTrackError):
    pass


class AuthorizationError(PlaceTrackError):
    pass


class InvalidTransitionError(PlaceTrackError):
    pass


class DuplicateApplicationError(PlaceTrackError):
    pass


class NotEligibleError(PlaceTrackError):
    def __init__(self, explanations):
        self.explanations = list(explanations)
        super().__init__("Not eligible: " + " ".join(self.explanations))


class NotFoundError(PlaceTrackError):
    pass
