from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from werkzeug.utils import secure_filename
import os
import google.generativeai as genai
from ..models import db, Transkrip

upload = Blueprint('upload', __name__)
GOOGLE_API_KEY = 'AIzaSyDBV4t5y7oNh05oZnQxTYcK3rA1FiBd1Wc'
genai.configure(api_key=GOOGLE_API_KEY)


@upload.route('/upload', methods=['GET', 'POST'])
def upload_audio():
    if request.method == 'POST':
        audios = request.files.getlist('audio')
        user_id = session.get('user_id')

        if not user_id:
            flash('Anda harus login', 'error')
            return redirect(url_for('auth.login'))

        if audios:
            all_transcribe = []
            model = genai.GenerativeModel('models/gemini-2.0-flash-lite')

            upload_folder = os.path.join(current_app.root_path, 'static')
            os.makedirs(upload_folder, exist_ok=True)

            for audio in audios:
                if audio.filename == '':
                    continue

                filename = secure_filename(audio.filename)
                path = os.path.join(upload_folder, filename)
                audio.save(path)

                mime_type = 'audio/mpeg'

                with open(path, "rb") as f:
                    gemini_file = genai.upload_file(f, mime_type=mime_type)

                response = model.generate_content([
                    "Tolong transkripkan file audio ini ke dalam bentuk teks percakapan.",
                    gemini_file
                ])
                teks = response.text
                all_transcribe.append(teks)

            combined = "\n\n".join(all_transcribe)
            new_transkrip = Transkrip(name=audios[0].filename, teks=combined, user_id=user_id)
            db.session.add(new_transkrip)
            db.session.commit()

            return redirect(url_for('upload.daftar_soal', transkrip_id=new_transkrip.id))

    return render_template('upload.html')


# @upload.route('/transkrip/<int:transkrip_id>')
# def view_transkrip(transkrip_id):
#     transkrip = Transkrip.query.get_or_404(transkrip_id)
#     return render_template('transkrip.html', transkrip=transkrip)

@upload.route('/soal')
def daftar_soal():
    semua_transkrip = Transkrip.query.order_by(Transkrip.created_at.desc()).all()
    return render_template('transkrip.html', transkrip_list=semua_transkrip)
