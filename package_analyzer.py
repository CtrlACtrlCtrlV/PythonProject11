#!/usr/bin/env python3

import yaml
import sys
import base64
import json
import collections
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import re


class PackageAnalyzer:
    def __init__(self, config_path="config_test1.yaml"):
        self.config_path = Path(config_path)
        self.config_data = {}

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

    def extract_github_info(self, repo_url):
        patterns = [
            r'https://github\.com/([^/]+)/([^/]+)',
            r'git@github\.com:([^/]+)/([^/]+)\.git'
        ]

        for pattern in patterns:
            match = re.match(pattern, repo_url)
            if match:
                return match.group(1), match.group(2)

        raise ValueError(f"Неподдерживаемый формат URL репозитория: {repo_url}")

    def get_cargo_toml_content(self, owner, repo, version):
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/Cargo.toml?ref={version}"

        try:
            request = Request(url)
            request.add_header('User-Agent', 'PackageAnalyzer/1.0')

            with urlopen(request) as response:
                data = json.loads(response.read().decode())

                if 'content' not in data:
                    raise ValueError("Cargo.toml не найден в репозитории")

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

        dependency_pattern = r'^(\w+)\s*=\s*(.+)$'
        section_pattern = r'^\[dependencies\]'
        in_dependencies_section = False

        for line in cargo_toml_content.split('\n'):
            line = line.strip()

            if not line or line.startswith('#'):
                continue

            if line == '[dependencies]':
                in_dependencies_section = True
                continue
            elif line.startswith('[') and in_dependencies_section:
                break

            if in_dependencies_section:
                match = re.match(dependency_pattern, line)
                if match:
                    dep_name = match.group(1)
                    dep_value = match.group(2).strip()

                    if dep_value.startswith('{') and dep_value.endswith('}'):
                        version_match = re.search(r'version\s*=\s*"([^"]+)"', dep_value)
                        if version_match:
                            dependencies[dep_name] = version_match.group(1)
                        else:
                            dependencies[dep_name] = dep_value
                    else:
                        dependencies[dep_name] = dep_value.strip('"')

        return dependencies

    def build_dependency_graph_bfs(self, start_package, start_version):
        graph = {}
        visited = set()
        queue = collections.deque([(start_package, start_version)])

        print(f"Построение графа зависимостей для {start_package}...")

        while queue:
            current_package, current_version = queue.popleft()

            if current_package in visited:
                print(f"Обнаружен цикл: {current_package} уже посещен")
                continue

            visited.add(current_package)

            if self.config_data['filter_substring'] and \
                    self.config_data['filter_substring'].lower() in current_package.lower():
                print(f"Пропуск пакета {current_package} (фильтр: {self.config_data['filter_substring']})")
                continue

            try:
                owner, repo = self.extract_github_info(self.config_data['repo_url'])
                cargo_content = self.get_cargo_toml_content(owner, repo, current_version)
                dependencies = self.parse_dependencies(cargo_content)

                graph[current_package] = dependencies

                for dep_name, dep_version in dependencies.items():
                    if dep_name not in visited:
                        queue.append((dep_name, current_version))
                        print(f"Добавлена зависимость: {current_package} -> {dep_name}")

            except Exception as e:
                print(f"Ошибка при обработке пакета {current_package}: {e}")
                graph[current_package] = {}

        return graph

    def read_test_graph(self, file_path):
        graph = {}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    parts = line.split()
                    if len(parts) >= 1:
                        package = parts[0]
                        dependencies = parts[1].split(',') if len(parts) > 1 else []
                        graph[package] = dependencies

        except FileNotFoundError:
            raise FileNotFoundError(f"Тестовый файл {file_path} не найден")
        except Exception as e:
            raise RuntimeError(f"Ошибка чтения тестового файла: {e}")

        return graph

    def build_test_graph_bfs(self, test_graph, start_package):
        graph = {}
        visited = set()
        queue = collections.deque([start_package])

        print(f"Построение тестового графа из {start_package}...")

        while queue:
            current_package = queue.popleft()

            if current_package in visited:
                print(f"Обнаружен цикл: {current_package} уже посещен")
                continue

            visited.add(current_package)

            if self.config_data['filter_substring'] and \
                    self.config_data['filter_substring'].lower() in current_package.lower():
                print(f"Пропуск пакета {current_package} (фильтр: {self.config_data['filter_substring']})")
                continue

            dependencies = test_graph.get(current_package, [])
            graph[current_package] = {dep: "test-version" for dep in dependencies}

            for dep in dependencies:
                if dep not in visited:
                    queue.append(dep)
                    print(f"Добавлена зависимость: {current_package} -> {dep}")

        return graph

    def print_graph_info(self, graph):
        """Выводит информацию о построенном графе"""
        print("\n" + "=" * 60)
        print("ИНФОРМАЦИЯ О ГРАФЕ ЗАВИСИМОСТЕЙ")
        print("=" * 60)

        total_packages = len(graph)
        total_dependencies = sum(len(deps) for deps in graph.values())

        print(f"Всего пакетов в графе: {total_packages}")
        print(f"Всего зависимостей: {total_dependencies}")
        print(f"Фильтр подстроки: '{self.config_data['filter_substring']}'")

        print("\nСтруктура графа:")
        for package, dependencies in sorted(graph.items()):
            if dependencies:
                dep_list = ", ".join(sorted(dependencies.keys()))
                print(f"  {package} -> {dep_list}")
            else:
                print(f"  {package} -> (нет зависимостей)")

        print("\nАнализ графа:")
        has_dependencies = any(dependencies for dependencies in graph.values())
        if not has_dependencies:
            print("  Граф не содержит зависимостей")
        elif total_packages == 1:
            print("  Граф содержит только корневой пакет")
        else:
            print("  Граф содержит транзитивные зависимости")

    def run(self):
        try:
            print("Анлизатор графа ...")

            # Загрузка конфигурации
            self.load_config()

            mode = self.config_data['mode']
            package_name = self.config_data['package_name']

            if mode == "test":
                print(f"Режим: ТЕСТОВЫЙ (файл: {self.config_data['repo_url']})")
                test_graph = self.read_test_graph(self.config_data['repo_url'])
                graph = self.build_test_graph_bfs(test_graph, package_name)
            else:
                print(f"Режим: РЕАЛЬНЫЙ (репозиторий: {self.config_data['repo_url']})")
                graph = self.build_dependency_graph_bfs(package_name, self.config_data['version'])

            self.print_graph_info(graph)

            print(f"\nГраф успешно построен! Выходное изображение: {self.config_data['output_image']}")

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