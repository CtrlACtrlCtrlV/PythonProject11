#!/usr/bin/env python3

import yaml
import sys
from pathlib import Path

class PackageAnalyzer:
    def __init__(self, config_path="config.yaml"):
        self.config_path = Path(config_path)
        self.config_data = {}

        # Обязательные параметры
        self.required_keys = {
            'package_name',
            'repo_url',
            'mode',
            'version',
            'output_image',
            'filter_substring'
        }

    def load_config(self):
        try:
            if not self.config_path.exists():
                raise FileNotFoundError(f"Конфигурационный файл {self.config_path} не найден")

            with open(self.config_path, 'r', encoding='utf-8') as file:
                self.config_data = yaml.safe_load(file)

            if self.config_data is None:
                raise ValueError("Конфигурационный файл пуст")

            self._validate_config()

            return True

        except yaml.YAMLError as e:
            raise ValueError(f"Ошибка формата YAML: {e}")
        except Exception as e:
            raise RuntimeError(f"Ошибка загрузки конфигурации: {e}")

    def _validate_config(self):
        missing_keys = self.required_keys - set(self.config_data.keys())
        if missing_keys:
            raise ValueError(f"Отсутствуют обязательные параметры: {', '.join(missing_keys)}")

        for key in self.required_keys:
            if not isinstance(self.config_data[key], str):
                raise TypeError(f"Параметр '{key}' должен быть строкой")

    def display_config(self):
        print("Настраиваемые параметры пользователя:")
        print("=" * 40)
        for key in sorted(self.config_data.keys()):
            print(f"{key}: {self.config_data[key]}")
        print("=" * 40)

    def run(self):
        try:
            print("Запуск анализатора пакетов...")

            self.load_config()

            self.display_config()

            print("Конфигурация успешно загружена!")

        except (FileNotFoundError, ValueError, TypeError, RuntimeError) as e:
            print(f"Ошибка конфигурации: {e}", file=sys.stderr)
            sys.exit(1)
        except KeyboardInterrupt:
            print("\nПрограмма прервана пользователем", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Неизвестная ошибка: {e}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    analyzer = PackageAnalyzer()
    analyzer.run()