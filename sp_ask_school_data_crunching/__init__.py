"""Package for analyzing LibraryH3lp chat data for Scholars Portal Ask service."""

from .analytics import (
    SchoolChatAnalytics,
    analyze_school,
    ServiceAnalytics,
    analyze_service,
    DateRangeTrendAnalysis,
    analyze_date_range_trends
)

__version__ = "0.1.0"

__all__ = [
    'SchoolChatAnalytics',
    'analyze_school',
    'ServiceAnalytics',
    'analyze_service',
    'DateRangeTrendAnalysis',
    'analyze_date_range_trends'
]