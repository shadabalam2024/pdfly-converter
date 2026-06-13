from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import subprocess
import os
import tempfile
import uuid

app = Flask(__name__)
CORS(app)  # Allow requests from your website

@app.route('/')
def index():
    return jsonify({ 'status': 'PDFly Converter API is running' })

@app.route('/pdf-to-word', methods=['POST'])
def pdf_to_word():
    if 'file' not in request.files:
        return jsonify({ 'error': 'No file uploaded' }), 400

    file = request.files['file']
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({ 'error': 'Only PDF files are accepted' }), 400

    # Save uploaded PDF to a temp folder
    tmp_dir = tempfile.mkdtemp()
    pdf_path = os.path.join(tmp_dir, f'{uuid.uuid4()}.pdf')
    file.save(pdf_path)

    try:
        # Use LibreOffice to convert PDF → DOCX
        result = subprocess.run([
            'libreoffice', '--headless', '--convert-to', 'docx',
            '--outdir', tmp_dir, pdf_path
        ], capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            return jsonify({ 'error': 'Conversion failed', 'details': result.stderr }), 500

        # Find the output .docx file
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
        # Cleanup temp files
        try:
            os.remove(pdf_path)
        except:
            pass

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
