from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
import sqlite3
import os

from io import BytesIO
from semantic_search import SemanticSearch
import cloudinary

cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET')
)

app = Flask(__name__)

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')
UPLOAD_FOLDER = 'uploads'

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

print("AppTest.py started")

# Connect to the database
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def search_keyword(keyword):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, filename, file_date, detected_objects, has_faces, detected_text 
        FROM image_data 
        WHERE filename LIKE ? COLLATE NOCASE
           OR detected_objects LIKE ? COLLATE NOCASE
           OR has_faces LIKE ? COLLATE NOCASE
           OR detected_text LIKE ? COLLATE NOCASE
    """, (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'))
    results = cursor.fetchall()
    conn.close()
    return results


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        keyword = request.form['keyword']
        if not keyword:
            return redirect(url_for('index'))

        results = search_keyword(keyword)
        return render_template('index.html', results=results, keyword=keyword)

    return render_template('index.html', results=None)


#@app.route('/view_photo/<path:filename>')
#def view_photo(filename):
#    # Просто передаем имя файла, без повторного объединения путей
#    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


#@app.route('/download_photo/<path:filename>')
#def download_photo(filename):
#    # Просто передаем имя файла, без повторного объединения путей
#    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


@app.route('/api/full_text/<int:image_id>')
def api_full_text(image_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT detected_text FROM image_data WHERE id = ?", (image_id,))
    result = cursor.fetchone()
    conn.close()

    if result is None or result['detected_text'] is None:
        return jsonify({"text": None})

    return jsonify({"text": result['detected_text']})


#@app.route('/download_text/<int:image_id>')
#def download_text(image_id):
#    conn = get_db_connection()
#    cursor = conn.cursor()
    cursor.execute("SELECT detected_text, filename FROM image_data WHERE id = ?", (image_id,))
    result = cursor.fetchone()
    conn.close()

    if result is None or result['detected_text'] is None:
        return "Text is not found or is not available", 404

    # Создаем текстовый файл для скачивания
    filename = f"{os.path.splitext(result['filename'])[0]}_text.txt"
    with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), 'w', encoding='utf-8') as f:
        f.write(result['detected_text'])

    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)




# Инициализируем поиск при запуске сервера
print("Before SemanticSearch")
semantic_search_engine = SemanticSearch(DATABASE)
print("After SemanticSearch")

@app.route('/api/semantic-search/', methods=['POST'])
def semantic_search():
    try:
        data = request.get_json()
        print("Request data:", data)
        query = data.get('query', '')
        top_k = int(data.get('top_k', 20))
        offset = int(data.get('offset', 0))
        print("Calling semantic_search_engine.search with:", query, top_k, offset)
        results = semantic_search_engine.search(query, top_k, offset)
        print("Results:", results)
        return jsonify({'results': results})
    except Exception as e:
        print("Error in /api/semantic-search/:", e)
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 400


@app.route('/api/keyword-search/', methods=['GET'])
def api_keyword_search():
    keyword = request.args.get('keyword', '')
    offset = int(request.args.get('offset', 0))
    limit = int(request.args.get('limit', 20))
    sort = request.args.get('sort', 'file_date DESC')
    faces = request.args.get('faces')
    objects = request.args.get('objects')

    query = "SELECT id, filename, file_date, detected_objects, has_faces, detected_text FROM image_data WHERE 1=1"
    params = []
    if keyword:
        query += " AND (filename LIKE ? COLLATE NOCASE OR detected_objects LIKE ? COLLATE NOCASE OR has_faces LIKE ? COLLATE NOCASE OR detected_text LIKE ? COLLATE NOCASE)"
        params += [f'%{keyword}%'] * 4
    if faces is not None:
        query += " AND has_faces = ?"
        params.append(faces)
    if objects:
        query += " AND detected_objects LIKE ? COLLATE NOCASE"
        params.append(f'%{objects}%')
    # Получаем общее количество
    count_query = f"SELECT COUNT(*) FROM ({query})"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]
    # Добавляем сортировку и пагинацию
    query += f" ORDER BY {sort} LIMIT ? OFFSET ?"
    params += [limit, offset]
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    results = [{
        'id': row['id'],
        'filename': row['filename'],
        'file_date': row['file_date'],
        'detected_objects': row['detected_objects'],
        'has_faces': row['has_faces'],
        'detected_text': row['detected_text']
    } for row in rows]
    return jsonify({'results': results, 'total': total})


if __name__ == '__main__':
    print("About to start Flask server")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)