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
        '/opt/libreoffice/program/soffice',
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
    if not lo:
        return jsonify({ 'error': 'LibreOffice not found' }), 500
    result = subprocess.run([lo, '--version'], capture_output=True, text=True)
    return jsonify({ 'stdout': result.stdout, 'stderr': result.stderr, 'returncode': result.returncode })

@app.route('/test-convert', methods=['GET'])
def test_convert():
    """Creates a tiny test PDF and converts it to check if pipeline works"""
    lo_path = find_libreoffice()
    if not lo_path:
        return jsonify({ 'error': 'LibreOffice not found' }), 500

    tmp_dir = tempfile.mkdtemp()
    # Create a minimal test text file and convert to docx
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
        return jsonify({ 'error': 'LibreOffice is not installed on the server' }), 500

    tmp_dir = tempfile.mkdtemp()
    safe_name = f"{uuid.uuid4()}.pdf"
    pdf_path = os.path.join(tmp_dir, safe_name)
    file.save(pdf_path)

    try:
        result = subprocess.run([
            lo_path, '--headless', '--convert-to', 'docx',
            '--outdir', tmp_dir, pdf_path
        ], capture_output=True, text=True, timeout=60)

        docx_files = glob.glob(os.path.join(tmp_dir, '*.docx'))
        if not docx_files:
            return jsonify({
                'error': 'Output file not found',
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'files_in_tmp': os.listdir(tmp_dir)
            }), 500

        docx_path = docx_files[0]
        original_name = file.filename.replace('.pdf', '.docx')
        return send_file(
            docx_path,
            as_attachment=True,
            download_name=original_name,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

    except subprocess.TimeoutExpired:
        return jsonify({ 'error': 'Conversion timed out — try a smaller PDF' }), 500
    except Exception as e:
        return jsonify({ 'error': str(e) }), 500
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
