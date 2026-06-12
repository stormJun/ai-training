<!-- Converted from p20-mcp.ipynb -->

```python
# 基于 Function Calling 的实现

LOGISTICS_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_logistics_companies",
            "description": "查询支持的物流公司信息"
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_shipping_fee",
            "description": "计算运费",
            "parameters": {
                "type": "object",
                "properties": {
                    "weight": {"type": "number", "description": "重量(kg)"},
                    "distance": {"type": "number", "description": "距离(km)"},
                    "company": {"type": "string", "description": "物流公司"}
                },
                "required": ["weight", "distance", "company"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "estimate_delivery_time",
            "description": "估算配送时效",
            "parameters": {
                "type": "object",
                "properties": {
                    "from_city": {"type": "string", "description": "起始城市"},
                    "to_city": {"type": "string", "description": "目的城市"},
                    "company": {"type": "string", "description": "物流公司"}
                },
                "required": ["from_city", "to_city", "company"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "track_shipment",
            "description": "查询物流状态",
            "parameters": {
                "type": "object",
                "properties": {
                    "tracking_number": {"type": "string", "description": "运单号"}
                },
                "required": ["tracking_number"]
            }
        }
    }
]


def query_logistics_companies():
    return "支持的物流公司: 顺丰, 圆通, 中通, 韵达, 京东物流, 德邦"

def calculate_shipping_fee(weight, distance, company):
    # 物流公司基础运费表
    base_fees = {
        "顺丰": 15, "圆通": 8, "中通": 8,
        "韵达": 7, "京东物流": 12, "德邦": 10
    }
    base_fee = base_fees.get(company, 10)
    weight_fee = weight * 1.5
    distance_fee = distance * 0.3
    total = base_fee + weight_fee + distance_fee
    return f"{company}快递: 重量{weight}kg, 距离{distance}km, 预估运费{total:.2f}元"

def estimate_delivery_time(from_city, to_city, company):
    # 简单的时效估算逻辑
    if from_city == to_city:
        return "同城配送，预计1天内送达"
    else:
        return "跨城配送，预计1-3天送达"

def track_shipment(tracking_number):
    # 模拟物流状态查询
    statuses = [
        "已揽收", "运输中", "到达目的地分拨中心", "派送中", "已签收"
    ]
    import random
    status = random.choice(statuses)
    return f"运单号 {tracking_number} 当前状态: {status}"


# Step 2: 调用模型获取调用意图（物流场景示例）
messages = [{"role": "user", "content": "从北京寄5kg包裹到上海，用顺丰快递要多少钱？"}]
llm_output = call_llm(messages, tools=LOGISTICS_TOOLS)

# Step 3: 解析并本地执行函数调用
if llm_output.get("tool_calls"):
    tool_call = llm_output["tool_calls"][0]
    function_name = tool_call["function"]["name"]
    args = json.loads(tool_call["function"]["arguments"])

    if function_name == "calculate_shipping_fee":
        result = calculate_shipping_fee(args["weight"], args["distance"], args["company"])
    elif function_name == "estimate_delivery_time":
        result = estimate_delivery_time(args["from_city"], args["to_city"], args["company"])
    elif function_name == "query_logistics_companies":
        result = query_logistics_companies()
    elif function_name == "track_shipment":
        result = track_shipment(args["tracking_number"])

# Step 4: 将结果回传给模型生成最终回复
messages.append({
    "role": "tool",
    "content": result,
    "tool_call_id": tool_call["id"]
})
final_response = call_llm(messages)



# 查询物流公司
messages = [{"role": "user", "content": "有哪些物流公司可以选择？"}]

# 查询配送时效
messages = [{"role": "user", "content": "从深圳到广州要几天能到？"}]

# 查询物流状态
messages = [{"role": "user", "content": "帮我查一下运单号SF1234567890的状态"}]
```

```python
# 基于 MCP 的实现

# Step 0: 初始化 MCP 客户端，动态发现物流工具
client = Client()
await client.connect("mcp://logistics-service.com")
tools = await client.list_tools()  # 自动获取远程物流工具清单



# 完整的 MCP 调用
# 构建MCP工具提示
def build_mcp_tool_prompt(tools):
    tool_descs = "\n".join(f"<tool>{t['name']}</tool>: {t['description']}" for t in tools)
    return f"""
你是一个物流智能助手，可以使用以下工具解决物流相关问题。
可用工具列表：
{tool_descs}

请按如下 XML 格式调用工具：
<tool_use>
  <name>工具名称</name>
  <arguments>{{"参数1": "值1", "参数2": "值2"}}</arguments>
</tool_use>

示例：
<tool_use>
  <name>calculate_shipping_fee</name>
  <arguments>{{"weight": 5, "distance": 1200, "company": "顺丰"}}</arguments>
</tool_use>
"""

# Step 1: 构造 Prompt 并调用模型识别意图
system_prompt = build_mcp_tool_prompt(tools)
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": "从北京寄5kg包裹到上海，用顺丰快递要多少钱？"}
]
assistant_response = await call_llm(messages)

# Step 2: 解析模型输出并远程调用工具
tool_use = parse_tool_use(assistant_response)
if tool_use:
    result = await client.call_tool(
        name=tool_use["name"],
        arguments=tool_use["arguments"]
    )

# Step 3: 返回结果供模型生成最终响应
messages.append({
    "role": "tool",
    "content": result,
    "tool_call_id": tool_use.get("id")
})
final_response = await call_llm(messages)


# 工具解析函数
def parse_tool_use(response):
    import re
    import json

    match = re.search(
        r"<tool_use>\s*<name>(.*?)</name>\s*<arguments>(.*?)</arguments>\s*</tool_use>",
        response,
        re.DOTALL
    )
    if match:
        name, args_str = match.groups()
        try:
            arguments = json.loads(args_str.strip())
            return {"name": name.strip(), "arguments": arguments}
        except json.JSONDecodeError:
            return None
    return None



```
