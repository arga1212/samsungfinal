from flask import Flask, render_template, request, jsonify, send_file, Blueprint
import google.generativeai as genai
import json
import math
import PyPDF2
import os
import io
import tempfile
from werkzeug.utils import secure_filename
from app.models import db, Quiz, Question, Choice  # Pastikan models diimpor dengan benar
from flask_login import current_user, login_required

# Blueprint untuk quiz
quiz = Blueprint('quiz', __name__)

# Konfigurasi API Gemini
API_KEY = 'AIzaSyDBV4t5y7oNh05oZnQxTYcK3rA1FiBd1Wc'  # Ganti dengan API Key Anda
genai.configure(api_key=API_KEY)

@quiz.route('/quiz')
def index():
    return render_template('quiz.html')

# Fungsi untuk ekstrak teks dari file PDF
def extract_text_from_pdf(file_path):
    with open(file_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text += page.extract_text() + "\n"
    return text

def extract_text_from_file(file_path):
    file_ext = os.path.splitext(file_path)[1].lower()
    
    if file_ext == '.pdf':
        return extract_text_from_pdf(file_path)
    elif file_ext in ['.txt', '.md', '.html', '.htm']:
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='latin-1') as file:
                    return file.read()
            except Exception as e:
                return f"Error: Tidak dapat membaca file dengan encoding yang dikenali. {str(e)}"
    else:
        return "Format file tidak didukung. Harap gunakan PDF, TXT, MD, atau HTML."

def generate_questions(modul_content, jumlah_soal):
    """Menghasilkan soal dari isi modul"""
    model_soal = genai.GenerativeModel(
        'models/gemini-2.0-flash',
        generation_config=genai.types.GenerationConfig(
            temperature=0.2,
            top_p=0.1,
            top_k=40,
            max_output_tokens=4096
        )
    )

    # Distribusi Bloom
    c1_count = math.ceil(jumlah_soal * 0.20)
    c2_count = math.ceil(jumlah_soal * 0.25)
    c3_count = math.ceil(jumlah_soal * 0.25)
    c4_count = math.ceil(jumlah_soal * 0.15)
    c5_count = math.ceil(jumlah_soal * 0.10)
    c6_count = math.floor(jumlah_soal * 0.05)

    prompt_soal = f"""
Gunakan isi modul pembelajaran berikut sebagai satu-satunya sumber informasi untuk membuat soal.

=== MULAI MODUL ===
{modul_content}
=== AKHIR MODUL ===

Buatkan {jumlah_soal} soal pilihan ganda berdasarkan modul pembelajaran di atas.

Instruksi penting:
1. Setiap soal harus memiliki SATU kategori taksonomi Bloom (C1-C6) yang tepat:
    - C1: Mengingat
    - C2: Memahami
    - C3: Menerapkan
    - C4: Menganalisis
    - C5: Mengevaluasi
    - C6: Mencipta
    
2. Distribusikan soal berdasarkan taksonomi Bloom:
    - C1: {c1_count} soal
    - C2: {c2_count} soal
    - C3: {c3_count} soal
    - C4: {c4_count} soal
    - C5: {c5_count} soal
    - C6: {c6_count} soal

3. Setiap soal HARUS memiliki 5 pilihan jawaban (A-E) dengan SATU jawaban benar.

4. Sertakan penjelasan untuk setiap soal, mengapa jawaban tersebut benar dan lainnya salah.

5. Format hasil HARUS dalam JSON seperti ini:
{{
  "soal": [
    {{
      "pertanyaan": "...",
      "kategori_taksonomi": "C1",
      "pilihan": [
        "A. ...",
        "B. ...",
        "C. ...",
        "D. ...",
        "E. ..."
      ],
      "jawaban_benar": "A",
      "penjelasan": "...",
      "taxon": "C1"
    }}
  ]
}}
"""

    try:
        response = model_soal.generate_content(
            prompt_soal,
            request_options={"timeout": 600}
        )
        response_text = response.text.strip()

        # Ambil bagian JSON dari respons
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}')
        if start_idx != -1 and end_idx != -1:
            json_text = response_text[start_idx:end_idx+1]
            hasil_soal = json.loads(json_text)
            return hasil_soal
        else:
            return {"error": "Format JSON tidak valid dalam respons"}
        
    except json.JSONDecodeError as je:
        return {"error": f"Error parsing JSON: {str(je)}", "raw_text": response_text}
    except Exception as e:
        return {"error": f"Error saat menghasilkan soal: {str(e)}"}

@quiz.route('/generate', methods=['POST'])
@login_required
def generate():
    """Endpoint untuk menghasilkan soal dari input dan menyimpannya ke database"""
    input_type = request.form.get('inputType')
    jumlah_soal = int(request.form.get('jumlahSoal', 10))
    
    if input_type == 'text':
        modul_content = request.form.get('modulText', '')
    elif input_type == 'file':
        if 'modulFile' not in request.files:
            return jsonify({"error": "Tidak ada file yang diunggah"})
        file = request.files['modulFile']
        if file.filename == '':
            return jsonify({"error": "Tidak ada file yang dipilih"})
        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(tempfile.gettempdir(), filename)
            file.save(file_path)
            modul_content = extract_text_from_file(file_path)
            try:
                os.unlink(file_path)
            except:
                pass
    else:
        return jsonify({"error": "Tipe input tidak valid"})

    if not modul_content or modul_content.strip() == "":
        return jsonify({"error": "Konten modul kosong"})

    hasil_soal = generate_questions(modul_content, jumlah_soal)
    
    if "error" in hasil_soal:
        return jsonify(hasil_soal)

    # Menyimpan hasil soal ke dalam database
    quiz_title = "Quiz from GPT"
    new_quiz = Quiz(title=quiz_title, user_id=current_user.id)
    db.session.add(new_quiz)
    db.session.flush()  # Flush agar ID quiz dapat diakses

    for soal in hasil_soal.get('soal', []):
        question = Question(
            text=soal['pertanyaan'],
            correct_answer=soal['jawaban_benar'],
            explanation=soal['penjelasan'],
            taxonomy=soal['taxon'],
            quiz_id=new_quiz.id
        )
        db.session.add(question)
        db.session.flush()  # Flush agar ID question dapat diakses

        for choice in soal['pilihan']:
            choice_obj = Choice(
                choice_text=choice,
                question_id=question.id
            )
            db.session.add(choice)

    db.session.commit()  # Simpan perubahan ke database

    return jsonify({"message": "Quiz berhasil disimpan", "quiz_id": new_quiz.id})

@quiz.route('/download', methods=['POST'])
def download():
    """Endpoint untuk mengunduh hasil soal sebagai file JSON"""
    data = request.json
    with tempfile.NamedTemporaryFile(delete=False, suffix='.json', mode='w', encoding='utf-8') as temp:
        json.dump(data, temp, ensure_ascii=False, indent=2)
        temp_file_path = temp.name

    return send_file(
        temp_file_path,
        as_attachment=True,
        download_name='soal_output.json',
        mimetype='application/json'
    )
