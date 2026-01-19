import os
import time
from concurrent import futures

import requests
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

# Один поток достаточно: важно показать задержку и что ответ на /set_result приходит сразу
executor = futures.ThreadPoolExecutor(max_workers=1)

MAIN_SERVICE_URL = os.getenv("MAIN_SERVICE_URL", "http://localhost:8080").rstrip("/")
LAB8_TOKEN = os.getenv("LAB8_TOKEN", "lab8tokn")
LAB8_DELAY_SEC = int(os.getenv("LAB8_DELAY_SEC", "6"))  # 5-10 секунд по методичке


def _get_headers() -> dict:
    return {"X-Lab8-Token": LAB8_TOKEN}


def _calculate_total_amount(monthly_payments: list[float]) -> float:
    """
    Расчёт общей суммы ежемесячного платежа по всем кредитным продуктам в заявке.
    
    Формула по предметной области (банковская система):
    total_amount = сумма всех monthly_payment по услугам в заявке
    
    Например, если клиент берёт:
    - Автокредит: 1500 руб/мес
    - Ипотека: 2300 руб/мес
    - Потребительский кредит: 850 руб/мес
    То total_amount = 4650 руб/мес
    """
    total = 0.0
    for p in monthly_payments:
        try:
            total += float(p)
        except (TypeError, ValueError):
            continue
    return round(total, 2)


def _do_async_work(pk: int) -> None:
    try:
        print(f"[КРЕДИТНЫЙ СКОРИНГ] Начало асинхронной обработки заявки ID={pk}")
        
        # 1) имитируем долгий расчет 5-10 секунд (проверка кредитной истории в БКИ)
        print(f"[КРЕДИТНЫЙ СКОРИНГ] Имитация проверки кредитной истории в БКИ ({LAB8_DELAY_SEC} сек)...")
        time.sleep(LAB8_DELAY_SEC)

        # 2) получаем исходные данные для расчета у основного сервиса (без прямого доступа к БД)
        input_url = f"{MAIN_SERVICE_URL}/api/async/applications/{pk}/input"
        print(f"[КРЕДИТНЫЙ СКОРИНГ] Запрос исходных данных заявки: {input_url}")
        
        r = requests.get(input_url, headers=_get_headers(), timeout=5)
        r.raise_for_status()
        data = r.json()
        print(f"[КРЕДИТНЫЙ СКОРИНГ] Получены исходные данные: {data}")

        monthly_payments = data.get("monthly_payments") or []
        total_amount = _calculate_total_amount(monthly_payments)
        
        # Для демонстрации генерируем случайный scoring_result
        import random
        scoring_result = random.choice(["approved", "rejected", "pending"])
        
        print(f"[КРЕДИТНЫЙ СКОРИНГ] ✅ Расчёт завершён:")
        print(f"  - Общая сумма ежемесячного платежа: {total_amount} руб")
        print(f"  - Результат скоринга: {scoring_result.upper()}")

        # 3) отправляем результат обратно в основной сервис (callback) с псевдо-токеном
        callback_url = f"{MAIN_SERVICE_URL}/api/async/applications/{pk}/result"
        print(f"[КРЕДИТНЫЙ СКОРИНГ] Отправка результата в основной сервис: {callback_url}")
        
        callback_response = requests.put(
            callback_url,
            headers=_get_headers(),
            json={"total_amount": total_amount, "scoring_result": scoring_result},
            timeout=5,
        )
        callback_response.raise_for_status()
        
        print(f"[КРЕДИТНЫЙ СКОРИНГ] ✅ Результат успешно передан в банковский сервис, статус={callback_response.status_code}")
        
    except Exception as e:
        print(f"[КРЕДИТНЫЙ СКОРИНГ] ❌ ОШИБКА при обработке заявки ID={pk}: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


@api_view(["GET"])
def health(request):
    return Response(
        {
            "status": "ok",
            "main_service_url": MAIN_SERVICE_URL,
            "delay_sec": LAB8_DELAY_SEC,
        }
    )


@api_view(["POST"])
def set_result(request):
    print(f"[КРЕДИТНЫЙ СКОРИНГ] Получен POST /set_result, данные: {request.data}")
    
    # Принимаем pk из JSON или query param, чтобы удобно тестировать из Insomnia
    pk = request.data.get("pk") if isinstance(request.data, dict) else None
    if pk is None:
        pk = request.query_params.get("pk")

    if pk is None:
        print("[КРЕДИТНЫЙ СКОРИНГ] ❌ Ошибка: pk не передан")
        return Response({"error": "pk is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        pk_int = int(pk)
    except (TypeError, ValueError):
        print(f"[КРЕДИТНЫЙ СКОРИНГ] ❌ Ошибка: pk не число: {pk}")
        return Response({"error": "pk must be int"}, status=status.HTTP_400_BAD_REQUEST)

    # Запуск фоновой задачи
    print(f"[КРЕДИТНЫЙ СКОРИНГ] Запуск асинхронной проверки для заявки ID={pk_int}")
    executor.submit(_do_async_work, pk_int)

    # Быстрый ответ (асинхронность)
    print(f"[КРЕДИТНЫЙ СКОРИНГ] Мгновенный ответ клиенту для заявки ID={pk_int}")
    return Response({"status": "accepted", "pk": pk_int}, status=status.HTTP_200_OK)


