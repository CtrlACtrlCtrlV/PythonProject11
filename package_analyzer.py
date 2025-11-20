#!/usr/bin/env python3

import yaml
import sys
import base64
import json
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import re


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

        except yaml.YAMLError as e:
            raise ValueError(f"Ошибка YAML: {e}")
        except Exception as e:
            raise RuntimeError(f"Ошибка загрузки конфигурации: {e}")

    def _validate_config(self):
        """Проверяет валидность конфигурации"""
        missing_keys = self.required_keys - set(self.config_data.keys())
        if missing_keys:
            raise ValueError(f"Отсутствуют параметры: {', '.join(missing_keys)}")

        for key in self.required_keys:
            if not isinstance(self.config_data[key], str):
                raise TypeError(f"Параметр '{key}' должен быть строкой")

    def extract_github_info(self, repo_url):
        patterns = [
            r'https://github\.com/([^/]+)/([^/]+)',
            r'git@github\.com:([^/]+)/([^/]+)\.git'
        ]

        for pattern in patterns:
            match = re.match(pattern, repo_url)
            if match:
                return match.group(1), match.group(2)

        raise ValueError(f"Неподдерживаемый формат репозитория: {repo_url}")

    def get_cargo_toml_content(self, owner, repo, version):
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/Cargo.toml?ref={version}"

        try:
            # Добавляем User-Agent для GitHub API
            request = Request(url)
            request.add_header('User-Agent', 'PackageAnalyzer/1.0')

            with urlopen(request) as response:
                data = json.loads(response.read().decode())

                if 'content' not in data:
                    raise ValueError("Cargo.toml не найден в репозитории")

                # Декодируем base64 содержимое
                content = base64.b64decode(data['content']).decode('utf-8')
                return content

        except HTTPError as e:
            if e.code == 404:
                raise ValueError(f"Cargo.toml не найден для версии {version}")
            else:
                raise RuntimeError(f"Ошибка GitHub API: {e.code} {e.reason}")
        except URLError as e:
            raise RuntimeError(f"Ошибка сети: {e.reason}")

    def parse_dependencies(self, cargo_toml_content):
        dependencies = {}

        # Регулярные выражения для поиска зависимостей
        dependency_pattern = r'^(\w+)\s*=\s*(.+)$'
        section_pattern = r'^\[dependencies\]'
        in_dependencies_section = False

        for line in cargo_toml_content.split('\n'):
            line = line.strip()

            # Пропускаем комментарии и пустые строки
            if not line or line.startswith('#'):
                continue

            # Проверяем начало секции dependencies
            if line == '[dependencies]':
                in_dependencies_section = True
                continue
            # Проверяем конец секции dependencies (начало новой секции)
            elif line.startswith('[') and in_dependencies_section:
                break

            # Парсим зависимости в текущей секции
            if in_dependencies_section:
                match = re.match(dependency_pattern, line)
                if match:
                    dep_name = match.group(1)
                    dep_value = match.group(2).strip()

                    # Обрабатываем разные форматы зависимостей
                    if dep_value.startswith('{') and dep_value.endswith('}'):
                        # Зависимость в виде таблицы { version = "1.0", features = [...] }
                        try:
                            # Упрощенный парсинг для извлечения версии
                            version_match = re.search(r'version\s*=\s*"([^"]+)"', dep_value)
                            if version_match:
                                dependencies[dep_name] = version_match.group(1)
                            else:
                                dependencies[dep_name] = dep_value
                        except:
                            dependencies[dep_name] = dep_value
                    else:
                        # Простая строковая зависимость
                        dependencies[dep_name] = dep_value.strip('"')

        return dependencies

    def filter_dependencies(self, dependencies, filter_substring):
        if not filter_substring:
            return dependencies

        return {name: version for name, version in dependencies.items()
                if filter_substring.lower() in name.lower()}

    def display_dependencies(self, dependencies):
        package_name = self.config_data['package_name']
        version = self.config_data['version']

        print(f"Прямые зависимости пакета {package_name} версии {version}:")
        print("=" * 50)

        if not dependencies:
            print("Зависимости не найдены")
        else:
            for dep_name, dep_version in sorted(dependencies.items()):
                print(f"  - {dep_name}: {dep_version}")

        print("=" * 50)

    def run(self):
        try:
            print("Запуск анализатора зависимостей Rust-пакетов...")

            self.load_config()

            owner, repo = self.extract_github_info(self.config_data['repo_url'])
            print(f"Анализ репозитория: {owner}/{repo}")

            cargo_content = self.get_cargo_toml_content(owner, repo, self.config_data['version'])

            dependencies = self.parse_dependencies(cargo_content)

            filtered_deps = self.filter_dependencies(
                dependencies,
                self.config_data['filter_substring']
            )

            self.display_dependencies(filtered_deps)

            print("Анализ зависимостей завершен успешно!")

        except (FileNotFoundError, ValueError, TypeError, RuntimeError) as e:
            print(f"Ошибка: {str(e)}", file=sys.stderr)
            sys.exit(1)
        except KeyboardInterrupt:
            print("\nПрограмма прервана пользователем", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Неизвестная ошибка: {str(e)}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    analyzer = PackageAnalyzer()
    analyzer.run()