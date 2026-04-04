# RPA 与 AI 工作流集成完全指南

## 目录

- [第一部分：RPA 基础](#第一部分rpa-基础)
  - [1.1 RPA 概念与架构](#11-rpa-概念与架构)
  - [1.2 RPA 应用场景](#12-rpa-应用场景)
  - [1.3 RPA 技术栈](#13-rpa-技术栈)
- [第二部分：影刀 RPA 平台](#第二部分影刀-rpa-平台)
  - [2.1 影刀 RPA 介绍](#21-影刀-rpa-介绍)
  - [2.2 xbot 核心 API](#22-xbot-核心-api)
  - [2.3 流程开发模式](#23-流程开发模式)
- [第三部分：Dify AI 工作流](#第三部分dify-ai-工作流)
  - [3.1 Dify 平台介绍](#31-dify-平台介绍)
  - [3.2 工作流 vs 聊天应用](#32-工作流-vs-聊天应用)
  - [3.3 API 接口详解](#33-api-接口详解)
- [第四部分：RPA + AI 集成实现](#第四部分rpa--ai-集成实现)
  - [4.1 集成架构设计](#41-集成架构设计)
  - [4.2 核心代码实现](#42-核心代码实现)
  - [4.3 错误处理与日志](#43-错误处理与日志)
- [第五部分：实战案例](#第五部分实战案例)
  - [5.1 智能表单填写](#51-智能表单填写)
  - [5.2 发票自动识别与录入](#52-发票自动识别与录入)
  - [5.3 客服工单自动处理](#53-客服工单自动处理)
  - [5.4 Excel 数据智能分析](#54-excel-数据智能分析)
- [第六部分：最佳实践与优化](#第六部分最佳实践与优化)
- [第七部分：问题排查与调试](#第七部分问题排查与调试)

---

# 第一部分：RPA 基础

## 1.1 RPA 概念与架构

### 什么是 RPA？

**RPA (Robotic Process Automation)**: 机器人流程自动化，通过软件机器人模拟人类在计算机��的操作，实现业务流程自动化。

```
传统人工操作:
  用户 → 鼠标/键盘 → 应用程序 → 数据处理

RPA 自动化:
  RPA 机器人 → 模拟输入 → 应用程序 → 批量处理
```

---

### RPA 核心能力

```python
# RPA 的三大核心能力

1. UI 自动化 (UI Automation)
   - 模拟鼠标点击、移动
   - 模拟键盘输入
   - 识别界面元素 (按钮、输入框等)

2. 数据处理 (Data Processing)
   - Excel 读写
   - 数据库操作
   - 文件操作
   - 网页爬取

3. 系统集成 (System Integration)
   - API 调用
   - 邮件收发
   - FTP 传输
   - 应用间数据传递
```

---

### RPA 架构模式

#### 有人值守 RPA (Attended RPA)

```
特点: 人机协同，人工触发执行

应用场景:
  - 客服人员使用 RPA 辅助查询客户信息
  - 销售人员使用 RPA 快速生成报价单
  - 财务人员使用 RPA 自动填充表单

优点: 灵活、实时响应
缺点: 需要人工介入
```

---

#### 无人值守 RPA (Unattended RPA)

```
特点: 完全自动化，定时/事件触发

应用场景:
  - 每天凌晨自动生成财务报表
  - 监控邮件自动下载附件并处理
  - 定时从多个系统同步数据

优点: 全自动、7×24 运行
缺点: 需要完善的异常处理
```

---

#### 混合模式 (Hybrid RPA)

```
结合有人值守和无人值守的优势

示例流程:
  1. 无人值守: 夜间自动收集数据
  2. 有人值守: 白天人工审核结果
  3. 无人值守: 审核通过后自动提交
```

---

### RPA 技术栈对比

| 平台 | ��型 | 开发方式 | 价格 | 特点 |
|------|------|---------|------|------|
| **影刀 RPA** | 商业 | 可视化 + Python | 免费版/付费版 | 国产、易用、中文支持好 |
| **UiPath** | 商业 | 可视化 + .NET | 收费 | 全球最大、功能强大 |
| **Automation Anywhere** | 商业 | 可视化 + 脚本 | 收费 | 企业级、云原生 |
| **Blue Prism** | 商业 | 可视化 | 收费 | 安全性高、银行偏好 |
| **TagUI** | 开源 | Python/CLI | 免费 | 轻量级、命令行 |
| **Robot Framework** | 开源 | Python | 免费 | 测试框架、扩展性强 |

---

## 1.2 RPA 应用场景

### 财务场景

```
发票处理自动化:
  1. 监控邮件中的发票附件 (PDF/图片)
  2. OCR 识别发票信息 (发票号、金额、日期)
  3. AI 校验发票真伪
  4. 自动录入财务系统
  5. 生成对账报告

效果:
  - 处理速度: 人工 5分钟/张 → RPA 10秒/张
  - 准确率: 95% → 99.5%
  - 成本: 节省 80% 人力
```

---

### 客服场景

```
工单自动分类与回复:
  1. 监控工单系统新工单
  2. AI 分析工单内容 (问题类型、紧急程度)
  3. 自动分配给合适的客服人员
  4. 常见问题自动回复
  5. 复杂问题转人工并提供参考答案

效果:
  - 首次响应时间: 30分钟 → 30秒
  - 简单问题处理: 100% 自动化
  - 客服满意度: +25%
```

---

### HR 场景

```
简历筛选自动化:
  1. 从招聘网站下载简历
  2. AI 提取关键信息 (学历、经验、技能)
  3. 根据 JD 匹配度打分
  4. 自动发送面试邀请邮件
  5. 同步到 ATS 系统

效果:
  - 筛选速度: 200份/天 → 2000份/天
  - 优质候选人发现率: +30%
```

---

### 供应链场景

```
采购订单自动处理:
  1. 接收供应商报价邮件
  2. AI 提取价格、交期等信息
  3. 对比历史价格，识别异常
  4. 自动生成采购订单
  5. 同步 ERP 系统

效果:
  - 处理时间: 2小时 → 5分钟
  - 价格合规率: +15%
```

---

## 1.3 RPA 技术栈

### 元素识别技术

```python
# 1. 图像识别 (Image Recognition)
特点: 通过截图对比识别元素
优点: 不受应用限制
缺点: 分辨率变化时失效

# 2. OCR 识别 (Optical Character Recognition)
特点: 识别屏幕上的文字
优点: 可处理无法直接访问的文本
缺点: 准确率受字体影响

# 3. UI 自动化 (UI Automation)
特点: 通过操作系统 API 识别控件
优点: 准确、稳定
缺点: 需要应用支持 (Windows: UIA, macOS: Accessibility)

# 4. 选择器 (Selector)
特点: 通过 XPath/CSS Selector 定位网页元素
优点: 精确定位
缺点: 仅适用于网页/Electron 应用
```

---

### 常见 RPA 库对比

| 库名 | 语言 | 平台 | 用途 | 优势 |
|------|------|------|------|------|
| **pyautogui** | Python | 跨平台 | 鼠标键盘控制 | 简单易用 |
| **pywinauto** | Python | Windows | UI 自动化 | Windows 原生支持 |
| **selenium** | 多语言 | 浏览器 | Web 自动化 | 生态丰富 |
| **playwright** | 多语言 | 浏览器 | Web 自动化 | 性能好、API 现代 |
| **pyperclip** | Python | 跨平台 | 剪贴板操作 | 跨平台剪贴板 |
| **openpyxl** | Python | 跨平台 | Excel 操作 | Excel 读写 |

---

# 第二部分：影刀 RPA 平台

## 2.1 影刀 RPA 介绍

### 影刀 RPA 特点

```
1. 可视化开发
   - 拖拽式流程设计
   - 所见即所得
   - 降低开发门槛

2. Python 脚本支持
   - 可视化 + 代码混合开发
   - 调用 Python 生态
   - 自定义复杂逻辑

3. 云端调度
   - 支持定时任务
   - 支持远程触发
   - 流程版本管理

4. 企业级功能
   - 流程权限管理
   - 执行日志审计
   - 机器人集群管理
```

---

### 影刀 RPA 架构

```
┌─────────────────────────────────────────────┐
│           影刀 RPA 控制台 (Web)              │
│  - 流程设计器                                │
│  - 任务调度器                                │
│  - 日志监控                                  │
└─────────────────────────────────────────────┘
                    ↓ API
┌─────────────────────────────────────────────┐
│          影刀 RPA 客户端 (桌面应用)           │
│  - 流程执行引擎                              │
│  - xbot 核心库                               │
│  - 插件市场                                  │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│              操作系统 API                     │
│  - UI Automation (元素识别)                  │
│  - 鼠标键盘模拟                              │
│  - 进程管理                                  │
└─────────────────────────────────────────────┘
```

---

## 2.2 xbot 核心 API

### 2.2.1 基础 API

```python
import xbot
from xbot import print, sleep

# 1. 日志输出
print("开始执行流程")  # 会显示在影刀控制台

# 2. 延迟
sleep(2)  # 延迟 2 秒

# 3. 截图
xbot.screen.capture_screen("screenshot.png")

# 4. 获取剪贴板
clipboard_text = xbot.clipboard.get_text()

# 5. 设置剪贴板
xbot.clipboard.set_text("Hello RPA")
```

---

### 2.2.2 UI 自动化 API

```python
# 1. 元素定位
# 方式 1: 通过选择器 (推荐)
element = xbot.web.get_element(
    browser=browser_obj,
    selector='#username'  # CSS Selector
)

# 方式 2: 通过图像识别
element = xbot.image.find_on_screen(
    image_path="button.png",
    similarity=0.9  # 相似度阈值
)

# 2. 鼠标操作
xbot.mouse.click(x=100, y=200)  # 点击坐标
xbot.mouse.click(element=element)  # 点击元素
xbot.mouse.double_click(element=element)  # 双击
xbot.mouse.right_click(element=element)  # 右键

# 3. 键盘操作
xbot.keyboard.input_text("Hello World")  # 输入文本
xbot.keyboard.press_key("enter")  # 按键
xbot.keyboard.hotkey("ctrl", "c")  # 组合键

# 4. 元素操作
element.click()  # 点击
element.input_text("test")  # 输入
text = element.get_text()  # 获取文本
value = element.get_attribute("value")  # 获取属性
```

---

### 2.2.3 Web 自动化 API

```python
# 1. 浏览器控制
browser = xbot.web.create_browser(
    browser_type="chrome",  # chrome/edge/firefox
    url="https://www.example.com"
)

# 2. 页面操作
browser.navigate("https://www.google.com")  # 跳转
browser.refresh()  # 刷新
browser.back()  # 后退
browser.forward()  # 前进

# 3. 元素操作
element = browser.find_element("#search-input")
element.input_text("RPA automation")
element.click()

# 4. 等待
browser.wait_element_appear("#result", timeout=10)

# 5. 执行 JavaScript
result = browser.execute_script("return document.title")

# 6. 截图
browser.save_screenshot("page.png")

# 7. 获取页面源码
html = browser.get_page_source()

# 8. 关闭浏览器
browser.close()
```

---

### 2.2.4 Excel 操作 API

```python
# 1. 打开 Excel
excel = xbot.excel.open_excel(
    file_path="data.xlsx",
    visible=True  # 是否显示 Excel 窗口
)

# 2. 读取数据
# 读取单元格
value = excel.read_cell(sheet="Sheet1", cell="A1")

# 读取区域
data = excel.read_range(
    sheet="Sheet1",
    start_cell="A1",
    end_cell="C10"
)

# 读取整列
column_data = excel.read_column(sheet="Sheet1", column="A")

# 3. 写入数据
excel.write_cell(sheet="Sheet1", cell="A1", value="Name")
excel.write_range(sheet="Sheet1", start_cell="A2", data=[
    ["Alice", 25, "Engineer"],
    ["Bob", 30, "Manager"]
])

# 4. 工作表操作
excel.add_sheet("NewSheet")
excel.delete_sheet("OldSheet")
excel.rename_sheet("Sheet1", "Data")

# 5. 保存与关闭
excel.save()
excel.save_as("output.xlsx")
excel.close()
```

---

### 2.2.5 数据库操作 API

```python
# 1. 连接数据库
db = xbot.database.connect(
    db_type="mysql",
    host="localhost",
    port=3306,
    user="root",
    password="password",
    database="test_db"
)

# 2. 执行查询
result = db.execute_query("SELECT * FROM users WHERE age > 25")
# result = [{"id": 1, "name": "Alice", "age": 30}, ...]

# 3. 执行更新
affected_rows = db.execute_update(
    "UPDATE users SET status = 'active' WHERE id = 1"
)

# 4. 插入数据
db.execute_insert(
    "INSERT INTO users (name, age) VALUES ('Charlie', 28)"
)

# 5. 关闭连接
db.close()
```

---

### 2.2.6 文件操作 API

```python
# 1. 文件读写
content = xbot.file.read_text("input.txt")
xbot.file.write_text("output.txt", "Hello RPA")

# 2. 文件复制/移动
xbot.file.copy("source.txt", "destination.txt")
xbot.file.move("old_path.txt", "new_path.txt")

# 3. 文件删除
xbot.file.delete("temp.txt")

# 4. 目录操作
xbot.folder.create("new_folder")
xbot.folder.delete("old_folder")
files = xbot.folder.list_files("path/to/folder")

# 5. 文件属性
exists = xbot.file.exists("file.txt")
size = xbot.file.get_size("file.txt")
```

---

## 2.3 流程开发模式

### 可视化流程示例

```
┌─────────────────┐
│  开始           │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 打开浏览器      │
│ URL: xxx.com    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 输入账号密码    │
│ 元素: #username │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 点击登录        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 调用 Python     │
│ 模块: RPA.py    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  结束           │
└─────────────────┘
```

---

### Python 模块开发规范

```python
# RPA.py - 影刀 RPA Python 模块模板

import xbot
from xbot import print, sleep
from .import package  # 影刀内部包
from .package import variables as glv  # 全局变量

def main(args):
    """
    主函数: 作为独立流程运行时执行

    参数:
        args: 流程参数字典
    """
    pass

def custom_function(input_param):
    """
    自定义函数: 可被可视化流程中的"调用模块"指令调用

    参数:
        input_param: 输入参数

    返回:
        处理结果
    """
    # 1. 参数校验
    if not input_param:
        print("错误: 输入参数为空")
        return None

    # 2. 业务逻辑
    result = process_data(input_param)

    # 3. 日志记录
    print(f"处理完成: {result}")

    # 4. 返回结果
    return result

def process_data(data):
    """内部辅助函数"""
    # 实现具体逻辑
    return data.upper()
```

---

# 第三部分：Dify AI 工作流

## 3.1 Dify 平台介绍

### Dify 是什么？

**Dify**: 开源的 LLM 应用开发平台，提供可视化的 AI 工作流编排能力

```
核心功能:
  1. 工作流编排 (Workflow)
     - 可视化节点连接
     - 支持条件分支、循环
     - 内置 LLM、工具调用、代码执行等节点

  2. 聊天应用 (Chat Application)
     - 即开即用的对话 AI
     - 支持上下文记忆
     - 可嵌入网站/App

  3. 知识库 (Knowledge Base)
     - 文档上传与向量化
     - RAG 检索增强

  4. 插件市场 (Plugin Marketplace)
     - 第三方工具集成
     - 自定义工具开发
```

---

### Dify 架构

```
┌──────────────────────────────────────────┐
│          Dify Web UI (前端)               │
│  - 工作流可视化编辑器                     │
│  - 应用配置界面                           │
│  - API Key 管理                           │
└──────────────────────────────────────────┘
                   ↓ HTTP API
┌──────────────────────────────────────────┐
│          Dify API Server (后端)           │
│  - 工作流执行引擎                         │
│  - LLM 调用管理                           │
│  - 向量数据库集成                         │
└──────────────────────────────────────────┘
                   ↓
┌──────────────────────────────────────────┐
│           外部服务                        │
│  - OpenAI / Claude / Qwen                │
│  - Vector DB (Qdrant / Weaviate)        │
│  - 第三方 API (天气、翻译等)              │
└──────────────────────────────────────────┘
```

---

## 3.2 工作流 vs 聊天应用

### 工作流 (Workflow)

```
特点:
  - 复杂逻辑编排
  - 多步骤处理
  - 输入 → 处理 → 输出

适用场景:
  - 数据处理流程 (ETL)
  - 文档生成 (合同、报告)
  - 决策树判断
  - 批量任务

示例工作流:
  输入: 客户信息
    ↓
  [LLM 节点] 生成问候语
    ↓
  [条件判断] 是否 VIP 客户?
    ↓ 是              ↓ 否
  [工具调用]        [邮件节点]
  查询专属优惠      发送标准邮件
    ↓
  输出: 处理结果
```

---

### 聊天应用 (Chat Application)

```
特点:
  - 对话式交互
  - 上下文记忆
  - 流式输出

适用场景:
  - 客服机器人
  - 知识问答
  - 个人助手

示例对话:
  用户: "我想了解产品 A 的价格"
  AI:   "产品 A 的价格是 199 元，有什么其他问题吗？"
  用户: "有折扣吗？"
  AI:   "产品 A 目前有 8 折优惠，到手价 159 元"
```

---

### 选择指南

| 需求 | 推荐类型 | 原因 |
|------|---------|------|
| RPA 集成 | **工作流** | 单次调用、明确输入输出 |
| 客服对话 | **聊天应用** | 需要上下文记忆 |
| 批量数据处理 | **工作流** | 无需交互、批量执行 |
| 知识问答 | **聊天应用** | 多轮对话、检索知识库 |
| 文档生成 | **工作流** | 结构化输出 |

---

## 3.3 API 接口详解

### 3.3.1 工作流 API

```python
import requests
import json

# 1. 执行工作流
url = "https://api.dify.ai/v1/workflows/run"

headers = {
    'Authorization': 'Bearer app-xxxxxxxxxxxxx',  # API Key
    'Content-Type': 'application/json'
}

data = {
    "inputs": {
        "customer_name": "张三",
        "order_id": "12345"
    },
    "response_mode": "blocking",  # blocking/streaming
    "user": "user-001"
}

response = requests.post(url, headers=headers, json=data)

if response.status_code == 200:
    result = response.json()
    # 结构:
    # {
    #   "workflow_run_id": "xxx",
    #   "task_id": "yyy",
    #   "data": {
    #     "status": "succeeded",
    #     "outputs": {
    #       "result": "处理完成"
    #     }
    #   }
    # }
    outputs = result['data']['outputs']
    print(outputs)
```

---

### 3.3.2 聊天应用 API

```python
# 2. 发送聊天消息
url = "https://api.dify.ai/v1/chat-messages"

headers = {
    'Authorization': 'Bearer app-xxxxxxxxxxxxx',
    'Content-Type': 'application/json'
}

data = {
    "inputs": {},  # 附加参数
    "query": "你好，我想咨询产品价格",
    "response_mode": "blocking",
    "conversation_id": "",  # 空字符串表示新对话
    "user": "user-001"
}

response = requests.post(url, headers=headers, json=data)

if response.status_code == 200:
    result = response.json()
    # 结构:
    # {
    #   "message_id": "xxx",
    #   "conversation_id": "yyy",  # 用于后续对话
    #   "answer": "您好，请问您想了解哪款产品？",
    #   "created_at": 1234567890
    # }
    answer = result['answer']
    conversation_id = result['conversation_id']
    print(f"AI 回复: {answer}")

# 3. 继续对话
data_next = {
    "query": "产品 A 的价格是多少？",
    "conversation_id": conversation_id,  # 使用上次的 ID
    "user": "user-001"
}

response_next = requests.post(url, headers=headers, json=data_next)
# AI 会记住上下文
```

---

### 3.3.3 流式响应

```python
# 流式输出 (适合实时显示)
data_streaming = {
    "query": "写一篇关于 AI 的文章",
    "response_mode": "streaming",  # 改为 streaming
    "user": "user-001"
}

response = requests.post(url, headers=headers, json=data_streaming, stream=True)

# 逐行读取 SSE (Server-Sent Events)
for line in response.iter_lines():
    if line:
        line_str = line.decode('utf-8')
        if line_str.startswith('data: '):
            data_str = line_str[6:]  # 去掉 "data: " 前缀

            if data_str == '[DONE]':
                break

            try:
                chunk = json.loads(data_str)
                if 'answer' in chunk:
                    print(chunk['answer'], end='', flush=True)
            except json.JSONDecodeError:
                pass
```

---

### 3.3.4 错误处理

```python
# 常见错误码
ERROR_CODES = {
    400: "请求参数错误",
    401: "API Key 无效或过期",
    403: "权限不足",
    404: "应用不存在",
    429: "请求频率超限",
    500: "服务器内部错误"
}

def call_dify_with_retry(url, headers, data, max_retries=3):
    """带重试的 Dify API 调用"""

    for attempt in range(max_retries):
        try:
            response = requests.post(
                url,
                headers=headers,
                json=data,
                timeout=30
            )

            if response.status_code == 200:
                return response.json()

            elif response.status_code == 429:
                # 限流: 等待后重试
                wait_time = 2 ** attempt  # 指数退避
                print(f"限流中，等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
                continue

            elif response.status_code in [500, 502, 503]:
                # 服务器错误: 重试
                print(f"服务器错误 (尝试 {attempt+1}/{max_retries})")
                time.sleep(1)
                continue

            else:
                # 其他错误: 不重试
                error_msg = ERROR_CODES.get(response.status_code, "未知错误")
                raise Exception(f"API 调用失败 ({response.status_code}): {error_msg}")

        except requests.RequestException as e:
            print(f"网络错误: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(1)

    raise Exception("达到最大重试次数")
```

---

# 第四部分：RPA + AI 集成实现

## 4.1 集成架构设计

### 架构图

```
┌─────────────────────────────────────────────────┐
│           影刀 RPA 流程 (可视化)                 │
│                                                  │
│  ┌──────┐   ┌──────┐   ┌──────┐   ┌──────┐    │
│  │ 打开 │──▶│ 提取 │──▶│ 调用 │──▶│ 填写 │    │
│  │ 网页 │   │ 数据 │   │Python│   │ 表单 │    │
│  └──────┘   └──────┘   └──┬───┘   └──────┘    │
│                            │                     │
└────────────────────────────┼─────────────────────┘
                             │
                             ▼
            ┌────────────────────────────┐
            │   RPA.py (Python 模块)      │
            │                             │
            │  def run_dify_workflow():   │
            │    - 构造请求               │
            │    - 调用 Dify API          │
            │    - 解析响应               │
            │    - 返回结果               │
            └────────────┬────────────────┘
                         │ HTTP POST
                         ▼
            ┌────────────────────────────┐
            │   Dify AI 工作流            │
            │                             │
            │  输入: 客户信息             │
            │   ↓                         │
            │  [LLM] 生成回复             │
            │   ↓                         │
            │  [工具] 查询数据库          │
            │   ↓                         │
            │  输出: 处理结果             │
            └────────────────────────────┘
```

---

### 数据流

```
1. RPA 触发
   ↓
2. 提取表单数据 (姓名、需求等)
   {"name": "张三", "query": "咨询价格"}
   ↓
3. 调用 RPA.py 模块
   run_dify_workflow(input_data)
   ↓
4. 构造 Dify API 请求
   {
     "inputs": {...},
     "query": "咨询价格",
     "user": "zhang-san"
   }
   ↓
5. Dify 执行工作流
   - LLM 理解需求
   - 查询价格数据库
   - 生成专业回复
   ↓
6. 返回结果给 RPA
   {"answer": "产品 A 价格 199 元"}
   ↓
7. RPA 填写到网页表单
   ↓
8. 完成流程
```

---

## 4.2 核心代码实现

### 4.2.1 完整的 RPA.py 实现

```python
# RPA.py - 影刀 RPA Python 模块

import xbot
from xbot import print, sleep
from .import package
from .package import variables as glv
import requests
import json
import time

def main(args):
    """主函数"""
    # 测试用例
    test_input = {
        "query": "我想了解产品价格",
        "customer_name": "张三",
        "customer_id": "C12345"
    }

    result = run_dify_workflow(test_input)
    print(f"测试结果: {result}")

def run_dify_workflow(Dify_workflow_Input):
    """
    执行 Dify 工作流并返回结果

    参数:
        Dify_workflow_Input (dict): 工作流输入
            - query (str): 用户查询
            - 其他业务参数

    返回:
        dict: 工作流输出
            - answer (str): AI 回复
            - 其他业务结果

    异常:
        返回 None 表示执行失败
    """

    # ========== 配置部分 ==========
    # 1. API 端点 (根据应用类型选择)
    # 工作流: https://api.dify.ai/v1/workflows/run
    # 聊天应用: https://api.dify.ai/v1/chat-messages

    url = "http://localhost/v1/chat-messages"  # 本地部署
    # url = "https://api.dify.ai/v1/chat-messages"  # 云端

    # 2. API Key (从 Dify 控制台获取)
    api_key = "app-mMl5Qiq3Gv9yGoJGjDRjH8m6"

    # 3. 请求头
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }

    # 4. 代理设置 (可选)
    proxies = {
        'https': 'http://127.0.0.1:7897',
        'http': 'http://127.0.0.1:7897'
    }
    use_proxy = False  # 是否使用代理

    # ========== 参数处理 ==========
    # 确保所有值为字符串类型
    Dify_workflow_Input = {
        k: str(v) for k, v in Dify_workflow_Input.items()
    }

    # 提取 query (必需参数)
    query = Dify_workflow_Input.get("query", "")
    if not query:
        print("错误: query 参数为空")
        return None

    # 其他参数作为 inputs
    inputs = {
        k: v for k, v in Dify_workflow_Input.items()
        if k != "query"
    }

    # ========== 构造请求体 ==========
    data = {
        "inputs": inputs,
        "query": query,
        "response_mode": "blocking",  # blocking/streaming
        "user": inputs.get("customer_id", "default-user-id")
    }

    # 日志
    print("=" * 50)
    print("调用 Dify API")
    print(f"URL: {url}")
    print(f"Inputs: {json.dumps(inputs, ensure_ascii=False)}")
    print(f"Query: {query}")
    print("=" * 50)

    # ========== 发送请求 ==========
    try:
        # 发送 POST 请求
        response = requests.post(
            url,
            headers=headers,
            json=data,
            proxies=proxies if use_proxy else None,
            timeout=60  # 60 秒超时
        )

        # 打印响应信息
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.text[:500]}")  # 截取前 500 字符

        # 检查状态码
        response.raise_for_status()

        # ========== 解析响应 ==========
        result = response.json()

        # 根据应用类型解析结果
        # 情况 1: 工作流应用
        if 'data' in result and 'outputs' in result['data']:
            Dify_workflow_Output = result['data']['outputs']
            print(f"✓ 工作流执行成功")
            print(f"输出: {json.dumps(Dify_workflow_Output, ensure_ascii=False)}")
            return Dify_workflow_Output

        # 情况 2: 聊天应用 (data.answer)
        elif 'data' in result and 'answer' in result['data']:
            answer = result['data']['answer']
            print(f"✓ 聊天应用回复: {answer}")
            return {"answer": answer}

        # 情况 3: 聊天应用 (answer 在顶层)
        elif 'answer' in result:
            answer = result['answer']
            print(f"✓ AI 回复: {answer}")
            return {"answer": answer}

        # 情况 4: 未知响应格式
        else:
            print("⚠️  警告: 响应格式未识别")
            print(f"完整响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
            return result

    except requests.exceptions.Timeout:
        print("✗ 错误: 请求超时 (60秒)")
        return None

    except requests.exceptions.HTTPError as e:
        print(f"✗ HTTP 错误: {e}")
        print(f"响应内容: {response.text}")
        return None

    except requests.exceptions.RequestException as e:
        print(f"✗ 请求错误: {str(e)}")
        return None

    except json.JSONDecodeError as e:
        print(f"✗ JSON 解析错误: {e}")
        print(f"原始响应: {response.text}")
        return None

    except Exception as e:
        print(f"✗ 未知错误: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return None

def run_dify_chat_conversation(query, conversation_id=None):
    """
    进行多轮对话

    参数:
        query (str): 用户输入
        conversation_id (str): 对话 ID (None 表示新对话)

    返回:
        tuple: (answer, new_conversation_id)
    """
    url = "http://localhost/v1/chat-messages"
    headers = {
        'Authorization': 'Bearer app-mMl5Qiq3Gv9yGoJGjDRjH8m6',
        'Content-Type': 'application/json',
    }

    data = {
        "query": query,
        "conversation_id": conversation_id or "",
        "response_mode": "blocking",
        "user": "user-001"
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()

        result = response.json()
        answer = result.get('answer', '')
        new_conversation_id = result.get('conversation_id', '')

        return answer, new_conversation_id

    except Exception as e:
        print(f"对话错误: {e}")
        return None, None
```

---

### 4.2.2 带重试机制的增强版

```python
def run_dify_workflow_with_retry(Dify_workflow_Input, max_retries=3):
    """
    带重试机制的 Dify 调用

    参数:
        Dify_workflow_Input (dict): 输入参数
        max_retries (int): 最大重试次数

    返回:
        dict: 执行结果
    """

    for attempt in range(max_retries):
        print(f"\n尝试 {attempt + 1}/{max_retries}")

        result = run_dify_workflow(Dify_workflow_Input)

        if result is not None:
            print(f"✓ 执行成功 (第 {attempt + 1} 次尝试)")
            return result

        # 失败处理
        if attempt < max_retries - 1:
            wait_time = 2 ** attempt  # 指数退避: 1s, 2s, 4s
            print(f"× 执行失败，{wait_time} 秒后重试...")
            sleep(wait_time)
        else:
            print("✗ 达到最大重试次数，执行失败")
            return None

    return None
```

---

## 4.3 错误处理与日志

### 4.3.1 完善的错误处理

```python
class DifyAPIError(Exception):
    """Dify API 自定义异常"""
    def __init__(self, status_code, message, response_body=None):
        self.status_code = status_code
        self.message = message
        self.response_body = response_body
        super().__init__(self.message)

def run_dify_workflow_safe(Dify_workflow_Input):
    """
    安全版本: 抛出详细异常
    """
    url = "http://localhost/v1/chat-messages"
    headers = {
        'Authorization': 'Bearer app-xxxxx',
        'Content-Type': 'application/json',
    }

    # 参数校验
    if not isinstance(Dify_workflow_Input, dict):
        raise TypeError("输入必须是字典类型")

    if 'query' not in Dify_workflow_Input:
        raise ValueError("缺少必需参数: query")

    # 构造请求
    data = {
        "inputs": {k: str(v) for k, v in Dify_workflow_Input.items() if k != "query"},
        "query": str(Dify_workflow_Input["query"]),
        "response_mode": "blocking",
        "user": "default-user"
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)

        # 详细的状态码处理
        if response.status_code == 200:
            return response.json()

        elif response.status_code == 400:
            raise DifyAPIError(
                400,
                "请求参数错误",
                response.text
            )

        elif response.status_code == 401:
            raise DifyAPIError(
                401,
                "API Key 无效或已过期",
                response.text
            )

        elif response.status_code == 403:
            raise DifyAPIError(
                403,
                "权限不足，请检查 API Key 权限",
                response.text
            )

        elif response.status_code == 404:
            raise DifyAPIError(
                404,
                "应用不存在或已删除",
                response.text
            )

        elif response.status_code == 429:
            raise DifyAPIError(
                429,
                "请求频率超限，请稍后重试",
                response.text
            )

        elif response.status_code >= 500:
            raise DifyAPIError(
                response.status_code,
                "Dify 服务器错误",
                response.text
            )

        else:
            raise DifyAPIError(
                response.status_code,
                f"未知错误 ({response.status_code})",
                response.text
            )

    except requests.exceptions.Timeout:
        raise TimeoutError("请求超时 (60秒)")

    except requests.exceptions.ConnectionError:
        raise ConnectionError("无法连接到 Dify 服务器，请检查网络和 URL")

    except json.JSONDecodeError:
        raise ValueError(f"响应不是有效的 JSON: {response.text}")

# 使用示例
try:
    result = run_dify_workflow_safe(input_data)
    print(f"成功: {result}")

except DifyAPIError as e:
    print(f"Dify API 错误 ({e.status_code}): {e.message}")
    print(f"详细信息: {e.response_body}")

except TimeoutError as e:
    print(f"超时: {e}")

except ConnectionError as e:
    print(f"连接失败: {e}")

except Exception as e:
    print(f"未知错误: {e}")
```

---

### 4.3.2 结构化日志

```python
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('rpa_dify.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def run_dify_workflow_logged(Dify_workflow_Input):
    """带日志的版本"""

    request_id = datetime.now().strftime("%Y%m%d%H%M%S")

    logger.info(f"[{request_id}] 开始调用 Dify API")
    logger.info(f"[{request_id}] 输入参数: {json.dumps(Dify_workflow_Input, ensure_ascii=False)}")

    try:
        # 调用 API
        start_time = time.time()
        result = run_dify_workflow(Dify_workflow_Input)
        elapsed_time = time.time() - start_time

        if result:
            logger.info(f"[{request_id}] 调用成功 (耗时 {elapsed_time:.2f}秒)")
            logger.info(f"[{request_id}] 返回结果: {json.dumps(result, ensure_ascii=False)}")
            return result
        else:
            logger.error(f"[{request_id}] 调用失败")
            return None

    except Exception as e:
        logger.exception(f"[{request_id}] 异常: {e}")
        return None
```

---

**未完待续...**

下一部分将包含：
- **第五部分: 实战案例** (智能表单填写、发票识别等)
- **第六部分: 最佳实践与优化**
- **第七部分: 问题排查与调试**

---

**当前进度**: 第一至四部分完成 ✅

**文档版本**: v1.0 (Part 1/2)
**最后更新**: 2025-12-15
**基于源文件**: RPA.py (04_workflow_orchestration/rpa_and_ai_workflow)
