"""
Authentication views: login, logout, post-login role redirect.
"""
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Role


def login_view(request):
    """
    Renders the login form on GET.
    Authenticates the user on POST and redirects based on role.
    """
    if request.user.is_authenticated:
        return redirect(_role_redirect(request.user))

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        if not username or not password:
            messages.error(request, "Username and password are required.")
            return render(request, "auth/login.html")

        user = authenticate(request, username=username, password=password)
        if user is None:
            messages.error(request, "Invalid username or password.")
            return render(request, "auth/login.html")

        login(request, user)

        # Redirect to ?next= if present, otherwise role-based dashboard
        next_url = request.GET.get("next") or request.POST.get("next")
        if next_url:
            return redirect(next_url)
        return redirect(_role_redirect(user))

    return render(request, "auth/login.html")


def logout_view(request):
    """Log out and redirect to login page."""
    logout(request)
    messages.info(request, "You have been signed out.")
    return redirect("login")


def _role_redirect(user):
    """Return the dashboard name based on UserProfile.role (preferred),
    then fall back to is_staff/groups for backward compatibility.
    """
    profile = getattr(user, "profile", None)
    if profile:
        if profile.role == Role.PRINCIPAL:
            return "dashboard_principal"
        if profile.role == Role.HOD:
            return "dashboard_hod"
        if profile.role == Role.TEACHER:
            return "teacher_dashboard"
        if profile.role == Role.ADMIN:
            return "admin_dashboard"

    # Backwards-compat / fallback checks
    if user.is_staff:
        return "admin_dashboard"
    if user.groups.filter(name="Principal").exists():
        return "dashboard_principal"
    if user.groups.filter(name="HOD").exists():
        return "dashboard_hod"
    if user.groups.filter(name="Teacher").exists():
        return "teacher_dashboard"

    return "index"
