#!/usr/bin/env python3
"""
Скрипт для тестирования обработки ошибок
"""

import os
import tempfile


def create_test_config(content: str) -> str:
    """Создание временного конфигурационного файла для тестирования"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(content)
        return f.name


def test_scenarios():
    """Тестовые сценарии из учебного пособия"""

    test_cases = [
        {
            'name': 'Отсутствующий файл',
            'config': '',
            'file_exists': False
        },
        {
            'name': 'Некорректный YAML',
            'config': 'package_name: [unclosed list',
            'file_exists': True
        },
        {
            'name': 'Отсутствует обязательный параметр',
            'config': '''
package_name: "test"
repo_url: "https://example.com"
mode: "remote"
version: "1.0.0"
output_image: "graph.png"
# filter_substring отсутствует
''',
            'file_exists': True
        },
        {
            'name': 'Неверный режим работы',
            'config': '''
package_name: "test"
repo_url: "https://example.com"
mode: "invalid_mode"
version: "1.0.0"
output_image: "graph.png"
filter_substring: "test"
''',
            'file_exists': True
        },
        {
            'name': 'Некорректное имя выходного файла',
            'config': '''
package_name: "test"
repo_url: "https://example.com"
mode: "remote"
version: "1.0.0"
output_image: "graph.jpg"  # должно быть .png
filter_substring: "test"
''',
            'file_exists': True
        }
    ]

    for test_case in test_cases:
        print(f"\n=== Тест: {test_case['name']} ===")

        if test_case['file_exists']:
            config_path = create_test_config(test_case['config'])
        else:
            config_path = "nonexistent_file.yaml"

        # Импортируем и запускаем основной скрипт
        import subprocess
        result = subprocess.run(
            ['python', 'main.py', config_path],
            capture_output=True,
            text=True
        )

        print(f"Код возврата: {result.returncode}")
        print(f"Вывод: {result.stdout}")
        if result.stderr:
            print(f"Ошибки: {result.stderr}")

        # Удаляем временный файл
        if test_case['file_exists'] and os.path.exists(config_path):
            os.unlink(config_path)


if __name__ == "__main__":
    test_scenarios()