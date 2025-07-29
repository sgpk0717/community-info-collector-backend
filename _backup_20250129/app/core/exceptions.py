class AppException(Exception):
    """Base exception for the application"""
    pass

class RedditAPIException(AppException):
    """Exception raised when Reddit API calls fail"""
    pass

class OpenAIAPIException(AppException):
    """Exception raised when OpenAI API calls fail"""
    pass

class SupabaseException(AppException):
    """Exception raised when Supabase operations fail"""
    pass

class ValidationException(AppException):
    """Exception raised when validation fails"""
    pass