from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

from .models import UserProfile, Role, Department, Course, TeacherCourseAssignment


class LoginRedirectTests(TestCase):
    def setUp(self):
        # principal, hod, teacher and admin (is_staff) users
        self.u_principal = User.objects.create_user(username='principal', password='p')
        UserProfile.objects.create(user=self.u_principal, role=Role.PRINCIPAL)

        self.u_hod = User.objects.create_user(username='hod', password='h')
        UserProfile.objects.create(user=self.u_hod, role=Role.HOD)

        self.u_teacher = User.objects.create_user(username='teacher', password='t')
        UserProfile.objects.create(user=self.u_teacher, role=Role.TEACHER)

        self.u_admin = User.objects.create_user(username='admin', password='a', is_staff=True)
        UserProfile.objects.create(user=self.u_admin, role=Role.ADMIN)

    def post_login(self, username, password):
        return self.client.post(reverse('login'), {'username': username, 'password': password})

    def test_principal_redirects_to_principal_dashboard(self):
        resp = self.post_login('principal', 'p')
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('dashboard_principal'), resp['Location'])

    def test_hod_redirects_to_hod_dashboard(self):
        resp = self.post_login('hod', 'h')
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('dashboard_hod'), resp['Location'])

    def test_teacher_redirects_to_teacher_dashboard(self):
        resp = self.post_login('teacher', 't')
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('teacher_dashboard'), resp['Location'])

    def test_admin_redirects_to_admin_dashboard(self):
        resp = self.post_login('admin', 'a')
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('admin_dashboard'), resp['Location'])


class AssignmentConstraintTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name='CS')
        self.course = Course.objects.create(code='CS101', name='Intro', department=self.dept)

        self.teacher1 = User.objects.create_user(username='t1', password='1')
        UserProfile.objects.create(user=self.teacher1, role=Role.TEACHER)

        self.teacher2 = User.objects.create_user(username='t2', password='2')
        UserProfile.objects.create(user=self.teacher2, role=Role.TEACHER)

        self.hod = User.objects.create_user(username='hod2', password='h2')
        UserProfile.objects.create(user=self.hod, role=Role.HOD)

        self.admin = User.objects.create_user(username='admin2', password='a2', is_staff=True)
        UserProfile.objects.create(user=self.admin, role=Role.ADMIN)

    def test_assign_subject_action_blocks_second_teacher(self):
        self.client.login(username='hod2', password='h2')
        # assign first teacher
        resp1 = self.client.post(reverse('assign_subject'), {'course_id': self.course.id, 'teacher_id': self.teacher1.id})
        self.assertEqual(TeacherCourseAssignment.objects.filter(course=self.course).count(), 1)
        self.assertEqual(TeacherCourseAssignment.objects.get(course=self.course).teacher, self.teacher1)

        # attempt to assign second teacher to same course
        resp2 = self.client.post(reverse('assign_subject'), {'course_id': self.course.id, 'teacher_id': self.teacher2.id})
        self.assertEqual(TeacherCourseAssignment.objects.filter(course=self.course).count(), 1)
        # still teacher1
        self.assertEqual(TeacherCourseAssignment.objects.get(course=self.course).teacher, self.teacher1)

    def test_admin_assign_course_blocks_second_teacher(self):
        self.client.login(username='admin2', password='a2')
        # admin assigns first teacher
        resp1 = self.client.post(reverse('admin_assign_course'), {'course_id': self.course.id, 'teacher_id': self.teacher1.id})
        self.assertEqual(TeacherCourseAssignment.objects.filter(course=self.course).count(), 1)

        # admin attempts to assign second teacher
        resp2 = self.client.post(reverse('admin_assign_course'), {'course_id': self.course.id, 'teacher_id': self.teacher2.id})
        self.assertEqual(TeacherCourseAssignment.objects.filter(course=self.course).count(), 1)
        self.assertEqual(TeacherCourseAssignment.objects.get(course=self.course).teacher, self.teacher1)

    def test_db_constraint_prevents_direct_duplicate(self):
        TeacherCourseAssignment.objects.create(teacher=self.teacher1, course=self.course)
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            TeacherCourseAssignment.objects.create(teacher=self.teacher2, course=self.course)
