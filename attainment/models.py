from django.db import models

class ProgrammeOutcome(models.Model):
    # PO1 to PO12 identified by NBA [cite: 6, 148]
    code = models.CharField(max_length=10) # e.g., PO1
    description = models.TextField() # e.g., Engineering knowledge [cite: 22, 114]

    def __str__(self):
        return self.code

class Course(models.Model):
    code = models.CharField(max_length=20) # e.g., 18CSC205J [cite: 271, 527]
    name = models.CharField(max_length=100) # e.g., Operating Systems [cite: 532]
    
    def __str__(self):
        return f"{self.code} - {self.name}"

class CourseOutcome(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    co_number = models.CharField(max_length=10) # e.g., CO1
    description = models.TextField() # e.g., Express fundamental concepts [cite: 175]
    target_proficiency = models.FloatField(default=60.0) # p% [cite: 51, 235]
    attainment_target = models.FloatField(default=70.0) # y% [cigte: 53, 238]
    
    # Mapping to POs (The Articulation Matrix) [cite: 10, 152]
    # In a full app, use a ManyToMany with a 'through' table for correlation levels
    po_mappings = models.ManyToManyField(ProgrammeOutcome, through='COPOMapping')

class COPOMapping(models.Model):
    co = models.ForeignKey(CourseOutcome, on_delete=models.CASCADE)
    po = models.ForeignKey(ProgrammeOutcome, on_delete=models.CASCADE)
    correlation_level = models.IntegerField(choices=[(1, 'Low'), (2, 'Moderate'), (3, 'High')]) # [cite: 41-43, 229]
    
class Assessment(models.Model):
    name = models.CharField(max_length=50) # CIA1, CIA2, etc. [cite: 17, 162]
    course = models.ForeignKey(Course, on_delete=models.CASCADE)

class Question(models.Model):
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE)
    q_number = models.IntegerField()
    max_marks = models.FloatField() # [cite: 273, 337]
    co = models.ForeignKey(CourseOutcome, on_delete=models.CASCADE) # The "Tagging" [cite: 66, 251]

class StudentMark(models.Model):
    student_id = models.CharField(max_length=20) # [cite: 292, 542]
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    marks_obtained = models.FloatField() # [cite: 338]