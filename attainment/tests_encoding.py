from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import SurveyTemplate, SurveyQuestion, AcademicYear, Department, Program, Course, Assessment, AssessmentComponent, UserProfile
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
import csv

class SurveyEncodingTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.teacher = User.objects.create_user('teacher2','t2@example.com','pass')
        UserProfile.objects.create(user=self.teacher, role='TEACHER')
        ay = AcademicYear.objects.create(name='2025-26')
        dept = Department.objects.create(name='ECE')
        prog = Program.objects.create(name='B.Tech ECE', department=dept)
        course = Course.objects.create(code='EC101', name='IntroE', department=dept, program=prog, academic_year=ay)
        self.assessment = Assessment.objects.create(name='IA-1', assessment_type='CIA', assessment_category='IA1', course=course, max_marks=100)

    def test_latin1_encoded_survey_upload(self):
        # create template
        st = SurveyTemplate.objects.create(name='Course Exit Enc', survey_type='COURSE', created_by=self.teacher)
        SurveyQuestion.objects.create(template=st, code='CO1', text='CO1?')

        # create latin-1 encoded CSV containing a special char
        rows = [['CO1'], ['Strongly Agree'], ['Agree'], ['Neutral'], ['Disagree']]
        content = "\n".join([','.join(r) for r in rows])
        # encode in cp1252 (windows-1252) to simulate non-utf8
        data = content.encode('cp1252')
        upload_file = SimpleUploadedFile('survey_latin1.csv', data, content_type='text/csv')

        self.client.login(username='teacher2', password='pass')
        url = reverse('upload_survey')
        response = self.client.post(url, {'template': st.id, 'file': upload_file, 'course': self.assessment.course.id})
        # should redirect on success
        self.assertEqual(response.status_code, 302)
        # ensure summary exists
        from .models import SurveyUpload
        su = SurveyUpload.objects.latest('uploaded_at')
        self.assertEqual(su.total_responses, 4)
