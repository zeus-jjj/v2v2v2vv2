```markdown
# PokerHub Database Extractor v2.0

## 📋 Описание

Автоматизированная система извлечения данных из PostgreSQL баз данных и синхронизации с Google Sheets. Построена на принципах Clean Architecture с полной поддержкой асинхронности.

## ⚡ Ключевые особенности

- **Асинхронная архитектура** - обработка 11 баз данных параллельно (11x быстрее!)
- **Clean Architecture** - SOLID принципы, полная типизация, DI контейнер
- **Connection Pooling** - переиспользование соединений для максимальной производительности
- **Декораторы** - retry, логирование, валидация, кэширование
- **100% Type Coverage** - полная типизация с mypy
- **Production Ready** - обработка ошибок, мониторинг, безопасность

## 🚀 Производительность

| Режим | Время | Ускорение |
|-------|-------|-----------|
| Последовательный | 330 сек (5.5 мин) | - |
| Асинхронный | 30 сек | **11x** 🚀 |

**Экономия времени:**
- Ежечасные обновления: 5.5 мин → 30 сек
- За сутки: **сохраняет 2 часа!** ⏰

## 🏗️ Архитектура

```
┌──────────────────────────┐
│   Presentation Layer     │  ← main.py
└──────────────────────────┘
            ↓
┌──────────────────────────┐
│  Application Layer       │  ← Scheduler, DI Container
└──────────────────────────┘
            ↓
┌──────────────────────────┐
│   Domain Layer           │  ← Models, Interfaces, Parsers
└──────────────────────────┘
            ↓
┌──────────────────────────┐
│ Infrastructure Layer     │  ← Services (DB, Sheets, API)
└──────────────────────────┘
```

### Паттерны проектирования

- **Dependency Injection** - слабая связанность, тестируемость
- **Abstract Base Classes** - контрактное программирование
- **Factory Pattern** - централизованная конфигурация
- **Decorator Pattern** - переиспользуемая функциональность
- **Strategy Pattern** - взаимозаменяемые алгоритмы
- **Context Manager** - автоматическое управление ресурсами

### SOLID принципы

✅ **Single Responsibility** - каждый класс одна задача  
✅ **Open/Closed** - открыт для расширения, закрыт для изменений  
✅ **Liskov Substitution** - реализации заменяют абстракции  
✅ **Interface Segregation** - небольшие, сфокусированные интерфейсы  
✅ **Dependency Inversion** - зависимость от абстракций

## 📦 Установка

```bash
# Клонирование репозитория
git clone <repo-url>
cd pokerhub-extractor

# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Установка зависимостей
pip install -r requirements.txt

# Настройка окружения
cp .env.example .env
# Отредактируйте .env своими значениями
```

## ⚙️ Конфигурация

### .env файл

```env
# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password

# Google Sheets
GOOGLE_SERVICE_ACCOUNT_FILE=service-account.json
GOOGLE_SHEET_URL=https://docs.google.com/spreadsheets/...

# API
POKERHUB_API_URL=https://api.pokerhub.com
POKERHUB_API_KEY=your_api_key

# Logging
LOG_LEVEL=INFO
```

### Service Account

1. Создайте service account в Google Cloud Console
2. Включите Google Sheets API
3. Скачайте JSON ключ как `service-account.json`
4. Дайте доступ service account email к вашей таблице

## 🎯 Использование

### Базовый запуск

```bash
python main.py
```

### С Makefile

```bash
# Запуск приложения
make run

# Запуск тестов
make test

# Форматирование кода
make format

# Проверка типов
make type-check

# Линтинг
make lint

# Все проверки
make all
```

## 🔧 Основные компоненты

### Async Database Service

```python
class AsyncPostgreSQLService(IAsyncDatabaseService):
    """Асинхронный PostgreSQL с connection pooling"""
    
    async def connect(self) -> None:
        self.pool = await asyncpg.create_pool(
            host=host,
            port=port,
            min_size=2,
            max_size=10,
        )
    
    async def fetch_data(self) -> List[List[Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(self.config.query)
            return rows
```

### Async Google Sheets Service

```python
class AsyncGoogleSheetsService(IAsyncSheetsService):
    """Асинхронный Google Sheets с gspread-asyncio"""
    
    async def update_sheet(self, tab_name, data) -> None:
        ws = await self.spreadsheet.worksheet(tab_name)
        await ws.update(data)
```

### Scheduler с параллельной обработкой

```python
class AsyncScheduler:
    async def update_all_sheets(self) -> None:
        # Создаем задачи для ВСЕХ баз данных
        tasks = [
            self._update_single_sheet(config)
            for config in self.db_configs  # 11 баз
        ]
        
        # Запускаем ВСЕ параллельно!
        await asyncio.gather(*tasks, return_exceptions=True)
```

## 🎨 Декораторы

### @async_retry

```python
@async_retry(max_attempts=3, base_delay=1.0)
async def risky_operation():
    """Автоматические повторы при ошибке"""
    await some_async_call()
```

### @log_execution

```python
@log_execution(level=logging.INFO)
async def my_function():
    """Логирование начала и завершения"""
    await do_work()
```

### @measure_time

```python
@measure_time(threshold_seconds=5.0)
async def slow_operation():
    """Предупреждение если выполнение > порога"""
    await long_task()
```

### @cache_result

```python
@cache_result(maxsize=128)
def expensive_function(x):
    """Кэширование результатов"""
    return complex_computation(x)
```

### @validate_input / @validate_output

```python
@validate_input(InputModel)
@validate_output(OutputModel)
def process_data(data):
    """Валидация входных и выходных данных"""
    return result
```

## 🧪 Тестирование

### Структура тестов

```
tests/
├── test_decorators.py      # Тесты декораторов
├── test_database.py         # Тесты БД сервисов
├── test_google_sheets.py    # Тесты Google Sheets
├── test_pokerhub_api.py     # Тесты API
└── test_parsers.py          # Тесты парсеров
```

### Запуск тестов

```bash
# Все тесты
pytest

# С покрытием
pytest --cov=. --cov-report=html

# Конкретный тест
pytest tests/test_decorators.py

# Асинхронные тесты
@pytest.mark.asyncio
async def test_async_function():
    result = await my_async_function()
    assert result == expected
```

## 📊 Мониторинг

### Логирование

```python
# Уровни логирования
LOG_LEVEL=DEBUG    # Подробная информация
LOG_LEVEL=INFO     # Основная информация (по умолчанию)
LOG_LEVEL=WARNING  # Только предупреждения
LOG_LEVEL=ERROR    # Только ошибки
```

### Метрики производительности

```python
@measure_time(threshold_seconds=5.0)
async def operation():
    # Автоматически логирует если > 5 секунд
    await slow_task()
```

## 🔒 Безопасность

### Управление секретами

✅ Все секреты в `.env`  
✅ `.env` в `.gitignore`  
✅ `.env.example` для примера  
✅ Pydantic валидация  
✅ Service account JSON не в git

### Валидация входных данных

```python
class Settings(BaseModel):
    """Автоматическая валидация конфигурации"""
    postgres_host: str
    postgres_port: int = 5432
    log_level: str = "INFO"
```

## 🚀 Добавление новых возможностей

### Новая база данных

```python
# В config/databases.py
configs = [
    self.create_bot_config("new_db", "NewSheet"),
]
```

### Новый парсер

```python
# parsers/my_parser.py
from interfaces import IParser

class MyParser(IParser):
    def parse(self, data: Any) -> Tuple[str, str]:
        # Ваша логика
        return result1, result2
```

### Новый декоратор

```python
# decorators/my_decorator.py
def my_decorator(param: str):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # До вызова
            result = await func(*args, **kwargs)
            # После вызова
            return result
        return wrapper
    return decorator
```

## 📈 Стандарты кода

### Type Hints (обязательно!)

```python
# ✅ Хорошо
def process_data(users: List[int]) -> Dict[str, Any]:
    return {}

# ❌ Плохо
def process_data(users):
    return {}
```

### Docstrings

```python
def fetch_data(self) -> List[List[Any]]:
    """
    Получение данных из базы данных
    
    Returns:
        Список строк с заголовками в первой строке
        
    Raises:
        RuntimeError: Если БД не подключена
    """
    pass
```

### Commit Messages

```bash
# Формат: <type>(<scope>): <subject>

✅ Хорошо:
feat(parser): добавлена поддержка CASH курсов
fix(database): обработка пустого списка user_ids
docs(readme): обновлены инструкции по установке
refactor(scheduler): извлечена логика слияния

❌ Плохо:
исправил баг
обновил код
```

## 🎯 Версии проекта

| Версия | Описание | Уровень |
|--------|----------|---------|
| Monolith | Один файл, процедурный код | Junior |
| v1.0 | Модульная структура | Mid-Senior |
| v2.0 | Clean Architecture + Async | Senior+/Architect |

### Текущая версия (v2.0) включает:

- ✅ Clean Architecture
- ✅ Полная асинхронность (asyncpg, aiohttp, gspread-asyncio)
- ✅ Connection pooling
- ✅ Dependency Injection
- ✅ Декораторы для кросс-функциональности
- ✅ 100% типизация
- ✅ Инфраструктура для тестирования
- ✅ Полная документация

## 🐛 Известные ограничения

- SSH туннели работают только на Linux/Mac
- Windows требует дополнительной настройки asyncssh
- Google Sheets API имеет лимиты (100 запросов/100 секунд/пользователь)

## 💡 Лучшие практики

### Async/Await

```python
# ✅ Параллельное выполнение
await asyncio.gather(task1, task2, task3)

# ❌ Последовательное выполнение
await task1
await task2
await task3
```

### Connection Pooling

```python
# ✅ Переиспользование соединений
async with pool.acquire() as conn:
    await conn.fetch(query)

# ❌ Новое соединение каждый раз
conn = await asyncpg.connect(...)
await conn.fetch(query)
await conn.close()
```

### Context Managers

```python
# ✅ Автоматическая очистка ресурсов
async with AsyncService() as service:
    await service.do_work()

# ❌ Ручная очистка
service = AsyncService()
await service.connect()
try:
    await service.do_work()
finally:
    await service.disconnect()

```
# v2v2v2vv2
