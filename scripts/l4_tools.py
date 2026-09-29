import asyncio
import json
from typing import cast

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolParam

from app.config.config import settings

client = AsyncOpenAI(api_key=settings.ark_api_key, base_url=settings.ark_base_url)
"""
tools 是 JSON Schema，写给模型看的「简历」。 
三要素缺一不可：name（模型喊的名字）、description（模型决策的唯一依据——它不看你的代码，只看这段中文描述来决定「该不该用这个工具」。
写得含糊，模型就乱调用或不调用）、parameters（JSON Schema 描述参数的形状）。
属性里的  同样重要——告诉模型「city 该填什么description格式」。
"""
tools: list[ChatCompletionToolParam] = [
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "获取指定城市当前的实时天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名,如:北京"},
                },
                "required": ["city"],
            },
        },
    }
]


def get_current_weather(city: str):
    print("我被调用了！！！")
    return json.dumps({"city": city, "weather": "晴", "temperature": 0}, ensure_ascii=False)


async def main():
    messages: list[ChatCompletionMessageParam] = [{"role": "user", "content": "北京今天天气怎么样?适合跑步吗?"}]

    # 第一轮：模型决定“调研申请”
    first = await client.chat.completions.create(model=settings.ark_model, messages=messages, tools=tools)

    assistant_msg = first.choices[0].message
    """
    finish_reason 是这堂课的钥匙。 
    L1 以来它一直是 stop（正常说完）；当模型决定用工具，它变成 tool_calls。
    你的代码以后就靠判断它来分支。另外记住 length（被 max_tokens 截断），三个值以后都会遇到。
    """
    print("第一轮 finish_reason:", first.choices[0].finish_reason)
    print("第一轮 tool_calls:", assistant_msg.tool_calls)

    # 收窄 1:模型可以不调用工具(tool_calls 是 Optional)
    if first.choices[0].finish_reason != "tool_calls" or assistant_msg.tool_calls is None:
        print("模型没调用工具，直接回答：", assistant_msg.content)
        return

    messages.append(cast(ChatCompletionMessageParam, assistant_msg))

    tool_call = assistant_msg.tool_calls[0]

    # 收窄 2:tool_calls 元素是联合类型(function | custom),用判别字段分派
    if tool_call.type != "function":
        raise RuntimeError("本课只支持 function 工具,收到了 custom 工具调用")
    """
    tool_call.function.arguments 是 JSON 字符串，不是对象。 
    这是新手第二大坑（第一大是以为模型会执行函数）。
    模型输出的一切都是文本，参数必须 json.loads 自己解。
    也意味着解析可能失败——模型偶尔会生成不合法 JSON，健壮代码要兜底（L5 再处理）。
    """
    args = json.loads(tool_call.function.arguments)
    result = get_current_weather(args["city"])

    """
    messages.append(assistant_msg) 这行最反直觉，也最关键。 
    把模型那条「带着 tool_calls 的 assistant 消息」原样追加回历史。
    回忆 L1 灵魂知识点：多轮 = 重发全部历史——tool_calls 消息也是历史的一部分，不回填，
    第二轮模型就不知道「刚才我要调工具」这件事了。
    这行的角色是 assistant，即使 content 是 None（它这次没说话，只递了申请单）
    """
    messages.append(
        {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": result,
        }
    )
    """
    tool_call_id 必须精确回填。 
    role="tool" 的消息靠这个 id 和某次调用对账。
    现在只有一个工具感知不强，
    L4 后半会多工具并行调用——三个 tool_calls 对应三条 tool 消息，id 错一条模型就张冠李戴。
    """

    """
    两轮两次 API 调用。 
    第一轮出申请单、第二轮给答案，中间夹着你的真实执行。
    Agent 的所有「智能感」都来自这个朴素循环的重复。
    """
    # 第二轮：模型消化结果，说人话
    second = await client.chat.completions.create(model=settings.ark_model, messages=messages)
    print("第二轮 finish_reason:", second.choices[0].finish_reason)
    print("最终回答:", second.choices[0].message.content)


if __name__ == "__main__":
    asyncio.run(main())
