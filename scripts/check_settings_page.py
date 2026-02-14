import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','coAtttainemnt.settings')
import django
django.setup()
from django.template import loader, TemplateSyntaxError
from django.test import RequestFactory
from django.contrib.auth.models import User
import attainment.admin_views as av

# compile template
try:
    loader.get_template('admin_panel/settings.html')
    print('TEMPLATE COMPILE: OK')
except TemplateSyntaxError as e:
    print('TEMPLATE SYNTAX ERROR:', e)
    raise

# simulate request as admin using RequestFactory
rf = RequestFactory()
req = rf.get('/admin-panel/settings/')
try:
    admin = User.objects.get(username='admin')
except User.DoesNotExist:
    print('ADMIN USER NOT FOUND (run seed_users)')
    raise SystemExit(1)
req.user = admin
resp = av.admin_settings(req)
print('VIEW CALL STATUS:', getattr(resp, 'status_code', 'no-status'))
if hasattr(resp, 'content'):
    print(resp.content.decode('utf-8')[:2000])
