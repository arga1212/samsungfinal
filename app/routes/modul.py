from flask import Blueprint, request, render_template, flash, redirect, url_for, session
from flask_login import login_required
from ..models import User, Transkrip, Summarize, Modul
from .. import db
import google.generativeai as genai
import json

# Konfigurasi Gemini AI
GOOGLE_API_KEY = 'AIzaSyDBV4t5y7oNh05oZnQxTYcK3rA1FiBd1Wc'
genai.configure(api_key=GOOGLE_API_KEY)

modul_bp = Blueprint('modul', __name__)

def clean_json_output(text):
    try:
        teks = text.replace('```json', '').replace('```', '')
        teks = teks.replace('~~~json', '').replace('~~~', '')
        return teks.strip()
    except Exception as e:
        flash(f"Error saat membersihkan output: {str(e)}", 'error')
        return ""

@modul_bp.route('/generate-modul/<int:transkrip_id>', methods=['GET', 'POST'])
def generate_modul(transkrip_id):
    user_id = session.get('user_id')
    if not user_id:
        flash("Silakan login terlebih dahulu", "warning")
        return redirect(url_for('auth.login'))

    transkrip = Transkrip.query.filter_by(id=transkrip_id, user_id=user_id).first_or_404()

    if not transkrip.teks:
        flash('Teks transkrip kosong', 'error')
        return redirect(url_for('upload.view_transkrip', transkrip_id=transkrip_id))

    model_modul = genai.GenerativeModel('models/gemini-2.0-flash')

    prompt_modul = """
    Buatkan modul pembelajaran dari materi berikut. Output HARUS dalam format JSON murni seperti contoh berikut dan SEMUA field wajib diisi:

    {
      "judul_modul": "Judul modul sesuai topik",
      "deskripsi_singkat": "Penjelasan ringkas mengenai modul",
      "Bab": [
        {
          "Sub_Bab": "Nama sub bab",
          "isi": "Isi sub bab, terdiri dari minimal 3 paragraf yang dipisah dengan <br>"
        },
        {
          "Sub_Bab": "Sub bab kedua",
          "isi": "..."
        }
      ],
      "rangkuman": "Kesimpulan dan penutup dari seluruh materi"
    }

    Pastikan modul terdiri dari minimal 3 sub bab, setiap sub bab minimal 3 paragraf yang dipisahkan dengan <br>. Semua data dikemas dalam satu objek JSON seperti contoh.
    """

    try:
        response = model_modul.generate_content(
            [prompt_modul, transkrip.teks],
            request_options={"timeout": 600}
        )

        teks_modul = clean_json_output(response.text.strip())

        try:
            modul_json = json.loads(teks_modul)
            modul_text = json.dumps(modul_json, ensure_ascii=False, indent=2)
            
            new_modul = Modul(
                data_modul=modul_text,
                transkrip_id=transkrip_id,
                user_id=user_id
            )
            db.session.add(new_modul)
            db.session.commit()

            flash('Modul berhasil dibuat', 'success')
            return redirect(url_for('modul.show_modul', modul_id=new_modul.id))
            
        except json.JSONDecodeError:
            flash('Gagal parsing JSON dari output Gemini', 'error')
            return redirect(url_for('upload.view_transkrip', transkrip_id=transkrip_id))

    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('upload.view_transkrip', transkrip_id=transkrip_id))


@modul_bp.route('/show_modul/<int:modul_id>')
@login_required
def show_modul(modul_id):
    user_id = session.get('user_id')
    modul = Modul.query.filter_by(id=modul_id, user_id=user_id).first_or_404()

    transkrip = Transkrip.query.get(modul.transkrip_id)

    try:
        modul_data = json.loads(modul.data_modul)
    except json.JSONDecodeError:
        modul_data = {"error": "Format JSON tidak valid"}

    return render_template('show_modul.html', 
                           modul=modul_data, 
                           modul_obj=modul, 
                           transkrip=transkrip)
