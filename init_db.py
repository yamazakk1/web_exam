from app import app, db
from models import Role, Genre, ReviewStatus, User
from werkzeug.security import generate_password_hash

def init_database():
    with app.app_context():
        # Создаём таблицы
        db.create_all()
        
        # Добавляем роли
        roles_data = [
            {'name': 'администратор', 'description': 'суперпользователь, имеет полный доступ к системе, в том числе к созданию и удалению книг'},
            {'name': 'модератор', 'description': 'может редактировать данные книг и производить модерацию рецензий'},
            {'name': 'пользователь', 'description': 'может оставлять рецензии'}
        ]
        
        for role_data in roles_data:
            if not Role.query.filter_by(name=role_data['name']).first():
                role = Role(**role_data)
                db.session.add(role)
                print(f"Роль '{role_data['name']}' создана")
        
        # Добавляем жанры
        genres_data = [
            'Фантастика', 'Фэнтези', 'Детектив', 'Роман', 
            'Научная литература', 'История', 'Поэзия', 
            'Приключения', 'Ужасы', 'Триллер'
        ]
        
        for genre_name in genres_data:
            if not Genre.query.filter_by(name=genre_name).first():
                genre = Genre(name=genre_name)
                db.session.add(genre)
                print(f"Жанр '{genre_name}' создан")
        
        # Добавляем статусы рецензий
        statuses_data = ['На рассмотрении', 'Одобрена']
        for status_name in statuses_data:
            if not ReviewStatus.query.filter_by(name=status_name).first():
                status = ReviewStatus(name=status_name)
                db.session.add(status)
                print(f"Статус '{status_name}' создан")
        
        db.session.commit()
        
        # Создаём тестовых пользователей
        if not User.query.filter_by(login='admin').first():
            admin_role = Role.query.filter_by(name='администратор').first()
            admin = User(
                login='admin',
                password_hash=generate_password_hash('admin123'),
                last_name='Администраторов',
                first_name='Админ',
                role_id=admin_role.id
            )
            db.session.add(admin)
            print("Пользователь 'admin' создан")
        
        if not User.query.filter_by(login='moderator').first():
            mod_role = Role.query.filter_by(name='модератор').first()
            moderator = User(
                login='moderator',
                password_hash=generate_password_hash('moderator123'),
                last_name='Модераторов',
                first_name='Модератор',
                role_id=mod_role.id
            )
            db.session.add(moderator)
            print("Пользователь 'moderator' создан")
        
        if not User.query.filter_by(login='user').first():
            user_role = Role.query.filter_by(name='пользователь').first()
            user = User(
                login='user',
                password_hash=generate_password_hash('user123'),
                last_name='Пользователев',
                first_name='Пользователь',
                role_id=user_role.id
            )
            db.session.add(user)
            print("Пользователь 'user' создан")
        
        db.session.commit()
        print("База данных успешно инициализирована!")

if __name__ == '__main__':
    init_database()