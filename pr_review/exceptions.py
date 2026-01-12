"""
Custom exceptions for the PR Review System
"""


class PRReviewError(Exception):
    """Base exception for PR Review System errors"""
    pass


class GitHubAPIError(PRReviewError):
    """Raised when GitHub API requests fail"""
    
    def __init__(self, message: str, status_code: int = None, response: dict = None):
        self.status_code = status_code
        self.response = response
        super().__init__(message)


class MetricsCalculationError(PRReviewError):
    """Raised when metrics calculation fails"""
    pass


class AILabelingError(PRReviewError):
    """Raised when AI labeling fails"""
    pass


class ReviewerAssignmentError(PRReviewError):
    """Raised when reviewer assignment fails"""
    pass


class DiscordNotificationError(PRReviewError):
    """Raised when Discord notification fails"""
    pass


class ConfigurationError(PRReviewError):
    """Raised when configuration is invalid or missing"""
    pass


class ValidationError(PRReviewError):
    """Raised when input validation fails"""
    pass
