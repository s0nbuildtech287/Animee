from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from math import ceil
import os
from werkzeug.utils import secure_filename
import time

app = Flask(__name__)

# Cấu hình thư mục upload
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Tạo thư mục uploads nếu chưa có
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Kiểm tra định dạng file
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Kết nối cơ sở dữ liệu SQLite
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Khởi tạo cơ sở dữ liệu
def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            rating INTEGER,
            image_path TEXT,
            movie_url TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Gọi hàm khởi tạo cơ sở dữ liệu
init_db()

# Route cho trang chính (hiển thị danh sách phim với phân trang)
@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 6  # Số phim mỗi trang
    conn = get_db_connection()
    movies = conn.execute('SELECT * FROM movies LIMIT ? OFFSET ?', 
                         (per_page, (page - 1) * per_page)).fetchall()
    total_movies = conn.execute('SELECT COUNT(*) FROM movies').fetchone()[0]
    total_pages = ceil(total_movies / per_page)
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
        
        # Xử lý upload ảnh
        if 'image' not in request.files:
            return 'No file part'
        file = request.files['image']
        if file.filename == '':
            return 'No selected file'
        if file and allowed_file(file.filename):
            filename = secure_filename(f"{int(time.time())}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_path = f"uploads/{filename}"
            
            conn = get_db_connection()
            conn.execute('INSERT INTO movies (title, description, rating, image_path, movie_url) VALUES (?, ?, ?, ?, ?)',
                        (title, description, rating, image_path, movie_url))
            conn.commit()
            conn.close()
            return redirect(url_for('index'))
        else:
            return 'Invalid file format'
    return render_template('add_movie.html')

# Route để chỉnh sửa phim
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_movie(id):
    conn = get_db_connection()
    movie = conn.execute('SELECT * FROM movies WHERE id = ?', (id,)).fetchone()
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        rating = int(request.form['rating'])
        movie_url = request.form['movie_url']
        image_path = movie['image_path']
        
        # Xử lý upload ảnh mới nếu có
        if 'image' in request.files and request.files['image'].filename != '':
            file = request.files['image']
            if file and allowed_file(file.filename):
                # Xóa ảnh cũ nếu tồn tại
                if os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(image_path))):
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(image_path)))
                # Lưu ảnh mới
                filename = secure_filename(f"{int(time.time())}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_path = f"uploads/{filename}"
        
        conn.execute('UPDATE movies SET title = ?, description = ?, rating = ?, image_path = ?, movie_url = ? WHERE id = ?',
                    (title, description, rating, image_path, movie_url, id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    
    conn.close()
    return render_template('edit_movie.html', movie=movie)

# Route để xóa phim
@app.route('/delete/<int:id>')
def delete_movie(id):
    conn = get_db_connection()
    movie = conn.execute('SELECT image_path FROM movies WHERE id = ?', (id,)).fetchone()
    if movie and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(movie['image_path']))):
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(movie['image_path'])))
    conn.execute('DELETE FROM movies WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# Route cho trang chi tiết phim
@app.route('/detail/<int:id>')
def detail_movie(id):
    conn = get_db_connection()
    movie = conn.execute('SELECT * FROM movies WHERE id = ?', (id,)).fetchone()
    conn.close()
    if movie:
        return render_template('detail_movie.html', movie=movie)
    return 'Phim không tồn tại', 404

if __name__ == '__main__':
    app.run(debug=True)