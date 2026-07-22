# Python面试题

## 基础概念

### 什么是GIL？它对多线程有什么影响？

GIL（Global Interpreter Lock）是CPython解释器中的全局解释器锁。它确保同一时刻只有一个线程执行Python字节码。

影响：
- CPU密集型任务：多线程无法利用多核，建议使用多进程
- IO密集型任务：GIL影响较小，多线程仍然有效
- 解决方案：使用multiprocessing、asyncio或C扩展

### 深拷贝和浅拷贝的区别

浅拷贝只复制对象的引用，深拷贝递归复制所有子对象。

```python
import copy

a = [[1, 2], [3, 4]]
b = copy.copy(a)      # 浅拷贝
c = copy.deepcopy(a)  # 深拷贝

a[0][0] = 99
print(b[0][0])  # 99，浅拷贝受影响
print(c[0][0])  # 1，深拷贝不受影响
```

### 装饰器的作用和实现

装饰器是在不修改原函数代码的情况下扩展函数功能的设计模式。

```python
def timer(func):
    def wrapper(*args, **kwargs):
        import time
        start = time.time()
        result = func(*args, **kwargs)
        print(f"耗时: {time.time() - start:.2f}s")
        return result
    return wrapper

@timer
def slow_function():
    import time
    time.sleep(1)
```

### 生成器和迭代器

迭代器：实现__iter__和__next__方法的对象
生成器：使用yield关键字的函数，自动实现迭代器协议

```python
# 生成器
def fibonacci():
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b

# 使用
fib = fibonacci()
for _ in range(10):
    print(next(fib))
```

## 高级特性

### async/await的使用场景

async/await用于异步编程，适合IO密集型任务：

```python
import asyncio

async def fetch_data(url):
    # 模拟IO操作
    await asyncio.sleep(1)
    return f"Data from {url}"

async def main():
    tasks = [fetch_data(f"http://api.com/{i}") for i in range(5)]
    results = await asyncio.gather(*tasks)
    print(results)

asyncio.run(main())
```

### 上下文管理器

使用with语句管理资源：

```python
class DatabaseConnection:
    def __enter__(self):
        self.conn = connect_db()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()

# 使用
with DatabaseConnection() as conn:
    conn.execute("SELECT * FROM users")
```

### 元类

元类是创建类的类：

```python
class SingletonMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class Database(metaclass=SingletonMeta):
    pass
```

## 常见面试代码题

### 列表去重并保持顺序

```python
def deduplicate(lst):
    seen = set()
    return [x for x in lst if not (x in seen or seen.add(x))]
```

### 字典按值排序

```python
d = {"a": 3, "b": 1, "c": 2}
sorted_d = dict(sorted(d.items(), key=lambda x: x[1]))
```

### 斐波那契数列（递归和迭代）

```python
# 递归（带缓存）
from functools import lru_cache

@lru_cache(maxsize=None)
def fib_recursive(n):
    if n < 2:
        return n
    return fib_recursive(n-1) + fib_recursive(n-2)

# 迭代
def fib_iterative(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a
```

### 二分查找

```python
def binary_search(arr, target):
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
```
