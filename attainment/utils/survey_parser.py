import csv
from io import TextIOWrapper

LIKERT = {
    'Strongly Agree': 3,
    'Agree': 2,
    'Neutral': 1,
    'Disagree': 0,
}

class SurveyValidationError(Exception):
    pass


def parse_survey_csv(file_obj, template):
    # file_obj is UploadedFile
    # Read raw bytes and attempt decoding using several common encodings
    raw = file_obj.read()
    text = None
    decode_errors = []
    for enc in ('utf-8-sig', 'utf-8', 'cp1252', 'latin-1'):
        try:
            text = raw.decode(enc)
            break
        except Exception as e:
            decode_errors.append((enc, str(e)))
    if text is None:
        # Provide a helpful error message including attempted encodings
        tried = ', '.join([e for e,_ in decode_errors])
        raise SurveyValidationError(f'Unable to decode CSV file. Tried encodings: {tried}. Please re-save the CSV with UTF-8 encoding and try again.')

    lines = [row for row in csv.reader(text.splitlines())]
    rows = lines
    # rewind uploaded file so subsequent save() operations can read it
    try:
        file_obj.seek(0)
    except Exception:
        pass
    if not rows or len(rows) < 1:
        raise SurveyValidationError('CSV must have a header row and at least one response')
    header = [str(h).strip() for h in rows[0]]

    # Expected question codes
    expected = [q.code for q in template.questions.all()]
    # Validate that header columns (ignoring extra columns like timestamp) match expected set
    # Require that all expected questions are present
    missing = [e for e in expected if e not in header]
    if missing:
        raise SurveyValidationError(f'Missing survey question columns: {missing}')

    # Parse rows
    total = 0
    counts = {q: {k:0 for k in LIKERT.keys()} for q in expected}
    errors = []

    for r_idx, row in enumerate(rows[1:], start=2):
        if not any([c for c in row if str(c).strip()!='']):
            # skip empty rows
            continue
        total += 1
        row_map = {header[i]: (str(row[i]).strip() if i < len(row) else '') for i in range(len(header))}
        for q in expected:
            val = row_map.get(q, '').strip()
            if val not in LIKERT:
                errors.append(f'Row {r_idx}: Column {q} has invalid response "{val}"')
            else:
                counts[q][val] += 1

    if errors:
        raise SurveyValidationError('\n'.join(errors))

    # Build summary: for each question compute average score
    summary = {}
    for q in expected:
        total_responses = sum(counts[q].values())
        score_total = sum(LIKERT[k]*counts[q][k] for k in counts[q])
        avg = (score_total / total_responses) if total_responses>0 else 0.0
        summary[q] = {
            'counts': counts[q],
            'total_responses': total_responses,
            'score_total': score_total,
            'average': avg,
        }

    return {
        'header': header,
        'summary': summary,
        'total_responses': total,
    }