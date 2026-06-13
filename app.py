from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import subprocess
import os
import tempfile
import uuid
import shutil
import glob

app = Flask(__name__)
CORS(app)

def find_libreoffice():
    paths = [
        'libreoffice', 'soffice',
        '/usr/bin/libreoffice', '/usr/bin/soffice',
        '/usr/lib/libreoffice/program/soffice',
    ]
    for path in paths:
        if shutil.which(path) or os.path.exists(path):
            return path
    return None

@app.route('/')
def index():
    lo = find_libreoffice()
    return jsonify({ 'status': 'running', 'libreoffice': lo or 'not found' })

@app.route('/test-lo')
def test_lo():
    lo = find_libreoffice()
    result = subprocess.run([lo, '--version'], capture_output=True, text=True)
    return jsonify({ 'stdout': result.stdout, 'stderr': result.stderr, 'returncode': result.returncode })

@app.route('/test-convert')
def test_convert():
    lo_path = find_libreoffice()
    tmp_dir = tempfile.mkdtemp()
    txt_path = os.path.join(tmp_dir, 'test.txt')
    with open(txt_path, 'w') as f:
        f.write('Hello from PDFly conversion test.')
    try:
        result = subprocess.run([
            lo_path, '--headless', '--convert-to', 'docx',
            '--outdir', tmp_dir, txt_path
        ], capture_output=True, text=True, timeout=60)
        docx_files = glob.glob(os.path.join(tmp_dir, '*.docx'))
        return jsonify({
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'docx_found': len(docx_files) > 0,
            'files_in_tmp': os.listdir(tmp_dir)
        })
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

@app.route('/pdf-to-word', methods=['POST'])
def pdf_to_word():
    if 'file' not in request.files:
        return jsonify({ 'error': 'No file uploaded' }), 400

    file = request.files['file']
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({ 'error': 'Only PDF files accepted' }), 400

    lo_path = find_libreoffice()
    if not lo_path:
        return jsonify({ 'error': 'LibreOffice not found' }), 500

    tmp_dir = tempfile.mkdtemp()
    pdf_path = os.path.join(tmp_dir, f'{uuid.uuid4()}.pdf')
    file.save(pdf_path)

    try:
        # Step 1: Extract text from PDF using pdftotext
        txt_path = pdf_path.replace('.pdf', '.txt')
        txt_result = subprocess.run(
            ['pdftotext', '-layout', pdf_path, txt_path],
            capture_output=True, text=True, timeout=30
        )

        if txt_result.returncode != 0 or not os.path.exists(txt_path):
            # Fallback: use LibreOffice directly on PDF
            result = subprocess.run([
                lo_path, '--headless', '--infilter=writer_pdf_import',
                '--convert-to', 'docx',
                '--outdir', tmp_dir, pdf_path
            ], capture_output=True, text=True, timeout=60)
        else:
            # Step 2: Convert extracted text to docx via LibreOffice
            result = subprocess.run([
                lo_path, '--headless', '--convert-to', 'docx',
                '--outdir', tmp_dir, txt_path
            ], capture_output=True, text=True, timeout=60)

        # Find output docx
        docx_files = glob.glob(os.path.join(tmp_dir, '*.docx'))
        if not docx_files:
            return jsonify({
                'error': 'Output file not found',
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'files': os.listdir(tmp_dir)
            }), 500

        original_name = file.filename.replace('.pdf', '.docx')
        return send_file(
            docx_files[0],
            as_attachment=True,
            download_name=original_name,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

    except subprocess.TimeoutExpired:
        return jsonify({ 'error': 'Conversion timed out' }), 500
    except Exception as e:
        return jsonify({ 'error': str(e) }), 500
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
