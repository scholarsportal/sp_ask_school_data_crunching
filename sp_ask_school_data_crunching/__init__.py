"""Package for analyzing LibraryH3lp chat data for Scholars Portal Ask service."""

from .analytics.school_analytics import SchoolChatAnalytics, analyze_school

__version__ = "0.1.0"
__all__ = ["SchoolChatAnalytics", "analyze_school"]