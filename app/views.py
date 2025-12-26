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
    # Формула по предметной области: суммарный ежемесячный платеж по всем услугам в заявке
    total = 0.0
    for p in monthly_payments:
        try:
            total += float(p)
        except (TypeError, ValueError):
            continue
    return round(total, 2)


def _do_async_work(pk: int) -> None:
    try:
        print(f"[ЛР8] Начало async обработки для заявки ID={pk}")
        
        # 1) имитируем долгий расчет 5-10 секунд
        print(f"[ЛР8] Задержка {LAB8_DELAY_SEC} секунд...")
        time.sleep(LAB8_DELAY_SEC)

        # 2) получаем исходные данные для расчета у основного сервиса (без прямого доступа к БД)
        input_url = f"{MAIN_SERVICE_URL}/api/async/applications/{pk}/input"
        print(f"[ЛР8] Запрос исходных данных: {input_url}")
        
        r = requests.get(input_url, headers=_get_headers(), timeout=5)
        r.raise_for_status()
        data = r.json()
        print(f"[ЛР8] Получены исходные данные: {data}")

        monthly_payments = data.get("monthly_payments") or []
        total_amount = _calculate_total_amount(monthly_payments)
        
        # Для демонстрации генерируем случайный scoring_result
        import random
        scoring_result = random.choice(["approved", "rejected", "pending"])
        
        print(f"[ЛР8] Рассчитано: total_amount={total_amount}, scoring_result={scoring_result}")

        # 3) отправляем результат обратно в основной сервис (callback) с псевдо-токеном
        callback_url = f"{MAIN_SERVICE_URL}/api/async/applications/{pk}/result"
        print(f"[ЛР8] Отправка callback: {callback_url}")
        
        callback_response = requests.put(
            callback_url,
            headers=_get_headers(),
            json={"total_amount": total_amount, "scoring_result": scoring_result},
            timeout=5,
        )
        callback_response.raise_for_status()
        
        print(f"[ЛР8] ✅ Callback успешно отправлен для ID={pk}, статус={callback_response.status_code}")
        
    except Exception as e:
        print(f"[ЛР8] ❌ ОШИБКА при обработке ID={pk}: {type(e).__name__}: {e}")
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
    print(f"[ЛР8] Получен POST /set_result, данные: {request.data}")
    
    # Принимаем pk из JSON или query param, чтобы удобно тестировать из Insomnia
    pk = request.data.get("pk") if isinstance(request.data, dict) else None
    if pk is None:
        pk = request.query_params.get("pk")

    if pk is None:
        print("[ЛР8] ❌ Ошибка: pk не передан")
        return Response({"error": "pk is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        pk_int = int(pk)
    except (TypeError, ValueError):
        print(f"[ЛР8] ❌ Ошибка: pk не число: {pk}")
        return Response({"error": "pk must be int"}, status=status.HTTP_400_BAD_REQUEST)

    # Запуск фоновой задачи
    print(f"[ЛР8] Запуск фоновой задачи для ID={pk_int}")
    executor.submit(_do_async_work, pk_int)

    # Быстрый ответ (асинхронность)
    print(f"[ЛР8] Мгновенный ответ клиенту для ID={pk_int}")
    return Response({"status": "accepted", "pk": pk_int}, status=status.HTTP_200_OK)


