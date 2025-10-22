import argparse
import sys
import os

def positive_int(value):
    ivalue = int(value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError(f"{value} не является положительным целым числом")
    return ivalue

def main():
    parser = argparse.ArgumentParser(description="Анализатор зависимостей пакетов")
    
    parser.add_argument(
        "-p", "--package-name",
        required=True,
        help="Имя анализируемого пакета"
    )
    
    parser.add_argument(
        "-r", "--repo",
        required=True,
        help="URL-адрес репозитория или путь к файлу тестового репозитория"
    )
    
    parser.add_argument(
        "-m", "--repo-mode",
        choices=["local", "remote"],
        default="local",
        help="Режим работы с тестовым репозиторием (local или remote)"
    )
    
    parser.add_argument(
        "-o", "--output",
        default="graph.png",
        help="Имя сгенерированного файла с изображением графа"
    )
    
    parser.add_argument(
        "-a", "--ascii-tree",
        action="store_true",
        help="Включить вывод зависимостей в формате ASCII-дерева"
    )
    
    parser.add_argument(
        "-d", "--max-depth",
        type=positive_int,
        default=3,
        help="Максимальная глубина анализа зависимостей (положительное целое число)"
    )
    
    parser.add_argument(
        "-f", "--filter",
        help="Подстрока для фильтрации пакетов"
    )

    args = parser.parse_args()

    # Проверка существования локального репозитория
    if args.repo_mode == "local" and not os.path.exists(args.repo):
        print(f"Ошибка: Локальный репозиторий '{args.repo}' не существует.")
        sys.exit(1)

    # Вывод параметров
    print("Параметры конфигурации:")
    print(f"  Имя пакета: {args.package_name}")
    print(f"  Репозиторий: {args.repo}")
    print(f"  Режим репозитория: {args.repo_mode}")
    print(f"  Выходной файл: {args.output}")
    print(f"  ASCII-дерево: {args.ascii_tree}")
    print(f"  Макс. глубина: {args.max_depth}")
    print(f"  Фильтр: {args.filter or 'Не задан'}")

if __name__ == "__main__":
    main()