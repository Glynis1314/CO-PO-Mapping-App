import csv
from io import TextIOWrapper

from attainment.models import AssessmentComponent


class MarksValidationError(Exception):
    pass


def parse_csv_file(file_obj):
    # file_obj is an UploadedFile; decode as text
    wrapper = TextIOWrapper(file_obj.file, encoding='utf-8-sig')
    reader = csv.reader(wrapper)
    rows = list(reader)
    return rows


def parse_xlsx_file(file_obj):
    # Import openpyxl at runtime so installs after server start are recognized
    try:
        import openpyxl
    except Exception:
        raise MarksValidationError('openpyxl is required to parse Excel files')

    wb = openpyxl.load_workbook(file_obj.file, read_only=True, data_only=True)
    ws = wb.active
    rows = []
    for row in ws.iter_rows(values_only=True):
        rows.append([cell if cell is not None else '' for cell in row])
    return rows


def parse_marks_upload(uploaded_file, assessment):
    """
    Parse and validate a marks upload file for the given assessment.
    Returns a dict with keys:
    - headers: list
    - sample_rows: list of dicts {roll, Q1: value, ...}
    - errors: list of error strings
    - metadata: dict with counts and validation summary
    """
    filename = uploaded_file.name.lower()
    if filename.endswith('.csv'):
        rows = parse_csv_file(uploaded_file)
    elif filename.endswith('.xlsx') or filename.endswith('.xlsm'):
        rows = parse_xlsx_file(uploaded_file)
    else:
        raise MarksValidationError('Unsupported file format. Use CSV or XLSX.')

    if not rows or len(rows) < 2:
        raise MarksValidationError('File must have header row and at least one student row')

    header = [str(h).strip() for h in rows[0]]
    errors = []

    # Header must start with RollNo (case-insensitive)
    if len(header) < 2 or header[0].lower() != 'rollno':
        errors.append('First column must be RollNo')

    # Map expected components
    components = AssessmentComponent.objects.filter(assessment=assessment)
    component_map = {c.component_number: c for c in components}

    # Check mapping completeness (every component has linked CO by DB design)
    if not components.exists():
        errors.append('Assessment has no components defined')

    # Validate that all question IDs in header exist in components
    missing_components = [h for h in header[1:] if h not in component_map]
    if missing_components:
        errors.append(f'Missing question IDs: {missing_components}')

    sample_rows = []
    row_errors = []
    total_students = 0

    for r_idx, row in enumerate(rows[1:1+200]):  # preview only first 200
        total_students += 1
        # Normalize row length to header length
        row = [str(c).strip() if c is not None else '' for c in row]
        while len(row) < len(header):
            row.append('')
        roll = row[0]
        # Include both a normalized 'roll' key and the exact header key (e.g., 'RollNo') so templates can use either
        row_dict = {header[0]: roll, 'roll': roll}
        for col_idx, colname in enumerate(header[1:], start=1):
            val = row[col_idx] if col_idx < len(row) else ''
            if val == '':
                val_num = 0.0
            else:
                try:
                    val_num = float(val)
                except ValueError:
                    val_num = None
            row_dict[colname] = val_num
            # validation check
            if colname in component_map and val_num is not None:
                comp = component_map[colname]
                if val_num > comp.max_marks:
                    row_errors.append(f'Row {r_idx+2} ({roll}): Column {colname} value {val_num} exceeds max {comp.max_marks}')
            elif colname in component_map and val_num is None:
                row_errors.append(f'Row {r_idx+2} ({roll}): Column {colname} contains non-numeric value')
        sample_rows.append(row_dict)

    # Build metadata
    metadata = {
        'header': header,
        'component_list': list(component_map.keys()),
        'sample_count': total_students,
    }

    validated = not errors and not row_errors

    return {
        'headers': header,
        'sample_rows': sample_rows,
        'errors': errors + row_errors,
        'validated': validated,
        'metadata': metadata,
    }