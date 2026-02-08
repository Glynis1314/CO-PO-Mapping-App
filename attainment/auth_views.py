"""
Authentication views: login, logout, post-login role redirect.
"""
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages


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
    """Return the URL name for the user's dashboard based on their role."""
    profile = getattr(user, "profile", None)
    if profile is None:
        return "index"

    role = profile.role
    if role == "ADMIN":
        return "dashboard_principal"
    elif role == "HOD":
        return "dashboard_hod"
    elif role == "TEACHER":
        return "teacher_dashboard"
    return "index"
