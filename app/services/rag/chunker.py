"""文本切块(行业 baseline):句子级切分 + 贪心聚合 + 尾部重叠。

参数取行业惯用区间:块 ~300 字,重叠 ~50 字(约 15%)。
原则:单块语义自足——embedding 后既能被"它讲什么"命中,
又不因切缝丢失指代(重叠就是防这个)。
"""

import re

CHUNK_SIZE = 300
CHUNK_OVERLAP = 50

# 非终止字符序列 + 可选终止符:中英句子连标点完整保留
_SENTENCE_RE = re.compile(r"[^。！？!?；;\n]+[。！？!?；;\n]*")


def _split_sentences(text: str):
    """切成最小语义单元:句子。丢纯空白,保留标点。"""
    return [seg for seg in (s.strip() for s in _SENTENCE_RE.findall(text)) if seg]


def split_text(text: str):
    """切块，贪心算法"""
    sentences = _split_sentences(text)
    chunks: list[str] = []
    buf: list[str] = []
    buf_len = 0

    for s in sentences:
        if buf and buf_len + len(s) > CHUNK_SIZE:
            chunks.append("".join(buf))
            tail: list[str] = []
            tail_len = 0
            while buf and tail_len + len(buf[-1]) <= CHUNK_OVERLAP:
                tail.insert(0, buf.pop())
                tail_len += len(tail[0])
            buf, buf_len = tail, tail_len
        buf.append(s)
        buf_len += len(s)
    if buf:
        chunks.append("".join(buf))
    return chunks
