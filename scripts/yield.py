def couner():
    print("第一次 yield 之前")
    yield 1
    print("第二次 yield 之前")
    yield 2
    print("第三次 yield 之前")
    yield 3


gen = couner()
# print("函数调用完了，但是函数体一行都没跑")

# print(gen)  # <generator object counter at ...>
# print(next(gen))  # 跑到第一个 yield，交出 1，暂停
# print(next(gen))  # 从暂停处醒来，跑到第二个 yield
# print(next(gen))  # 第三个
# print(next(gen))    # ????


def make_list():
    result: list[int] = []
    for i in range(3):
        result.append(i)
    return result


# def make_gen():
#     for i in range(3):
#         yield i


# print(list(make_gen()))


# def echo():
#     while True:
#         received = yield  # 暂停在这里，等外面 send 东西进来
#         print("收到:", received)


# g = echo()
# next(g)  # 先启动，跑到第一个 yield 暂停
# g.send("你好")
# g.send("世界")
