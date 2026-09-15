d = {"a": 1, "b": 2}

def show(a: int, b: int) -> None:
    print(a, b)

show(**d)   # ✅ 1 2  — key 和参数名完全匹配
print(*d)   # ✅ a b  — 单星号按位置展开,print 接受任意位置参数
