import tkinter as tk
from tkinter import scrolledtext
import shlex

class Emulator:
    def __init__(self, root):
        self.root = root
        self.root.title("Docker")
        
        # Настройка цветовой схемы (опционально)
        self.bg_color = "#1E1E1E"
        self.fg_color = "#FFFFFF"
        self.prompt_color = "#496FC1"
        
        # Создание текстового поля для вывода
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
        
        # Создание поля для ввода команд
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
        self.input_field.bind("<Return>", self.process_command)
        self.input_field.focus()
        
        # Настройка обработки команд
        self.exit_cmd = 'exit'
        
        # Вывод приветственного сообщения
        self.display_welcome()
    
    def display_welcome(self):
        welcome_msg = "Welcome to the terminal! For exit, enter 'exit' command.\n"
        self.output_area.config(state=tk.NORMAL)
        self.output_area.insert(tk.END, welcome_msg)
        self.output_area.config(state=tk.DISABLED)
        self.output_area.see(tk.END)
    
    def process_command(self, event):
        command = self.input_field.get()
        self.input_field.delete(0, tk.END)
        
        # Отображение введенной команды
        self.output_area.config(state=tk.NORMAL)
        self.output_area.insert(tk.END, f"docker$ {command}\n")
        
        # Обработка команды
        parts = shlex.split(command)
        if not parts:
            pass
        elif parts[0] == self.exit_cmd:
            self.output_area.insert(tk.END, "Terminating...\n")
            self.root.after(500, self.root.destroy)  # Задержка перед закрытием
        elif parts[0] == 'ls':
            self.output_area.insert(tk.END, f"{parts}\n")
        elif parts[0] == 'cd':
            self.output_area.insert(tk.END, f"{parts}\n")
        else:
            self.output_area.insert(tk.END, f"{command}: command doesn't exist.\n")
        
        # Прокрутка к концу и блокировка редактирования
        self.output_area.see(tk.END)
        self.output_area.config(state=tk.DISABLED)

if __name__ == "__main__":
    root = tk.Tk()
    emulator = Emulator(root)
    root.mainloop()