import re
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd

from Core.parser.base_parser import BaseParser, PDFParser, ExcelParser, CSVParser
from Models.statement import StatementFile


class KaspiPDFParser(PDFParser):
    """
    Парсер выписок Kaspi Bank в формате PDF
    """
    
    def __init__(self, statement: StatementFile = None):
        super().__init__(statement)
    
    def get_bank_code(self) -> str:
        """
        Получение кода банка
        
        :return: Код банка (KASPI)
        """
        return "KASPI"
    
    def parse_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Парсинг PDF-файла выписки Kaspi Bank
        
        :param file_path: Путь к файлу выписки
        :return: Список транзакций
        """
        if not self.validate_file(file_path):
            print(f"Файл не найден: {file_path}")
            return []
        
        # Извлекаем текст из PDF
        text = self.extract_text_from_pdf(file_path)
        
        # Список для хранения транзакций
        transactions = []
        
        # Паттерн для поиска транзакций в выписке Kaspi
        # Формат: Дата | Описание | Сумма | Тип (приход/расход)
        transaction_pattern = r'(\d{2}\.\d{2}\.\d{4})\s+(.+?)\s+([\d\s,.]+)\s*(тг|₸)?\s+(приход|расход)'
        
        # Находим все транзакции в тексте
        matches = re.finditer(transaction_pattern, text, re.MULTILINE)
        
        for match in matches:
            date_str, description, amount_str, currency, transaction_type = match.groups()
            
            # Преобразуем дату
            try:
                date = datetime.strptime(date_str, "%d.%m.%Y")
            except ValueError:
                # Если не удалось разобрать дату, пропускаем транзакцию
                continue
            
            # Очищаем сумму от пробелов и заменяем запятую на точку
            amount_str = amount_str.replace(' ', '').replace(',', '.')
            
            try:
                amount = float(amount_str)
            except ValueError:
                # Если не удалось преобразовать сумму, пропускаем транзакцию
                continue
            
            # Определяем, доход это или расход
            is_income = transaction_type.lower() == 'приход'
            
            # Если это расход, меняем знак суммы
            if not is_income:
                amount = abs(amount)  # Убедимся, что сумма положительная
            
            # Создаем запись о транзакции
            transaction = {
                "date": date,
                "description": description.strip(),
                "amount": amount,
                "is_income": is_income,
                "reference": None,  # В PDF обычно нет референса
                "category_id": None  # Категория будет определена позже
            }
            
            transactions.append(transaction)
        
        # Если не удалось найти транзакции по стандартному паттерну,
        # пробуем альтернативный формат
        if not transactions:
            # Альтернативный паттерн для другого формата выписки
            alt_pattern = r'(\d{2}\.\d{2}\.\d{4})\s+(.+?)\s+([\d\s,.]+)\s*(KZT|тг|₸)'
            
            matches = re.finditer(alt_pattern, text, re.MULTILINE)
            
            for match in matches:
                date_str, description, amount_str, currency = match.groups()
                
                # Преобразуем дату
                try:
                    date = datetime.strptime(date_str, "%d.%m.%Y")
                except ValueError:
                    continue
                
                # Очищаем сумму
                amount_str = amount_str.replace(' ', '').replace(',', '.')
                
                try:
                    amount = float(amount_str)
                except ValueError:
                    continue
                
                # Определяем тип транзакции по ключевым словам в описании
                is_income = False
                income_keywords = ['поступление', 'зачисление', 'возврат', 'перевод на счет']
                expense_keywords = ['оплата', 'списание', 'снятие', 'перевод со счета']
                
                for keyword in income_keywords:
                    if keyword.lower() in description.lower():
                        is_income = True
                        break
                
                for keyword in expense_keywords:
                    if keyword.lower() in description.lower():
                        is_income = False
                        break
                
                # Если это расход, меняем знак суммы
                if not is_income:
                    amount = abs(amount)
                
                # Создаем запись о транзакции
                transaction = {
                    "date": date,
                    "description": description.strip(),
                    "amount": amount,
                    "is_income": is_income,
                    "reference": None,
                    "category_id": None
                }
                
                transactions.append(transaction)
        
        # Пост-обработка транзакций
        return self.post_process_transactions(transactions)


class KaspiExcelParser(ExcelParser):
    """
    Парсер выписок Kaspi Bank в формате Excel
    """
    
    def __init__(self, statement: StatementFile = None):
        super().__init__(statement)
    
    def get_bank_code(self) -> str:
        """
        Получение кода банка
        
        :return: Код банка (KASPI)
        """
        return "KASPI"
    
    def parse_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Парсинг Excel-файла выписки Kaspi Bank
        
        :param file_path: Путь к файлу выписки
        :return: Список транзакций
        """
        if not self.validate_file(file_path):
            print(f"Файл не найден: {file_path}")
            return []
        
        # Извлекаем данные из Excel
        data = self.extract_data_from_excel(file_path)
        
        if not data:
            return []
        
        # Список для хранения транзакций
        transactions = []
        
        # Определяем заголовки столбцов
        # В разных форматах выписок Kaspi могут быть разные заголовки
        # Попробуем найти соответствующие столбцы по ключевым словам
        
        date_column = None
        description_column = None
        amount_column = None
        type_column = None
        reference_column = None
        
        # Поиск по всем возможным названиям столбцов
        for column in data[0].keys():
            column_lower = str(column).lower()
            
            if any(keyword in column_lower for keyword in ['дата', 'date']):
                date_column = column
            
            if any(keyword in column_lower for keyword in ['описание', 'назначение', 'description']):
                description_column = column
            
            if any(keyword in column_lower for keyword in ['сумма', 'amount']):
                amount_column = column
            
            if any(keyword in column_lower for keyword in ['тип', 'type', 'приход', 'расход', 'операция']):
                type_column = column
            
            if any(keyword in column_lower for keyword in ['референс', 'reference', 'номер']):
                reference_column = column
        
        # Если не найдены обязательные столбцы, попробуем определить их по содержимому
        if not (date_column and amount_column):
            for row in data:
                for column, value in row.items():
                    if not date_column and isinstance(value, str) and re.match(r'\d{2}\.\d{2}\.\d{4}', value):
                        date_column = column
                    
                    if not amount_column and isinstance(value, (int, float)) and value != 0:
                        amount_column = column
                
                if date_column and amount_column:
                    break
        
        # Если не найдены обязательные столбцы, возвращаем пустой список
        if not (date_column and amount_column):
            print("Не удалось определить структуру файла выписки")
            return []
        
        # Обрабатываем транзакции
        for row in data:
            # Пропускаем строки с заголовками или пустые строки
            if not row.get(date_column) or not row.get(amount_column):
                continue
            
            # Преобразуем дату
            date_value = row[date_column]
            date = None
            
            if isinstance(date_value, datetime):
                date = date_value
            elif isinstance(date_value, str):
                try:
                    # Пробуем различные форматы даты
                    for date_format in ["%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"]:
                        try:
                            date = datetime.strptime(date_value, date_format)
                            break
                        except ValueError:
                            continue
                except:
                    continue
            
            if not date:
                continue
            
            # Получаем описание
            description = ""
            if description_column and row.get(description_column):
                description = str(row[description_column])
            
            # Получаем сумму
            amount = 0
            if amount_column:
                amount_value = row[amount_column]
                if isinstance(amount_value, (int, float)):
                    amount = float(amount_value)
                elif isinstance(amount_value, str):
                    # Очищаем строку от нецифровых символов, кроме точки и запятой
                    amount_str = re.sub(r'[^\d.,]', '', amount_value)
                    amount_str = amount_str.replace(',', '.')
                    try:
                        amount = float(amount_str)
                    except ValueError:
                        continue
            
            # Определяем, доход это или расход
            is_income = True
            
            if type_column and row.get(type_column):
                type_value = str(row[type_column]).lower()
                is_income = any(keyword in type_value for keyword in ['приход', 'поступление', 'income', 'credit', 'зачисление'])
                
                if any(keyword in type_value for keyword in ['расход', 'списание', 'expense', 'debit']):
                    is_income = False
            elif amount < 0:
                # Если сумма отрицательная, считаем, что это расход
                is_income = False
                amount = abs(amount)
            
            # Получаем референс
            reference = None
            if reference_column and row.get(reference_column):
                reference = str(row[reference_column])
            
            # Создаем запись о транзакции
            transaction = {
                "date": date,
                "description": description,
                "amount": amount,
                "is_income": is_income,
                "reference": reference,
                "category_id": None  # Категория будет определена позже
            }
            
            transactions.append(transaction)
        
        # Пост-обработка транзакций
        return self.post_process_transactions(transactions)


class KaspiCSVParser(CSVParser):
    """
    Парсер выписок Kaspi Bank в формате CSV
    """
    
    def __init__(self, statement: StatementFile = None):
        super().__init__(statement)
    
    def get_bank_code(self) -> str:
        """
        Получение кода банка
        
        :return: Код банка (KASPI)
        """
        return "KASPI"
    
    def parse_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Парсинг CSV-файла выписки Kaspi Bank
        
        :param file_path: Путь к файлу выписки
        :return: Список транзакций
        """
        if not self.validate_file(file_path):
            print(f"Файл не найден: {file_path}")
            return []
        
        # Пробуем разные разделители и кодировки
        for delimiter in [',', ';', '\t']:
            for encoding in ['utf-8', 'cp1251', 'latin1']:
                try:
                    data = self.extract_data_from_csv(file_path, encoding=encoding, delimiter=delimiter)
                    if data:  # Если удалось прочитать данные
                        break
                except Exception as e:
                    continue
            if data:
                break
        
        if not data:
            print("Не удалось прочитать CSV-файл")
            return []
        
        # Дальнейший код аналогичен парсеру для Excel,
        # но с учетом особенностей CSV-файлов Kaspi Bank
        
        # Список для хранения транзакций
        transactions = []
        
        # Определяем заголовки столбцов
        date_column = None
        description_column = None
        amount_column = None
        type_column = None
        reference_column = None
        
        # Поиск по всем возможным названиям столбцов
        for column in data[0].keys():
            column_lower = str(column).lower()
            
            if any(keyword in column_lower for keyword in ['дата', 'date']):
                date_column = column
            
            if any(keyword in column_lower for keyword in ['описание', 'назначение', 'description']):
                description_column = column
            
            if any(keyword in column_lower for keyword in ['сумма', 'amount']):
                amount_column = column
            
            if any(keyword in column_lower for keyword in ['тип', 'type', 'приход', 'расход', 'операция']):
                type_column = column
            
            if any(keyword in column_lower for keyword in ['референс', 'reference', 'номер']):
                reference_column = column
        
        # Если не найдены обязательные столбцы, попробуем определить их по содержимому
        if not (date_column and amount_column):
            for row in data:
                for column, value in row.items():
                    if not date_column and isinstance(value, str) and re.match(r'\d{2}\.\d{2}\.\d{4}', value):
                        date_column = column
                    
                    if not amount_column and isinstance(value, (str, int, float)):
                        try:
                            if isinstance(value, str):
                                value = value.replace(',', '.').replace(' ', '')
                            float_value = float(value)
                            if float_value != 0:
                                amount_column = column
                        except ValueError:
                            continue
                
                if date_column and amount_column:
                    break
        
        # Если не найдены обязательные столбцы, возвращаем пустой список
        if not (date_column and amount_column):
            print("Не удалось определить структуру CSV-файла выписки")
            return []
        
        # Обрабатываем транзакции
        for row in data:
            # Пропускаем строки с заголовками или пустые строки
            if not row.get(date_column) or not row.get(amount_column):
                continue
            
            # Преобразуем дату
            date_value = row[date_column]
            date = None
            
            if isinstance(date_value, datetime):
                date = date_value
            elif isinstance(date_value, str):
                try:
                    # Пробуем различные форматы даты
                    for date_format in ["%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"]:
                        try:
                            date = datetime.strptime(date_value, date_format)
                            break
                        except ValueError:
                            continue
                except:
                    continue
            
            if not date:
                continue
            
            # Получаем описание
            description = ""
            if description_column and row.get(description_column):
                description = str(row[description_column])
            
            # Получаем сумму
            amount = 0
            if amount_column:
                amount_value = row[amount_column]
                if isinstance(amount_value, (int, float)):
                    amount = float(amount_value)
                elif isinstance(amount_value, str):
                    # Очищаем строку от нецифровых символов, кроме точки и запятой
                    amount_str = re.sub(r'[^\d.,]', '', amount_value)
                    amount_str = amount_str.replace(',', '.')
                    try:
                        amount = float(amount_str)
                    except ValueError:
                        continue
            
            # Определяем, доход это или расход
            is_income = True
            
            if type_column and row.get(type_column):
                type_value = str(row[type_column]).lower()
                is_income = any(keyword in type_value for keyword in ['приход', 'поступление', 'income', 'credit', 'зачисление'])
                
                if any(keyword in type_value for keyword in ['расход', 'списание', 'expense', 'debit']):
                    is_income = False
            elif amount < 0:
                # Если сумма отрицательная, считаем, что это расход
                is_income = False
                amount = abs(amount)
            
            # Получаем референс
            reference = None
            if reference_column and row.get(reference_column):
                reference = str(row[reference_column])
            
            # Создаем запись о транзакции
            transaction = {
                "date": date,
                "description": description,
                "amount": amount,
                "is_income": is_income,
                "reference": reference,
                "category_id": None  # Категория будет определена позже
            }
            
            transactions.append(transaction)
        
        # Пост-обработка транзакций
        return self.post_process_transactions(transactions)