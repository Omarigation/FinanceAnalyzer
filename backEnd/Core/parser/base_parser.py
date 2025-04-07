from abc import ABC, abstractmethod
import os
from typing import List, Dict, Any, Optional

from Models.statement import StatementFile


class BaseParser(ABC):
    """
    Базовый абстрактный класс для парсеров банковских выписок
    """
    
    def __init__(self, statement: StatementFile = None):
        """
        Инициализация парсера
        
        :param statement: Объект выписки (опционально)
        """
        self.statement = statement
    
    @abstractmethod
    def parse_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Абстрактный метод для парсинга файла выписки
        
        :param file_path: Путь к файлу выписки
        :return: Список транзакций
        """
        pass
    
    @abstractmethod
    def get_file_format(self) -> str:
        """
        Абстрактный метод для получения формата файла
        
        :return: Формат файла (pdf, csv, xls, xlsx)
        """
        pass
    
    @abstractmethod
    def get_bank_code(self) -> str:
        """
        Абстрактный метод для получения кода банка
        
        :return: Код банка (KASPI, HALYK, и т.д.)
        """
        pass
    
    def validate_file(self, file_path: str) -> bool:
        """
        Проверка существования файла
        
        :param file_path: Путь к файлу
        :return: True, если файл существует, иначе False
        """
        return os.path.isfile(file_path)
    
    def post_process_transactions(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Пост-обработка транзакций после парсинга
        
        :param transactions: Список транзакций
        :return: Обработанный список транзакций
        """
        return transactions


class PDFParser(BaseParser):
    """
    Базовый класс для парсеров выписок в формате PDF
    """
    
    def get_file_format(self) -> str:
        """
        Получение формата файла
        
        :return: Формат файла (pdf)
        """
        return "pdf"
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """
        Извлечение текста из PDF-файла
        
        :param file_path: Путь к PDF-файлу
        :return: Извлеченный текст
        """
        import pdfplumber
        
        text = ""
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
        except Exception as e:
            print(f"Ошибка при чтении PDF: {str(e)}")
        
        return text


class ExcelParser(BaseParser):
    """
    Базовый класс для парсеров выписок в формате Excel (XLS, XLSX)
    """
    
    def get_file_format(self) -> str:
        """
        Получение формата файла
        
        :return: Формат файла (xls или xlsx)
        """
        if self.statement and self.statement.FileName:
            ext = self.statement.FileName.split('.')[-1].lower()
            if ext in ["xls", "xlsx"]:
                return ext
        return "xlsx"  # По умолчанию предполагаем XLSX
    
    def extract_data_from_excel(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Извлечение данных из Excel-файла
        
        :param file_path: Путь к Excel-файлу
        :return: Извлеченные данные
        """
        import pandas as pd
        
        try:
            # Определяем формат файла
            ext = file_path.split('.')[-1].lower()
            
            # Читаем Excel-файл
            if ext == "xls":
                df = pd.read_excel(file_path, engine="xlrd")
            else:
                df = pd.read_excel(file_path, engine="openpyxl")
            
            # Преобразуем DataFrame в список словарей
            data = df.to_dict(orient="records")
            return data
        
        except Exception as e:
            print(f"Ошибка при чтении Excel: {str(e)}")
            return []


class CSVParser(BaseParser):
    """
    Базовый класс для парсеров выписок в формате CSV
    """
    
    def get_file_format(self) -> str:
        """
        Получение формата файла
        
        :return: Формат файла (csv)
        """
        return "csv"
    
    def extract_data_from_csv(self, file_path: str, encoding="utf-8", delimiter=",") -> List[Dict[str, Any]]:
        """
        Извлечение данных из CSV-файла
        
        :param file_path: Путь к CSV-файлу
        :param encoding: Кодировка файла
        :param delimiter: Разделитель полей
        :return: Извлеченные данные
        """
        import pandas as pd
        
        try:
            # Читаем CSV-файл
            df = pd.read_csv(file_path, encoding=encoding, delimiter=delimiter)
            
            # Преобразуем DataFrame в список словарей
            data = df.to_dict(orient="records")
            return data
        
        except UnicodeDecodeError:
            # Если не удалось прочитать с указанной кодировкой, пробуем другие
            for enc in ["utf-8", "cp1251", "latin1"]:
                try:
                    df = pd.read_csv(file_path, encoding=enc, delimiter=delimiter)
                    data = df.to_dict(orient="records")
                    return data
                except UnicodeDecodeError:
                    continue
            
            print("Не удалось определить кодировку CSV-файла")
            return []
        
        except Exception as e:
            print(f"Ошибка при чтении CSV: {str(e)}")
            return []


def get_parser_for_statement(statement: StatementFile) -> Optional[BaseParser]:
    """
    Фабричный метод для получения подходящего парсера для выписки
    
    :param statement: Объект выписки
    :return: Объект парсера или None, если подходящий парсер не найден
    """
    from Core.parser.kaspi_parser import KaspiPDFParser, KaspiExcelParser, KaspiCSVParser
    from Core.parser.halyk_parser import HalykPDFParser, HalykExcelParser, HalykCSVParser
    
    # Получаем расширение файла
    ext = statement.FileName.split('.')[-1].lower()
    
    # Определяем парсер в зависимости от банка и формата файла
    if statement.bank.Code == "KASPI":
        if ext == "pdf":
            return KaspiPDFParser(statement)
        elif ext == "xlsx" or ext == "xls":
            return KaspiExcelParser(statement)
        elif ext == "csv":
            return KaspiCSVParser(statement)
    
    elif statement.bank.Code == "HALYK":
        if ext == "pdf":
            return HalykPDFParser(statement)
        elif ext == "xlsx" or ext == "xls":
            return HalykExcelParser(statement)
        elif ext == "csv":
            return HalykCSVParser(statement)
    
    # Можно добавить другие банки и форматы по мере необходимости
    
    # Если не нашли подходящий парсер
    return None