from datetime import datetime
from decimal import Decimal

# описываем форматы входных и выходных данных api через pydantic схемы
from pydantic import BaseModel, ConfigDict, Field, model_validator

"""
по факту мы описываем то же самое что и в models но уже для api
а не для бд sqlachemy
"""


class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)  # обязательная строка
    description: str | None = None  # описание необязательно
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)  # цена обязательна
    stock: int = Field(ge=0)  # кол-во на складе


"""ПРИМЕР
данные на входе
{
  "name": "Coffee",
  "description": "Delicious drink",
  "price": "100.00",
  "stock": 5
}
созданный объект
product = ProductBase(
    name="Coffee",
    description=None,
    price=Decimal("100.00"),
    stock=5,
)
"""


# основа для загрузки других схем
class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    price: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    stock: int | None = Field(default=None, ge=0)

    @model_validator(
        mode="after"
    )  # это pydantic валидатор, он выполнится после преобразования
    def check_not_empty(self) -> "ProductUpdate":
        if not self.model_fields_set:  # содержит названия полей
            raise ValueError("At least one field must be provided")
            # такая ошибка автоматически возвращает 422 (Unprocessable Entity)
        return self  # если все правильно возвращаем созданный объект


class ProductRead(ProductBase):  # наследует интерфейс объекта product
    model_config = ConfigDict(from_attributes=True)  # читает данные сразу из бд модели
    id: int


class OrderItemCreate(
    BaseModel
):  # сюда передаем id продукта для добавления и его кол-во
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):  # создание заказа, получаем минимум один продукт
    items: list[OrderItemCreate] = Field(min_length=1)


class OrderItemRead(
    BaseModel
):  # это скорее аналитический класс, здесь мы получаем данные о товаре
    # получает данные от сервара, то есть уже готовый заказ
    model_config = ConfigDict(from_attributes=True)
    product_id: int
    quantity: int
    unit_price: Decimal


class OrderRead(
    BaseModel
):  # это еще один аналитический класс, но здесь мы получаем данные о заказе от клиента
    # здесь он уже позволяет создать заказ, который будет валиден
    model_config = ConfigDict(from_attributes=True)

    id: int
    items: list[OrderItemRead]
    total: Decimal
    status: str
    created_at: datetime
