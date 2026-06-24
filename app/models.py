from datetime import datetime, timezone
from decimal import Decimal

# я выбрал sqlachemy из-за его простоты
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Product(Base):
    __tablename__ = "products"  # заголовок
    __table_args__ = (
        CheckConstraint("price > 0", name="price_positive"),
        CheckConstraint("stock >= 0", name="non_negative"),
    )  # указываем ограничения таблицы в кортеже спец аргумента
    # аннотируем числовое значение в столбец id и присваиваем ему первичный ключ
    # то есть бд сама задает его значение, клиенту достаточно передать остальные аттрибуты
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))  # название до 100 символов
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # описания может и не быть
    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2)
    )  # 10 целых чисел с точностью 2 знаков после запятой. float дает погрешности, поэтому decimal
    stock: Mapped[int]  # доступный на складе товар


test_product = Product(
    name="Coffe",
    price=Decimal("100"),
    stock=0,
    description="Delicious drink",
)
# print(test_product.description)


class Order(Base):
    __tablename__ = "orders"  # заголовок

    id: Mapped[int] = mapped_column(primary_key=True)  # первичный ключ
    total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2)
    )  # от 2 цифр после запятой до 12 целых цифр
    status: Mapped[str] = mapped_column(String(30), default="created")
    """
    на практике статус всегда будет created, однако этот функционал
    минимален и закладывает основу дальнейшей масштабируемости
    тем не менее можно передать свой уникальный статус при создании
    *до 30 символов
    """
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )  # дата создания, при этом  клиент не должен иметь возможности это передать
    # значит функция выполняется отдельно при каждой новой записи
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )  # перечень предметов заказа, реализуется связь один(заказ) ко многим(предметы)
    """
    можно было бы добавить ограничение на минимальный total > 0, 
    но заказ состоит из элементов у каждого из которых уже была
    проверка на положительный ценник а значит что здесь это будет
    лишней работой. плюс ко всему, pydantic не даст вернуть
    пустую схему без заказов

    back_populates обеспечивает обратную связь с Order.items и OrderItem.order
    так как имена должны совпадать перекрестно:
    Order.Items <-> OrderItem.order

    cascade (all, delete-orphan) означает что можно выполнять все операции,
    но если позиция больше не принадлежит заказу, то она удаляется

    lazy - selectin делает следующее, сначала получаем список всех заказов
    (сущетсвующих), затем мы сможем импользовать каждый этот заказ внутри
    грубо говоря мы получаем order_{n}.items как объект, где n - это номер заказа
    в противном случае выполняется запрос на каждую позицию заказа и на каждый заказ
    """


class OrderItem(Base):
    __tablename__ = "order_items"  # заголовок
    __table_args__ = (
        CheckConstraint("quantity > 0", name="item_quantity_positive"),
    )  # указываем ограничение таблицы, кол-во предмета в заказе > 0

    # аннотируем числовое значение в столбец id и присваиваем ему первичный ключ
    # бд сама задает уникальное значение для каждой новой позиции заказа
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE")
    )  # внешний ключ который связывает позицию с ее заказом
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT")
    )  # внешний ключ который связывает позицию в заказе с определенным товаром
    quantity: Mapped[int]  # количество выбранного товара в этой позиции заказа
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2)
    )  # цена одной единицы товара

    """
    order_id хранит номер заказа к которому принадлежит эта позиция

    product_id хранит номер товара который добавлялся, а ondelete RESTRICT означает
    что товар нельзя удалить если он уже используется хоть где-то

    quantity хранит кол-во определенного товара, обрабатывая при это вырожденный случай

    unit_price сохраняет цену на момент создания, так как в обычной практике заказы
    оплачиваются по той цене, по которой брали его товары, плюс важно хранить не актуальное
    значение чека, а то, при котором оно оплачивалось
    это обеспечивает целостность
    """

    order: Mapped[Order] = relationship(
        back_populates="items"
    )  # обратная связь с заказом которому принадлежит данный товар
    # благодаря этому можно добавлять новые позиции без угроза целостности
    # а sqlalchemy сам привяжет позицию к заказу