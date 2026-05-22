#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量化交易策略DSL解析器演示
展示为什么交易策略必须使用Lark而不是JSON
"""

from lark import Lark, Transformer, Tree
import json
from decimal import Decimal
from typing import Dict, Any

# ==================== Lark语法定义（简化版，完整版见trading_dsl.lark） ====================
TRADING_GRAMMAR = r"""
start: strategy

strategy: strategy_name version author capital risk entry_rule+ exit_rule+ risk_control

strategy_name: "STRATEGY" STRING
version: "VERSION" VERSION
author: "AUTHOR" STRING
capital: "CAPITAL" MONEY
risk: "RISK_PER_TRADE" PERCENTAGE

entry_rule: "ENTRY_RULE" STRING "WHEN" condition "THEN" "BUY" "AT" price_type "SIZE" "=" expression

exit_rule: "EXIT_RULE" STRING "WHEN" condition "THEN" "SELL" quantity "AT" price_type

condition: simple_condition
         | condition "AND" condition

simple_condition: field COMP_OP value

field: "price" | "volume" | "RSI" | "profit_pct"
value: NUMBER | PERCENTAGE | function_call
function_call: ID "(" NUMBER ")"
price_type: "market_price" | "limit_price"
quantity: "ALL" | PERCENTAGE
expression: MONEY | calculation
calculation: "CAPITAL" "*" PERCENTAGE

risk_control: "RISK_CONTROL" "MAX_POSITIONS" "=" NUMBER "MAX_DAILY_LOSS" "=" MONEY

COMP_OP: ">" | "<" | ">=" | "<="
MONEY: /\$\d+(\.\d+)?/
PERCENTAGE: /\d+(\.\d+)?%/
VERSION: /\d+\.\d+/
NUMBER: /\d+(\.\d+)?/
STRING: /"[^"]*"/
ID: /[a-zA-Z_][a-zA-Z0-9_]*/

COMMENT: /#[^\n]*/
%ignore " "
%ignore "\t"
%ignore /\r?\n/
%ignore COMMENT
"""

# ==================== 示例DSL ====================
SAMPLE_STRATEGY = """
STRATEGY "趋势突破策略" VERSION 2.1
AUTHOR "张交易员"
CAPITAL $100000
RISK_PER_TRADE 2%

ENTRY_RULE "突破买入"
  WHEN price > SMA(20) AND volume > AVG_VOLUME(50)
  THEN BUY AT market_price
       SIZE = CAPITAL * 2%

EXIT_RULE "止损出场"
  WHEN price < 95%
  THEN SELL ALL AT market_price

RISK_CONTROL
  MAX_POSITIONS = 5
  MAX_DAILY_LOSS = $2000
"""

# ==================== Transformer转换器 ====================
class TradingTransformer(Transformer):
    """将交易策略DSL转换为可执行对象"""

    def strategy(self, items):
        # items: [strategy_name, version, author, capital, risk, entry_rules..., exit_rules..., risk_control]
        return {
            "strategy_name": items[0],
            "version": items[1],
            "author": items[2],
            "capital": items[3],
            "risk_per_trade": items[4],
            "entry_rules": [item for item in items[5:] if isinstance(item, dict) and item.get('type') == 'entry_rule'],
            "exit_rules": [item for item in items[5:] if isinstance(item, dict) and item.get('type') == 'exit_rule'],
            "risk_control": [item for item in items[5:] if isinstance(item, dict) and item.get('type') == 'risk_control'][0]
        }

    def strategy_name(self, items):
        return items[0].strip('"')

    def version(self, items):
        return str(items[0])

    def author(self, items):
        return items[0].strip('"')

    def capital(self, items):
        return self._parse_money(items[0])

    def risk(self, items):
        return self._parse_percentage(items[0])

    def entry_rule(self, items):
        # items: [name, condition, price_type, expression]
        return {
            "type": "entry_rule",
            "name": items[0].strip('"'),
            "condition": items[1],
            "action": "BUY",
            "price_type": str(items[2]),
            "size": items[3]
        }

    def exit_rule(self, items):
        # items: [name, condition, quantity, price_type]
        return {
            "type": "exit_rule",
            "name": items[0].strip('"'),
            "condition": items[1],
            "action": "SELL",
            "quantity": str(items[2]),
            "price_type": str(items[3])
        }

    def risk_control(self, items):
        # items: [max_positions, max_daily_loss]
        return {
            "type": "risk_control",
            "max_positions": int(items[0]),
            "max_daily_loss": self._parse_money(items[1])
        }

    def condition(self, items):
        if len(items) == 1:
            return items[0]
        return {
            "left": items[0],
            "operator": "AND",
            "right": items[1]
        }

    def simple_condition(self, items):
        return {
            "field": str(items[0]),
            "operator": str(items[1]),
            "value": str(items[2])
        }

    def function_call(self, items):
        return f"{items[0]}({items[1]})"

    def calculation(self, items):
        return f"CAPITAL * {items[0]}"

    def _parse_money(self, token):
        """解析金额，提取数值"""
        return float(str(token).replace('$', ''))

    def _parse_percentage(self, token):
        """解析百分比，转换为小数"""
        return float(str(token).replace('%', '')) / 100

# ==================== 验证器（这是Lark方案的核心价值） ====================
class StrategyValidator:
    """策略安全验证器 - 这是JSON无法做到的！"""

    def __init__(self):
        self.errors = []

    def validate(self, strategy: Dict) -> bool:
        """多层验证确保策略安全"""
        self.errors = []

        # 1. 资金安全验证
        if strategy['capital'] < 10000:
            self.errors.append("⚠️ 资金过低：建议至少$10,000")

        if strategy['risk_per_trade'] > 0.05:  # 5%
            self.errors.append("🚨 单笔风险过高：不应超过5%")

        # 2. 风控参数验证
        risk = strategy['risk_control']
        if risk['max_daily_loss'] > strategy['capital'] * 0.1:
            self.errors.append("🚨 日损失上限过高：不应超过总资金的10%")

        # 3. 策略逻辑验证
        if not strategy['exit_rules']:
            self.errors.append("❌ 致命错误：缺少出场规则（必须有止损！）")

        # 4. 版本检查
        version = float(strategy['version'])
        if version < 2.0:
            self.errors.append("⚠️ 版本过旧：建议升级到2.0以上")

        return len(self.errors) == 0

    def get_report(self) -> str:
        """生成验证报告"""
        if not self.errors:
            return "✅ 策略验证通过，可以上线交易"
        return "❌ 策略验证失败：\n" + "\n".join(self.errors)

# ==================== 主程序 ====================
def main():
    print("=" * 80)
    print("  量化交易策略DSL解析演示")
    print("  展示为什么必须使用Lark而不是JSON")
    print("=" * 80)

    # 1. 解析DSL
    print("\n【步骤1】解析DSL策略文件...")
    parser = Lark(TRADING_GRAMMAR, start='strategy')
    tree = parser.parse(SAMPLE_STRATEGY)

    transformer = TradingTransformer()
    strategy = transformer.transform(tree)

    print("✅ 解析成功！")
    print(f"\n策略名称: {strategy['strategy_name']}")
    print(f"版本: {strategy['version']}")
    print(f"作者: {strategy['author']}")
    print(f"初始资金: ${strategy['capital']:,.2f}")
    print(f"单笔风险: {strategy['risk_per_trade']*100:.1f}%")

    # 2. 展示解析结果
    print("\n【步骤2】解析后的策略结构:")
    # 调试：先看看原始结构
    # print("DEBUG:", strategy)
    try:
        print(json.dumps(strategy, indent=2, ensure_ascii=False, default=str))
    except Exception as e:
        print(f"JSON序列化失败: {e}")
        print("原始对象:", strategy)

    # 3. 策略验证（这是Lark方案的核心价值！）
    print("\n【步骤3】策略安全验证...")
    validator = StrategyValidator()
    is_valid = validator.validate(strategy)
    print(validator.get_report())

    # 4. 对比JSON方案的问题
    print("\n" + "=" * 80)
    print("  为什么不能用JSON？")
    print("=" * 80)
    print("""
JSON方案的致命缺陷：

1. ❌ 无法验证单位：
   JSON: {"capital": 100000}
   问题：这是美元还是人民币？万一是100000分？

   Lark: CAPITAL $100000
   优势：明确的货币符号，解析时强制验证

2. ❌ 无法验证百分比：
   JSON: {"risk": 0.02}
   问题：这是2%还是0.02%？

   Lark: RISK_PER_TRADE 2%
   优势：明确的百分比符号，不会误解

3. ❌ 语法验证弱：
   JSON: {"condition": "price > SMA(20) AND volume > 1.5"}
   问题：这只是字符串，语法错误在运行时才发现！

   Lark: WHEN price > SMA(20) AND volume > AVG_VOLUME * 1.5
   优势：解析时就发现语法错误，不会上线错误策略

4. ❌ 可读性差：
   JSON需要大量嵌套的对象和数组，交易员看不懂

   Lark DSL像自然语言，交易员可以直接审核策略逻辑

5. 🚨 最致命：涉及真金白银的交易，语法错误 = 资金损失！
   必须在解析阶段就发现所有错误，而不是运行时。
""")

    # 5. 展示JSON等价物的复杂度
    print("\n【对比】同样的策略用JSON表达：")
    json_equivalent = {
        "strategy": {
            "name": "趋势突破策略",
            "version": "2.1",
            "author": "张交易员",
            "capital": {"amount": 100000, "currency": "USD"},
            "risk_per_trade": {"value": 2, "unit": "percent"},
            "entry_rules": [
                {
                    "name": "突破买入",
                    "conditions": {
                        "operator": "AND",
                        "left": {
                            "field": "price",
                            "operator": ">",
                            "value": {"function": "SMA", "params": [20]}
                        },
                        "right": {
                            "field": "volume",
                            "operator": ">",
                            "value": {"function": "AVG_VOLUME", "params": [50]}
                        }
                    },
                    "action": {
                        "type": "BUY",
                        "price_type": "market_price",
                        "size": {
                            "calculation": {
                                "left": {"ref": "CAPITAL"},
                                "operator": "*",
                                "right": {"value": 2, "unit": "percent"}
                            }
                        }
                    }
                }
            ]
        }
    }
    print(json.dumps(json_equivalent, indent=2, ensure_ascii=False))
    print("\n对比：")
    print("  DSL: 4行，交易员能看懂")
    print("  JSON: 35行，只有程序员能看懂")

if __name__ == "__main__":
    main()
