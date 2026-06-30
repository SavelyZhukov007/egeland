# эти библиотеки облегчают работу для большо кол-ва данных
from collections import defaultdict
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

# подключаем модули приложения
from app.database import get_db
from app.models import Order, OrderItem, Product
from app.schemas import OrderCreate, OrderRead

router = APIRouter(prefix="/orders")
"""
создаем класс APIRouter, который будет добавлять префикс /orders
перед каждым рутом прописанным в это плане
"""


def order_query():
    # создаем общий запрос который получает заказ сразу вместе с его позициями
    """
    сначала получаем заказы, затем связанные позиции
    тогда не будет отдельного запроса для каждого заказа
    """
    return select(Order).options(selectinload(Order.items))


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def create_order(payload: OrderCreate, db: Session = Depends(get_db)) -> Order:
    """
    post запрос создает новый заказ из уже проверенной схемы
    клиент передает только id товара и нужное кол-во, все остальные данные
    включая цену, итоговый чек, статус и дату рассчитывает сам сервер
    """
    quantities: dict[int, int] = defaultdict(int)
    for item in payload.items:
        quantities[item.product_id] += item.quantity
        # если один продукт передали несколько раз, объединяем его кол-во в одно значение

    # одним запросом получаем все продукты id которых были переданы клиентом
    products = list(db.scalars(select(Product).where(Product.id.in_(quantities))))
    # преобразуем список в словарь чтобы затем получать продукт сразу по его id
    products_by_id = {product.id: product for product in products}

    # из переданных id вычитаем все найденные id и получаем отсутствующие продукты
    missing_ids = sorted(set(quantities) - products_by_id.keys())
    if missing_ids:  # обрабатываем вырожденный случай когда товара не существует
        raise HTTPException(
            status_code=404,
            detail=f"Products not found: {'| '.join(map(str, missing_ids))}",
        )

    # отдельно проверяем остаток каждого товара до того как изменять данные в бд
    for product_id, quantity in quantities.items():
        product = products_by_id[product_id]
        if product.stock < quantity:
            # если товара меньше чем хочет клиент, заказ не может быть создан
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Not enough stock for product {product_id}: "
                    f"requested {quantity}, available {product.stock}"
                ),
            )

    # создаем заказ с нулевым чеком, его точное значение рассчитаем ниже
    order = Order(total=Decimal("0.00"))
    total = Decimal("0.00")
    for product_id, quantity in quantities.items():
        product = products_by_id[product_id]
        product.stock -= quantity  # уменьшаем доступное кол-во товара на складе
        total += product.price * quantity  # считаем общий чек на стороне сервера
        order.items.append(
            OrderItem(
                product_id=product.id,
                quantity=quantity,
                unit_price=product.price,
            )
        )
        # сохраняем цену позиции на момент заказа чтобы дальнейшие изменения ее не затронули

    order.total = total  # передаем полностью рассчитанный чек в готовый заказ
    db.add(order)  # добавляем заказ, его позиции и измененные остатки в одну сессию
    try:
        db.commit()  # подтверждаем все изменения одной транзакцией
    except Exception:
        db.rollback()  # если что-то пошло не так полностью отменяем изменения
        raise  # повторно вызываем ту же ошибку чтобы она не потерялась

    # заново получаем готовый заказ из бд сразу со всеми его позициями
    return db.scalar(order_query().where(Order.id == order.id))


@router.get("", response_model=list[OrderRead])
def list_orders(db: Session = Depends(get_db)) -> list[Order]:
    # получаем все существующие заказы вместе с позициями и сортируем по id
    return list(db.scalars(order_query().order_by(Order.id)))


@router.get("/{order_id}", response_model=OrderRead)
def get_order(order_id: int, db: Session = Depends(get_db)) -> Order:
    # получаем один заказ по его номеру сразу вместе с перечнем позиций
    order = db.scalar(order_query().where(Order.id == order_id))
    if order is None:  # если такого заказа нет возвращаем клиенту ошибку 404
        raise HTTPException(status_code=404, detail="Order not found")
    return order