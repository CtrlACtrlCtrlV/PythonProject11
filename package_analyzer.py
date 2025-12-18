import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import shlex
import json
import urllib.request
import re


class VFSApp:
    def __init__(self, root):
        self.root = root
        self.root.title("VFS - Виртуальная Файловая Система")
        self.current_path = "/"

        self.create_widgets()

    def create_widgets(self):

        self.output_area = scrolledtext.ScrolledText(
            self.root,
            width=90,
            height=25,
            state='disabled',
            font=("Courier New", 10)
        )
        self.output_area.pack(padx=10, pady=10, fill='both', expand=True)


        input_frame = ttk.Frame(self.root)
        input_frame.pack(padx=10, pady=5, fill='x')

        ttk.Label(input_frame, text="VFS>", font=("Arial", 10, "bold")).pack(side='left')

        self.command_entry = ttk.Entry(input_frame, width=80, font=("Arial", 10))
        self.command_entry.pack(side='left', fill='x', expand=True, padx=(5, 0))
        self.command_entry.bind('<Return>', self.execute_command)


        ttk.Button(
            input_frame,
            text="Выполнить",
            command=self.execute_command
        ).pack(side='right', padx=(5, 0))


        self.status_var = tk.StringVar()
        self.status_var.set("Готов")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief='sunken')
        status_bar.pack(side='bottom', fill='x')


        self.print_output("=" * 80)
        self.print_output("VFS - Виртуальная Файловая Система")
        self.print_output("Версия 2.0 (с поддержкой анализа зависимостей Cargo)")
        self.print_output("=" * 80)
        self.print_output("\nДоступные команды:")
        self.print_output("  ls [args]           - список файлов (заглушка)")
        self.print_output("  cd <path>           - сменить директорию")
        self.print_output("  deps <crate> <ver>  - показать зависимости пакета Rust")
        self.print_output("  help                - показать справку")
        self.print_output("  exit                - выход\n")

    def execute_command(self, event=None):
        command_string = self.command_entry.get().strip()
        self.command_entry.delete(0, 'end')

        if not command_string:
            return

        self.print_output(f"> {command_string}")

        try:
            parts = shlex.split(command_string)
        except ValueError as e:
            self.print_output(f"Ошибка парсинга: {str(e)}", error=True)
            return

        if not parts:
            return

        cmd = parts[0].lower()
        args = parts[1:]


        if cmd == "exit":
            self.root.quit()
        elif cmd == "ls":
            self.cmd_ls(args)
        elif cmd == "cd":
            self.cmd_cd(args)
        elif cmd == "deps":
            self.cmd_deps(args)
        elif cmd == "help":
            self.cmd_help()
        else:
            self.print_output(f"Ошибка: неизвестная команда '{cmd}'", error=True)

    def cmd_ls(self, args):
        """Заглушка для команды ls"""
        if args:
            self.print_output(f"Команда 'ls' с аргументами: {args}")
        else:
            self.print_output("Команда 'ls': вывод списка файлов")
            self.print_output("drwxr-xr-x  user user  4096 Dec  1 10:00 .")
            self.print_output("drwxr-xr-x  user user  4096 Dec  1 10:00 ..")
            self.print_output("-rw-r--r--  user user   123 Dec  1 10:00 file.txt")
            self.print_output("drwxr-xr-x  user user  4096 Dec  1 10:00 directory")

    def cmd_cd(self, args):
        """Заглушка для команды cd"""
        if len(args) != 1:
            self.print_output("Ошибка: команда 'cd' требует ровно один аргумент", error=True)
            return
        self.print_output(f"Изменение директории на: {args[0]}")
        self.current_path = args[0]
        self.print_output(f"Текущий путь: {self.current_path}")

    def cmd_deps(self, args):
        """Получение зависимостей пакета Rust/Cargo"""
        if len(args) != 2:
            self.print_output("Ошибка: команда 'deps' требует два аргумента: <пакет> <версия>", error=True)
            self.print_output("Пример: deps serde 1.0.0", error=True)
            return

        crate_name = args[0]
        crate_version = args[1]

        self.status_var.set(f"Получение зависимостей для {crate_name} {crate_version}...")
        self.root.update()

        try:
            dependencies = self.get_cargo_dependencies(crate_name, crate_version)
            self.display_dependencies(crate_name, crate_version, dependencies)
        except Exception as e:
            self.print_output(f"Ошибка при получении зависимостей: {str(e)}", error=True)
        finally:
            self.status_var.set("Готов")

    def get_cargo_dependencies(self, crate_name, version):
        """Получение зависимостей из Cargo.toml через crates.io API"""

        api_url = f"https://crates.io/api/v1/crates/{crate_name}/{version}"

        self.print_output(f"Запрос к API: {api_url}")

        try:

            req = urllib.request.Request(
                api_url,
                headers={'User-Agent': 'VFS-App/1.0'}
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status != 200:
                    raise Exception(f"HTTP ошибка: {response.status}")

                data = json.loads(response.read().decode('utf-8'))


                dependencies = []


                if 'version' not in data:
                    raise Exception("Информация о версии не найдена в ответе API")

                version_data = data['version']


                if 'dependencies' in version_data:
                    for dep in version_data['dependencies']:
                        dep_info = {
                            'name': dep.get('crate_id', 'unknown'),
                            'version_req': dep.get('req', '*'),
                            'features': dep.get('features', []),
                            'optional': dep.get('optional', False),
                            'kind': dep.get('kind', 'normal')
                        }
                        dependencies.append(dep_info)

                return dependencies

        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise Exception(f"Пакет '{crate_name}' версии '{version}' не найден")
            else:
                raise Exception(f"Ошибка HTTP: {e.code} - {e.reason}")
        except urllib.error.URLError as e:
            raise Exception(f"Ошибка подключения: {str(e)}")
        except json.JSONDecodeError as e:
            raise Exception(f"Ошибка разбора JSON: {str(e)}")
        except Exception as e:
            raise Exception(f"Неизвестная ошибка: {str(e)}")

    def display_dependencies(self, crate_name, version, dependencies):
        """Отображение зависимостей в красивом формате"""
        self.print_output("=" * 80)
        self.print_output(f"ЗАВИСИМОСТИ ПАКЕТА: {crate_name} {version}")
        self.print_output("=" * 80)

        if not dependencies:
            self.print_output("  Пакет не имеет зависимостей")
            return


        normal_deps = [d for d in dependencies if d['kind'] == 'normal']
        dev_deps = [d for d in dependencies if d['kind'] == 'dev']
        build_deps = [d for d in dependencies if d['kind'] == 'build']

        if normal_deps:
            self.print_output("\nОбычные зависимости:")
            for dep in normal_deps:
                optional = " (опционально)" if dep['optional'] else ""
                features = f" [фичи: {', '.join(dep['features'])}]" if dep['features'] else ""
                self.print_output(f"  • {dep['name']} {dep['version_req']}{optional}{features}")

        if dev_deps:
            self.print_output("\nЗависимости для разработки:")
            for dep in dev_deps:
                self.print_output(f"  • {dep['name']} {dep['version_req']}")

        if build_deps:
            self.print_output("\nЗависимости для сборки:")
            for dep in build_deps:
                self.print_output(f"  • {dep['name']} {dep['version_req']}")

        self.print_output(f"\nВсего зависимостей: {len(dependencies)}")
        self.print_output("=" * 80)

    def cmd_help(self):
        """Вывод справки по командам"""
        self.print_output("\nСПРАВКА ПО КОМАНДАМ:")
        self.print_output("=" * 50)
        self.print_output("ls [аргументы]")
        self.print_output("  Вывод списка файлов и директорий")
        self.print_output("")
        self.print_output("cd <путь>")
        self.print_output("  Изменение текущей директории")
        self.print_output("")
        self.print_output("deps <пакет> <версия>")
        self.print_output("  Получение зависимостей пакета Rust/Cargo")
        self.print_output("  Пример: deps serde 1.0.0")
        self.print_output("")
        self.print_output("help")
        self.print_output("  Вывод этой справки")
        self.print_output("")
        self.print_output("exit")
        self.print_output("  Выход из программы")
        self.print_output("=" * 50)

    def print_output(self, text, error=False):
        """Вывод текста в область вывода"""
        self.output_area.configure(state='normal')

        if error:
            self.output_area.tag_configure('error', foreground='red')
            self.output_area.insert('end', text + '\n', 'error')
        else:
            self.output_area.insert('end', text + '\n')

        self.output_area.see('end')
        self.output_area.configure(state='disabled')


def main():
    root = tk.Tk()
    root.geometry("900x600")

    # Центрирование окна
    root.update_idletasks()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    window_width = root.winfo_width()
    window_height = root.winfo_height()

    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")

    app = VFSApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()