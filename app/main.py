from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

# импорт компонентов
from app.api.orders import router as orders_router
from app.api.products import router as products_router
from app.database import Base, engine


# асинхронный генератор для ускорения create_all() и none означает что yield значения не берет
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """
    обозначаем жизненный цкил приложения, где FastApi это аннотация типа
    app, а сам аргумент app не используется, по умолчанию FastApi сам ее вызовет
    но не передаст аргументы, и может вернуть вырожденный случай, так как сам app
    внутри функции не используется
    """
    Base.metadata.create_all(
        bind=engine
    )  # инициализация наследуюмых таблиц (проверка плюс создание)
    yield  # указываем что все необходимое есть, начинаем прием и обработку запросов
    engine.dispose()  # избавляемся от содержимого при остановке сервера


app = FastAPI(lifespan=lifespan)  # указываем функцию инициализации

# подключаем пути
app.include_router(products_router)
app.include_router(orders_router)


# проверка работоспособности
@app.get("/health")
def healthcheck() -> dict[str, str]:
    """
    при вызове get запроса url/health возвращаем сообщение
    """
    return {"working": "yes"}
