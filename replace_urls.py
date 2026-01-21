#!/usr/bin/env python3
"""
replace_urls.py
Safely replace Django {% url 'name' %} tags with static paths in templates/.
Creates backups in templates/backups/.
"""

import re, os, shutil

# customize mapping here
mapping = {
    'index': '/',
    'dashboard_hod': '/hod/dashboard/',
    'dashboard_teacher': '/teacher/dashboard/',
    'dashboard_principal': '/principal/dashboard/',
    'subjects': '/subjects/',
    'assign_subjects': '/assign-subjects/',
    'create_assessment': '/teacher/create-assessment/',
    'assessment_list': '/teacher/assessments/',
    'upload_marks': '/teacher/upload-marks/',
    'co_mapping': '/teacher/co-mapping/',
    'po_mapping': '/teacher/po-mapping/',
    'thresholds': '/teacher/thresholds/',
    'attainment_report': '/reports/attainment/',
    'evidence_upload': '/evidence/',
    'import_sample': '/import-samples/',
    'settings_users': '/settings/users/',
    'samples': '/samples/',
}

TEMPLATES_DIR = 'templates'
BACKUP_DIR = os.path.join(TEMPLATES_DIR, 'backups')

if not os.path.isdir(TEMPLATES_DIR):
    print(f"Error: '{TEMPLATES_DIR}' not found. Run this script from project root.")
    exit(1)

os.makedirs(BACKUP_DIR, exist_ok=True)

# Matches {% url 'name' %} or {% url "name" %}
pattern_single = re.compile(r"{%\s*url\s*'([^']+)'\s*%}")
pattern_double = re.compile(r'{%\s*url\s*"([^"]+)"\s*%}')

def replace_in_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    new_text = text

    # find all single-quoted url tags and replace if in mapping
    def _repl_single(m):
        name = m.group(1)
        return mapping.get(name, m.group(0))  # keep original if mapping not found

    # same for double-quoted
    def _repl_double(m):
        name = m.group(1)
        return mapping.get(name, m.group(0))

    new_text = pattern_single.sub(_repl_single, new_text)
    new_text = pattern_double.sub(_repl_double, new_text)

    if new_text != text:
        # backup
        relpath = os.path.relpath(path, TEMPLATES_DIR)
        backup_path = os.path.join(BACKUP_DIR, relpath)
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        shutil.copy2(path, backup_path)
        # write new file
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_text)
        print(f"Updated: {path} (backup saved to {backup_path})")
    else:
        print(f"No change: {path}")

# walk templates dir
for root, dirs, files in os.walk(TEMPLATES_DIR):
    for file in files:
        if file.endswith('.html'):
            replace_in_file(os.path.join(root, file))

print("Done.")