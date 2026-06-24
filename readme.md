## решение
```mermaid
flowchart LR
    Client["HTTP-клиент или Swagger"] --> FastAPI["app/main.py"]
    FastAPI --> ProductRoutes["api/products.py"]
    FastAPI --> OrderRoutes["api/orders.py"]

    ProductRoutes --> Schemas["schemas.py"]
    OrderRoutes --> Schemas

    ProductRoutes --> Session["database.py / Session"]
    OrderRoutes --> Session

    Session --> Models["models.py"]
    Models --> SQLite["store.db / SQLite"]
```

## настройка и запуск
```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install fastapi "uvicorn[standard]" "pydantic>=2" "sqlalchemy>=2" fastapi
```

## создание декларативных таблиц
```
DeclarativeBase->
    >Base->
        >Product
        >Order
        >OrderItem
```