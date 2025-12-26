## Async Django сервис для ЛР8

Этот сервис реализует **один HTTP метод** `POST /set_result` и выполняет «долгое» вычисление **5–10 секунд** в фоне, а затем отправляет callback в основной Go‑сервис **по HTTP** (без прямого обращения к БД).

### Переменные окружения

- `MAIN_SERVICE_URL` — base URL основного Go‑сервиса (например `http://localhost:8080`)
- `LAB8_TOKEN` — псевдо‑токен (должен совпадать с `config/config*.toml` в Go, по умолчанию `lab8tokn`)
- `LAB8_DELAY_SEC` — задержка (по умолчанию `6`)

### Запуск (локально)

```bash
cd async-django
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py runserver 0.0.0.0:8090
```

### Пример запроса (Insomnia/Postman)

`POST /set_result` с JSON:

```json
{ "pk": 123 }
```

Ответ приходит сразу, а результат обновится в основном сервисе через ~`LAB8_DELAY_SEC` секунд.


