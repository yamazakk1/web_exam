from app import app, db
from models import User, Book, Genre, Review, ReviewStatus

def add_test_data():
    with app.app_context():
        if Book.query.first():
            print("Тестовые данные уже существуют")
            return

        genres = Genre.query.all()

        books_data = [
            {
                'title': 'Мастер и Маргарита',
                'description': '''# Мастер и Маргарита

Великий роман Михаила Булгакова, который стал классикой мировой литературы.

## Сюжет
Действие происходит в Москве 1930-х годов, куда прибывает загадочный иностранец Воланд со своей свитой.

## Основные темы
* Любовь и верность
* Добро и зло
* Творчество и свобода''',
                'year': 1966,
                'publisher': 'Москва',
                'author': 'Михаил Булгаков',
                'pages': 480,
                'genre_names': ['Роман', 'Фэнтези']
            },
            {
                'title': 'Преступление и наказание',
                'description': '''# Преступление и наказание

Роман Фёдора Достоевского, впервые опубликованный в 1866 году.

## Главный герой
Родион Раскольников - бывший студент, совершивший убийство старухи-процентщицы.

## Философские вопросы
* Имеет ли право человек на преступление?
* Что есть добро и зло?
* Можно ли оправдать убийство?''',
                'year': 1866,
                'publisher': 'Русский вестник',
                'author': 'Фёдор Достоевский',
                'pages': 527,
                'genre_names': ['Роман', 'Детектив']
            },
            {
                'title': '1984',
                'description': '''# 1984

Антиутопический роман Джорджа Оруэлла.

## Мир будущего
Тоталитарное общество под контролем Большого Брата.

## Ключевые концепции
* Мыслепреступление
* Новояз
* Двоемыслие''',
                'year': 1949,
                'publisher': 'Secker & Warburg',
                'author': 'Джордж Оруэлл',
                'pages': 328,
                'genre_names': ['Фантастика', 'Роман']
            }
        ]

        for book_data in books_data:
            book = Book(
                title=book_data['title'],
                description=book_data['description'],
                year=book_data['year'],
                publisher=book_data['publisher'],
                author=book_data['author'],
                pages=book_data['pages']
            )

            for genre_name in book_data['genre_names']:
                genre = Genre.query.filter_by(name=genre_name).first()
                if genre:
                    book.genres.append(genre)
            
            db.session.add(book)

        user = User.query.filter_by(login='user').first()
        approved_status = ReviewStatus.query.filter_by(name='Одобрена').first()
        
        if user and approved_status:
            review = Review(
                book_id=1,
                user_id=user.id,
                rating=5,
                text='''Отличная книга! 

Одна из лучших, что я читал. 

**Рекомендую всем!**''',
                status_id=approved_status.id
            )
            db.session.add(review)
        
        db.session.commit()
        print("Тестовые данные добавлены!")
        print(f"Книг создано: {Book.query.count()}")
        print(f"Рецензий создано: {Review.query.count()}")

if __name__ == '__main__':
    add_test_data()