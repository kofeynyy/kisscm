import argparse
import sys
import os
import json
import urllib.request
import urllib.error
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
import re

def positive_int(value):
    ivalue = int(value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError(f"{value} не является положительным целым числом")
    return ivalue

class PyPIParser(HTMLParser):
    """Парсер для извлечения ссылок на пакеты из HTML страницы PyPI"""
    def __init__(self):
        super().__init__()
        self.package_links = []
        
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            attrs_dict = dict(attrs)
            href = attrs_dict.get('href', '')
            if href and ('/packages/' in href or href.endswith('.whl') or href.endswith('.tar.gz')):
                self.package_links.append(href)

class DependencyAnalyzer:
    """Анализатор зависимостей пакетов"""
    
    def __init__(self, repo, repo_mode):
        self.repo = repo
        self.repo_mode = repo_mode
        
    def get_package_metadata(self, package_name):
        """Получить метаданные пакета"""
        if self.repo_mode == "remote":
            return self._get_remote_package_metadata(package_name)
        else:
            return self._get_local_package_metadata(package_name)
    
    def _get_remote_package_metadata(self, package_name):
        """Получить метаданные пакета из удаленного репозитория"""
        try:
            # Пытаемся получить данные через JSON API PyPI
            url = f"https://pypi.org/pypi/{package_name}/json"
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read().decode())
                return data
        except urllib.error.URLError:
            # Если не удалось через API, парсим HTML страницу
            return self._parse_pypi_html(package_name)
    
    def _parse_pypi_html(self, package_name):
        """Парсинг HTML страницы пакета на PyPI"""
        try:
            url = f"https://pypi.org/project/{package_name}/"
            with urllib.request.urlopen(url) as response:
                html_content = response.read().decode()
                
            # Ищем зависимости в HTML контенте
            dependencies = self._extract_dependencies_from_html(html_content)
            
            return {
                "info": {
                    "name": package_name,
                    "requires_dist": dependencies
                }
            }
        except Exception as e:
            print(f"Ошибка при парсинге HTML для пакета {package_name}: {e}")
            return {"info": {"name": package_name, "requires_dist": []}}
    
    def _extract_dependencies_from_html(self, html_content):
        """Извлечение зависимостей из HTML контента"""
        dependencies = []
        
        # Паттерны для поиска зависимостей в HTML
        patterns = [
            r'Requires:</span>\s*([^<]+)',  # Для новой версии PyPI
            r'requires:</span>\s*([^<]+)',  # Альтернативный вариант
            r'Requires Dist</th><td><ul><li>([^<]+)</li>',  # Старая версия PyPI
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                # Очистка и разделение зависимостей
                deps = [dep.strip() for dep in match.split(',')]
                dependencies.extend(deps)
        
        # Удаление дубликатов и пустых строк
        dependencies = list(set([dep for dep in dependencies if dep]))
        
        return dependencies
    
    def _get_local_package_metadata(self, package_name):
        """Получить метаданные пакета из локального репозитория"""
        # Для локального режима ищем файлы с метаданными
        metadata_files = []
        
        if os.path.isfile(self.repo):
            # Если указан файл, проверяем его
            if self.repo.endswith('.json'):
                with open(self.repo, 'r') as f:
                    return json.load(f)
        elif os.path.isdir(self.repo):
            # Если указана директория, ищем соответствующие файлы
            for root, dirs, files in os.walk(self.repo):
                for file in files:
                    if file.endswith('.json') and package_name in file:
                        metadata_files.append(os.path.join(root, file))
        
        # Если нашли файлы метаданных, используем первый подходящий
        if metadata_files:
            with open(metadata_files[0], 'r') as f:
                return json.load(f)
        
        # Если файлов нет, возвращаем пустые данные
        return {"info": {"name": package_name, "requires_dist": []}}
    
    def get_direct_dependencies(self, package_name):
        """Получить прямые зависимости пакета"""
        metadata = self.get_package_metadata(package_name)
        
        if "info" in metadata and "requires_dist" in metadata["info"]:
            dependencies = metadata["info"]["requires_dist"]
            if dependencies is not None:
                return dependencies
        
        return []

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
    print()

    # Анализ зависимостей
    analyzer = DependencyAnalyzer(args.repo, args.repo_mode)
    
    print(f"Анализ прямых зависимостей пакета '{args.package_name}':")
    print("-" * 50)
    
    try:
        dependencies = analyzer.get_direct_dependencies(args.package_name)
        
        if dependencies:
            print("Прямые зависимости:")
            for i, dep in enumerate(dependencies, 1):
                print(f"  {i}. {dep}")
        else:
            print("Прямые зависимости не найдены.")
            
    except Exception as e:
        print(f"Ошибка при анализе зависимостей: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()