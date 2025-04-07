from typing import List, Dict, Any
from datetime import datetime
from collections import defaultdict
import re


def analyze_expenses(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Анализ расходов из списка транзакций
    
    :param transactions: Список транзакций
    :return: Результаты анализа расходов
    """
    # Фильтруем только расходные транзакции
    expense_transactions = [t for t in transactions if not t.get("is_income", True)]
    
    # Если нет расходных транзакций, возвращаем пустой результат
    if not expense_transactions:
        return {
            "total": 0,
            "count": 0,
            "average": 0,
            "by_category": {},
            "by_month": {},
            "largest": None,
            "smallest": None,
            "categories": []
        }
    
    # Общая сумма расходов
    total_expense = sum(t.get("amount", 0) for t in expense_transactions)
    
    # Количество расходных транзакций
    count = len(expense_transactions)
    
    # Средний расход
    average_expense = total_expense / count if count > 0 else 0
    
    # Группировка по категориям
    expense_by_category = defaultdict(float)
    for t in expense_transactions:
        category = t.get("category", "Другое")
        expense_by_category[category] += t.get("amount", 0)
    
    # Группировка по месяцам
    expense_by_month = defaultdict(float)
    for t in expense_transactions:
        date = t.get("date")
        if date and isinstance(date, datetime):
            month = date.strftime("%Y-%m")
            expense_by_month[month] += t.get("amount", 0)
    
    # Находим самую большую и самую маленькую транзакцию
    sorted_transactions = sorted(expense_transactions, key=lambda t: t.get("amount", 0), reverse=True)
    largest_transaction = sorted_transactions[0] if sorted_transactions else None
    smallest_transaction = sorted_transactions[-1] if sorted_transactions else None
    
    # Анализ категорий расходов
    expense_categories = categorize_expenses(expense_transactions)
    
    # Формируем результат
    result = {
        "total": total_expense,
        "count": count,
        "average": average_expense,
        "by_category": dict(expense_by_category),
        "by_month": dict(expense_by_month),
        "largest": largest_transaction,
        "smallest": smallest_transaction,
        "categories": expense_categories
    }
    
    return result


def categorize_expenses(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Категоризация расходов по ключевым словам
    
    :param transactions: Список расходных транзакций
    :return: Список категорий расходов с суммами
    """
    # Словарь для хранения категорий расходов
    categories = defaultdict(float)
    
    # Ключевые слова для определения категорий расходов
    category_keywords = {
        "Аренда": [
            "аренда", "съем", "rent", "недвижимость", "офис", "помещение"
        ],
        "Коммунальные услуги": [
            "коммунальные", "электричество", "вода", "газ", "отопление", "utility",
            "электроэнергия", "жкх", "квартплата"
        ],
        "Зарплата": [
            "зарплата", "оклад", "аванс", "заработная плата", "вознаграждение", "платеж", "сотрудник",
            "зп", "з/п", "оплата труда", "salary", "wage"
        ],
        "Налоги": [
            "налог", "tax", "сбор", "пошлина", "взнос", "ндс", "подоходный", "енвд",
            "усн", "налог на имущество", "ндфл", "налоговая"
        ],
        "Связь и интернет": [
            "телефон", "мобильный", "интернет", "связь", "телеком", "билайн", "мтс", "мегафон",
            "теле2", "beeline", "telephone", "internet", "сотовый", "роутер", "хостинг", "domain"
        ],
        "Канцелярские товары": [
            "канцелярия", "канцтовары", "бумага", "ручки", "office supplies", "канц", "печать",
            "принтер", "заправка картриджа", "тонер", "картридж"
        ],
        "Транспортные расходы": [
            "транспорт", "такси", "проезд", "доставка", "transport", "яндекс такси", "uber", "убер",
            "перевозка", "логистика", "топливо", "бензин", "дизель", "гсм"
        ],
        "Маркетинг и реклама": [
            "реклама", "маркетинг", "продвижение", "advertising", "marketing", "реклама", "smm", "пиар",
            "pr", "контекст", "таргет", "target", "рекламная кампания", "рекламный", "размещение рекламы"
        ],
        "Закупка товаров": [
            "товар", "закупка", "поставка", "запасы", "supply", "purchase", "закуп", "поставщик", "опт",
            "wholesale", "оптовый", "материалы", "сырьё", "сырье", "партия товара"
        ],
        "Программное обеспечение": [
            "программное обеспечение", "software", "софт", "лицензия", "license", "подписка", "subscription",
            "облако", "cloud", "saas", "сервис", "продление", "renewal"
        ],
        "Оборудование": [
            "оборудование", "компьютер", "ноутбук", "принтер", "hardware", "устройство", "техника",
            "equipment", "монитор", "сервер", "устройство", "гаджет", "оргтехника"
        ],
        "Обучение и развитие": [
            "обучение", "курс", "тренинг", "семинар", "education", "training", "повышение квалификации",
            "development", "conference", "конференция", "вебинар", "мастер-класс", "workshop"
        ],
        "Питание": [
            "питание", "еда", "продукты", "food", "обед", "ресторан", "кафе", "столовая", "перекус",
            "lunch", "кофе", "coffee", "meal", "ужин", "завтрак"
        ],
        "Представительские расходы": [
            "представительские", "деловая встреча", "business meeting", "клиент", "переговоры", "ресторан",
            "банкет", "entertainment", "мероприятие", "event", "hospitality"
        ]
    }
    
    # Анализируем каждую транзакцию
    for transaction in transactions:
        description = transaction.get("description", "").lower()
        amount = transaction.get("amount", 0)
        
        # Определяем категорию расхода по описанию
        category_found = False
        for category, keywords in category_keywords.items():
            for keyword in keywords:
                if keyword.lower() in description:
                    categories[category] += amount
                    category_found = True
                    break
            if category_found:
                break
        
        # Если категория не определена, относим к категории "Другое"
        if not category_found:
            categories["Другое"] += amount
    
    # Формируем результат
    return [
        {
            "category": category,
            "amount": amount,
            "percentage": (amount / sum(categories.values()) * 100) if sum(categories.values()) > 0 else 0
        }
        for category, amount in sorted(categories.items(), key=lambda x: x[1], reverse=True)
    ]