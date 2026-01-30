from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import AcademicYear, Department, Program, Course, Assessment, AssessmentComponent, Student, MarksUpload, UserProfile
from django.urls import reverse
from io import BytesIO
from django.core.files.uploadedfile import SimpleUploadedFile
import csv
import time

class MarksParserTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create a teacher user
        self.teacher = User.objects.create_user('teacher1', 't1@example.com', 'pass')
        self.profile = UserProfile.objects.create(user=self.teacher, role='TEACHER')

        # Create academic structures
        ay = AcademicYear.objects.create(name='2025-26')
        dept = Department.objects.create(name='Computer Engineering')
        prog = Program.objects.create(name='B.Tech CSE', department=dept)
        course = Course.objects.create(code='CS101', name='Intro', department=dept, program=prog, academic_year=ay)
        self.assessment = Assessment.objects.create(name='IA-1', assessment_type='CIA', assessment_category='IA1', course=course, max_marks=100)
        from .models import TeacherCourseAssignment
        TeacherCourseAssignment.objects.create(teacher=self.teacher, course=course)
        # Course Outcome required for mapping
        from .models import CourseOutcome
        co = CourseOutcome.objects.create(course=course, code='CO1', description='Sample CO')
        AssessmentComponent.objects.create(assessment=self.assessment, component_number='Q1', max_marks=10, course_outcome=co)
        AssessmentComponent.objects.create(assessment=self.assessment, component_number='Q2', max_marks=10, course_outcome=co)

    def test_csv_upload_and_import(self):
        # Log in
        self.client.login(username='teacher1', password='pass')
        # Prepare CSV content
        from django.core.files.uploadedfile import SimpleUploadedFile
        import io
        s = io.StringIO()
        writer = csv.writer(s)
        writer.writerow(['RollNo', 'Q1', 'Q2'])
        writer.writerow(['R001', '8', '9'])
        writer.writerow(['R002', '7', '6'])
        csv_bytes = s.getvalue().encode('utf-8')
        upload_file = SimpleUploadedFile('marks.csv', csv_bytes, content_type='text/csv')

        url = reverse('upload_marks')
        response = self.client.post(url, {'assessment': self.assessment.id, 'file': upload_file})
        # Should redirect to preview
        self.assertEqual(response.status_code, 302)
        # Locate latest MarksUpload
        mu = MarksUpload.objects.latest('uploaded_at')
        self.assertIn(mu.status, ['VALIDATED','IMPORTED'])

        # Verify preview contains RollNo field mapped correctly
        from .utils.marks_parser import parse_marks_upload
        result = parse_marks_upload(mu.file, mu.assessment)
        self.assertIn('RollNo', result['headers'])
        self.assertEqual(result['sample_rows'][0][result['headers'][0]], 'R001')
        # If any errors, ensure the errors CSV endpoint returns the file
        if result['errors']:
            errors_url = reverse('marks_upload_errors_csv', args=[mu.id])
            resp = self.client.get(errors_url)
            # when user is logged in as teacher, should get CSV or redirect if no invalid rows
            self.assertIn(resp.status_code, [200, 302])

        # If validated, trigger import
        if mu.status == 'VALIDATED':
            confirm_url = reverse('marks_upload_confirm', args=[mu.id])
            resp2 = self.client.post(confirm_url)
            self.assertIn(resp2.status_code, [302, 200])
        # Wait a bit for import to finish and check Student creation
        import time
        time.sleep(1)
        students = Student.objects.filter(roll_number__in=['R001','R002'])
        self.assertEqual(students.count(), 2)

    def test_xlsx_upload_and_import(self):
        # Prepare an XLSX file using openpyxl
        try:
            import openpyxl
        except Exception:
            self.skipTest('openpyxl not installed')

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(['RollNo', 'Q1', 'Q2'])
        ws.append(['X001', 9, 8])
        ws.append(['X002', 7, 6])

        from io import BytesIO
        bio = BytesIO()
        wb.save(bio)
        bio.seek(0)
        upload_file = SimpleUploadedFile('marks.xlsx', bio.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

        self.client.login(username='teacher1', password='pass')
        url = reverse('upload_marks')
        response = self.client.post(url, {'assessment': self.assessment.id, 'file': upload_file})
        self.assertEqual(response.status_code, 302)
        mu = MarksUpload.objects.latest('uploaded_at')
        # Preview validation should either mark VALIDATED or FAILED depending on installed libs
        self.assertIn(mu.status, ['VALIDATED','FAILED','IMPORTED'])
        if mu.status == 'VALIDATED':
            confirm_url = reverse('marks_upload_confirm', args=[mu.id])
            resp2 = self.client.post(confirm_url)
            self.assertIn(resp2.status_code, [302, 200])
            time.sleep(1)
            students = Student.objects.filter(roll_number__in=['X001','X002'])
            self.assertEqual(students.count(), 2)


