import os
from collections.abc import Generator

# подключаем библиотеки
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./store.db")
"""
при отсуствии записываем в переменную окружения базу данных sqlite с
форматом подключения :/// к файлу ./store.db
"""


class Base(DeclarativeBase):
    """
    я применил подход декларативного описание моделей
    то есть бд создается не при помощи нашего кода
    а при помощи результата его преобразования в t-sql

    создаем класс для наследования остальных классов
    product, order & orderitems
    а DeclarativeBase позволяет описывать таблицу
    обычными python классами

    в первую очередь это решает проблему разных метаданных таблиц
    по факту мы создаем единый класс с одним набором метаданных для всех таблиц
    """

    pass


# создаем бд
engine = create_engine(
    DATABASE_URL,
    connect_args=(
        {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
    ),
)


if DATABASE_URL.startswith("sqlite"):
    """
    если база данных в заголовке имеет
    метку sqlite, то проверяем внешние
    ключи для каждого соединения

    таким образом указываем автовызов
    функции каждый раз когда регистрируется
    новое соединение

    затем открываем cursor() чтобы выполнить
    в нем sql команду "pragma foreign_keys = on"
    таким образом гарантируем что правила по типу
    ondelete() будут отрабатывать
    кратко говоря пресекаем все вырожденные случаи разом
    """

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("pragma foreign_keys = on")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
"""
сесиия это объект для работы с бд, инициализированный через специальный вызов
expire_on_commit здесь для отладки, он позволяет читать таблицы после транзакции
"""


def get_db() -> Generator[Session]:
    with SessionLocal() as session:
        yield session
