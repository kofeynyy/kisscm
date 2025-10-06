import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox
import shlex
import argparse
import os
import sys

class Emulator:
    def __init__(self, root, vfs_path=None, script_path=None):
        self.root = root
        self.root.title("Docker")

        self.vfs_path = vfs_path
        self.script_path = script_path

        self.bg_color = "#1E1E1E"
        self.fg_color = "#FFFFFF"
        self.prompt_color = "#496FC1"

        # Текстовое поле для вывода
        self.output_area = scrolledtext.ScrolledText(
            root,
            wrap=tk.WORD,
            width=80,
            height=25,
            bg=self.bg_color,
            fg=self.fg_color,
            insertbackground=self.fg_color,
            font=("Courier New", 10)
        )
        self.output_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        self.output_area.config(state=tk.DISABLED)

        # Поле для ввода команд
        self.input_frame = tk.Frame(root, bg=self.bg_color)
        self.input_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.prompt_label = tk.Label(
            self.input_frame,
            text="docker$ ",
            fg=self.prompt_color,
            bg=self.bg_color,
            font=("Courier New", 10)
        )
        self.prompt_label.pack(side=tk.LEFT)

        self.input_field = tk.Entry(
            self.input_frame,
            bg=self.bg_color,
            fg=self.fg_color,
            insertbackground=self.fg_color,
            font=("Courier New", 10)
        )
        self.input_field.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.input_field.bind("<Return>", self.process_command_event)
        self.input_field.focus()

        # Настройка обработки команд
        self.exit_cmd = 'exit'

        # Вывод приветственного сообщения и отладочных параметров
        self.display_welcome()
        self.display_debug_info()

        # Если задан стартовый скрипт через argv — выполнить его после старта интерфейса
        if self.script_path:
            self.root.after(100, self.run_startup_script)

    def display_welcome(self):
        welcome_msg = "Welcome to the terminal! For exit, enter 'exit' command.\n"
        self._append_output(welcome_msg)

    def display_debug_info(self):
        debug_lines = [
            "\n=== Debug: startup parameters ===",
            f"VFS path    : {self.vfs_path!s}",
            f"Startup file: {self.script_path!s}",
            "=================================\n"
        ]
        self._append_output("\n".join(debug_lines))

    def _append_output(self, text):
        self.output_area.config(state=tk.NORMAL)
        self.output_area.insert(tk.END, text)
        self.output_area.config(state=tk.DISABLED)
        self.output_area.see(tk.END)

    def process_command_event(self, event):
        command = self.input_field.get()
        self.input_field.delete(0, tk.END)
        # При интерактивном вводе показываем введённую команду и выполняем её
        self._append_output(f"docker$ {command}\n")
        self.execute_command(command)

    def execute_command(self, command):
        """
        Выполняет команду и выводит результат в output_area.
        Используется и интерактивно, и для стартового скрипта.
        Поддерживает интерактивное управление параметрами через 'set' и 'run-script'.
        """
        parts = []
        try:
            parts = shlex.split(command)
        except ValueError as e:
            # Ошибка парсинга, вывести сообщение
            self._append_output(f"Error parsing command: {e}\n")
            return

        if not parts:
            return

        cmd = parts[0].lower()

        # --- Управление параметрами через консоль ---
        if cmd == 'set':
            # синтаксис: set vfs <path>  или set script <path>
            if len(parts) < 3:
                self._append_output("set: usage: set vfs <path> | set script <path>\n")
                return
            key = parts[1].lower()
            value = " ".join(parts[2:])  # поддержка путей с пробелами
            if key == 'vfs':
                self.vfs_path = os.path.abspath(value)
                self._append_output(f"[debug] VFS path set to: {self.vfs_path}\n")
            elif key == 'script':
                self.script_path = os.path.abspath(value)
                self._append_output(f"[debug] Startup script set to: {self.script_path}\n")
            else:
                self._append_output("set: unknown key. Use 'vfs' or 'script'.\n")
            return

        if cmd in ('show',):
            # show params
            if len(parts) == 1 or (len(parts) >= 2 and parts[1].lower() == 'params'):
                self.display_debug_info()
            else:
                self._append_output("show: usage: show params\n")
            return

        if cmd in ('run-script', 'run', 'source'):
            if not self.script_path:
                self._append_output("run: no startup script set. Use 'set script <path>'.\n")
                return
            # Выполнить текущий script (как если бы он был передан через argv)
            self.run_startup_script()
            return

        # --- прежние команды (только вывод аргументов) ---
        if cmd == self.exit_cmd:
            self._append_output("Terminating...\n")
            self.root.after(500, self.root.destroy)
        elif cmd == 'ls':
            # По требованию: реализуем ls *только* как вывод разобранных аргументов
            self._append_output(f"{parts}\n")
        elif cmd == 'cd':
            # cd должен быть реализован чисто на уровне вывода аргументов
            if len(parts) >= 2:
                self._append_output(f"{parts}\n")
            else:
                self._append_output("cd: missing argument\n")
        else:
            self._append_output(f"{command}: command doesn't exist.\n")

    def run_startup_script(self):
        """Читает и выполняет команды из стартового скрипта (self.script_path).
        Комментарии начинающиеся с '#' игнорируются. Во время выполнения каждая
        команда выводится как ввод (docker$ ...) и затем её результат.
        """
        path = self.script_path
        if not path:
            return

        if not os.path.isfile(path):
            self._append_output(f"Startup script not found: {path}\n")
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            self._append_output(f"Failed to read startup script: {e}\n")
            return

        self._append_output(f"\n--- Executing startup script: {path} ---\n")
        for raw_line in lines:
            # Убираем переносы и пробелы
            line = raw_line.rstrip("\n").rstrip("\r")
            stripped = line.strip()
            if not stripped:
                # пропустить пустые строки
                continue
            # Поддержка комментариев: строки, начинающиеся с '#', игнорируем
            if stripped.startswith("#"):
                continue

            # Показываем ввод (как от пользователя) и выполняем
            self._append_output(f"docker$ {stripped}\n")
            self.execute_command(stripped)
        self._append_output(f"--- End of startup script ---\n\n")


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Simple Docker-like emulator")
    parser.add_argument(
        "-v", "--vfs",
        dest="vfs_path",
        help="Path to physical location of VFS",
        default=None
    )
    parser.add_argument(
        "-s", "--script",
        dest="script_path",
        help="Path to startup script containing emulator commands",
        default=None
    )
    return parser.parse_args(argv)


def prompt_for_required_paths(default_vfs=None, default_script=None):
    """
    Открывает модальные диалоги (Tk) и принудительно требует ввод непустых путей
    для VFS и стартового скрипта. Возвращает (vfs_path, script_path) как строки.
    Если пользователь нажмёт Отмена и подтвердит выход — программа завершится.
    """
    # Создаём временный root для диалогов
    dialog_root = tk.Tk()
    dialog_root.withdraw()
    dialog_root.lift()
    dialog_root.attributes("-topmost", True)

    try:
        # VFS path
        while True:
            vfs = simpledialog.askstring(
                "VFS path required",
                "Enter path to physical VFS (required):",
                initialvalue=(default_vfs or ""),
                parent=dialog_root
            )
            if vfs is None:
                # пользователь нажал Cancel
                if messagebox.askyesno("Exit?", "No VFS provided. Exit application?", parent=dialog_root):
                    dialog_root.destroy()
                    sys.exit(0)
                else:
                    continue
            vfs = vfs.strip()
            if vfs == "":
                messagebox.showwarning("Input required", "VFS path cannot be empty.", parent=dialog_root)
                continue
            # Принудительно принимаем значение (не проверяем существование)
            break

        # Script path
        while True:
            script = simpledialog.askstring(
                "Startup script required",
                "Enter path to startup script (required):",
                initialvalue=(default_script or ""),
                parent=dialog_root
            )
            if script is None:
                if messagebox.askyesno("Exit?", "No startup script provided. Exit application?", parent=dialog_root):
                    dialog_root.destroy()
                    sys.exit(0)
                else:
                    continue
            script = script.strip()
            if script == "":
                messagebox.showwarning("Input required", "Startup script path cannot be empty.", parent=dialog_root)
                continue
            break

        return vfs, script
    finally:
        try:
            dialog_root.destroy()
        except:
            pass


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])

    # Принудительный ввод (диалоги) — значения по умолчанию берём из argv, если они есть
    vfs_val, script_val = prompt_for_required_paths(default_vfs=args.vfs_path, default_script=args.script_path)

    # Теперь создаём основное окно эмулятора с полученными путями
    root = tk.Tk()
    emulator = Emulator(root, vfs_path=vfs_val, script_path=script_val)
    root.mainloop()
