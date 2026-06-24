# подключаем компоненты fastapi для создания путей, зависимостей и ошибок
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Product
from app.schemas import ProductCreate, ProductRead, ProductUpdate

# создаем отдельный список путей для работы с продуктами
router = APIRouter(prefix="/products", tags=["products"])
"""
prefix автоматически добавляет /products перед каждым путем в этом файле
а tags нужен для объединения всех этих запросов внутри документации api
"""


def get_product_or_404(product_id: int, db: Session) -> Product:
    """
    дополнительная функция которая получает id продукта и активную сессию
    если такого продукта не существует, сразу обрабатываем вырожденный случай
    и возвращаем клиенту понятную ошибку 404
    """
    product = db.get(Product, product_id)
    if product is None:  # если get ничего не нашел, то получили None
        raise HTTPException(status_code=404, detail="Product not found")
    return product  # если продукт существует возвращаем его бд модель


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)) -> Product:
    """
    post запрос создает новый продукт, payload уже был проверен pydantic схемой
    ProductCreate, а Depends автоматически получает сессию из get_db

    response_model указывает в каком виде клиент получит готовый продукт
    status 201 означает что новый объект был успешно создан
    """
    product = Product(**payload.model_dump())
    # model_dump превращает pydantic объект в словарь, а ** разбирает его атрибуты
    db.add(product)  # добавляем созданный объект в текущую сессию
    db.commit()  # подтверждаем транзакцию и записываем продукт в бд
    db.refresh(product)  # повторно получаем продукт вместе с присвоенным ему id
    return product  # fastapi сам преобразует модель в ProductRead


@router.get("", response_model=list[ProductRead])
def list_products(db: Session = Depends(get_db)) -> list[Product]:
    # получаем все существующие продукты и сортируем их по первичному ключу
    return list(db.scalars(select(Product).order_by(Product.id)))
    """
    select формирует sql запрос к таблице products, scalars достает именно
    объекты Product без лишней обертки, затем превращаем результат в список
    """


@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: int, db: Session = Depends(get_db)) -> Product:
    # получаем конкретный продукт по его номеру или возвращаем ошибку 404
    return get_product_or_404(product_id, db)


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int, payload: ProductUpdate, db: Session = Depends(get_db)
) -> Product:
    """
    patch запрос изменяет только те атрибуты продукта которые передал клиент
    перед обновлением отдельно проверяем что продукт с таким id существует
    """
    product = get_product_or_404(product_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        # exclude_unset убирает все поля которые клиент не передавал
        setattr(product, field, value)
        # setattr по очереди записывает полученное значение в нужный атрибут
    db.commit()  # подтверждаем все изменения одной транзакцией
    db.refresh(product)  # получаем актуальное состояние продукта из бд
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: Session = Depends(get_db)) -> Response:
    """
    delete запрос удаляет продукт, но сначала проверяет что он существует
    код 204 означает что операция прошла успешно и ответ не имеет содержимого
    """
    product = get_product_or_404(product_id, db)
    db.delete(product)  # помечаем найденный продукт для удаления
    try:
        db.commit()  # пытаемся подтвердить удаление
    except IntegrityError as exc:
        db.rollback()  # при ошибке возвращаем бд к состоянию до транзакции
        raise HTTPException(
            status_code=409,
            detail="Product cannot be deleted because it is used in an order",
        ) from exc
        # ошибка 409 возникает если продукт уже связан с какой-либо позицией заказа
    return Response(status_code=status.HTTP_204_NO_CONTENT)