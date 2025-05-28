from flask import Flask, render_template, request, redirect, url_for
import pymysql
from math import ceil
import os
from werkzeug.utils import secure_filename
import time
from google.cloud import storage

app = Flask(__name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Kiểm tra định dạng file
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Hàm upload file lên Cloud Storage
def upload_to_gcs(file, bucket_name='anime-library-461214.appspot.com'):
    client = storage.Client()
    bucket = client.get_bucket(bucket_name)
    filename = secure_filename(f"{int(time.time())}_{file.filename}")
    blob = bucket.blob(f"uploads/{filename}")
    blob.upload_from_file(file)
    blob.make_public()  # Làm tệp công khai để truy cập qua URL
    return blob.public_url

# Kết nối cơ sở dữ liệu MySQL
def get_db_connection():
    if os.environ.get('GAE_ENV', '').startswith('standard'):
        conn = pymysql.connect(
            unix_socket='/cloudsql/anime-library-461214:asia-east1:anime-library-db',
            user='root',
            password='123456',
            db='anime-db',
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    else:
        conn = pymysql.connect(
            host='104.199.163.45',
            user='root',
            password='123456',
            db='anime-db',
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    return conn

# Khởi tạo cơ sở dữ liệu
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            rating INTEGER,
            image_path VARCHAR(255),
            movie_url VARCHAR(255)
        )
    ''')
    conn.commit()
    cursor.close()
    conn.close()

# Gọi hàm khởi tạo cơ sở dữ liệu
init_db()

# Route cho trang chính (hiển thị danh sách phim với phân trang)
@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 6
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM movies LIMIT %s OFFSET %s', 
                  (per_page, (page - 1) * per_page))
    movies = cursor.fetchall()
    cursor.execute('SELECT COUNT(*) as count FROM movies')
    total_movies = cursor.fetchone()['count']
    total_pages = ceil(total_movies / per_page)
    cursor.close()
    conn.close()
    return render_template('index.html', movies=movies, page=page, total_pages=total_pages)

# Route để thêm phim mới
@app.route('/add', methods=['GET', 'POST'])
def add_movie():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        rating = int(request.form['rating'])
        movie_url = request.form['movie_url']
        
        if 'image' not in request.files:
            return 'No file part'
        file = request.files['image']
        if file.filename == '':
            return 'No selected file'
        if file and allowed_file(file.filename):
            image_path = upload_to_gcs(file)
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO movies (title, description, rating, image_path, movie_url) VALUES (%s, %s, %s, %s, %s)',
                          (title, description, rating, image_path, movie_url))
            conn.commit()
            cursor.close()
            conn.close()
            return redirect(url_for('index'))
        else:
            return 'Invalid file format'
    return render_template('add_movie.html')

# Route để chỉnh sửa phim
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_movie(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM movies WHERE id = %s', (id,))
    movie = cursor.fetchone()
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        rating = int(request.form['rating'])
        movie_url = request.form['movie_url']
        image_path = movie['image_path']
        
        if 'image' in request.files and request.files['image'].filename != '':
            file = request.files['image']
            if file and allowed_file(file.filename):
                image_path = upload_to_gcs(file)
        
        cursor.execute('UPDATE movies SET title = %s, description = %s, rating = %s, image_path = %s, movie_url = %s WHERE id = %s',
                      (title, description, rating, image_path, movie_url, id))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('index'))
    
    cursor.close()
    conn.close()
    return render_template('edit_movie.html', movie=movie)

# Route để xóa phim
@app.route('/delete/<int:id>')
def delete_movie(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT image_path FROM movies WHERE id = %s', (id,))
    movie = cursor.fetchone()
    # Không cần xóa tệp vì đã dùng Cloud Storage
    cursor.execute('DELETE FROM movies WHERE id = %s', (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('index'))

# Route cho trang chi tiết phim
@app.route('/detail/<int:id>')
def detail_movie(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM movies WHERE id = %s', (id,))
    movie = cursor.fetchone()
    cursor.close()
    conn.close()
    if movie:
        return render_template('detail_movie.html', movie=movie)
    return 'Phim không tồn tại', 404

if __name__ == '__main__':
    app.run(debug=True)