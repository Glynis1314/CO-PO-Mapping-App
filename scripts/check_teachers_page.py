import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coAtttainemnt.settings')
import django
django.setup()
from django.test import Client
c = Client()
ok = c.login(username='admin', password='admin123')
print('LOGIN', ok)
r = c.get('/admin-panel/teachers/')
print('STATUS', r.status_code)
print('TEMPLATE_NAMES', r.templates and [t.name for t in r.templates])
print('CONTENT_HEAD')
print(r.content.decode('utf-8', 'replace')[:2000])
