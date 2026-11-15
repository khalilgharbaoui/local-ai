import importlib.util
import sys

spec = importlib.util.spec_from_file_location("eval_module", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

REFERENCE = {
    "merge_intervals": '''
def merge_intervals(intervals):
    result = []
    for start, end in sorted(intervals):
        if result and start <= result[-1][1]:
            result[-1][1] = max(result[-1][1], end)
        else:
            result.append([start, end])
    return result
''',
    "parse_duration": '''
import re
def parse_duration(text):
    match = re.fullmatch(r"(?:(\\d+)d)?(?:(\\d+)h)?(?:(\\d+)m)?(?:(\\d+)s)?", text)
    if not text or not match:
        raise ValueError(text)
    days, hours, minutes, seconds = (int(part or 0) for part in match.groups())
    return days * 86400 + hours * 3600 + minutes * 60 + seconds
''',
    "roman_to_int": '''
def roman_to_int(s):
    pairs = [(1000,'M'),(900,'CM'),(500,'D'),(400,'CD'),(100,'C'),(90,'XC'),(50,'L'),(40,'XL'),(10,'X'),(9,'IX'),(5,'V'),(4,'IV'),(1,'I')]
    values = {'I':1,'V':5,'X':10,'L':50,'C':100,'D':500,'M':1000}
    if not s or any(char not in values for char in s):
        raise ValueError(s)
    total = 0
    for index, char in enumerate(s):
        value = values[char]
        total += -value if index + 1 < len(s) and values[s[index + 1]] > value else value
    number, out = total, ''
    for value, symbol in pairs:
        while number >= value:
            out += symbol
            number -= value
    if not 1 <= total <= 3999 or out != s:
        raise ValueError(s)
    return total
''',
    "split_csv_line": '''
def split_csv_line(line):
    fields, field, quoted, index = [], '', False, 0
    while index < len(line):
        char = line[index]
        if quoted:
            if char == '"' and index + 1 < len(line) and line[index + 1] == '"':
                field += '"'
                index += 1
            elif char == '"':
                quoted = False
            else:
                field += char
        elif char == '"':
            quoted = True
        elif char == ',':
            fields.append(field)
            field = ''
        else:
            field += char
        index += 1
    fields.append(field)
    return fields
''',
    "lru_cache": '''
from collections import OrderedDict
class LRUCache:
    def __init__(self, capacity):
        self.capacity, self.items = capacity, OrderedDict()
    def get(self, key):
        if key not in self.items:
            return -1
        self.items.move_to_end(key)
        return self.items[key]
    def put(self, key, value):
        if self.capacity <= 0:
            return
        self.items[key] = value
        self.items.move_to_end(key)
        if len(self.items) > self.capacity:
            self.items.popitem(last=False)
''',
    "topo_sort": '''
import heapq
def topo_sort(deps):
    nodes = set(deps) | {dep for values in deps.values() for dep in values}
    indegree = {node: 0 for node in nodes}
    children = {node: [] for node in nodes}
    for node, values in deps.items():
        for dep in values:
            indegree[node] += 1
            children[dep].append(node)
    ready = [node for node in nodes if indegree[node] == 0]
    heapq.heapify(ready)
    order = []
    while ready:
        node = heapq.heappop(ready)
        order.append(node)
        for child in children[node]:
            indegree[child] -= 1
            if indegree[child] == 0:
                heapq.heappush(ready, child)
    if len(order) != len(nodes):
        raise ValueError("cycle")
    return order
''',
    "bugfix_bisect": '''
def first_index_at_least(values, target):
    lo, hi = 0, len(values)
    while lo < hi:
        mid = (lo + hi) // 2
        if values[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    return lo
''',
}

for task in module.CODING_TASKS:
    passed, error = module.run_tests(REFERENCE[task["name"]], task["tests"])
    print(task["name"], "PASS" if passed else f"FAIL {error}")
print("extract:", repr(module.extract_code("text\n```python\nx = 1\n```\nmore")))
