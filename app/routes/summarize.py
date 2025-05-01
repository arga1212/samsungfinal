from flask import Blueprint, request, redirect, url_for, flash, render_template, session
from ..models import User, Transkrip, Summarize, Modul
from .. import db
import google.generativeai as genai
import json

# Inisialisasi blueprint
summarize_bp = Blueprint('summarize', __name__)

# Konfigurasi API
GOOGLE_API_KEY = 'AIzaSyDBV4t5y7oNh05oZnQxTYcK3rA1FiBd1Wc'
genai.configure(api_key=GOOGLE_API_KEY)

@summarize_bp.route('/summarize/<int:transkrip_id>', methods=['GET', 'POST'])
def summarize(transkrip_id):
    user_id = session.get('user_id')
    if not user_id:
        flash("Silakan login terlebih dahulu", 'warning')
        return redirect(url_for('auth.login'))

    # Ambil transkrip berdasarkan transkrip_id dan user_id
    transkrip = Transkrip.query.filter_by(id=transkrip_id, user_id=user_id).first_or_404()

    if not transkrip.teks:
        flash('Teks transkrip kosong', 'error')
        return redirect(url_for('upload.view_transkrip', transkrip_id=transkrip_id))

    model_summarize = genai.GenerativeModel('models/gemini-2.0-flash')

    prompt_summarize = """
    Tolong buatkan rangkuman dari materi berikut ini. Output HARUS berbentuk JSON murni seperti contoh di bawah dan SEMUA field wajib diisi, walaupun materinya tidak lengkap:
    [
        {
            "judul_rangkuman": "Judul",
            "pengertian_utama": "Pengertian ringkas",
            "poin_rangkuman": ["Poin 1", "Poin 2", "Poin 3"],
            "contoh_ilustrasi": ["Contoh 1", "Contoh 2"],
            "kesimpulan": "Kesimpulan akhir"
        }
    ]
    """

    try:
        # Menghasilkan rangkuman dari teks menggunakan model AI
        response = model_summarize.generate_content([prompt_summarize, transkrip.teks])
        teks_summarize = clean_json_output(response.text.strip())

        try:
            # Coba mengonversi hasil menjadi JSON
            summary_json = json.loads(teks_summarize)
            summary_text = json.dumps(summary_json, ensure_ascii=False, indent=2)

            # Simpan hasil rangkuman ke dalam database
            new_summary = Summarize(
                data_summary=summary_text,
                transkrip_id=transkrip_id,
                user_id=user_id
            )
            db.session.add(new_summary)
            db.session.commit()

            flash('Summarize berhasil dibuat', 'success')

            # Render halaman summarize.html dan tampilkan hasilnya
            return render_template('summarize.html', summary=new_summary, transkrip=transkrip)

        except json.JSONDecodeError:
            flash('Gagal parsing JSON dari output Gemini', 'error')
            return redirect(url_for('upload.view_transkrip', transkrip_id=transkrip_id))

    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('upload.view_transkrip', transkrip_id=transkrip_id))
    


def clean_json_output(text):
    try:
        # Membersihkan teks dari format yang tidak perlu
        teks = text.replace('```json', '').replace('```', '')
        teks = teks.replace('~~~json', '').replace('~~~', '')
        return teks.strip()
    except Exception as e:
        flash(f"Error saat membersihkan output: {str(e)}", 'error')
        return ""
