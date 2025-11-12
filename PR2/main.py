import argparse
import json
import os
import re
import subprocess
import sys
from collections import deque, defaultdict
from typing import Dict, List, Set, Tuple, Optional

try:
    # для более красивых ASCII-деревьев, если доступно (не обязательно)
    from textwrap import indent
except Exception:
    indent = None


def positive_int(value: str) -> int:
    """Проверяет, что значение является положительным целым числом"""
    ivalue = int(value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError(f"{value} не является положительным целым числом")
    return ivalue


def sanitize_requirement(req: str) -> str:
    """Извлекает простое имя пакета из строки requires-dist.

    Примеры:
      'requests (>=2.0)' -> 'requests'
      'pkgname; extra == "dev"' -> 'pkgname'
      'pkgname[extra] (==1.0); python_version < "3.9"' -> 'pkgname'
    """
    if not req:
        return req
    # отделяем маркеры окружения
    req = req.split(';', 1)[0].strip()
    # удаляем дополнения в квадратных скобках
    req = re.sub(r"\[.*?\]", "", req)
    # удаляем спецификаторы версий
    req = re.split(r"\s|\(|<|>|=|!", req)[0]
    return req


class DependencySource:
    """Абстрактный источник метаданных пакетов.

    Конкретные реализации:
      - LocalGraphSource: читает JSON-отображение смежности (для тестового режима)
      - PyPISource: запрашивает PyPI JSON API и использует парсинг HTML как запасной вариант
      - LocalMetadataFilesSource: ищет JSON-файлы метаданных в локальной директории
    """

    def get_direct_dependencies(self, package_name: str) -> List[str]:
        raise NotImplementedError


class LocalGraphSource(DependencySource):
    """Тестовый источник: репозиторий - это JSON-файл, содержащий отображение смежности.

    Ключи и значения - имена пакетов (строки). Этот режим ожидает, что пакеты будут
    представлены заглавными буквами (но код работает с произвольными строками).
    """

    def __init__(self, graph_path: str):
        self.graph_path = graph_path
        self.graph = self._load_graph()

    def _load_graph(self) -> Dict[str, List[str]]:
        if not os.path.exists(self.graph_path):
            raise FileNotFoundError(f"Тестовый репозиторий '{self.graph_path}' не найден")
        with open(self.graph_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("Тестовый репозиторий должен содержать JSON-объект (mapping)")
        # убеждаемся, что все значения являются списками
        normalized = {k: list(v) if isinstance(v, list) else [v] for k, v in data.items()}
        return normalized

    def get_direct_dependencies(self, package_name: str) -> List[str]:
        return self.graph.get(package_name, [])


class PyPISource(DependencySource):
    """Источник, который запрашивает PyPI JSON API и использует простой парсинг HTML как запасной вариант."""

    def __init__(self):
        pass

    def _parse_requires_dist(self, requires_dist) -> List[str]:
        if not requires_dist:
            return []
        result = []
        for r in requires_dist:
            name = sanitize_requirement(r)
            if name:
                result.append(name)
        return result

    def get_direct_dependencies(self, package_name: str) -> List[str]:
        # Сначала пробуем JSON API
        import urllib.request
        import urllib.error
        import json

        api_url = f"https://pypi.org/pypi/{package_name}/json"
        try:
            with urllib.request.urlopen(api_url, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                requires = data.get('info', {}).get('requires_dist')
                return self._parse_requires_dist(requires)
        except Exception:
            # Запасной вариант: минимальная попытка парсинга HTML (сохраняет поведение оригинального скрипта)
            try:
                page_url = f"https://pypi.org/project/{package_name}/"
                with urllib.request.urlopen(page_url, timeout=10) as resp:
                    html = resp.read().decode(errors='ignore')
                # грубая эвристика для поиска зависимостей
                patterns = [r'Requires:</span>\s*([^<]+)', r'requires:</span>\s*([^<]+)']
                deps = []
                for pat in patterns:
                    for m in re.findall(pat, html, re.IGNORECASE | re.DOTALL):
                        # разделяем по запятой и точке с запятой
                        for piece in re.split(r'[;,]', m):
                            name = sanitize_requirement(piece)
                            if name:
                                deps.append(name)
                return list(dict.fromkeys(deps))
            except Exception:
                return []


class LocalMetadataFilesSource(DependencySource):
    """Режим локального репозитория: ищет в директории (или отдельном файле) JSON-метаданные
    и пытается извлечь requires_dist.

    Ожидаемая структура JSON-метаданных похожа на PyPI JSON (верхнеуровневый 'info' с
    списком 'requires_dist'), но реализация допускает и более простые структуры.
    """

    def __init__(self, repo_path: str):
        self.repo_path = repo_path

    def _find_metadata_files(self, package_name: str) -> List[str]:
        """Находит файлы метаданных для указанного пакета"""
        files = []
        if os.path.isfile(self.repo_path):
            files = [self.repo_path]
        else:
            for root, _, filenames in os.walk(self.repo_path):
                for fn in filenames:
                    if fn.endswith('.json') and package_name in fn:
                        files.append(os.path.join(root, fn))
        return files

    def _extract_from_file(self, path: str, package_name: str) -> List[str]:
        """Извлекает зависимости из файла метаданных"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Пробуем различные возможные структуры
            if isinstance(data, dict):
                if 'info' in data and isinstance(data['info'], dict):
                    requires = data['info'].get('requires_dist')
                    if requires:
                        return [sanitize_requirement(x) for x in requires]
                # Возможно, это отображение смежности (в стиле тестов)
                if package_name in data and isinstance(data[package_name], list):
                    return data[package_name]
            return []
        except Exception:
            return []

    def get_direct_dependencies(self, package_name: str) -> List[str]:
        files = self._find_metadata_files(package_name)
        for f in files:
            deps = self._extract_from_file(f, package_name)
            if deps:
                return deps
        return []


class DependencyGraph:
    """Строит граф зависимостей используя BFS и поддерживает операции над ним."""

    def __init__(self, source: DependencySource, max_depth: int = 3, name_filter: Optional[str] = None):
        self.source = source
        self.max_depth = max_depth
        self.name_filter = name_filter.lower() if name_filter else None
        # отображение смежности: узел -> множество(соседей)
        self.adj: Dict[str, Set[str]] = defaultdict(set)

    def _passes_filter(self, name: str) -> bool:
        """Проверяет, проходит ли имя пакета через фильтр"""
        if not name:
            return False
        if self.name_filter and self.name_filter in name.lower():
            return False
        return True

    def build_bfs(self, root: str) -> Tuple[Dict[str, Set[str]], Dict[str, int]]:
        """Строит ориентированный граф зависимостей, достижимый из `root`, используя BFS.

        Возвращает кортеж (отображение_смежности, отображение_глубин) где отображение_глубин[узел] - это
        глубина (расстояние в ребрах) от корня. Корень имеет глубину 0.
        """
        q = deque()
        depth: Dict[str, int] = {}
        seen: Set[str] = set()

        root = root.strip()
        if not self._passes_filter(root):
            return {}, {}

        q.append(root)
        depth[root] = 0
        seen.add(root)

        while q:
            current = q.popleft()
            current_depth = depth[current]
            if current_depth >= self.max_depth:
                # не расширяем соседей за пределы max_depth, но записываем узел
                continue
            try:
                deps = self.source.get_direct_dependencies(current)
            except Exception as e:
                print(f"Ошибка при получении зависимостей для {current}: {e}")
                deps = []

            for raw in deps:
                name = sanitize_requirement(raw)
                if not name:
                    continue
                if not self._passes_filter(name):
                    # полностью пропускаем отфильтрованные пакеты
                    continue
                self.adj[current].add(name)
                if name not in seen:
                    seen.add(name)
                    depth[name] = current_depth + 1
                    q.append(name)
                else:
                    # уже видели - все равно записываем ребро (цикл или поперечное ребро)
                    # но не добавляем узел обратно в очередь
                    depth.setdefault(name, min(depth.get(name, 10**9), current_depth + 1))

        return self.adj, depth

    def export_adjlist(self) -> Dict[str, List[str]]:
        """Экспортирует граф в виде списка смежности"""
        return {k: sorted(list(v)) for k, v in self.adj.items()}

    def ascii_tree(self, root: str, depth_map: Dict[str, int]) -> str:
        """Создает простое ASCII-дерево, ограниченное max_depth.

        Примечание: Поскольку граф может содержать циклы, это дерево строится путем
        следования структуре смежности, но избегая бесконечной рекурсии с помощью
        множества посещенных узлов для текущего пути.
        """
        lines = []

        def _recurse(node: str, prefix: str, visited_path: Set[str], current_depth: int):
            lines.append(f"{prefix}{node}")
            if current_depth >= self.max_depth:
                return
            if node in visited_path:
                lines.append(f"{prefix}  (обнаружен цикл к {node})")
                return
            visited_path.add(node)
            for child in sorted(self.adj.get(node, [])):
                _recurse(child, prefix + "  ", set(visited_path), current_depth + 1)

        _recurse(root, "", set(), 0)
        return "\n".join(lines)

def save_json(path: str, data) -> None:
    """Сохраняет данные в JSON-файл"""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Анализатор зависимостей пакетов (BFS)")

    parser.add_argument('-p', '--package-name', required=False, help='Имя анализируемого пакета (root)')
    parser.add_argument('-r', '--repo', required=False, help="URL/путь к репозиторию или тест-файлу")
    parser.add_argument('-m', '--repo-mode', choices=['local', 'remote', 'test'], default='local', help='Режим репозитория: local (dir or metadata), remote (PyPI), test (graph json)')
    parser.add_argument('-o', '--output', default='graph.json', help='Имя выходного файла (JSON) для сохранённого графа')
    parser.add_argument('-a', '--ascii-tree', action='store_true', help='Вывести ASCII-дерево зависимостей')
    parser.add_argument('-d', '--max-depth', type=positive_int, default=3, help='Максимальная глубина анализа')
    parser.add_argument('-f', '--filter', help='Подстрока для фильтрации пакетов (не учитывать)')
    parser.add_argument('--demo', action='store_true', help='Запустить демонстрацию работы на тестовых графах')

    args = parser.parse_args()

    if args.demo:
        run_demo()
        return

    if not args.package_name:
        print('Ошибка: нужно указать --package-name или использовать --demo')
        sys.exit(1)

    # Выбираем реализацию источника
    if args.repo_mode == 'test':
        if not args.repo:
            print('Ошибка: для test-режима нужно указать путь к JSON-файлу с графом через --repo')
            sys.exit(1)
        source = LocalGraphSource(args.repo)
    elif args.repo_mode == 'remote':
        source = PyPISource()
    else:  # local
        if not args.repo:
            print('Ошибка: для local-режима нужно указать путь к директории/файлу через --repo')
            sys.exit(1)
        source = LocalMetadataFilesSource(args.repo)

    graph = DependencyGraph(source, max_depth=args.max_depth, name_filter=args.filter)
    adj, depth_map = graph.build_bfs(args.package_name)

    adjlist = graph.export_adjlist()

    # Сохраняем результаты
    output_path = args.output
    save_json(output_path, {
        'root': args.package_name,
        'max_depth': args.max_depth,
        'filter': args.filter,
        'adjacency': adjlist,
        'depths': depth_map,
    })

    print(f"Сохранён граф в {output_path}")

    if args.ascii_tree:
        tree = graph.ascii_tree(args.package_name, depth_map)
        print('\nASCII-дерево:')
        print('-' * 40)
        print(tree)

# ----------------------- Демонстрационные вспомогательные функции -----------------------

def _create_test_graph_file(path: str, graph: Dict[str, List[str]]):
    """Создает тестовый файл графа"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    save_json(path, graph)


def run_demo():
    """Демонстрирует функциональность на нескольких тестовых случаях.

    Создает временную папку `demo_test_repo` с несколькими JSON-файлами графов,
    демонстрирующих ациклические графы, циклы, фильтрацию и ограничение глубины.
    Затем запускает анализатор на этих графах и выводит результаты. Если git доступен,
    также создает коммиты для этих результатов.
    """
    base = os.path.abspath('demo_test_repo')
    os.makedirs(base, exist_ok=True)

    cases = {
        'acyclic.json': {
            'A': ['B', 'C'],
            'B': ['D'],
            'C': [],
            'D': []
        },
        'cycle.json': {
            'A': ['B'],
            'B': ['C'],
            'C': ['A']
        },
        'complex.json': {
            'A': ['B', 'C'],
            'B': ['D', 'E'],
            'C': ['F'],
            'D': ['G'],
            'E': ['C'],
            'F': [],
            'G': ['A']
        }
    }

    print('Создаю тестовые графы в demo_test_repo/...')
    for name, graph in cases.items():
        path = os.path.join(base, name)
        _create_test_graph_file(path, graph)
        print(f'  - {path}')

    demo_runs = [
        # ациклический полная глубина
        (os.path.join(base, 'acyclic.json'), 'A', 5, None),
        # обнаружение цикла
        (os.path.join(base, 'cycle.json'), 'A', 10, None),
        # применяем фильтр для удаления узлов содержащих 'G' (здесь нет) и ограничение глубины
        (os.path.join(base, 'complex.json'), 'A', 2, None),
        # фильтруем 'C' для тестирования фильтра
        (os.path.join(base, 'complex.json'), 'A', 5, 'C'),
    ]

    for repo_path, root, max_d, flt in demo_runs:
        print('\n' + '=' * 60)
        print(f"Демонстрация: repo={repo_path}, root={root}, max_depth={max_d}, filter={flt}")
        src = LocalGraphSource(repo_path)
        g = DependencyGraph(src, max_depth=max_d, name_filter=flt)
        adj, depths = g.build_bfs(root)
        adjlist = g.export_adjlist()
        outname = os.path.join(base, f'result_{os.path.basename(repo_path)}_{root}.json')
        save_json(outname, {'root': root, 'adjacency': adjlist, 'depths': depths})
        print(f"Сохранён результат в {outname}")
        print('Список смежности:')
        print(json.dumps(adjlist, ensure_ascii=False, indent=2))
        print('Глубины:')
        print(json.dumps(depths, ensure_ascii=False, indent=2))
        print('\nASCII-дерево:')
        print('-' * 40)
        print(g.ascii_tree(root, depths))
        # пробуем закоммитить демо-результаты в корень demo_test_repo (инициализируем git если нужно)


if __name__ == '__main__':
    main()