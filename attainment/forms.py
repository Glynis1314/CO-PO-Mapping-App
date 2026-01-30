from django import forms
from .models import Assessment, MarksUpload, SurveyUpload, SurveyTemplate, Course, Program

class MarksUploadForm(forms.ModelForm):
    class Meta:
        model = MarksUpload
        fields = ['assessment', 'file']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Optionally, filter assessments to teacher's assigned courses
        if user is not None and hasattr(user, 'userprofile') and user.userprofile.role == 'TEACHER':
            self.fields['assessment'].queryset = Assessment.objects.filter(course__teachercourseassignment__teacher=user)


class SurveyUploadForm(forms.ModelForm):
    class Meta:
        model = SurveyUpload
        fields = ['template', 'file', 'course', 'program']

    def clean(self):
        cleaned = super().clean()
        template = cleaned.get('template')
        course = cleaned.get('course')
        program = cleaned.get('program')
        if template:
            if template.survey_type == 'COURSE' and not course:
                raise forms.ValidationError('Course must be selected for Course Exit surveys.')
            if template.survey_type == 'PROGRAM' and not program:
                raise forms.ValidationError('Program must be selected for Program Exit surveys.')
        return cleaned
