"""
Подсистема интерпретации и выполнения команд
Преобразует распознанные жесты в конкретные действия: генерация управляющих сигналов
(эмуляция кликов мыши, нажатий клавиш), запуск функций в подключенном приложении
или формирование аналитического отчета.
"""
import logging
from typing import Dict, Any, Optional, List
import httpx
import yaml
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class InterpretationService:
    """
    Сервис интерпретации жестов и выполнения соответствующих команд.
    Поддерживает различные типы действий: логирование, callback-запросы, эмуляцию ввода.
    """

    def __init__(self, mappings_file: Optional[str] = None):
        """
        Инициализация сервиса интерпретации.
        
        Args:
            mappings_file: Путь к YAML файлу с маппингами жестов на действия
        """
        self.mappings: Dict[str, Dict[str, Any]] = {}
        self.mappings_file = mappings_file or "configs/mappings.yaml"
        self.load_mappings()

    def load_mappings(self) -> None:
        """Загрузка маппингов из файла конфигурации."""
        try:
            mappings_path = Path(self.mappings_file)
            if mappings_path.exists():
                with open(mappings_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
                    self.mappings = config
                logger.info(f"Загружены маппинги из {self.mappings_file}: {len(self.mappings)} жестов")
            else:
                # Значения по умолчанию
                self._set_default_mappings()
                self.save_mappings()
                logger.info("Создан файл маппингов со значениями по умолчанию")
        except Exception as e:
            logger.exception(f"Ошибка загрузки маппингов: {e}")
            self._set_default_mappings()

    def _set_default_mappings(self) -> None:
        """Установка маппингов по умолчанию."""
        self.mappings = {
            "raise_right_hand": {
                "type": "log",
                "message": "Поднята правая рука - следующая страница",
                "description": "Навигация вперед"
            },
            "raise_left_hand": {
                "type": "log",
                "message": "Поднята левая рука - предыдущая страница",
                "description": "Навигация назад"
            },
            "both_hands_up": {
                "type": "callback",
                "url": "http://example.com/webhook/both_hands_up",
                "description": "Обе руки подняты - специальное действие"
            },
            "clap": {
                "type": "log",
                "message": "Хлопок - пауза/воспроизведение",
                "description": "Управление медиа"
            },
            "point_left": {
                "type": "log",
                "message": "Указание влево - навигация влево",
                "description": "Навигация"
            },
            "point_right": {
                "type": "log",
                "message": "Указание вправо - навигация вправо",
                "description": "Навигация"
            },
            "hands_close": {
                "type": "log",
                "message": "Руки близко - выбор/подтверждение",
                "description": "Выбор элемента"
            },
            "wave_right": {
                "type": "callback",
                "url": "http://example.com/webhook/wave",
                "description": "Мах правой рукой"
            },
            "wave_left": {
                "type": "log",
                "message": "Мах левой рукой",
                "description": "Приветствие"
            },
            "circle_right": {
                "type": "log",
                "message": "Круговое движение правой рукой",
                "description": "Специальное действие"
            }
        }

    def save_mappings(self) -> None:
        """Сохранение маппингов в файл."""
        try:
            mappings_path = Path(self.mappings_file)
            mappings_path.parent.mkdir(parents=True, exist_ok=True)
            with open(mappings_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.mappings, f, allow_unicode=True, default_flow_style=False)
            logger.info(f"Маппинги сохранены в {self.mappings_file}")
        except Exception as e:
            logger.exception(f"Ошибка сохранения маппингов: {e}")

    def add_mapping(self, gesture: str, action_type: str, **kwargs) -> bool:
        """
        Добавление нового маппинга жеста на действие.
        
        Args:
            gesture: Метка жеста
            action_type: Тип действия ("log", "callback", "keyboard", "mouse")
            **kwargs: Дополнительные параметры действия
        
        Returns:
            True если успешно добавлено
        """
        try:
            mapping = {"type": action_type, **kwargs}
            self.mappings[gesture] = mapping
            self.save_mappings()
            logger.info(f"Добавлен маппинг: {gesture} -> {action_type}")
            return True
        except Exception as e:
            logger.exception(f"Ошибка добавления маппинга: {e}")
            return False

    def remove_mapping(self, gesture: str) -> bool:
        """Удаление маппинга жеста."""
        if gesture in self.mappings:
            del self.mappings[gesture]
            self.save_mappings()
            logger.info(f"Удален маппинг: {gesture}")
            return True
        return False

    async def execute(self, gesture_label: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Выполнение действия, соответствующего распознанному жесту.
        
        Args:
            gesture_label: Метка распознанного жеста
            context: Дополнительный контекст (timestamp, landmarks, etc.)
        
        Returns:
            Результат выполнения действия
        """
        if gesture_label == "none":
            return {"status": "no_action", "message": "Жест не распознан"}
        
        mapping = self.mappings.get(gesture_label)
        if not mapping:
            logger.debug(f"Нет маппинга для жеста: {gesture_label}")
            return {
                "status": "no_mapping",
                "message": f"Жест '{gesture_label}' не имеет назначенного действия"
            }
        
        action_type = mapping.get("type", "log")
        context = context or {}
        
        try:
            if action_type == "log":
                message = mapping.get("message", f"Действие для жеста {gesture_label}")
                logger.info(f"Interpret action: {message}")
                return {
                    "status": "logged",
                    "message": message,
                    "gesture": gesture_label
                }
            
            elif action_type == "callback":
                url = mapping.get("url")
                if not url:
                    return {"status": "bad_mapping", "error": "URL не указан"}
                
                async with httpx.AsyncClient(timeout=5.0) as client:
                    payload = {
                        "gesture": gesture_label,
                        "timestamp": context.get("timestamp"),
                        **context
                    }
                    try:
                        resp = await client.post(url, json=payload)
                        return {
                            "status": "callback_sent",
                            "code": resp.status_code,
                            "gesture": gesture_label
                        }
                    except Exception as e:
                        logger.exception(f"Ошибка callback для {gesture_label}: {e}")
                        return {
                            "status": "callback_error",
                            "error": str(e),
                            "gesture": gesture_label
                        }
            
            elif action_type == "keyboard":
                # Эмуляция нажатия клавиш (требует дополнительных библиотек)
                key = mapping.get("key", "")
                logger.info(f"Keyboard action: {key} (не реализовано)")
                return {
                    "status": "keyboard_not_implemented",
                    "key": key,
                    "gesture": gesture_label
                }
            
            elif action_type == "mouse":
                # Эмуляция действий мыши (требует дополнительных библиотек)
                action = mapping.get("action", "")
                logger.info(f"Mouse action: {action} (не реализовано)")
                return {
                    "status": "mouse_not_implemented",
                    "action": action,
                    "gesture": gesture_label
                }
            
            else:
                logger.warning(f"Неизвестный тип действия: {action_type}")
                return {
                    "status": "unknown_type",
                    "type": action_type,
                    "gesture": gesture_label
                }
        
        except Exception as e:
            logger.exception(f"Ошибка выполнения действия для {gesture_label}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "gesture": gesture_label
            }

    def get_all_mappings(self) -> Dict[str, Dict[str, Any]]:
        """Получение всех маппингов."""
        return self.mappings.copy()

    def get_mapping(self, gesture: str) -> Optional[Dict[str, Any]]:
        """Получение маппинга для конкретного жеста."""
        return self.mappings.get(gesture)
