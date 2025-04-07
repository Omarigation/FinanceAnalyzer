from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Any, Dict, List, Optional
import os
from datetime import datetime
import json

from Access.database import get_db
from Core.auth import get_current_active_user, get_highest_role
from Models.user import User
from Models.statement import StatementFile, Transaction, ProcessingStatusEnum
from Models.analysis import AnalysisResult, AnalysisResultResponse, AnalysisDetailedResponse, AnalysisSummary, AnalysisRecommendation
from Models.event import EventLogCreate, EventTypeEnum, EventStatusEnum, log_event
from Core.analyzer.income_analyzer import analyze_income
from Core.analyzer.expense_analyzer import analyze_expenses
from Core.analyzer.tax_calculator import calculate_tax
from Core.parser.base_parser import get_parser_for_statement

router = APIRouter()

async def process_statement_file(statement_id: int, db: Session):
    """
    Фоновая задача для обработки загруженного файла выписки
    """
    try:
        # Получаем информацию о выписке
        statement = db.query(StatementFile).filter(StatementFile.Id == statement_id).first()
        if not statement:
            return
        
        # Обновляем статус обработки
        statement.ProcessingStatus = ProcessingStatusEnum.PROCESSING
        db.commit()
        
        # Получаем парсер для типа файла
        parser = get_parser_for_statement(statement)
        if not parser:
            statement.ProcessingStatus = ProcessingStatusEnum.FAILED
            db.commit()
            return
        
        # Парсим файл выписки
        transactions = parser.parse_file(statement.FilePath)
        
        # Сохраняем транзакции в базу данных
        for transaction_data in transactions:
            transaction = Transaction(
                StatementFileId=statement.Id,
                TransactionDate=transaction_data["date"],
                Amount=transaction_data["amount"],
                Description=transaction_data["description"],
                CategoryId=transaction_data.get("category_id"),
                IsIncome=transaction_data["is_income"],
                Reference=transaction_data.get("reference")
            )
            db.add(transaction)
        
        # Анализируем доходы
        income_analysis = analyze_income(transactions)
        
        # Анализируем расходы
        expense_analysis = analyze_expenses(transactions)
        
        # Рассчитываем налоги
        tax_calculation = calculate_tax(income_analysis["total"], expense_analysis["total"])
        
        # Создаем запись с результатами анализа
        total_income = income_analysis["total"]
        total_expense = expense_analysis["total"]
        net_profit = total_income - total_expense
        
        analysis_result = AnalysisResult(
            StatementFileId=statement.Id,
            TotalIncome=total_income,
            TotalExpense=total_expense,
            NetProfit=net_profit,
            RecommendedTaxAmount=tax_calculation["tax_amount"]
        )
        
        db.add(analysis_result)
        
        # Обновляем статус обработки
        statement.ProcessingStatus = ProcessingStatusEnum.COMPLETED
        statement.ProcessingDate = datetime.now()
        
        db.commit()
        
        # Логируем успешную обработку
        event_data = EventLogCreate(
            user_id=statement.UserId,
            event_type=EventTypeEnum.GET_ANALYSIS,
            event_status=EventStatusEnum.SUCCESS,
            description=f"Успешная обработка выписки: {statement.Id}, файл: {statement.FileName}"
        )
        log_event(db, event_data)
        
    except Exception as e:
        # В случае ошибки обновляем статус
        if statement:
            statement.ProcessingStatus = ProcessingStatusEnum.FAILED
            db.commit()
        
        # Логируем ошибку
        event_data = EventLogCreate(
            user_id=statement.UserId if statement else None,
            event_type=EventTypeEnum.GET_ANALYSIS,
            event_status=EventStatusEnum.FAILED,
            description=f"Ошибка при обработке выписки: {statement_id if statement_id else 'unknown'}, ошибка: {str(e)}"
        )
        log_event(db, event_data)


@router.post("/process/{statement_id}", response_model=Dict[str, str])
async def start_analysis(
    statement_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Запуск процесса анализа выписки
    """
    # Получаем информацию о выписке
    statement = db.query(StatementFile).filter(
        StatementFile.Id == statement_id,
        StatementFile.UserId == current_user.Id
    ).first()
    
    if not statement:
        # Логируем попытку анализа недоступной выписки
        event_data = EventLogCreate(
            user_id=current_user.Id,
            event_type=EventTypeEnum.GET_ANALYSIS,
            event_status=EventStatusEnum.FAILED,
            description=f"Попытка анализа недоступной выписки: {statement_id}",
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent")
        )
        log_event(db, event_data)
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Выписка не найдена или доступ запрещен"
        )
    
    # Проверяем текущий статус обработки
    if statement.ProcessingStatus == ProcessingStatusEnum.PROCESSING:
        return {"status": "processing", "message": "Анализ уже выполняется"}
    
    # Добавляем задачу в фоновые задачи
    background_tasks.add_task(process_statement_file, statement_id, db)
    
    # Логируем запуск анализа
    event_data = EventLogCreate(
        user_id=current_user.Id,
        event_type=EventTypeEnum.GET_ANALYSIS,
        event_status=EventStatusEnum.SUCCESS,
        description=f"Запуск анализа выписки: {statement_id}",
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    log_event(db, event_data)
    
    return {"status": "started", "message": "Анализ запущен"}


@router.get("/results/{statement_id}", response_model=AnalysisResultResponse)
async def get_analysis_results(
    statement_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Получение результатов анализа выписки
    """
    # Получаем информацию о выписке
    statement = db.query(StatementFile).filter(
        StatementFile.Id == statement_id,
        StatementFile.UserId == current_user.Id
    ).first()
    
    if not statement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Выписка не найдена или доступ запрещен"
        )
    
    # Получаем результаты анализа
    analysis_result = db.query(AnalysisResult).filter(
        AnalysisResult.StatementFileId == statement_id
    ).first()
    
    if not analysis_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Результаты анализа не найдены"
        )
    
    # Возвращаем результаты анализа
    return {
        "id": analysis_result.Id,
        "statement_file": {
            "id": statement.Id,
            "file_name": statement.FileName,
            "upload_date": statement.UploadDate
        },
        "total_income": float(analysis_result.TotalIncome),
        "total_expense": float(analysis_result.TotalExpense),
        "net_profit": float(analysis_result.NetProfit),
        "recommended_tax_amount": float(analysis_result.RecommendedTaxAmount),
        "analysis_date": analysis_result.AnalysisDate
    }


@router.get("/detailed/{statement_id}", response_model=AnalysisDetailedResponse)
async def get_detailed_analysis(
    statement_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Получение детального анализа выписки
    """
    # Получаем информацию о выписке
    statement = db.query(StatementFile).filter(
        StatementFile.Id == statement_id,
        StatementFile.UserId == current_user.Id
    ).first()
    
    if not statement:
        # Логируем попытку получения детального анализа недоступной выписки
        event_data = EventLogCreate(
            user_id=current_user.Id,
            event_type=EventTypeEnum.GET_ANALYSIS,
            event_status=EventStatusEnum.FAILED,
            description=f"Попытка получения детального анализа недоступной выписки: {statement_id}",
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent")
        )
        log_event(db, event_data)
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Выписка не найдена или доступ запрещен"
        )
    
    # Получаем результаты анализа
    analysis_result = db.query(AnalysisResult).filter(
        AnalysisResult.StatementFileId == statement_id
    ).first()
    
    if not analysis_result:
        # Логируем попытку получения несуществующего анализа
        event_data = EventLogCreate(
            user_id=current_user.Id,
            event_type=EventTypeEnum.GET_ANALYSIS,
            event_status=EventStatusEnum.FAILED,
            description=f"Попытка получения несуществующего анализа для выписки: {statement_id}",
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent")
        )
        log_event(db, event_data)
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Результаты анализа не найдены"
        )
    
    # Получаем все транзакции для выписки
    transactions = db.query(Transaction).filter(
        Transaction.StatementFileId == statement_id
    ).all()
    
    # Формируем список транзакций
    transactions_list = []
    for transaction in transactions:
        category_name = None
        if transaction.category:
            category_name = transaction.category.Name
        
        transactions_list.append({
            "id": transaction.Id,
            "date": transaction.TransactionDate,
            "amount": float(transaction.Amount),
            "description": transaction.Description,
            "category": category_name,
            "is_income": transaction.IsIncome,
            "reference": transaction.Reference
        })
    
    # Анализируем доходы по категориям
    income_categories = {}
    expense_categories = {}
    
    for transaction in transactions:
        category_name = "Другое"
        if transaction.category:
            category_name = transaction.category.Name
        
        if transaction.IsIncome:
            if category_name not in income_categories:
                income_categories[category_name] = 0
            income_categories[category_name] += float(transaction.Amount)
        else:
            if category_name not in expense_categories:
                expense_categories[category_name] = 0
            expense_categories[category_name] += float(transaction.Amount)
    
    # Сортируем категории по сумме (по убыванию)
    top_income_categories = [
        {"category": k, "amount": v}
        for k, v in sorted(income_categories.items(), key=lambda item: item[1], reverse=True)
    ][:5]  # Топ-5 категорий доходов
    
    top_expense_categories = [
        {"category": k, "amount": v}
        for k, v in sorted(expense_categories.items(), key=lambda item: item[1], reverse=True)
    ][:5]  # Топ-5 категорий расходов
    
    # Анализируем транзакции по месяцам
    monthly_data = {}
    
    for transaction in transactions:
        month = transaction.TransactionDate.strftime("%Y-%m")
        if month not in monthly_data:
            monthly_data[month] = {
                "income": 0,
                "expense": 0,
                "profit": 0
            }
        
        if transaction.IsIncome:
            monthly_data[month]["income"] += float(transaction.Amount)
        else:
            monthly_data[month]["expense"] += float(transaction.Amount)
        
        monthly_data[month]["profit"] = monthly_data[month]["income"] - monthly_data[month]["expense"]
    
    # Преобразуем данные по месяцам в список
    monthly_summary = [
        {
            "month": k,
            "income": v["income"],
            "expense": v["expense"],
            "profit": v["profit"]
        }
        for k, v in sorted(monthly_data.items())
    ]
    
    # Рассчитываем маржу прибыли
    total_income = float(analysis_result.TotalIncome)
    total_expense = float(analysis_result.TotalExpense)
    net_profit = float(analysis_result.NetProfit)
    
    profit_margin = 0
    if total_income > 0:
        profit_margin = (net_profit / total_income) * 100
    
    # Формируем сводку анализа
    summary = {
        "total_income": total_income,
        "total_expense": total_expense,
        "net_profit": net_profit,
        "profit_margin": profit_margin,
        "recommended_tax_amount": float(analysis_result.RecommendedTaxAmount),
        "top_income_categories": top_income_categories,
        "top_expense_categories": top_expense_categories,
        "monthly_summary": monthly_summary
    }
    
    # Формируем рекомендации
    recommendations = []
    
    # Рекомендация по налогам
    recommendations.append({
        "type": "tax",
        "title": "Оплата налогов",
        "description": f"Рекомендуется отложить {analysis_result.RecommendedTaxAmount:.2f} KZT на оплату налогов.",
        "importance": 5
    })
    
    # Рекомендации по расходам
    if len(top_expense_categories) > 0:
        highest_expense = top_expense_categories[0]
        if highest_expense["amount"] > total_income * 0.3:
            recommendations.append({
                "type": "expense",
                "title": f"Высокие расходы в категории '{highest_expense['category']}'",
                "description": f"Расходы в категории '{highest_expense['category']}' составляют более 30% от общего дохода. Рассмотрите возможность оптимизации.",
                "importance": 4
            })
    
    # Рекомендация по прибыльности
    if profit_margin < 15:
        recommendations.append({
            "type": "general",
            "title": "Низкая рентабельность",
            "description": f"Маржа прибыли составляет {profit_margin:.2f}%, что ниже рекомендуемого значения (15%). Рассмотрите возможности увеличения доходов или снижения расходов.",
            "importance": 4
        })
    elif profit_margin > 50:
        recommendations.append({
            "type": "general",
            "title": "Высокая рентабельность",
            "description": f"Маржа прибыли составляет {profit_margin:.2f}%, что значительно выше среднего. Отличный результат!",
            "importance": 3
        })
    
    # Данные для графиков
    charts_data = {
        "income_by_category": top_income_categories,
        "expense_by_category": top_expense_categories,
        "monthly_summary": monthly_summary
    }
    
    # Логируем успешное получение детального анализа
    event_data = EventLogCreate(
        user_id=current_user.Id,
        event_type=EventTypeEnum.GET_ANALYSIS,
        event_status=EventStatusEnum.SUCCESS,
        description=f"Успешное получение детального анализа для выписки: {statement_id}",
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    log_event(db, event_data)
    
    # Возвращаем детальный анализ
    return {
        "analysis_result": {
            "id": analysis_result.Id,
            "statement_file": {
                "id": statement.Id,
                "file_name": statement.FileName,
                "upload_date": statement.UploadDate
            },
            "total_income": total_income,
            "total_expense": total_expense,
            "net_profit": net_profit,
            "recommended_tax_amount": float(analysis_result.RecommendedTaxAmount),
            "analysis_date": analysis_result.AnalysisDate
        },
        "summary": summary,
        "transactions": transactions_list,
        "recommendations": recommendations,
        "charts_data": charts_data
    }


@router.get("/status/{statement_id}", response_model=Dict[str, Any])
async def get_analysis_status(
    statement_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Получение статуса обработки выписки
    """
    # Получаем информацию о выписке
    statement = db.query(StatementFile).filter(
        StatementFile.Id == statement_id,
        StatementFile.UserId == current_user.Id
    ).first()
    
    if not statement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Выписка не найдена или доступ запрещен"
        )
    
    # Возвращаем статус обработки
    return {
        "id": statement.Id,
        "file_name": statement.FileName,
        "processing_status": statement.ProcessingStatus,
        "processing_date": statement.ProcessingDate,
        "has_results": db.query(AnalysisResult).filter(AnalysisResult.StatementFileId == statement_id).count() > 0
    }


@router.post("/guest-analysis/{statement_id}", response_model=Dict[str, Any])
async def guest_analysis(
    statement_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> Any:
    """
    Анализ выписки для гостя (без авторизации)
    """
    # Получаем информацию о выписке (для гостя UserId = NULL)
    statement = db.query(StatementFile).filter(
        StatementFile.Id == statement_id,
        StatementFile.UserId.is_(None)
    ).first()
    
    if not statement:
        # Логируем попытку гостевого анализа недоступной выписки
        event_data = EventLogCreate(
            event_type=EventTypeEnum.GET_ANALYSIS,
            event_status=EventStatusEnum.FAILED,
            description=f"Попытка гостевого анализа недоступной выписки: {statement_id}",
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent")
        )
        log_event(db, event_data)
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Выписка не найдена или доступ запрещен"
        )
    
    # Проверяем текущий статус обработки
    if statement.ProcessingStatus == ProcessingStatusEnum.PROCESSING:
        return {"status": "processing", "message": "Анализ уже выполняется"}
    
    # Если анализ еще не выполнен, запускаем обработку
    if statement.ProcessingStatus != ProcessingStatusEnum.COMPLETED:
        # Добавляем задачу в фоновые задачи
        background_tasks.add_task(process_statement_file, statement_id, db)
        
        # Логируем запуск гостевого анализа
        event_data = EventLogCreate(
            event_type=EventTypeEnum.GET_ANALYSIS,
            event_status=EventStatusEnum.SUCCESS,
            description=f"Запуск гостевого анализа выписки: {statement_id}",
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent")
        )
        log_event(db, event_data)
        
        # Возвращаем статус запуска
        return {"status": "started", "message": "Анализ запущен"}
    
    # Если анализ уже выполнен, получаем результаты
    analysis_result = db.query(AnalysisResult).filter(
        AnalysisResult.StatementFileId == statement_id
    ).first()
    
    if not analysis_result:
        # Логируем попытку получения несуществующего анализа
        event_data = EventLogCreate(
            event_type=EventTypeEnum.GET_ANALYSIS,
            event_status=EventStatusEnum.FAILED,
            description=f"Попытка гостевого получения несуществующего анализа для выписки: {statement_id}",
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent")
        )
        log_event(db, event_data)
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Результаты анализа не найдены"
        )
    
    # Для гостевого анализа используем тот же код, что и для авторизованного пользователя
    # Получаем все транзакции для выписки
    transactions = db.query(Transaction).filter(
        Transaction.StatementFileId == statement_id
    ).all()
    
    # Формируем список транзакций
    transactions_list = []
    for transaction in transactions:
        category_name = None
        if transaction.category:
            category_name = transaction.category.Name
        
        transactions_list.append({
            "id": transaction.Id,
            "date": transaction.TransactionDate,
            "amount": float(transaction.Amount),
            "description": transaction.Description,
            "category": category_name,
            "is_income": transaction.IsIncome,
            "reference": transaction.Reference
        })
    
    # Анализируем доходы и расходы по категориям
    # (код аналогичен коду для авторизованного пользователя)
    income_categories = {}
    expense_categories = {}
    
    for transaction in transactions:
        category_name = "Другое"
        if transaction.category:
            category_name = transaction.category.Name
        
        if transaction.IsIncome:
            if category_name not in income_categories:
                income_categories[category_name] = 0
            income_categories[category_name] += float(transaction.Amount)
        else:
            if category_name not in expense_categories:
                expense_categories[category_name] = 0
            expense_categories[category_name] += float(transaction.Amount)
    
    # Сортируем категории по сумме (по убыванию)
    top_income_categories = [
        {"category": k, "amount": v}
        for k, v in sorted(income_categories.items(), key=lambda item: item[1], reverse=True)
    ][:5]  # Топ-5 категорий доходов
    
    top_expense_categories = [
        {"category": k, "amount": v}
        for k, v in sorted(expense_categories.items(), key=lambda item: item[1], reverse=True)
    ][:5]  # Топ-5 категорий расходов
    
    # Анализируем транзакции по месяцам
    monthly_data = {}
    
    for transaction in transactions:
        month = transaction.TransactionDate.strftime("%Y-%m")
        if month not in monthly_data:
            monthly_data[month] = {
                "income": 0,
                "expense": 0,
                "profit": 0
            }
        
        if transaction.IsIncome:
            monthly_data[month]["income"] += float(transaction.Amount)
        else:
            monthly_data[month]["expense"] += float(transaction.Amount)
        
        monthly_data[month]["profit"] = monthly_data[month]["income"] - monthly_data[month]["expense"]
    
    # Преобразуем данные по месяцам в список
    monthly_summary = [
        {
            "month": k,
            "income": v["income"],
            "expense": v["expense"],
            "profit": v["profit"]
        }
        for k, v in sorted(monthly_data.items())
    ]
    
    # Рассчитываем маржу прибыли
    total_income = float(analysis_result.TotalIncome)
    total_expense = float(analysis_result.TotalExpense)
    net_profit = float(analysis_result.NetProfit)
    
    profit_margin = 0
    if total_income > 0:
        profit_margin = (net_profit / total_income) * 100
    
    # Формируем сводку анализа
    summary = {
        "total_income": total_income,
        "total_expense": total_expense,
        "net_profit": net_profit,
        "profit_margin": profit_margin,
        "recommended_tax_amount": float(analysis_result.RecommendedTaxAmount),
        "top_income_categories": top_income_categories,
        "top_expense_categories": top_expense_categories,
        "monthly_summary": monthly_summary
    }
    
    # Формируем рекомендации
    recommendations = []
    
    # Рекомендация по налогам
    recommendations.append({
        "type": "tax",
        "title": "Оплата налогов",
        "description": f"Рекомендуется отложить {analysis_result.RecommendedTaxAmount:.2f} KZT на оплату налогов.",
        "importance": 5
    })
    
    # Рекомендации по расходам
    if len(top_expense_categories) > 0:
        highest_expense = top_expense_categories[0]
        if highest_expense["amount"] > total_income * 0.3:
            recommendations.append({
                "type": "expense",
                "title": f"Высокие расходы в категории '{highest_expense['category']}'",
                "description": f"Расходы в категории '{highest_expense['category']}' составляют более 30% от общего дохода. Рассмотрите возможность оптимизации.",
                "importance": 4
            })
    
    # Рекомендация по прибыльности
    if profit_margin < 15:
        recommendations.append({
            "type": "general",
            "title": "Низкая рентабельность",
            "description": f"Маржа прибыли составляет {profit_margin:.2f}%, что ниже рекомендуемого значения (15%). Рассмотрите возможности увеличения доходов или снижения расходов.",
            "importance": 4
        })
    elif profit_margin > 50:
        recommendations.append({
            "type": "general",
            "title": "Высокая рентабельность",
            "description": f"Маржа прибыли составляет {profit_margin:.2f}%, что значительно выше среднего. Отличный результат!",
            "importance": 3
        })
    
    # Данные для графиков
    charts_data = {
        "income_by_category": top_income_categories,
        "expense_by_category": top_expense_categories,
        "monthly_summary": monthly_summary
    }
    
    # Логируем успешное получение гостевого анализа
    event_data = EventLogCreate(
        event_type=EventTypeEnum.GET_ANALYSIS,
        event_status=EventStatusEnum.SUCCESS,
        description=f"Успешное получение гостевого анализа для выписки: {statement_id}",
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    log_event(db, event_data)
    
    # Возвращаем детальный анализ (для гостя)
    return {
        "analysis_result": {
            "id": analysis_result.Id,
            "statement_file": {
                "id": statement.Id,
                "file_name": statement.FileName,
                "upload_date": statement.UploadDate
            },
            "total_income": total_income,
            "total_expense": total_expense,
            "net_profit": net_profit,
            "recommended_tax_amount": float(analysis_result.RecommendedTaxAmount),
            "analysis_date": analysis_result.AnalysisDate
        },
        "summary": summary,
        "transactions": transactions_list,
        "recommendations": recommendations,
        "charts_data": charts_data
    }