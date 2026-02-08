"""
Decorators for teacher module: course ownership, semester lock enforcement.
"""
from functools import wraps
from django.http import HttpResponseForbidden, Http404
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from attainment.models import Course, TeacherCourseAssignment


def teacher_owns_course(view_func):
    """
    Decorator that checks the logged-in user is assigned to the course
    identified by `course_id` in the URL kwargs.
    Injects `course` into the view's kwargs.
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        course_id = kwargs.get("course_id")
        course = get_object_or_404(Course, pk=course_id)
        if not TeacherCourseAssignment.objects.filter(
            teacher=request.user, course=course
        ).exists():
            html = render_to_string("403.html", request=request)
            return HttpResponseForbidden(html)
        kwargs["course"] = course
        return view_func(request, *args, **kwargs)
    return _wrapped


def semester_unlocked(view_func):
    """
    Decorator that blocks write operations when the course's semester is locked.
    Must be used AFTER teacher_owns_course (since it needs `course` in kwargs).
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        course = kwargs.get("course")
        if course and course.semester and course.semester.is_locked:
            html = render_to_string("403.html", request=request)
            return HttpResponseForbidden(html)
        return view_func(request, *args, **kwargs)
    return _wrapped
