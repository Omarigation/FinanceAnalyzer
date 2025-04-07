from typing import Dict, Any, Optional
from config import DEFAULT_TAX_RATES


def calculate_tax(income: float, expense: float, tax_regime: str = "ip_simplified") -> Dict[str, Any]:
    """
    Рассчитывает налоги на основе дохода и расхода
    
    :param income: Сумма дохода
    :param expense: Сумма расхода
    :param tax_regime: Налоговый режим (ip_simplified, ip_general, too_simplified, too_general)
    :return: Данные о налогах
    """
    # Получаем налоговую ставку для выбранного режима
    tax_rate = DEFAULT_TAX_RATES.get(tax_regime, 3.0)
    
    # Расчет налоговой базы в зависимости от режима
    if tax_regime == "ip_simplified" or tax_regime == "too_simplified":
        # Для упрощенного режима налоговая база - это общий доход
        tax_base = income
    else:
        # Для общего режима налоговая база - это доход минус расход (прибыль)
        tax_base = max(0, income - expense)
    
    # Расчет суммы налога
    tax_amount = tax_base * (tax_rate / 100)
    
    # Расчет эффективной налоговой ставки
    effective_tax_rate = (tax_amount / income) * 100 if income > 0 else 0
    
    # Формируем результат
    result = {
        "tax_regime": tax_regime,
        "tax_rate": tax_rate,
        "tax_base": tax_base,
        "tax_amount": tax_amount,
        "effective_tax_rate": effective_tax_rate,
        "income": income,
        "expense": expense,
        "profit": income - expense
    }
    
    return result


def calculate_tax_for_all_regimes(income: float, expense: float) -> Dict[str, Dict[str, Any]]:
    """
    Рассчитывает налоги для всех доступных налоговых режимов
    
    :param income: Сумма дохода
    :param expense: Сумма расхода
    :return: Данные о налогах для всех режимов
    """
    regimes = {
        "ip_simplified": "ИП, упрощенный режим (доход)",
        "ip_general": "ИП, общий режим (прибыль)",
        "too_simplified": "ТОО, упрощенный режим (доход)",
        "too_general": "ТОО, общий режим (прибыль)"
    }
    
    result = {}
    
    for regime_code, regime_name in regimes.items():
        tax_data = calculate_tax(income, expense, regime_code)
        tax_data["regime_name"] = regime_name
        result[regime_code] = tax_data
    
    # Находим оптимальный режим (с минимальной суммой налога)
    min_tax_regime = min(result.items(), key=lambda x: x[1]["tax_amount"])
    result["optimal_regime"] = min_tax_regime[0]
    
    return result


def get_tax_savings_recommendations(tax_data: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Формирует рекомендации по налоговой оптимизации
    
    :param tax_data: Данные о налогах для всех режимов
    :return: Рекомендации по налоговой оптимизации
    """
    optimal_regime = tax_data["optimal_regime"]
    optimal_tax = tax_data[optimal_regime]
    
    # Сравниваем с текущим режимом (предполагаем, что текущий режим - упрощенный ИП)
    current_regime = "ip_simplified"
    current_tax = tax_data[current_regime]
    
    # Рассчитываем возможную экономию
    potential_savings = current_tax["tax_amount"] - optimal_tax["tax_amount"]
    
    # Формируем рекомендации
    recommendations = []
    
    if potential_savings > 0:
        recommendations.append({
            "title": f"Смена налогового режима на {optimal_tax['regime_name']}",
            "description": f"Вы можете сэкономить {potential_savings:.2f} KZT на налогах, перейдя на {optimal_tax['regime_name']}.",
            "savings": potential_savings,
            "priority": "Высокий" if potential_savings > 10000 else "Средний"
        })
    
    # Добавляем общие рекомендации по оптимизации налогов
    if tax_data["ip_general"]["tax_amount"] < tax_data["ip_simplified"]["tax_amount"]:
        recommendations.append({
            "title": "Учет расходов",
            "description": "Официальный учет расходов может снизить налоговую нагрузку при общем режиме налогообложения.",
            "savings": tax_data["ip_simplified"]["tax_amount"] - tax_data["ip_general"]["tax_amount"],
            "priority": "Средний"
        })
    
    # Рекомендации по планированию
    recommendations.append({
        "title": "Налоговое планирование",
        "description": "Заранее планируйте крупные закупки и платежи для оптимизации налоговой нагрузки.",
        "savings": None,
        "priority": "Низкий"
    })
    
    return {
        "recommendations": recommendations,
        "current_regime": current_regime,
        "optimal_regime": optimal_regime,
        "potential_savings": potential_savings
    }