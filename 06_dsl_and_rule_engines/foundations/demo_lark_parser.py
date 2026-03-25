#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DSL解析演示程序
展示Lark如何将DSL代码解析为抽象语法树，再转换为Python数据结构

运行要求：
    pip install lark-parser

运行方式：
    python demo_lark_parser.py
"""

from lark import Lark, Transformer, Tree
import json
from typing import Dict, Any

# ==================== Lark语法定义 ====================
# 直接在代码中定义语法（实际项目中通常放在.lark文件中）
COFFEE_GRAMMAR = r"""
start: workflow

workflow: "WORKFLOW" STRING "VERSION" NUMBER (node | edge)+

node: "NODE" ID "TYPE" NODE_TYPE node_data*
NODE_TYPE: "initial" | "action" | "condition"

node_data: "DO" action
         | "WHEN" condition
         | "DESCRIPTION" STRING

edge: "EDGE" ID "->" ID (edge_condition)?
edge_condition: "CONDITION" condition

condition: SENSOR_PATH COMP NUMBER UNIT?
COMP: ">=" | "<"

action: wait_action | start_action | stop_action | turn_on_action | turn_off_action | send_action | alert_action | parameter_action

wait_action: "WAIT" NUMBER UNIT
start_action: "START" ID
stop_action: "STOP" ID
turn_on_action: "TURN_ON" ID
turn_off_action: "TURN_OFF" ID
send_action: "SEND" STRING "TO" ID
alert_action: "ALERT" STRING
parameter_action: "SET" ID "=" (NUMBER_WITH_UNIT | NUMBER UNIT? | STRING)

SENSOR_PATH: /[a-z]+(\.[a-z_]+)+/
TEMP_VALUE: /\d+(\.\d+)?°C/
VOLUME_VALUE: /\d+(\.\d+)?ml/
TIME_VALUE: /\d+(\.\d+)?s/
NUMBER_WITH_UNIT: TEMP_VALUE | VOLUME_VALUE | TIME_VALUE
UNIT: "°C" | "ml" | "s"
NUMBER: /-?\d+(\.\d+)?/

ID: /[a-zA-Z_][a-zA-Z0-9_]*/
STRING: /"[^"]*"/

COMMENT: /#[^\n]*/

%ignore " "
%ignore "\t"
%ignore /\r?\n/
%ignore COMMENT
"""

# ==================== DSL示例代码 ====================
SAMPLE_DSL = """
WORKFLOW "简化咖啡制作" VERSION 1.0

NODE start TYPE initial
  DESCRIPTION "系统启动"

NODE check_water TYPE condition
  WHEN water.level >= 300ml
  DESCRIPTION "检查水位"

NODE heat_water TYPE action
  DO TURN_ON heater
  DO SET target_temp = 93°C
  DESCRIPTION "加热水"

NODE make_coffee TYPE action
  DO START brewing
  DO WAIT 20s
  DO STOP brewing
  DESCRIPTION "制作咖啡"

EDGE start -> check_water
EDGE check_water -> heat_water
EDGE heat_water -> make_coffee
"""

# ==================== Transformer转换器 ====================
class CoffeeTransformer(Transformer):
    """将抽象语法树转换为Python字典"""

    def workflow(self, items):
        return {
            "workflow_name": items[0].strip('"'),
            "version": float(items[1]),
            "body": items[2:]
        }

    def node(self, items):
        return {
            "type": "node",
            "node_name": str(items[0]),
            "node_type": str(items[1]),
            "node_data": items[2:]
        }

    def edge(self, items):
        return {
            "type": "edge",
            "source": str(items[0]),
            "target": str(items[1]),
            "condition": items[2] if len(items) > 2 else None
        }

    def condition(self, items):
        return {
            "sensor": str(items[0]),
            "op": str(items[1]),
            "value": float(items[2]),
            "unit": str(items[3]) if len(items) > 3 else None
        }

    def wait_action(self, items):
        return {
            "action_type": "wait",
            "duration": float(items[0]),
            "unit": str(items[1]) if len(items) > 1 else None
        }

    def start_action(self, items):
        return {"action_type": "start", "device": str(items[0])}

    def stop_action(self, items):
        return {"action_type": "stop", "device": str(items[0])}

    def turn_on_action(self, items):
        return {"action_type": "turn_on", "device": str(items[0])}

    def turn_off_action(self, items):
        return {"action_type": "turn_off", "device": str(items[0])}

    def send_action(self, items):
        return {
            "action_type": "send",
            "message": items[0].strip('"'),
            "target": str(items[1])
        }

    def alert_action(self, items):
        return {"action_type": "alert", "message": items[0].strip('"')}

    def parameter_action(self, items):
        return {
            "action_type": "set_parameter",
            "param": str(items[0]),
            "value": str(items[1])
        }

    def node_data(self, items):
        return items[0]

    def action(self, items):
        return items[0]

    def edge_condition(self, items):
        return items[0]

# ==================== 辅助函数 ====================
def print_section(title: str):
    """打印分隔线和标题"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")

def print_tree(tree: Tree, indent: int = 0):
    """美化打印抽象语法树"""
    prefix = "  " * indent
    if isinstance(tree, Tree):
        print(f"{prefix}├─ {tree.data}")
        for child in tree.children:
            print_tree(child, indent + 1)
    else:
        # 叶子节点（Token）
        print(f"{prefix}└─ {repr(tree)}")

# ==================== 主程序 ====================
def main():
    print_section("第1步：输入的DSL代码")
    print(SAMPLE_DSL)

    # 创建Lark解析器
    parser = Lark(COFFEE_GRAMMAR, start='workflow')

    print_section("第2步：词法分析 - Token流")
    print("Lark会将DSL代码分解为一系列Token（词法单元）：")
    print("例如: 'WORKFLOW' -> KEYWORD, '\"简化咖啡制作\"' -> STRING, '1.0' -> NUMBER")
    print("（完整Token流较长，此处省略）")

    # 解析DSL代码生成AST
    tree = parser.parse(SAMPLE_DSL)

    print_section("第3步：语法分析 - 抽象语法树（AST）")
    print("Lark根据语法规则构建树形结构：\n")
    print_tree(tree)

    # 使用Transformer转换AST
    transformer = CoffeeTransformer()
    result = transformer.transform(tree)

    print_section("第4步：语义分析 - 转换为Python数据结构")
    print("Transformer将AST转换为更易处理的Python字典：\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    print_section("第5步：提取关键信息")
    print(f"工作流名称: {result['workflow_name']}")
    print(f"版本号: {result['version']}")
    print(f"\n节点总数: {len([item for item in result['body'] if item['type'] == 'node'])}")
    print(f"边总数: {len([item for item in result['body'] if item['type'] == 'edge'])}")

    print("\n节点列表:")
    for item in result['body']:
        if item['type'] == 'node':
            print(f"  - {item['node_name']} ({item['node_type']}): {len(item['node_data'])}个数据项")

    print("\n连接关系:")
    for item in result['body']:
        if item['type'] == 'edge':
            condition_str = f" [条件: {item['condition']}]" if item['condition'] else ""
            print(f"  - {item['source']} → {item['target']}{condition_str}")

    print_section("第6步：生成可执行工作流（示意）")
    print("基于解析结果，可以生成LangGraph工作流或其他可执行代码")
    print("""
示例代码框架：

from langgraph.graph import StateGraph

workflow = StateGraph(CoffeeState)

# 添加节点
workflow.add_node("start", start_node)
workflow.add_node("check_water", check_water_node)
workflow.add_node("heat_water", heat_water_node)
workflow.add_node("make_coffee", make_coffee_node)

# 添加边
workflow.add_edge("start", "check_water")
workflow.add_edge("check_water", "heat_water")
workflow.add_edge("heat_water", "make_coffee")

app = workflow.compile()
    """)

    print_section("完成！")
    print("DSL代码已成功解析并转换为结构化数据")
    print("可以基于这些数据生成任何形式的可执行代码或配置文件")

if __name__ == "__main__":
    main()
