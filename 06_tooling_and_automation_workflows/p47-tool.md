<!-- Converted from p47-tool.ipynb -->

importlib 的强大之处：

- 动态导入：可以在运行时根据字符串路径导入模块
- 模块创建：可以从文件路径创建模块对象
- 灵活加载：支持插件式架构，无需修改主代码即可添加新功能

```python
import importlib.util
import os
from typing import TypedDict, Dict, Callable

# 1. 工具装饰器
def tool(name: str, description: str = ""):
    def decorator(func):
        func.is_tool = True
        func.tool_name = name
        func.description = description
        return func
    return decorator

# 2. 核心：动态加载器
def load_tools_from_directory(tools_dir: str) -> Dict[str, Callable]:
    """
    动态工具加载器 - 运行时扫描目录
    与静态加载的核心区别
    """
    tools = {}

    # 检查目录是否存在
    if not os.path.exists(tools_dir):
        print(f" 工具目录不存在: {tools_dir}")
        return tools

    print(f" 扫描工具目录: {tools_dir}")

    # 动态扫描目录中的所有 Python 文件
    for filename in os.listdir(tools_dir):
        if filename.endswith('.py') and not filename.startswith('__'):
            file_path = os.path.join(tools_dir, filename)
            module_name = filename[:-3]  # 移除 .py 后缀

            try:
                # importlib 动态加载模块
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # 动态发现模块中的工具函数
                for attr_name in dir(module):
                    obj = getattr(module, attr_name)
                    if hasattr(obj, 'is_tool'):
                        tools[obj.tool_name] = obj
                        print(f" 发现工具: {obj.tool_name} ({obj.description})")

            except Exception as e:
                print(f" 加载失败 {filename}: {e}")

    return tools

# 3. 多客户支持的动态加载器
def load_customer_tools(customer_id: str, base_dir: str = "customers") -> Dict[str, Callable]:
    """
    为特定客户动态加载工具 - 真实业务场景
    """
    customer_tools_dir = os.path.join(base_dir, customer_id, "tools")
    print(f" 为客户 {customer_id} 加载专属工具...")
    return load_tools_from_directory(customer_tools_dir)

# 4. 配置驱动的动态加载器
def load_tools_by_config(config: dict) -> Dict[str, Callable]:
    """
    根据配置动态加载工具 - 支持 A/B 测试
    """
    tools = {}

    for tool_config in config.get("enabled_tools", []):
        tools_dir = tool_config["directory"]
        enabled_tools = tool_config.get("tools", [])

        # 加载目录中的所有工具
        dir_tools = load_tools_from_directory(tools_dir)

        # 根据配置筛选工具
        if enabled_tools:
            for tool_name in enabled_tools:
                if tool_name in dir_tools:
                    tools[tool_name] = dir_tools[tool_name]
        else:
            tools.update(dir_tools)

    return tools

# 5. LangGraph 状态（保持不变）
class AgentState(TypedDict):
    task: str
    tools: dict
    result: str
    customer_id: str  # 新增客户ID

# 6. 动态的 LangGraph 节点
def dynamic_load_tools_node(state: AgentState) -> AgentState:
    """
    动态工具加载节点 - 核心区别
    """
    customer_id = state.get("customer_id", "default")

    # 方式1: 从通用工具目录加载，运行时扫描，动态发现
    general_tools = load_tools_from_directory("tools/")

    # 方式2: 从客户专属目录加载
    customer_tools = load_customer_tools(customer_id)

    # 方式3: 根据配置加载
    config = {
        "enabled_tools": [
            {"directory": "tools/", "tools": ["calculator", "text_processor"]},
            {"directory": f"customers/{customer_id}/tools/"}
        ]
    }
    config_tools = load_tools_by_config(config)

    # 合并所有工具（客户工具优先级更高）
    all_tools = {}
    all_tools.update(general_tools)
    all_tools.update(customer_tools)
    all_tools.update(config_tools)

    state["tools"] = all_tools
    print(f" 动态加载完成，共 {len(all_tools)} 个工具: {list(all_tools.keys())}")

    return state

# 7. 热重载功能
def hot_reload_tools(state: AgentState) -> AgentState:
    """
    热重载工具 - 无需重启即可更新工具
    """
    print(" 执行热重载...")
    return dynamic_load_tools_node(state)

# 8. 演示运行
def run_dynamic_agent(task: str, customer_id: str = "default"):
    """运行真正动态的 Agent"""
    state = AgentState(
        task=task,
        tools={},
        result="",
        customer_id=customer_id
    )

    print(f" 启动动态 Agent (客户: {customer_id})")
    print("=" * 50)

    #### 硬编码，编译时确定
    ###state["tools"] = {"calculator": add_numbers}


    # 动态加载工具
    state = dynamic_load_tools_node(state)

    # 模拟工具执行
    if state["tools"]:
        tool_name = list(state["tools"].keys())[0]
        print(f" 使用工具: {tool_name}")
        state["result"] = f"使用 {tool_name} 处理任务: {task}"
    else:
        state["result"] = "未找到可用工具"

    return state

# 演示
if __name__ == "__main__":
    # 创建示例工具文件内容（实际使用时这些应该是独立文件）
    print(" 模拟工具目录结构:")
    print("tools/")
    print("├── math_tools.py")
    print("├── text_tools.py")
    print("customers/")
    print("├── customer_a/tools/")
    print("└── customer_b/tools/")
    print()

    # 运行演示
    result = run_dynamic_agent("处理数据", "customer_a")
    print(f"\n 最终结果: {result['result']}")
```

输出：

```text
 模拟工具目录结构:
tools/
├── math_tools.py
├── text_tools.py
customers/
├── customer_a/tools/
└── customer_b/tools/

 启动动态 Agent (客户: customer_a)
==================================================
 工具目录不存在: tools/
 为客户 customer_a 加载专属工具...
 工具目录不存在: customers\customer_a\tools
 工具目录不存在: tools/
 工具目录不存在: customers/customer_a/tools/
 动态加载完成，共 0 个工具: []

 最终结果: 未找到可用工具
```

## 异常处理机制

1. 工具失败重试

使用 tenacity 库实现智能重试机制，

在网络波动或临时故障时自动恢复。

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
def call_with_retry(tool, inputs):
    return tool.invoke(inputs)
````

配置最多重试3次，间隔时间指数增长（1秒、2秒、4秒），避免雪崩效应。

2. 超时中断

防止某个工具长时间阻塞整个对话流程。

```python
try:
    result = await asyncio.wait_for(tool.run(), timeout=10.0)
except asyncio.TimeoutError:
    raise ToolExecutionTimeout("工具执行超时")
```

设置合理超时时间（如10秒），超时后抛出异常并提示用户。

3. 结果缓存机制

对于频繁调用且结果不变的查询类工具，启用缓存以提升性能。

```python
cached_result = redis.get(f"tool:{hash(inputs)}")
if cached_result:
    return json.loads(cached_result)

result = tool.invoke(inputs)
redis.setex(f"tool:{hash(inputs)}", 300, json.dumps(result))  # 缓存5分钟
```

适用于订单查询、商品信息获取等幂等性操作，显著降低后端压力。

4. 文件监听与动态重载

使用 watchdog 库监听插件目录变化，检测到代码修改后自动重载。

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class PluginReloader(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith(".py"):
            plugin_name = extract_plugin_name(event.src_path)
            if plugin_name in loaded_plugins:
                importlib.reload(loaded_plugins[plugin_name])
                print(f"插件 {plugin_name} 已重新加载")
```

启动时运行监听器：
```python
observer = Observer()
observer.schedule(PluginReloader(), path="plugins", recursive=True)
observer.start()
```
