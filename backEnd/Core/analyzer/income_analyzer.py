from typing import List, Dict, Any
from datetime import datetime
from collections import defaultdict
import re


def analyze_income(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Анализ доходов из списка транзакций
    
    :param transactions: Список транзакций
    :return: Результаты анализа доходов
    """
    # Фильтруем только доходные транзакции
    income_transactions = [t for t in transactions if t.get("is_income", False)]
    
    # Если нет доходных транзакций, возвращаем пустой результат
    if not income_transactions:
        return {
            "total": 0,
            "count": 0,
            "average": 0,
            "by_category": {},
            "by_month": {},
            "largest": None,
            "smallest": None,
            "sources": []
        }
    
    # Общая сумма доходов
    total_income = sum(t.get("amount", 0) for t in income_transactions)
    
    # Количество доходных транзакций
    count = len(income_transactions)
    
    # Средний доход
    average_income = total_income / count if count > 0 else 0
    
    # Группировка по категориям
    income_by_category = defaultdict(float)
    for t in income_transactions:
        category = t.get("category", "Другое")
        income_by_category[category] += t.get("amount", 0)
    
    # Группировка по месяцам
    income_by_month = defaultdict(float)
    for t in income_transactions:
        date = t.get("date")
        if date and isinstance(date, datetime):
            month = date.strftime("%Y-%m")
            income_by_month[month] += t.get("amount", 0)
    
    # Находим самую большую и самую маленькую транзакцию
    sorted_transactions = sorted(income_transactions, key=lambda t: t.get("amount", 0), reverse=True)
    largest_transaction = sorted_transactions[0] if sorted_transactions else None
    smallest_transaction = sorted_transactions[-1] if sorted_transactions else None
    
    # Анализ источников дохода
    income_sources = analyze_income_sources(income_transactions)
    
    # Формируем результат
    result = {
        "total": total_income,
        "count": count,
        "average": average_income,
        "by_category": dict(income_by_category),
        "by_month": dict(income_by_month),
        "largest": largest_transaction,
        "smallest": smallest_transaction,
        "sources": income_sources
    }
    
    return result


def analyze_income_sources(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Анализ источников дохода
    
    :param transactions: Список доходных транзакций
    :return: Список источников дохода с суммами
    """
    # Словарь для хранения источников дохода
    sources = defaultdict(float)
    
    # Ключевые слова для определения источников дохода
    source_keywords = {
        "Заработная плата": [
            "зарплата", "заработная плата", "оклад", "аванс", "зп ", "з/п", "выплата", "зар.плата",
            "зар плата", "salary", "wage", "payroll"
        ],
        "Перевод": [
            "перевод", "transfer", "переведено", "поступление", "зачисление", "p2p", "перевод от"
        ],
        "Возврат": [
            "возврат", "refund", "возмещение", "компенсация", "reimbursement", "return"
        ],
        "Продажа товаров": [
            "продажа", "товар", "sale", "торговля", "реализация", "выручка", "товар"
        ],
        "Оказание услуг": [
            "услуги", "сервис", "service", "работы", "консультация", "разработка", "выполнение"
        ],
        "Инвестиции": [
            "дивиденд", "проценты", "вклад", "депозит", "инвестиции", "dividend", "interest", "investment",
            "доход по", "купон"
        ],
        "Кэшбэк": [
            "кэшбэк", "cashback", "кешбэк", "кэшбек", "возврат %", "возврат процента", "бонус"
        ]
    }
    
    # Анализируем каждую транзакцию
    for transaction in transactions:
        description = transaction.get("description", "").lower()
        amount = transaction.get("amount", 0)
        
        # Определяем источник дохода по описанию
        source_found = False
        for source, keywords in source_keywords.items():
            for keyword in keywords:
                if keyword.lower() in description:
                    sources[source] += amount
                    source_found = True
                    break
            if source_found:
                break
        
        # Если источник не определен, относим к категории "Другое"
        if not source_found:
            sources["Другое"] += amount
    
    # Формируем результат
    return [
        {
            "source": source,
            "amount": amount,
            "percentage": (amount / sum(sources.values()) * 100) if sum(sources.values()) > 0 else 0
        }
        for source, amount in sorted(sources.items(), key=lambda x: x[1], reverse=True)
    ]