from careerpilot.application.errors import ApplicationError


class ApplicationPreparationFailedError(ApplicationError):
    def __init__(
        self,
        message: str = "Application preparation could not be completed.",
    ) -> None:
        super().__init__(message, code="application_preparation_failed")
