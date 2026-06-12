<!-- Converted from p35-ReACT.ipynb -->

```python
from langchain_community.llms import OpenAI
from langchain.agents import AgentExecutor, create_react_agent

from langchain_core.prompts import PromptTemplate

template = '''Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}'''

prompt = PromptTemplate.from_template(template)

model = OpenAI()
tools = ...

agent = create_react_agent(model, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools)

agent_executor.invoke({"input": "hi"})

# Use with chat history
from langchain_core.messages import AIMessage, HumanMessage
agent_executor.invoke(
    {
        "input": "what's my name?",
        # Notice that chat_history is a string
        # since this prompt is aimed at LLMs, not chat models
        "chat_history": "Human: My name is Bob\nAI: Hello Bob!",
    }
)
```

```python
from langchain_community.llms import Tongyi
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import Tool

# 物流场景的 Mock 工具

def track_package(tracking_number):
    """包裹追踪工具"""
    tracking_number = str(tracking_number).strip()

    package_status = {
        "SF123456": {
            "status": "运输中",
            "location": "北京分拣中心",
            "estimated_delivery": "2024-01-15"
        },
        "YT789012": {
            "status": "已签收",
            "location": "上海浦东",
            "delivery_date": "2024-01-10"
        }
    }

    if tracking_number in package_status:
        info = package_status[tracking_number]
        if 'estimated_delivery' in info:
            return f"快递单号: {tracking_number}, 状态: {info['status']}, 位置: {info['location']}, 预计送达: {info['estimated_delivery']}"
        else:
            return f"快递单号: {tracking_number}, 状态: {info['status']}, 位置: {info['location']}, 送达日期: {info['delivery_date']}"
    else:
        return f"未找到快递单号 {tracking_number} 的信息"

def calculate_shipping_cost(params):
    """运费计算工具"""
    try:
        if ',' in params:
            parts = params.split(',')
            origin = parts[0].strip()
            destination = parts[1].strip()
            weight = float(parts[2].strip())
        else:
            return "请输入正确格式: 起始城市,目的城市,重量"

        base_cost = 10
        weight_cost = max(0, (weight - 1)) * 2
        total_cost = base_cost + weight_cost

        return f"运费计算结果: 从{origin}到{destination}，重量{weight}kg，运费: {total_cost}元"
    except Exception as e:
        return f"计算错误，请输入正确格式: 起始城市,目的城市,重量。错误: {str(e)}"

def check_inventory(product_code):
    """库存查询工具"""
    product_code = str(product_code).strip()

    inventory = {
        "A001": {"name": "iPhone 15", "stock": 150, "warehouse": "上海仓"},
        "B002": {"name": "MacBook Pro", "stock": 45, "warehouse": "深圳仓"},
        "C003": {"name": "iPad Air", "stock": 0, "warehouse": "北京仓"}
    }

    if product_code in inventory:
        item = inventory[product_code]
        status = "有货" if item['stock'] > 0 else "缺货"
        return f"商品代码: {product_code}, 名称: {item['name']}, 库存: {item['stock']}件, 仓库: {item['warehouse']}, 状态: {status}"
    else:
        return f"未找到商品代码 {product_code} 的信息"

# 创建工具
tools = [
    Tool(
        name="TrackPackage",
        description="追踪包裹状态，输入快递单号",
        func=track_package
    ),
    Tool(
        name="CalculateShipping",
        description="计算运费，输入格式：起始城市,目的城市,重量(如：北京,上海,2)",
        func=calculate_shipping_cost
    ),
    Tool(
        name="CheckInventory",
        description="查询库存，输入商品代码",
        func=check_inventory
    )
]

# 简化的 ReACT 提示模板
template = '''Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}'''

prompt = PromptTemplate.from_template(template)

# 初始化通义千问模型
try:
    model = Tongyi(temperature=0)
    agent = create_react_agent(model, tools, prompt)
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=3,
        return_intermediate_steps=True
    )

    # 测试案例
    if __name__ == "__main__":
        print("=== 物流 ReACT Agent===\n")

        test_cases = [
            "查询快递单号 SF123456",
            "从北京到上海寄2公斤包裹多少钱",
            "查询商品A001的库存"
        ]

        for i, question in enumerate(test_cases, 1):
            print(f"--- 测试案例 {i} ---")
            print(f"问题: {question}")
            print("-" * 50)

            try:
                result = agent_executor.invoke({"input": question})
                print(f"\n最终答案: {result.get('output', '无结果')}")

                # 显示中间步骤
                if 'intermediate_steps' in result:
                    print(f"执行步骤数: {len(result['intermediate_steps'])}")

            except Exception as e:
                print(f"Agent执行错误: {e}")

                # 提供备选答案，确保用户能看到正确结果
                print("\n使用直接工具调用作为备选:")
                if i == 1:  # 查询快递单号
                    backup_result = track_package("SF123456")
                    print(f"备选答案: {backup_result}")
                elif i == 2:  # 计算运费
                    backup_result = calculate_shipping_cost("北京,上海,2")
                    print(f"备选答案: {backup_result}")
                elif i == 3:  # 查询库存
                    backup_result = check_inventory("A001")
                    print(f"备选答案: {backup_result}")

            print("\n" + "="*60 + "\n")


except Exception as e:
    print(f"初始化错误: {e}")
    print("请确保已设置 DASHSCOPE_API_KEY 环境变量")

```

输出：

```text
=== 物流 ReACT Agent===

--- 测试案例 1 ---
问题: 查询快递单号 SF123456
--------------------------------------------------


[1m> Entering new AgentExecutor chain...[0m
[32;1m[1;3m需要使用TrackPackage工具查询快递单号状态
Action: TrackPackage
Action Input: SF123456[0m[36;1m[1;3m快递单号: SF123456, 状态: 运输中, 位置: 北京分拣中心, 预计送达: 2024-01-15[0m[32;1m[1;3mFinal Answer: 快递单号 SF123456 的状态为运输中，当前位置在北京分拣中心，预计送达时间为 2024-01-15。[0m

[1m> Finished chain.[0m

最终答案: 快递单号 SF123456 的状态为运输中，当前位置在北京分拣中心，预计送达时间为 2024-01-15。
执行步骤数: 1

============================================================

--- 测试案例 2 ---
问题: 从北京到上海寄2公斤包裹多少钱
--------------------------------------------------


[1m> Entering new AgentExecutor chain...[0m
[32;1m[1;3m需要计算运费
Action: CalculateShipping
Action Input: 北京,上海,2[0m[33;1m[1;3m运费计算结果: 从北京到上海，重量2.0kg，运费: 12.0元[0m[32;1m[1;3mFinal Answer: 从北京到上海寄2公斤包裹的运费是12元。[0m

[1m> Finished chain.[0m

最终答案: 从北京到上海寄2公斤包裹的运费是12元。
执行步骤数: 1

============================================================

--- 测试案例 3 ---
问题: 查询商品A001的库存
--------------------------------------------------


[1m> Entering new AgentExecutor chain...[0m
[32;1m[1;3m需要查询商品A001的库存，应该使用CheckInventory工具。
Action: CheckInventory
Action Input: A001[0m[38;5;200m[1;3m商品代码: A001, 名称: iPhone 15, 库存: 150件, 仓库: 上海仓, 状态: 有货[0m[32;1m[1;3mFinal Answer: 商品代码为A001的iPhone 15在上海仓有150件库存，状态为有货。[0m

[1m> Finished chain.[0m

最终答案: 商品代码为A001的iPhone 15在上海仓有150件库存，状态为有货。
执行步骤数: 1

============================================================

```

## FSM 状态机

```python
from langchain_community.llms import Tongyi
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from enum import Enum
from typing import Dict, Any, Optional
import json

# 定义订单处理状态
class OrderState(Enum):
    START = "开始"
    ORDER_VALIDATED = "订单已验证"
    PAYMENT_CHECKED = "付款状态已检查"
    PAYMENT_PROCESSED = "付款已处理"
    INVOICE_GENERATED = "发票已开具"
    END = "结束"
    ERROR = "错误"

# 状态机图定义（类似LangGraph的节点和边）
class OrderProcessGraph:
    def __init__(self):
        self.current_state = OrderState.START
        self.context = {}
        self.history = []

        # Mock数据
        self.orders = {
            "ORD001": {
                "customer": "张三",
                "product": "iPhone 15",
                "amount": 7999,
                "date": "2024-01-10",
                "payment_status": "未付款"
            },
            "ORD002": {
                "customer": "李四",
                "product": "MacBook Pro",
                "amount": 15999,
                "date": "2024-01-08",
                "payment_status": "未付款"
            },
            "ORD003": {
                "customer": "王五",
                "product": "iPad Air",
                "amount": 4999,
                "date": "2024-01-12",
                "payment_status": "已付款"
            }
        }

        # 初始化LLM
        self.llm = None
        try:
            self.llm = Tongyi(temperature=0)
            print("LangChain LLM 初始化成功")
        except Exception as e:
            print(f"LLM初始化失败，使用默认消息: {e}")

    def add_to_history(self, from_state: OrderState, to_state: OrderState, action: str, result: str):
        """添加历史记录"""
        self.history.append({
            'from': from_state.value,
            'to': to_state.value,
            'action': action,
            'result': result
        })

    def generate_message_with_llm(self, template_str: str, variables: Dict) -> str:
        """使用LangChain LLM生成消息"""
        if not self.llm:
            # 回退到默认消息
            return template_str.format(**variables)

        try:
            prompt = PromptTemplate.from_template(template_str + " 请生成一个专业简洁的确认消息。")
            chain = prompt | self.llm | StrOutputParser()
            return chain.invoke(variables)
        except Exception as e:
            print(f"LLM调用失败，使用默认消息: {e}")
            return template_str.format(**variables)

    # 节点函数（类似LangGraph的节点）
    def validate_order_node(self, order_number: str) -> Dict[str, Any]:
        """验证订单节点"""
        print(f"  执行节点: validate_order_node")
        print(f"  当前状态: {self.current_state.value}")

        if self.current_state != OrderState.START:
            message = f"错误：当前状态为 {self.current_state.value}，无法验证订单"
            return {
                'success': False,
                'message': message,
                'next_state': OrderState.ERROR
            }

        if order_number in self.orders:
            order_info = self.orders[order_number]
            self.context.update({
                'order_number': order_number,
                'order_info': order_info
            })

            # 使用LangChain生成消息
            template = "订单验证成功！订单号: {order_number}, 客户: {customer}, 商品: {product}, 金额: {amount}元"
            message = self.generate_message_with_llm(template, {
                'order_number': order_number,
                'customer': order_info['customer'],
                'product': order_info['product'],
                'amount': order_info['amount']
            })

            self.add_to_history(self.current_state, OrderState.ORDER_VALIDATED, "验证订单", message)
            self.current_state = OrderState.ORDER_VALIDATED

            return {
                'success': True,
                'message': message,
                'next_state': OrderState.ORDER_VALIDATED
            }
        else:
            message = f"订单号 {order_number} 不存在"
            self.add_to_history(self.current_state, OrderState.ERROR, "验证订单", message)
            self.current_state = OrderState.ERROR
            return {
                'success': False,
                'message': message,
                'next_state': OrderState.ERROR
            }

    def check_payment_node(self) -> Dict[str, Any]:
        """检查付款状态节点"""
        print(f"  执行节点: check_payment_node")
        print(f"  当前状态: {self.current_state.value}")

        if self.current_state != OrderState.ORDER_VALIDATED:
            message = f"错误：当前状态为 {self.current_state.value}，无法检查付款状态"
            return {
                'success': False,
                'message': message,
                'next_state': OrderState.ERROR
            }

        order_info = self.context.get('order_info', {})
        payment_status = order_info.get('payment_status', '未付款')

        if payment_status == '已付款':
            template = "付款状态检查完成：订单已付款，可以直接开具发票"
            message = self.generate_message_with_llm(template, {})
            self.context['payment_confirmed'] = True
            next_state = OrderState.PAYMENT_PROCESSED
        else:
            template = "付款状态检查完成：订单未付款，需要先处理付款"
            message = self.generate_message_with_llm(template, {})
            self.context['payment_confirmed'] = False
            next_state = OrderState.PAYMENT_CHECKED

        self.add_to_history(self.current_state, next_state, "检查付款状态", message)
        self.current_state = next_state

        return {
            'success': True,
            'message': message,
            'next_state': next_state,
            'payment_status': payment_status
        }

    def process_payment_node(self, payment_method: str = "支付宝") -> Dict[str, Any]:
        """处理付款节点"""
        print(f"  执行节点: process_payment_node")
        print(f"  当前状态: {self.current_state.value}")

        if self.current_state != OrderState.PAYMENT_CHECKED:
            message = f"错误：当前状态为 {self.current_state.value}，无法处理付款"
            return {
                'success': False,
                'message': message,
                'next_state': OrderState.ERROR
            }

        order_info = self.context.get('order_info', {})
        amount = order_info.get('amount', 0)
        order_number = self.context.get('order_number', '000')

        # 使用LangChain生成付款确认消息
        template = "付款处理完成！付款金额: {amount}元，付款方式: {payment_method}，交易号: TXN{order_number}-2024"
        message = self.generate_message_with_llm(template, {
            'amount': amount,
            'payment_method': payment_method,
            'order_number': order_number
        })

        self.context.update({
            'payment_amount': amount,
            'payment_method': payment_method,
            'transaction_id': f"TXN{order_number}-2024",
            'payment_confirmed': True
        })

        self.add_to_history(self.current_state, OrderState.PAYMENT_PROCESSED, "处理付款", message)
        self.current_state = OrderState.PAYMENT_PROCESSED

        return {
            'success': True,
            'message': message,
            'next_state': OrderState.PAYMENT_PROCESSED
        }

    def generate_invoice_node(self, invoice_type: str = "电子发票") -> Dict[str, Any]:
        """开具发票节点"""
        print(f"  执行节点: generate_invoice_node")
        print(f"  当前状态: {self.current_state.value}")

        if self.current_state != OrderState.PAYMENT_PROCESSED:
            message = f"错误：当前状态为 {self.current_state.value}，无法开具发票。必须先完成付款处理"
            return {
                'success': False,
                'message': message,
                'next_state': OrderState.ERROR
            }

        order_info = self.context.get('order_info', {})
        amount = order_info.get('amount', 0)
        order_number = self.context.get('order_number', '000')
        invoice_number = f"INV{order_number}-2024"

        # 使用LangChain生成发票确认消息
        template = "发票开具完成！发票号: {invoice_number}，金额: {amount}元，类型: {invoice_type}"
        message = self.generate_message_with_llm(template, {
            'invoice_number': invoice_number,
            'amount': amount,
            'invoice_type': invoice_type
        })

        self.context.update({
            'invoice_number': invoice_number,
            'invoice_amount': amount,
            'invoice_type': invoice_type,
            'invoice_status': '已开具'
        })

        self.add_to_history(self.current_state, OrderState.INVOICE_GENERATED, "开具发票", message)
        self.current_state = OrderState.INVOICE_GENERATED

        return {
            'success': True,
            'message': message,
            'next_state': OrderState.INVOICE_GENERATED
        }

    def end_node(self) -> Dict[str, Any]:
        """结束节点"""
        print(f"  执行节点: end_node")
        print(f"  当前状态: {self.current_state.value}")

        if self.current_state != OrderState.INVOICE_GENERATED:
            message = f"错误：当前状态为 {self.current_state.value}，流程未完成"
            return {
                'success': False,
                'message': message,
                'next_state': OrderState.ERROR
            }

        # 使用LangChain生成结束消息
        template = "订单处理流程已完成，所有步骤执行成功"
        message = self.generate_message_with_llm(template, {})

        self.add_to_history(self.current_state, OrderState.END, "结束流程", message)
        self.current_state = OrderState.END

        return {
            'success': True,
            'message': message,
            'next_state': OrderState.END
        }

    # 边函数（类似LangGraph的条件边）
    def should_process_payment(self) -> bool:
        """判断是否需要处理付款"""
        return not self.context.get('payment_confirmed', False)

    def get_status(self) -> str:
        """获取当前状态"""
        result = f"""
当前状态: {self.current_state.value}
流程上下文: {json.dumps(self.context, ensure_ascii=False, indent=2)}
"""

        if self.history:
            result += f"\n状态转换历史:\n"
            for i, step in enumerate(self.history, 1):
                result += f"  {i}. {step['from']} → {step['to']} ({step['action']})\n"

        return result

    def reset(self):
        """重置状态机"""
        self.current_state = OrderState.START
        self.context = {}
        self.history = []

# 订单处理执行器（类似LangGraph的执行器）
class OrderProcessExecutor:
    def __init__(self):
        self.graph = OrderProcessGraph()

    def execute_workflow(self, order_number: str, payment_method: str = "支付宝", invoice_type: str = "电子发票"):
        """执行完整的工作流程"""
        print(f"=== 开始处理订单 {order_number} ===\n")

        # 步骤1: 验证订单
        print("步骤1: 验证订单")
        result1 = self.graph.validate_order_node(order_number)
        print(f"结果: {result1['message']}")
        print(f"状态转换: {self.graph.current_state.value}\n")

        if not result1['success']:
            return result1

        # 步骤2: 检查付款状态
        print("步骤2: 检查付款状态")
        result2 = self.graph.check_payment_node()
        print(f"结果: {result2['message']}")
        print(f"状态转换: {self.graph.current_state.value}\n")

        if not result2['success']:
            return result2

        # 条件分支：如果未付款，则处理付款
        if self.graph.should_process_payment():
            print("步骤3: 处理付款")
            result3 = self.graph.process_payment_node(payment_method)
            print(f"结果: {result3['message']}")
            print(f"状态转换: {self.graph.current_state.value}\n")

            if not result3['success']:
                return result3
        else:
            print("步骤3: 跳过付款处理（订单已付款）")
            print(f"当前状态保持: {self.graph.current_state.value}\n")

        # 步骤4: 开具发票
        print("步骤4: 开具发票")
        result4 = self.graph.generate_invoice_node(invoice_type)
        print(f"结果: {result4['message']}")
        print(f"状态转换: {self.graph.current_state.value}\n")

        if not result4['success']:
            return result4

        # 步骤5: 结束流程
        print("步骤5: 结束流程")
        result5 = self.graph.end_node()
        print(f"结果: {result5['message']}")
        print(f"状态转换: {self.graph.current_state.value}\n")

        return result5

    def get_status(self):
        """获取状态"""
        return self.graph.get_status()

    def reset(self):
        """重置"""
        self.graph.reset()

def demo_fsm_langchain_complete():
    """演示完整的LangChain集成FSM实现"""
    print("=== 基于状态机的订单处理系统（LangChain完整版） ===\n")

    executor = OrderProcessExecutor()

    # 演示1: 未付款订单的完整流程
    print("--- 演示1: 未付款订单的完整流程 ---")
    result1 = executor.execute_workflow("ORD001", "微信支付", "增值税专用发票")

    print("--- 最终状态 ---")
    print(executor.get_status())
    print("="*80 + "\n")

    # 演示2: 已付款订单的流程
    print("--- 演示2: 已付款订单的流程 ---")
    executor.reset()
    result2 = executor.execute_workflow("ORD003", "支付宝", "电子普通发票")

    print("--- 最终状态 ---")
    print(executor.get_status())
    print("="*80 + "\n")

if __name__ == "__main__":
    demo_fsm_langchain_complete()
```

输出：

```text
=== 基于状态机的订单处理系统（LangChain完整版） ===

LangChain LLM 初始化成功
--- 演示1: 未付款订单的完整流程 ---
=== 开始处理订单 ORD001 ===

步骤1: 验证订单
  执行节点: validate_order_node
  当前状态: 开始
结果: 订单验证成功！
**订单号：** ORD001
**客户：** 张三
**商品：** iPhone 15
**金额：** 7999元

感谢您的确认，我们将尽快为您安排发货。如有任何疑问，请随时联系客服。
状态转换: 订单已验证

步骤2: 检查付款状态
  执行节点: check_payment_node
  当前状态: 订单已验证
结果: 订单尚未完成付款，请先完成支付以继续后续处理。感谢您的配合！
状态转换: 付款状态已检查

步骤3: 处理付款
  执行节点: process_payment_node
  当前状态: 付款状态已检查
结果: 付款处理完成。金额：7999元，方式：微信支付，交易号：TXNORD001-2024。感谢您的支付！
状态转换: 付款已处理

步骤4: 开具发票
  执行节点: generate_invoice_node
  当前状态: 付款已处理
结果: 发票开具完成确认：

发票号：INVORD001-2024
金额：7999元
类型：增值税专用发票

感谢您的确认！如有任何问题，请随时联系。
状态转换: 发票已开具

步骤5: 结束流程
  执行节点: end_node
  当前状态: 发票已开具
结果: 订单处理流程已顺利完成，所有步骤均成功执行。感谢您的配合！
状态转换: 结束

--- 最终状态 ---

当前状态: 结束
流程上下文: {
  "order_number": "ORD001",
  "order_info": {
    "customer": "张三",
    "product": "iPhone 15",
    "amount": 7999,
    "date": "2024-01-10",
    "payment_status": "未付款"
  },
  "payment_confirmed": true,
  "payment_amount": 7999,
  "payment_method": "微信支付",
  "transaction_id": "TXNORD001-2024",
  "invoice_number": "INVORD001-2024",
  "invoice_amount": 7999,
  "invoice_type": "增值税专用发票",
  "invoice_status": "已开具"
}

状态转换历史:
  1. 开始 → 订单已验证 (验证订单)
  2. 订单已验证 → 付款状态已检查 (检查付款状态)
  3. 付款状态已检查 → 付款已处理 (处理付款)
  4. 付款已处理 → 发票已开具 (开具发票)
  5. 发票已开具 → 结束 (结束流程)

================================================================================

--- 演示2: 已付款订单的流程 ---
=== 开始处理订单 ORD003 ===

步骤1: 验证订单
  执行节点: validate_order_node
  当前状态: 开始
结果: 订单验证成功！
**订单号：** ORD003
**客户：** 王五
**商品：** iPad Air
**金额：** 4999元

感谢您的确认！如有任何问题，请随时联系我们。
状态转换: 订单已验证

步骤2: 检查付款状态
  执行节点: check_payment_node
  当前状态: 订单已验证
结果: 确认消息如下：

**订单付款已确认，可直接开具发票。**

如需进一步操作或提供发票信息，请随时告知。
状态转换: 付款已处理

步骤3: 跳过付款处理（订单已付款）
当前状态保持: 付款已处理

步骤4: 开具发票
  执行节点: generate_invoice_node
  当前状态: 付款已处理
结果: 发票开具完成确认：

发票号：INVORD003-2024
金 额：4999元
类 型：电子普通发票

感谢您的确认！如需进一步协助，请随时联系。
状态转换: 发票已开具

步骤5: 结束流程
  执行节点: end_node
  当前状态: 发票已开具
结果: 订单处理流程已顺利完成，所有步骤已成功执行。感谢您的配合！
状态转换: 结束

--- 最终状态 ---

当前状态: 结束
流程上下文: {
  "order_number": "ORD003",
  "order_info": {
    "customer": "王五",
    "product": "iPad Air",
    "amount": 4999,
    "date": "2024-01-12",
    "payment_status": "已付款"
  },
  "payment_confirmed": true,
  "invoice_number": "INVORD003-2024",
  "invoice_amount": 4999,
  "invoice_type": "电子普通发票",
  "invoice_status": "已开具"
}

状态转换历史:
  1. 开始 → 订单已验证 (验证订单)
  2. 订单已验证 → 付款已处理 (检查付款状态)
  3. 付款已处理 → 发票已开具 (开具发票)
  4. 发票已开具 → 结束 (结束流程)

================================================================================

```
