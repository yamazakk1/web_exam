from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import Config
from models import db, User, Book, Genre, Cover, Review, ReviewStatus
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import hashlib
import bleach
import markdown
import os

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Для выполнения данного действия необходимо пройти процедуру аутентификации'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def check_rights(required_roles):
    if not current_user.is_authenticated:
        return False
    return current_user.role.name in required_roles

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)

    books_query = Book.query.order_by(Book.year.desc())
    books_pagination = books_query.paginate(page=page, per_page=10, error_out=False)
    books = books_pagination.items

    books_data = []
    for book in books:
        approved_reviews = Review.query.filter_by(book_id=book.id, status_id=2).all()  
        reviews_count = len(approved_reviews)
        avg_rating = round(sum([r.rating for r in approved_reviews]) / reviews_count, 1) if reviews_count > 0 else 0
        
        books_data.append({
            'book': book,
            'avg_rating': avg_rating,
            'reviews_count': reviews_count
        })
    
    return render_template('index.html', books_data=books_data, pagination=books_pagination)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form.get('login')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'
        
        user = User.query.filter_by(login=login).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Невозможно аутентифицироваться с указанными логином и паролем', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/book/<int:book_id>')
def book_view(book_id):
    book = Book.query.get_or_404(book_id)

    approved_reviews = Review.query.filter_by(book_id=book_id, status_id=2).order_by(Review.created_at.desc()).all()

    user_review = None
    if current_user.is_authenticated:
        user_review = Review.query.filter_by(book_id=book_id, user_id=current_user.id).first()

    description_html = markdown.markdown(book.description, extensions=['fenced_code', 'tables'])
    description_html = bleach.clean(description_html, tags=['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'em', 'ul', 'ol', 'li', 'a', 'code', 'pre', 'blockquote', 'table', 'thead', 'tbody', 'tr', 'th', 'td'])
    
    return render_template('book_view.html', 
                         book=book, 
                         reviews=approved_reviews, 
                         user_review=user_review, 
                         description_html=description_html)

@app.route('/book/add', methods=['GET', 'POST'])
@login_required
def book_add():
    if not check_rights(['администратор']):
        flash('У вас недостаточно прав для выполнения данного действия', 'danger')
        return redirect(url_for('index'))
    
    genres = Genre.query.all()
    
    if request.method == 'POST':
        try:
            title = request.form.get('title')
            description = request.form.get('description')
            year = request.form.get('year')
            publisher = request.form.get('publisher')
            author = request.form.get('author')
            pages = request.form.get('pages')
            genre_ids = request.form.getlist('genres')
            cover_file = request.files.get('cover')

            if not all([title, description, year, publisher, author, pages, genre_ids]):
                flash('При сохранении данных возникла ошибка. Проверьте корректность введённых данных.', 'danger')
                return render_template('book_form.html', book=None, genres=genres, form_data=request.form)
             
            clean_description = bleach.clean(description, tags=['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'em', 'ul', 'ol', 'li', 'a', 'code', 'pre', 'blockquote', 'table', 'thead', 'tbody', 'tr', 'th', 'td'])

            book = Book(
                title=title,
                description=clean_description,
                year=int(year),
                publisher=publisher,
                author=author,
                pages=int(pages)
            )

            for genre_id in genre_ids:
                genre = Genre.query.get(int(genre_id))
                if genre:
                    book.genres.append(genre)
            
            db.session.add(book)
            db.session.flush() 

            if cover_file and cover_file.filename:
                file_data = cover_file.read()
                md5_hash = hashlib.md5(file_data).hexdigest()
                cover_file.seek(0) 

                existing_cover = Cover.query.filter_by(md5_hash=md5_hash).first()
                
                if existing_cover:
                    existing_cover.book_id = book.id
                else:
                    cover = Cover(
                        filename=secure_filename(cover_file.filename),
                        mime_type=cover_file.content_type,
                        md5_hash=md5_hash,
                        book_id=book.id
                    )
                    db.session.add(cover)
                    db.session.flush()

                    ext = os.path.splitext(cover_file.filename)[1]
                    filename = f"{cover.id}{ext}"
                    cover.filename = filename
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    cover_file.save(filepath)
            
            db.session.commit()
            flash('Книга успешно добавлена!', 'success')
            return redirect(url_for('book_view', book_id=book.id))
            
        except Exception as e:
            db.session.rollback()
            flash('При сохранении данных возникла ошибка. Проверьте корректность введённых данных.', 'danger')
            return render_template('book_form.html', book=None, genres=genres, form_data=request.form)
    
    return render_template('book_form.html', book=None, genres=genres, form_data=None)

@app.route('/book/<int:book_id>/edit', methods=['GET', 'POST'])
@login_required
def book_edit(book_id):
    if not check_rights(['администратор', 'модератор']):
        flash('У вас недостаточно прав для выполнения данного действия', 'danger')
        return redirect(url_for('index'))
    
    book = Book.query.get_or_404(book_id)
    genres = Genre.query.all()
    
    if request.method == 'POST':
        try:
            book.title = request.form.get('title')
            description = request.form.get('description')
            book.year = int(request.form.get('year'))
            book.publisher = request.form.get('publisher')
            book.author = request.form.get('author')
            book.pages = int(request.form.get('pages'))

            book.description = bleach.clean(description, tags=['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'em', 'ul', 'ol', 'li', 'a', 'code', 'pre', 'blockquote', 'table', 'thead', 'tbody', 'tr', 'th', 'td'])

            book.genres = []
            genre_ids = request.form.getlist('genres')
            for genre_id in genre_ids:
                genre = Genre.query.get(int(genre_id))
                if genre:
                    book.genres.append(genre)
            
            db.session.commit()
            flash('Книга успешно обновлена!', 'success')
            return redirect(url_for('book_view', book_id=book.id))
            
        except Exception as e:
            db.session.rollback()
            flash('При сохранении данных возникла ошибка. Проверьте корректность введённых данных.', 'danger')
            return render_template('book_form.html', book=book, genres=genres, form_data=request.form)
    
    return render_template('book_form.html', book=book, genres=genres, form_data=None)

@app.route('/book/<int:book_id>/delete', methods=['POST'])
@login_required
def book_delete(book_id):
    if not check_rights(['администратор']):
        flash('У вас недостаточно прав для выполнения данного действия', 'danger')
        return redirect(url_for('index'))
    
    book = Book.query.get_or_404(book_id)

    if book.cover:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], book.cover.filename)
        if os.path.exists(filepath):
            os.remove(filepath)
    
    db.session.delete(book)
    db.session.commit()
    
    flash('Книга успешно удалена!', 'success')
    return redirect(url_for('index'))

@app.route('/book/<int:book_id>/review', methods=['GET', 'POST'])
@login_required
def review_create(book_id):
    existing_review = Review.query.filter_by(book_id=book_id, user_id=current_user.id).first()
    if existing_review:
        flash('Вы уже оставили рецензию на эту книгу', 'warning')
        return redirect(url_for('book_view', book_id=book_id))
    
    book = Book.query.get_or_404(book_id)
    
    if request.method == 'POST':
        try:
            rating = request.form.get('rating')
            text = request.form.get('text')
            
            if not all([rating, text]):
                flash('При сохранении данных возникла ошибка. Проверьте корректность введённых данных.', 'danger')
                return render_template('review_form.html', book=book, form_data=request.form)

            clean_text = bleach.clean(text, tags=['p', 'strong', 'em', 'ul', 'ol', 'li', 'a', 'code', 'pre', 'blockquote'])

            pending_status = ReviewStatus.query.filter_by(name='На рассмотрении').first()
            
            review = Review(
                book_id=book_id,
                user_id=current_user.id,
                rating=int(rating),
                text=clean_text,
                status_id=pending_status.id
            )
            
            db.session.add(review)
            db.session.commit()
            
            flash('Рецензия успешно добавлена!', 'success')
            return redirect(url_for('book_view', book_id=book_id))
            
        except Exception as e:
            db.session.rollback()
            flash('При сохранении данных возникла ошибка. Проверьте корректность введённых данных.', 'danger')
            return render_template('review_form.html', book=book, form_data=request.form)
    
    return render_template('review_form.html', book=book)

@app.template_filter('markdown')
def markdown_filter(text):
    html = markdown.markdown(text, extensions=['fenced_code', 'tables'])
    return bleach.clean(html, tags=['p', 'strong', 'em', 'ul', 'ol', 'li', 'a', 'code', 'pre', 'blockquote', 'h1', 'h2', 'h3'])

@app.route('/my_reviews')
@login_required
def my_reviews():
    reviews = Review.query.filter_by(user_id=current_user.id).order_by(Review.created_at.desc()).all()
    return render_template('my_reviews.html', reviews=reviews)

@app.route('/moderation')
@login_required
def moderation():
    if not check_rights(['модератор']):
        flash('У вас недостаточно прав для выполнения данного действия', 'danger')
        return redirect(url_for('index'))
    
    page = request.args.get('page', 1, type=int)

    pending_status = ReviewStatus.query.filter_by(name='На рассмотрении').first()
    reviews_query = Review.query.filter_by(status_id=pending_status.id).order_by(Review.created_at.asc())
    reviews_pagination = reviews_query.paginate(page=page, per_page=10, error_out=False)
    
    return render_template('moderation.html', reviews=reviews_pagination.items, pagination=reviews_pagination)

@app.route('/moderation/<int:review_id>', methods=['GET', 'POST'])
@login_required
def review_moderate(review_id):
    if not check_rights(['модератор']):
        flash('У вас недостаточно прав для выполнения данного действия', 'danger')
        return redirect(url_for('index'))
    
    review = Review.query.get_or_404(review_id)
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'approve':
            approved_status = ReviewStatus.query.filter_by(name='Одобрена').first()
            review.status_id = approved_status.id
            db.session.commit()
            flash('Рецензия одобрена!', 'success')
        elif action == 'reject':
            db.session.delete(review)
            db.session.commit()
            flash('Рецензия отклонена и удалена!', 'warning')
        
        return redirect(url_for('moderation'))

    review_text_html = markdown.markdown(review.text, extensions=['fenced_code', 'tables'])
    review_text_html = bleach.clean(review_text_html, tags=['p', 'strong', 'em', 'ul', 'ol', 'li', 'a', 'code', 'pre', 'blockquote'])
    
    return render_template('review_moderate.html', review=review, review_text_html=review_text_html)

@app.errorhandler(404)
def not_found_error(error):
    return render_template('base.html', content='<h1>Страница не найдена</h1>'), 404

if __name__ == '__main__':
    with app.app_context():
        db.create_all() 
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)