#!/usr/bin/env python3

import yaml
import sys
from typing import Dict, Any, List


class ConfigError(Exception):
    pass


class ConfigValidator:

    @staticmethod
    def validate_package_name(name: str) -> None:
        if not isinstance(name, str) or not name.strip():
            raise ConfigError("Имя пакета должно быть непустой строкой")

    @staticmethod
    def validate_repo_url(url: str) -> None:
        if not isinstance(url, str) or not url.strip():
            raise ConfigError("URL репозитория должен быть непустой строкой")

    @staticmethod
    def validate_mode(mode: str) -> None:
        valid_modes = ['local', 'remote']
        if mode not in valid_modes:
            raise ConfigError(f"Режим работы должен быть одним из: {valid_modes}")

    @staticmethod
    def validate_version(version: str) -> None:
        if not isinstance(version, str) or not version.strip():
            raise ConfigError("Версия пакета должна быть непустой строкой")

    @staticmethod
    def validate_output_image(filename: str) -> None:
        if not isinstance(filename, str) or not filename.endswith('.png'):
            raise ConfigError("Имя выходного файла должно иметь расширение .png")

    @staticmethod
    def validate_filter_substring(substring: str) -> None:
        if not isinstance(substring, str):
            raise ConfigError("Подстрока для фильтрации должна быть строкой")


class ConfigManager:

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self.required_keys = {
            'package_name', 'repo_url', 'mode', 'version',
            'output_image', 'filter_substring'
        }

    def load_config(self) -> 'ConfigManager':
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                self.config = yaml.safe_load(file)
        except FileNotFoundError:
            raise ConfigError(f"Конфигурационный файл '{self.config_path}' не найден")
        except yaml.YAMLError as e:
            raise ConfigError(f"Ошибка в формате YAML: {e}")

        return self

    def validate_required_keys(self) -> 'ConfigManager':
        missing_keys = self.required_keys - set(self.config.keys())
        if missing_keys:
            raise ConfigError(f"Отсутствуют обязательные параметры: {missing_keys}")

        return self

    def validate_values(self) -> 'ConfigManager':
        """Валидация значений параметров"""
        validators = {
            'package_name': ConfigValidator.validate_package_name,
            'repo_url': ConfigValidator.validate_repo_url,
            'mode': ConfigValidator.validate_mode,
            'version': ConfigValidator.validate_version,
            'output_image': ConfigValidator.validate_output_image,
            'filter_substring': ConfigValidator.validate_filter_substring
        }

        for key, validator in validators.items():
            validator(self.config[key])

        return self

    def print_config(self) -> 'ConfigManager':
        print("Конфигурационные параметры:")
        for key, value in self.config.items():
            print(f"{key}: {value}")

        return self


def main():

    if len(sys.argv) != 2:
        print("Использование: python main.py <config_file>")
        sys.exit(1)

    config_path = sys.argv[1]

    try:
        # Конвейер обработки конфигурации в стиле пособия
        (ConfigManager(config_path)
         .load_config()
         .validate_required_keys()
         .validate_values()
         .print_config())

    except ConfigError as e:
        print(f"Ошибка конфигурации: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()