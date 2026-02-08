"""
Role-based access control decorator.

Usage:
    @login_required
    @role_required('HOD', 'ADMIN')
    def my_view(request): ...
"""
from functools import wraps
from django.http import HttpResponseForbidden
from django.template.loader import render_to_string


def role_required(*allowed_roles):
    """
    Decorator that checks request.user has a UserProfile with role in `allowed_roles`.
    Must be used AFTER @login_required so request.user is authenticated.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            profile = getattr(request.user, "profile", None)
            if profile is None or profile.role not in allowed_roles:
                html = render_to_string("403.html", request=request)
                return HttpResponseForbidden(html)
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator
