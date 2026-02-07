# XML_Data_Base.py

import openpyxl
from openpyxl import Workbook
from typing import Dict, List, Optional, Tuple
import os


class ExcelDatabase:
    """
    Класс для работы с Excel-файлом как с базой данных для хранения информации о закатках и продуктах.
    """

    # Определяем структуру таблицы
    PRESERVES_SECTION = {
        'start_col': 'A',
        'end_col': 'E',
        'headers': ['Содержимое закатки', 'Объем', 'Количество', 'Примечания', 'Место нахождения']
    }

    VOLUMES_SECTION = {
        'col': 'H',
        'header': 'Объем',
        'data_start_row': 2
    }

    NOTES_SECTION = {
        'start_col': 'J',
        'end_col': 'K',
        'headers': ['Примечания', 'Расшифровка']
    }

    PRODUCTS_SECTION = {
        'start_col': 'M',
        'end_col': 'O',
        'headers': ['Название продукта', 'Количество', 'Место нахождение']
    }

    def __init__(self, file_path: str = 'XML_Dom.xlsx'):
        """
        Инициализация базы данных.

        Args:
            file_path (str): Путь к Excel-файлу
        """
        self.file_path = file_path
        self.wb = None
        self.ws = None
        self._volumes_cache = []
        self._notes_cache = {}
        self._locations_cache = set()

        self._load_or_create_file()
        self._cache_locations()

    def _load_or_create_file(self):
        """
        Загружает существующий Excel-файл или создает новый с базовой структурой.
        """
        try:
            if os.path.exists(self.file_path):
                self.wb = openpyxl.load_workbook(self.file_path)
                self.ws = self.wb.active
                print(f"Файл {self.file_path} успешно загружен")
            else:
                self._create_new_file()
        except Exception as e:
            print(f"Ошибка при загрузке файла: {e}")
            self._create_new_file()

        # Кэшируем справочные данные для быстрого доступа
        self._cache_reference_data()

    def _create_new_file(self):
        """
        Создает новый Excel-файл с базовой структурой.
        """
        print(f"Создание нового файла: {self.file_path}")
        self.wb = Workbook()
        self.ws = self.wb.active
        self.ws.title = "Лист1"

        # Заполняем заголовки
        # Заголовки для закаток (A-E)
        for idx, header in enumerate(self.PRESERVES_SECTION['headers']):
            col_letter = chr(ord('A') + idx)
            self.ws[f'{col_letter}1'] = header

        # Заголовок для объемов (H)
        self.ws['H1'] = self.VOLUMES_SECTION['header']

        # Заголовки для примечаний (J-K)
        for idx, header in enumerate(self.NOTES_SECTION['headers']):
            col_letter = chr(ord('J') + idx)
            self.ws[f'{col_letter}1'] = header

        # Заголовки для продуктов (M-O)
        for idx, header in enumerate(self.PRODUCTS_SECTION['headers']):
            col_letter = chr(ord('M') + idx)
            self.ws[f'{col_letter}1'] = header

        # Создаем столбцы для истории
        self.ws['R1'] = 'История закаток'
        self.ws['S1'] = 'История продуктов'

        self.save()

    def _cache_reference_data(self):
        """
        Кэширует справочные данные (объемы и примечания) для быстрого доступа.
        """
        # Кэшируем объемы из таблицы
        self._volumes_cache = []
        row = self.VOLUMES_SECTION['data_start_row']
        while True:
            cell_value = self.ws[f'H{row}'].value
            if cell_value is None:
                break
            self._volumes_cache.append(cell_value)
            row += 1

        # Кэшируем примечания (код -> расшифровка) из таблицы
        self._notes_cache = {}
        row = 2
        while True:
            code = self.ws[f'J{row}'].value
            description = self.ws[f'K{row}'].value

            if code is None or description is None:
                break

            self._notes_cache[code] = description
            row += 1

    def _cache_locations(self):
        """
        Кэширует уникальные места хранения из всех записей.
        """
        self._locations_cache = set()

        # Из закаток
        row = 2
        while self.ws[f'A{row}'].value is not None:
            location = self.ws[f'E{row}'].value
            if location:
                self._locations_cache.add(location)
            row += 1

        # Из продуктов
        row = 2
        while self.ws[f'M{row}'].value is not None:
            location = self.ws[f'O{row}'].value
            if location:
                self._locations_cache.add(location)
            row += 1

    def save(self):
        """
        Сохраняет изменения в файл.
        """
        try:
            self.wb.save(self.file_path)
            self._cache_locations()
            return True
        except Exception as e:
            print(f"Ошибка при сохранении файла: {e}")
            return False

    def _find_preserve(self, content: str, volume: float, note_code: str, location: str) -> Optional[int]:
        """
        Ищет закатку с точно такими же параметрами (включая место).
        """
        row = 2
        while self.ws[f'A{row}'].value is not None:
            if (self.ws[f'A{row}'].value == content and
                    self.ws[f'B{row}'].value == volume and
                    self.ws[f'D{row}'].value == note_code and
                    self.ws[f'E{row}'].value == location):
                return row
            row += 1
        return None

    def _find_product(self, name: str, location: str) -> Optional[int]:
        """
        Ищет продукт с точно такими же параметрами (включая место).
        """
        row = 2
        while self.ws[f'M{row}'].value is not None:
            if (self.ws[f'M{row}'].value == name and
                    self.ws[f'O{row}'].value == location):
                return row
            row += 1
        return None

    # ========== МЕТОДЫ ДЛЯ РАБОТЫ С ЗАКАТКАМИ ==========

    def get_all_preserves(self) -> List[Dict]:
        """
        Возвращает список всех закаток.
        """
        preserves = []
        row = 2

        while True:
            content = self.ws[f'A{row}'].value
            if content is None:
                break

            preserve = {
                'content': content,
                'volume': self.ws[f'B{row}'].value,
                'quantity': self.ws[f'C{row}'].value or 0,
                'note_code': self.ws[f'D{row}'].value,
                'note_description': self._notes_cache.get(self.ws[f'D{row}'].value, ''),
                'location': self.ws[f'E{row}'].value,
                'row': row
            }
            preserves.append(preserve)
            row += 1

        return preserves

    def get_preserves_grouped(self) -> Dict[Tuple, Dict]:
        """
        Возвращает закатки, сгруппированные по содержимому, объему и примечанию.
        """
        preserves = self.get_all_preserves()
        grouped = {}

        for preserve in preserves:
            key = (preserve['content'], preserve['volume'], preserve['note_code'])

            if key not in grouped:
                grouped[key] = {
                    'content': preserve['content'],
                    'volume': preserve['volume'],
                    'note_code': preserve['note_code'],
                    'note_description': preserve['note_description'],
                    'total_quantity': 0,
                    'locations': [],
                    'rows': []  # Сохраняем номера строк для каждого местоположения
                }

            # Проверяем, есть ли уже это место в списке
            location_found = False
            for loc in grouped[key]['locations']:
                if loc['location'] == preserve['location']:
                    loc['quantity'] += preserve['quantity']
                    loc['rows'].append(preserve['row'])
                    location_found = True
                    break

            if not location_found:
                grouped[key]['locations'].append({
                    'location': preserve['location'],
                    'quantity': preserve['quantity'],
                    'rows': [preserve['row']]
                })

            grouped[key]['total_quantity'] += preserve['quantity']

        return grouped

    def add_preserve(self, content: str, volume: float, quantity: int,
                     note_code: str, location: str) -> bool:
        """
        Добавляет новую закатку.
        """
        try:
            # Ищем существующую запись с такими же параметрами
            existing_row = self._find_preserve(content, volume, note_code, location)

            if existing_row:
                # Увеличиваем количество в существующей записи
                current_quantity = self.ws[f'C{existing_row}'].value or 0
                self.ws[f'C{existing_row}'] = current_quantity + quantity
            else:
                # Создаем новую запись
                row = 2
                while self.ws[f'A{row}'].value is not None:
                    row += 1

                self.ws[f'A{row}'] = content
                self.ws[f'B{row}'] = volume
                self.ws[f'C{row}'] = quantity
                self.ws[f'D{row}'] = note_code
                self.ws[f'E{row}'] = location

            # Добавляем в историю
            self._add_to_history('preserves', content)

            return self.save()
        except Exception as e:
            print(f"Ошибка при добавлении закатки: {e}")
            return False

    def remove_preserve(self, content: str, volume: float, note_code: str,
                        location: str, quantity: int) -> bool:
        """
        Удаляет закатку или уменьшает количество.

        Args:
            content (str): Содержимое закатки
            volume (float): Объем
            note_code (str): Код примечания
            location (str): Место нахождения
            quantity (int): Количество для удаления

        Returns:
            bool: True если успешно, False в случае ошибки
        """
        try:
            row = self._find_preserve(content, volume, note_code, location)

            if not row:
                return False

            current_quantity = self.ws[f'C{row}'].value or 0

            if quantity >= current_quantity:
                # Удаляем всю запись
                for col in range(1, 6):
                    self.ws.cell(row=row, column=col).value = None

                # Сдвигаем строки вверх
                self._shift_rows_up(row, start_col=1, end_col=5)
            else:
                # Уменьшаем количество
                self.ws[f'C{row}'] = current_quantity - quantity

            return self.save()
        except Exception as e:
            print(f"Ошибка при удалении закатки: {e}")
            return False

    # ========== МЕТОДЫ ДЛЯ РАБОТЫ С ПРОДУКТАМИ ==========

    def get_all_products(self) -> List[Dict]:
        """
        Возвращает список всех продуктов.
        """
        products = []
        row = 2

        while True:
            name = self.ws[f'M{row}'].value
            if name is None:
                break

            product = {
                'name': name,
                'quantity': self.ws[f'N{row}'].value or 0,
                'location': self.ws[f'O{row}'].value,
                'row': row
            }
            products.append(product)
            row += 1

        return products

    def get_products_grouped(self) -> Dict[str, Dict]:
        """
        Возвращает продукты, сгруппированные по названию.
        """
        products = self.get_all_products()
        grouped = {}

        for product in products:
            name = product['name']

            if name not in grouped:
                grouped[name] = {
                    'name': name,
                    'total_quantity': 0,
                    'locations': [],
                    'rows': []
                }

            # Проверяем, есть ли уже это место в списке
            location_found = False
            for loc in grouped[name]['locations']:
                if loc['location'] == product['location']:
                    loc['quantity'] += product['quantity']
                    loc['rows'].append(product['row'])
                    location_found = True
                    break

            if not location_found:
                grouped[name]['locations'].append({
                    'location': product['location'],
                    'quantity': product['quantity'],
                    'rows': [product['row']]
                })

            grouped[name]['total_quantity'] += product['quantity']

        return grouped

    def add_product(self, name: str, quantity: int, location: str) -> bool:
        """
        Добавляет новый продукт.
        """
        try:
            # Ищем существующую запись с такими же параметрами
            existing_row = self._find_product(name, location)

            if existing_row:
                # Увеличиваем количество в существующей записи
                current_quantity = self.ws[f'N{existing_row}'].value or 0
                self.ws[f'N{existing_row}'] = current_quantity + quantity
            else:
                # Создаем новую запись
                row = 2
                while self.ws[f'M{row}'].value is not None:
                    row += 1

                self.ws[f'M{row}'] = name
                self.ws[f'N{row}'] = quantity
                self.ws[f'O{row}'] = location

            # Добавляем в историю
            self._add_to_history('products', name)

            return self.save()
        except Exception as e:
            print(f"Ошибка при добавлении продукта: {e}")
            return False

    def remove_product(self, name: str, location: str, quantity: int) -> bool:
        """
        Удаляет продукт или уменьшает количество.

        Args:
            name (str): Название продукта
            location (str): Место нахождения
            quantity (int): Количество для удаления

        Returns:
            bool: True если успешно, False в случае ошибки
        """
        try:
            row = self._find_product(name, location)

            if not row:
                return False

            current_quantity = self.ws[f'N{row}'].value or 0

            if quantity >= current_quantity:
                # Удаляем всю запись
                for col in range(13, 16):
                    self.ws.cell(row=row, column=col).value = None

                # Сдвигаем строки вверх
                self._shift_rows_up(row, start_col=13, end_col=15)
            else:
                # Уменьшаем количество
                self.ws[f'N{row}'] = current_quantity - quantity

            return self.save()
        except Exception as e:
            print(f"Ошибка при удалении продукта: {e}")
            return False

    def _shift_rows_up(self, start_row: int, start_col: int, end_col: int):
        """
        Сдвигает строки вверх, начиная с указанной строки.
        """
        next_row = start_row + 1

        # Находим следующую непустую строку
        while True:
            # Проверяем первую колонку секции
            cell_value = self.ws.cell(row=next_row, column=start_col).value
            if cell_value is None:
                break

            # Копируем значения из следующей строки в текущую
            for col in range(start_col, end_col + 1):
                current_cell = self.ws.cell(row=next_row - 1, column=col)
                next_cell = self.ws.cell(row=next_row, column=col)
                current_cell.value = next_cell.value
                next_cell.value = None

            next_row += 1

    # ========== МЕТОДЫ ДЛЯ РАБОТЫ СО СПРАВОЧНИКАМИ ==========

    def get_available_volumes(self) -> List[float]:
        """
        Возвращает список доступных объемов закаток.
        """
        return self._volumes_cache.copy()

    def get_available_notes(self) -> Dict[str, str]:
        """
        Возвращает словарь доступных примечаний.
        """
        return self._notes_cache.copy()

    def get_available_locations(self) -> List[str]:
        """
        Возвращает список доступных мест хранения.
        """
        return sorted(list(self._locations_cache))

    def add_location(self, location: str) -> bool:
        """
        Добавляет новое место хранения.
        """
        try:
            self._locations_cache.add(location)
            return self.save()
        except Exception as e:
            print(f"Ошибка при добавлении места: {e}")
            return False

    # ========== МЕТОДЫ ДЛЯ РАБОТЫ С ИСТОРИЕЙ ==========

    def _add_to_history(self, history_type: str, value: str) -> bool:
        """
        Добавляет значение в историю.
        """
        try:
            col = 'R' if history_type == 'preserves' else 'S'

            # Получаем текущую историю
            history = []
            row = 2
            while row < 12:
                cell_value = self.ws[f'{col}{row}'].value
                if cell_value:
                    history.append(cell_value)
                row += 1

            # Удаляем дубликаты и добавляем новое значение в начало
            if value in history:
                history.remove(value)
            history.insert(0, value)

            # Ограничиваем 10 элементами
            history = history[:10]

            # Записываем обратно
            for i in range(2, 12):
                if i - 2 < len(history):
                    self.ws[f'{col}{i}'] = history[i - 2]
                else:
                    self.ws[f'{col}{i}'] = None

            return self.save()
        except Exception as e:
            print(f"Ошибка при добавлении в историю: {e}")
            return False

    def get_preserve_history(self) -> List[str]:
        """
        Возвращает историю названий закаток.
        """
        history = []
        row = 2
        while row < 12:
            value = self.ws[f'R{row}'].value
            if value:
                history.append(value)
            row += 1
        return history

    def get_product_history(self) -> List[str]:
        """
        Возвращает историю названий продуктов.
        """
        history = []
        row = 2
        while row < 12:
            value = self.ws[f'S{row}'].value
            if value:
                history.append(value)
            row += 1
        return history

    # ========== ПОИСК И ФИЛЬТРАЦИЯ ==========

    def search_preserves(self, **criteria) -> Dict[Tuple, Dict]:
        """
        Ищет закатки по заданным критериям и возвращает сгруппированные результаты.
        """
        all_preserves = self.get_all_preserves()
        filtered_preserves = []

        for preserve in all_preserves:
            match = True

            if 'content' in criteria and criteria['content']:
                if criteria['content'].lower() not in (preserve['content'] or '').lower():
                    match = False

            if 'volume_min' in criteria and criteria['volume_min'] is not None:
                if preserve['volume'] is None or preserve['volume'] < criteria['volume_min']:
                    match = False

            if 'volume_max' in criteria and criteria['volume_max'] is not None:
                if preserve['volume'] is None or preserve['volume'] > criteria['volume_max']:
                    match = False

            if 'note_code' in criteria and criteria['note_code']:
                if preserve['note_code'] != criteria['note_code']:
                    match = False

            if 'location' in criteria and criteria['location']:
                if criteria['location'].lower() not in (preserve['location'] or '').lower():
                    match = False

            if 'min_quantity' in criteria and criteria['min_quantity'] is not None:
                if preserve['quantity'] is None or preserve['quantity'] < criteria['min_quantity']:
                    match = False

            if match:
                filtered_preserves.append(preserve)

        # Группируем отфильтрованные результаты
        grouped = {}
        for preserve in filtered_preserves:
            key = (preserve['content'], preserve['volume'], preserve['note_code'])

            if key not in grouped:
                grouped[key] = {
                    'content': preserve['content'],
                    'volume': preserve['volume'],
                    'note_code': preserve['note_code'],
                    'note_description': preserve['note_description'],
                    'total_quantity': 0,
                    'locations': []
                }

            # Проверяем, есть ли уже это место в списке
            location_found = False
            for loc in grouped[key]['locations']:
                if loc['location'] == preserve['location']:
                    loc['quantity'] += preserve['quantity']
                    location_found = True
                    break

            if not location_found:
                grouped[key]['locations'].append({
                    'location': preserve['location'],
                    'quantity': preserve['quantity']
                })

            grouped[key]['total_quantity'] += preserve['quantity']

        return grouped

    def get_statistics(self) -> Dict:
        """
        Возвращает статистику по хранилищу.
        """
        grouped_preserves = self.get_preserves_grouped()
        grouped_products = self.get_products_grouped()

        total_preserves = sum(group['total_quantity'] for group in grouped_preserves.values())
        total_products = sum(group['total_quantity'] for group in grouped_products.values())

        # Группировка закаток по содержимому
        content_stats = {}
        for group in grouped_preserves.values():
            content = group['content']
            if content:
                if content not in content_stats:
                    content_stats[content] = 0
                content_stats[content] += group['total_quantity']

        # Группировка закаток по объему
        volume_stats = {}
        for group in grouped_preserves.values():
            volume = group['volume']
            if volume:
                if volume not in volume_stats:
                    volume_stats[volume] = 0
                volume_stats[volume] += group['total_quantity']

        # Подсчет уникальных мест хранения
        unique_locations = set()
        for group in grouped_preserves.values():
            for loc in group['locations']:
                unique_locations.add(loc['location'])

        for group in grouped_products.values():
            for loc in group['locations']:
                unique_locations.add(loc['location'])

        return {
            'total_preserves': total_preserves,
            'total_products': total_products,
            'unique_contents': len(content_stats),
            'unique_locations': len(unique_locations),
            'content_stats': content_stats,
            'volume_stats': volume_stats
        }


# Создаем глобальный экземпляр для использования в других модулей
db_instance = None


def init_database(file_path: str = 'XML_Dom.xlsx'):
    """
    Инициализирует глобальный экземпляр базы данных.
    """
    global db_instance
    db_instance = ExcelDatabase(file_path)
    return db_instance


def get_db() -> ExcelDatabase:
    """
    Возвращает глобальный экземпляр базы данных.
    """
    global db_instance
    if db_instance is None:
        db_instance = ExcelDatabase()
    return db_instance