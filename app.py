from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import subprocess
import os
import tempfile
import uuid
import shutil

app = Flask(__name__)
CORS(app)

# Find LibreOffice executable across different systems
def find_libreoffice():
    paths = [
        'libreoffice',
        'soffice',
        '/usr/bin/libreoffice',
        '/usr/bin/soffice',
        '/usr/lib/libreoffice/program/soffice',
        '/opt/libreoffice/program/soffice',
        '/Applications/LibreOffice.app/Contents/MacOS/soffice',  # Mac
        r'C:\Program Files\LibreOffice\program\soffice.exe',      # Windows
    ]
    for path in paths:
        if shutil.which(path) or os.path.exists(path):
            return path
    return None

@app.route('/')
def index():
    lo = find_libreoffice()
    return jsonify({ 'status': 'running', 'libreoffice': lo or 'not found' })

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
    pdf_path = os.path.join(tmp_dir, f'{uuid.uuid4()}.pdf')
    file.save(pdf_path)

    try:
        result = subprocess.run([
            lo_path, '--headless', '--convert-to', 'docx',
            '--outdir', tmp_dir, pdf_path
        ], capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            return jsonify({ 'error': 'Conversion failed', 'details': result.stderr }), 500

        docx_path = pdf_path.replace('.pdf', '.docx')
        if not os.path.exists(docx_path):
            return jsonify({ 'error': 'Output file not found' }), 500

        original_name = file.filename.replace('.pdf', '.docx')
        return send_file(docx_path, as_attachment=True, download_name=original_name,
                         mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')

    except subprocess.TimeoutExpired:
        return jsonify({ 'error': 'Conversion timed out' }), 500
    except Exception as e:
        return jsonify({ 'error': str(e) }), 500
    finally:
        try:
            os.remove(pdf_path)
        except:
            pass

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
