# RPA 与 AI 工作流集成指南（第2部分）

> 这是《RPA 与 AI 工作流集成指南》的第2部分，请先阅读第1部分

## 目录

- [第五部分：实战案例](#第五部分实战案例)
- [第六部分：最佳实践与优化](#第六部分最佳实践与优化)
- [第七部分：问题排查与调试](#第七部分问题排查与调试)

---

# 第五部分：实战案例

## 5.1 智能表单填写

### 场景描述

**业务需求**: 自动填写客户信息表单，AI 根据客户画像生成个性化内容

**传统流程**:
```
1. 人工打开客户管理系统
2. 逐个查看客户信息
3. 人工编写个性化问候语
4. 复制粘贴到表单
5. 提交
平均耗时: 5 分钟/客户
```

**自动化流程**:
```
1. RPA 读取客户列表
2. 逐个打开客户详情页
3. 提取客户信息 (姓名、行业、历史订单等)
4. 调用 Dify AI 生成个性化内容
5. RPA 填写表单并提交
平均耗时: 10 秒/客户
```

---

### 实现代码

#### Dify 工作流设计

```
工作流名称: "客户问候语生成"

输入参数:
  - customer_name: 客户姓名
  - industry: 所属行业
  - last_order_date: 最后订单日期
  - vip_level: VIP 等级

节点流程:
  1. [LLM 节点] 生成问候语
     提示词:
     """
     你是一位专业的客户关系经理。
     客户信息:
     - 姓名: {{customer_name}}
     - 行业: {{industry}}
     - 最后订单: {{last_order_date}}
     - VIP 等级: {{vip_level}}

     请生成一段个性化的问候语，要求:
     1. 称呼客户姓名
     2. 提及客户行业特点
     3. 如果是 VIP 客户，表达感谢
     4. 长度 50-80 字
     """

  2. [条件判断] 是否 VIP？
     判断: {{vip_level}} >= 3

  3a. [工具调用] 查询专属优惠
      API: /api/vip-offers?customer_id={{customer_id}}

  3b. [文本节点] 标准结束语
      "感谢您的支持！"

  4. [输出节点] 合并结果
     输出:
       - greeting: 问候语
       - offer: 优惠信息 (可选)
```

---

#### 影刀 RPA 流程

```python
# main_flow.py - 影刀 RPA 主流程

import xbot
from xbot import print, sleep
import RPA  # 导入 RPA.py 模块

def main(args):
    """主流程: 批量填写客户表单"""

    # 1. 读取客户列表 (从 Excel)
    excel = xbot.excel.open_excel("客户列表.xlsx")
    customers = excel.read_range(
        sheet="Sheet1",
        start_cell="A2",  # 跳过标题行
        end_cell="E100"
    )
    excel.close()

    print(f"共 {len(customers)} 位客户待处理")

    # 2. 打开浏览器
    browser = xbot.web.create_browser(
        browser_type="chrome",
        url="https://crm.example.com/customer-form"
    )

    # 等待页面加载
    browser.wait_element_appear("#customer-name", timeout=10)

    # 3. 逐个处理客户
    success_count = 0
    fail_count = 0

    for index, customer in enumerate(customers, start=1):
        print(f"\n处理第 {index}/{len(customers)} 位客户")

        try:
            # 提取客户信息
            customer_name = customer[0]
            industry = customer[1]
            last_order_date = customer[2]
            vip_level = int(customer[3])
            customer_id = customer[4]

            print(f"客户: {customer_name} | 行业: {industry} | VIP: {vip_level}")

            # 4. 调用 Dify AI 生成内容
            dify_input = {
                "query": "生成问候语",
                "customer_name": customer_name,
                "industry": industry,
                "last_order_date": last_order_date,
                "vip_level": vip_level,
                "customer_id": customer_id
            }

            ai_result = RPA.run_dify_workflow(dify_input)

            if ai_result is None:
                print(f"× AI 调用失败，跳过该客户")
                fail_count += 1
                continue

            greeting = ai_result.get("answer", "")
            offer = ai_result.get("offer", "")

            print(f"AI 生成内容: {greeting[:50]}...")

            # 5. 填写表单
            # 客户姓名
            name_input = browser.find_element("#customer-name")
            name_input.clear()
            name_input.input_text(customer_name)

            # 问候语
            greeting_textarea = browser.find_element("#greeting")
            greeting_textarea.clear()
            greeting_textarea.input_text(greeting)

            # 优惠信息 (如果有)
            if offer:
                offer_input = browser.find_element("#offer")
                offer_input.clear()
                offer_input.input_text(offer)

            # 6. 提交表单
            submit_button = browser.find_element("#submit-btn")
            submit_button.click()

            # 等待提交成功
            sleep(2)

            # 检查是否成功 (查找成功提示)
            success_msg = browser.find_element("#success-message")
            if success_msg:
                print(f"✓ 提交成功")
                success_count += 1
            else:
                print(f"× 提交失败")
                fail_count += 1

            # 重新加载表单页面 (准备下一个客户)
            browser.navigate("https://crm.example.com/customer-form")
            browser.wait_element_appear("#customer-name", timeout=10)

        except Exception as e:
            print(f"× 处理出错: {e}")
            fail_count += 1
            continue

    # 7. 统计结果
    print("\n" + "=" * 50)
    print("执行完成")
    print(f"成功: {success_count} | 失败: {fail_count}")
    print("=" * 50)

    # 8. 关闭浏览器
    browser.close()
```

---

### 优化点

```python
# 优化 1: 并发处理 (多开浏览器窗口)
from concurrent.futures import ThreadPoolExecutor

def process_customer_batch(customers_batch, browser_instance):
    """单个浏览器处理一批客户"""
    for customer in customers_batch:
        # 处理逻辑...
        pass

# 分成 3 批并发处理
with ThreadPoolExecutor(max_workers=3) as executor:
    batch_size = len(customers) // 3
    futures = []

    for i in range(3):
        batch = customers[i*batch_size : (i+1)*batch_size]
        browser = xbot.web.create_browser(...)
        future = executor.submit(process_customer_batch, batch, browser)
        futures.append(future)

    # 等待所有任务完成
    for future in futures:
        future.result()

# 效果: 3x 加速
```

---

## 5.2 发票自动识别与录入

### 场景描述

**业务需求**: 自动处理邮件中的发票附件，识别信息并录入财务系统

**流程图**:
```
监控邮箱
  ↓
发现新邮件 (主题含"发票")
  ↓
下载 PDF 附件
  ↓
OCR 识别发票信息
  ↓
调用 Dify AI 校验 + 分类
  ↓
录入财务系统
  ↓
回复确认邮件
```

---

### 实现代码

#### Dify 工作流: "发票信息提取与校验"

```
输入:
  - ocr_result: OCR 识别的原始文本
  - invoice_image_url: 发票图片 URL (可选)

节点:
  1. [LLM 节点] 信息提取
     提示词:
     """
     从以下 OCR 结果中提取发票信息:
     {{ocr_result}}

     请提取:
     - 发票号码
     - 开票日期
     - 金额 (大写和小写)
     - 销售方名称
     - 购买方名称
     - 税额

     输出 JSON 格式
     """

  2. [代码节点] 金额校验
     Python:
     ```python
     def main(invoice_data):
         # 校验大小写金额是否一致
         amount_num = invoice_data['amount_number']
         amount_cn = invoice_data['amount_chinese']

         # 转换为数字比较
         if abs(amount_num - cn_to_number(amount_cn)) > 0.01:
             return {"valid": False, "reason": "金额不一致"}

         return {"valid": True}
     ```

  3. [条件判断] 是否通过校验？

  4a. [HTTP 调用] 验真接口
      API: 国家税务总局发票查验接口

  4b. [输出] 校验失败，需人工审核

  5. [输出] 提取结果 + 校验状态
```

---

#### 影刀 RPA 流程

```python
# invoice_processing.py

import xbot
from xbot import print, sleep
import RPA
import os
from datetime import datetime

def main(args):
    """发票自动处理流程"""

    # 1. 连接邮箱
    email_client = xbot.email.connect(
        email_type="outlook",  # outlook/gmail
        account="finance@company.com",
        password="password"
    )

    print("✓ 邮箱连接成功")

    # 2. 查询未读邮件 (主题包含"发票")
    unread_emails = email_client.search_emails(
        folder="收件箱",
        filter_subject="发票",
        only_unread=True
    )

    print(f"发现 {len(unread_emails)} 封待处理邮件")

    # 3. 逐个处理
    for email_msg in unread_emails:
        print(f"\n处理邮件: {email_msg.subject}")

        try:
            # 4. 下载附件 (PDF/图片)
            attachments = email_msg.get_attachments()

            for attachment in attachments:
                filename = attachment.filename

                # 仅处理发票文件
                if not any(ext in filename.lower() for ext in ['.pdf', '.png', '.jpg']):
                    print(f"  跳过非发票文件: {filename}")
                    continue

                print(f"  处理附件: {filename}")

                # 保存到临时目录
                temp_path = f"./temp/{filename}"
                attachment.save(temp_path)

                # 5. OCR 识别
                if filename.endswith('.pdf'):
                    # PDF 转图片
                    images = xbot.pdf.to_images(temp_path)
                    ocr_text = xbot.ocr.recognize(images[0])
                else:
                    ocr_text = xbot.ocr.recognize(temp_path)

                print(f"  OCR 完成: {len(ocr_text)} 字符")

                # 6. 调用 Dify AI 提取信息
                dify_input = {
                    "query": "提取发票信息",
                    "ocr_result": ocr_text,
                    "invoice_image_url": temp_path
                }

                ai_result = RPA.run_dify_workflow(dify_input)

                if ai_result is None:
                    print("  × AI 提取失败")
                    continue

                # 7. 解析提取结果
                invoice_data = ai_result.get("invoice_data", {})
                validation = ai_result.get("validation", {})

                print(f"  发票号: {invoice_data.get('invoice_number')}")
                print(f"  金额: {invoice_data.get('amount_number')}")
                print(f"  校验: {'通过' if validation.get('valid') else '失败'}")

                # 8. 录入财务系统
                if validation.get("valid"):
                    success = record_to_finance_system(invoice_data)

                    if success:
                        print("  ✓ 录入成功")

                        # 9. 回复确认邮件
                        email_client.reply(
                            email_msg,
                            subject="Re: 发票已收到",
                            body=f"""
                            您好，

                            您的发票已成功录入系统:
                            - 发票号: {invoice_data['invoice_number']}
                            - 金额: {invoice_data['amount_number']} 元
                            - 处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

                            感谢您的配合！

                            财务部
                            """
                        )
                    else:
                        print("  × 录入失败")
                else:
                    print("  ⚠️  校验未通过，转人工审核")
                    # 发送提醒邮件给财务人员
                    send_alert_email(invoice_data, validation['reason'])

                # 10. 标记邮件为已读
                email_msg.mark_as_read()

                # 11. 清理临时文件
                os.remove(temp_path)

        except Exception as e:
            print(f"  × 处理出错: {e}")
            continue

    # 12. 断开邮箱连接
    email_client.disconnect()

    print("\n所有邮件处理完成")

def record_to_finance_system(invoice_data):
    """录入财务系统"""
    # 模拟 API 调用
    import requests

    api_url = "https://finance.company.com/api/invoices"
    headers = {"Authorization": "Bearer xxx"}

    response = requests.post(api_url, json=invoice_data, headers=headers)

    return response.status_code == 200

def send_alert_email(invoice_data, reason):
    """发送提醒邮件"""
    # 实现邮件发送逻辑
    pass
```

---

## 5.3 客服工单自动处理

### 场景描述

**业务需求**: 自动分类和回复客服工单

**分类规则**:
```
1. 简单问题 → AI 自动回复
   - 物流查询
   - 账户问题
   - 常见问答

2. 复杂问题 → 转人工 + AI 提供参考答案
   - 退款申请
   - 投诉建议
   - 技术故障
```

---

### 实现代码

#### Dify 工作流: "工单分类与回复"

```
输入:
  - ticket_content: 工单内容
  - customer_history: 客户历史 (可选)

节点:
  1. [LLM 节点] 问题分类
     提示词:
     """
     分析以下客服工单:
     {{ticket_content}}

     分类:
     1. 物流查询
     2. 账户问题
     3. 退款申请
     4. 投诉建议
     5. 技术故障
     6. 其他

     输出:
     {
       "category": "分类名称",
       "urgency": "高/中/低",
       "can_auto_reply": true/false
     }
     """

  2. [条件判断] 能否自动回复？

  3a. [LLM 节点] 生成自动回复
      提示词:
      """
      作为客服人员，回复以下工单:
      {{ticket_content}}

      要求:
      - 礼貌专业
      - 解决问题或提供指引
      - 100-200 字
      """

  3b. [LLM 节点] 生成参考答案
      提示词:
      """
      为客服人员提供参考答案...
      """

  4. [知识库检索] 查询相关文档
     查询: {{ticket_content}}
     Top-K: 3

  5. [输出] 分类结果 + 回复/参考答案
```

---

#### 影刀 RPA 流程

```python
# ticket_automation.py

import xbot
from xbot import print, sleep
import RPA

def main(args):
    """工单自动处理"""

    # 1. 打开工单系统
    browser = xbot.web.create_browser(
        browser_type="chrome",
        url="https://support.company.com/tickets"
    )

    # 登录 (假设已保存凭据)
    browser.wait_element_appear("#username", timeout=10)
    # ...登录逻辑

    # 2. 查询待处理工单
    browser.navigate("https://support.company.com/tickets?status=open")
    sleep(2)

    # 获取工单列表
    ticket_elements = browser.find_elements(".ticket-item")

    print(f"待处理工单: {len(ticket_elements)} 个")

    # 3. 逐个处理
    for index, ticket_elem in enumerate(ticket_elements, start=1):
        print(f"\n处理工单 {index}/{len(ticket_elements)}")

        try:
            # 点击工单
            ticket_elem.click()
            sleep(1)

            # 提取工单信息
            ticket_id = browser.find_element("#ticket-id").get_text()
            customer_name = browser.find_element("#customer-name").get_text()
            ticket_content = browser.find_element("#ticket-content").get_text()

            print(f"工单 {ticket_id} | 客户: {customer_name}")
            print(f"内容: {ticket_content[:50]}...")

            # 4. 调用 Dify AI 分类
            dify_input = {
                "query": "分类工单",
                "ticket_content": ticket_content,
                "customer_name": customer_name
            }

            ai_result = RPA.run_dify_workflow(dify_input)

            if ai_result is None:
                print("× AI 调用失败，跳过")
                browser.find_element("#back-btn").click()
                continue

            # 5. 解析结果
            category = ai_result.get("category", "未知")
            urgency = ai_result.get("urgency", "中")
            can_auto_reply = ai_result.get("can_auto_reply", False)
            reply_text = ai_result.get("reply", "")

            print(f"分类: {category} | 紧急度: {urgency} | 自动回复: {can_auto_reply}")

            # 6. 执行操作
            if can_auto_reply:
                # 自动回复
                reply_textarea = browser.find_element("#reply-textarea")
                reply_textarea.input_text(reply_text)

                # 提交回复
                submit_btn = browser.find_element("#submit-reply")
                submit_btn.click()

                # 关闭工单
                close_btn = browser.find_element("#close-ticket")
                close_btn.click()

                print("✓ 自动回复并关闭")

            else:
                # 转人工 + 添加备注
                assign_btn = browser.find_element("#assign-to-agent")
                assign_btn.click()

                # 选择合适的客服人员 (根据分类)
                agent_dropdown = browser.find_element("#agent-select")
                agent_dropdown.select_option(get_agent_by_category(category))

                # 添加 AI 参考答案作为备注
                notes_textarea = browser.find_element("#notes")
                notes_textarea.input_text(f"AI 参考答案:\n{reply_text}")

                # 提交
                submit_btn = browser.find_element("#submit-assignment")
                submit_btn.click()

                print("✓ 已转人工处理")

            # 返回列表
            browser.find_element("#back-to-list").click()
            sleep(1)

        except Exception as e:
            print(f"× 处理出错: {e}")
            continue

    # 7. 关闭浏览器
    browser.close()

    print("\n工单处理完成")

def get_agent_by_category(category):
    """根据分类选择客服人员"""
    mapping = {
        "物流查询": "物流组",
        "退款申请": "财务组",
        "技术故障": "技术组",
        "投诉建议": "主管"
    }
    return mapping.get(category, "通用组")
```

---

## 5.4 Excel 数据智能分析

### 场景描述

**业务需求**: 自动分析销售数据并生成报告

**流程**:
```
读取 Excel 数据
  ↓
调用 Dify AI 分析
  ↓
生成分析报告 (Markdown)
  ↓
转换为 PDF
  ↓
发送邮件给管理层
```

---

### 实现代码

```python
# sales_analysis.py

import xbot
from xbot import print, sleep
import RPA
import json

def main(args):
    """销售数据自动分析"""

    # 1. 读取 Excel
    excel = xbot.excel.open_excel("销售数据.xlsx")

    # 读取数据
    data = excel.read_range(
        sheet="月度销售",
        start_cell="A1",
        end_cell="F100"
    )

    excel.close()

    # 2. 数据预处理
    headers = data[0]  # 标题行
    rows = data[1:]    # 数据行

    # 转换为字典列表
    sales_data = []
    for row in rows:
        sales_data.append({
            headers[i]: row[i] for i in range(len(headers))
        })

    # 计算统计信息
    total_sales = sum(float(item['销售额']) for item in sales_data)
    top_products = sorted(
        sales_data,
        key=lambda x: float(x['销售额']),
        reverse=True
    )[:5]

    print(f"总销售额: {total_sales:,.2f} 元")
    print(f"Top 5 产品: {[p['产品名称'] for p in top_products]}")

    # 3. 调用 Dify AI 生成分析
    dify_input = {
        "query": "分析销售数据",
        "total_sales": str(total_sales),
        "data_summary": json.dumps(sales_data[:20], ensure_ascii=False),  # 样本数据
        "top_products": json.dumps(top_products, ensure_ascii=False)
    }

    ai_result = RPA.run_dify_workflow(dify_input)

    if ai_result is None:
        print("× AI 分析失败")
        return

    analysis_report = ai_result.get("answer", "")

    print("✓ AI 分析完成")
    print(f"报告预览:\n{analysis_report[:200]}...")

    # 4. 生成报告文件
    report_filename = f"销售分析报告_{xbot.datetime.now().strftime('%Y%m%d')}.md"
    xbot.file.write_text(report_filename, analysis_report)

    # 5. 转换为 PDF (可选)
    pdf_filename = report_filename.replace('.md', '.pdf')
    convert_md_to_pdf(report_filename, pdf_filename)

    # 6. 发送邮件
    send_report_email(pdf_filename)

    print("\n✓ 报告已发送")

def convert_md_to_pdf(md_file, pdf_file):
    """Markdown 转 PDF"""
    # 使用第三方工具 (如 pandoc)
    import subprocess
    subprocess.run([
        'pandoc',
        md_file,
        '-o', pdf_file,
        '--pdf-engine=xelatex'
    ])

def send_report_email(pdf_file):
    """发送报告邮件"""
    email_client = xbot.email.connect(...)

    email_client.send_email(
        to=["manager@company.com"],
        subject="月度销售分析报告",
        body="附件为本月销售分析报告，请查阅。",
        attachments=[pdf_file]
    )

    email_client.disconnect()
```

---

# 第六部分：最佳实践与优化

## 6.1 性能优化

### 6.1.1 批量处理优化

```python
# ❌ 低效: 逐个调用 AI
for item in items:
    result = RPA.run_dify_workflow({"query": item})
    process(result)

# ✅ 高效: 批量调用
batch_input = {
    "query": "批量处理",
    "items": json.dumps(items)
}
result = RPA.run_dify_workflow(batch_input)
```

---

### 6.1.2 缓存策略

```python
# 缓存常见问题的答案
import pickle
import hashlib

class DifyCache:
    def __init__(self, cache_file="dify_cache.pkl"):
        self.cache_file = cache_file
        self.cache = self.load_cache()

    def load_cache(self):
        try:
            with open(self.cache_file, 'rb') as f:
                return pickle.load(f)
        except:
            return {}

    def save_cache(self):
        with open(self.cache_file, 'wb') as f:
            pickle.dump(self.cache, f)

    def get_cache_key(self, input_data):
        # 生成输入的哈希值
        input_str = json.dumps(input_data, sort_keys=True)
        return hashlib.md5(input_str.encode()).hexdigest()

    def get(self, input_data):
        key = self.get_cache_key(input_data)
        return self.cache.get(key)

    def set(self, input_data, result):
        key = self.get_cache_key(input_data)
        self.cache[key] = result
        self.save_cache()

# 使用
cache = DifyCache()

def run_dify_with_cache(input_data):
    # 先查缓存
    cached = cache.get(input_data)
    if cached:
        print("✓ 使用缓存结果")
        return cached

    # 缓存未命中，调用 AI
    result = RPA.run_dify_workflow(input_data)
    cache.set(input_data, result)
    return result
```

---

### 6.1.3 连接池

```python
# 复用浏览器实例
class BrowserPool:
    def __init__(self, size=3):
        self.pool = [
            xbot.web.create_browser("chrome")
            for _ in range(size)
        ]
        self.available = self.pool.copy()

    def acquire(self):
        if not self.available:
            raise Exception("浏览器池已满")
        return self.available.pop()

    def release(self, browser):
        self.available.append(browser)

    def cleanup(self):
        for browser in self.pool:
            browser.close()

# 使用
pool = BrowserPool(size=3)

for task in tasks:
    browser = pool.acquire()
    try:
        process_task(browser, task)
    finally:
        pool.release(browser)

pool.cleanup()
```

---

## 6.2 可靠性保障

### 6.2.1 幂等性设计

```python
# 确保重复执行不会产生副作用

def submit_order_idempotent(order_id, order_data):
    """幂等的订单提交"""

    # 1. 检查订单是否已存在
    if check_order_exists(order_id):
        print(f"订单 {order_id} 已存在，跳过")
        return {"status": "already_exists"}

    # 2. 提交订单
    result = submit_order(order_data)

    # 3. 记录订单 ID (防止重复)
    record_order_id(order_id)

    return result
```

---

### 6.2.2 事务管理

```python
# 数据一致性保障

def transfer_money_with_transaction(from_account, to_account, amount):
    """带事务的转账操作"""

    db = xbot.database.connect(...)

    try:
        # 开启事务
        db.begin_transaction()

        # 操作 1: 扣款
        db.execute_update(
            f"UPDATE accounts SET balance = balance - {amount} WHERE id = {from_account}"
        )

        # 操作 2: 加款
        db.execute_update(
            f"UPDATE accounts SET balance = balance + {amount} WHERE id = {to_account}"
        )

        # 提交事务
        db.commit()
        print("✓ 转账成功")

    except Exception as e:
        # 回滚事务
        db.rollback()
        print(f"× 转账失败: {e}")

    finally:
        db.close()
```

---

### 6.2.3 断点续传

```python
# 支持中断后继续执行

class ProgressTracker:
    def __init__(self, progress_file="progress.json"):
        self.progress_file = progress_file
        self.progress = self.load_progress()

    def load_progress(self):
        try:
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        except:
            return {"processed": [], "last_index": 0}

    def save_progress(self):
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f)

    def is_processed(self, item_id):
        return item_id in self.progress["processed"]

    def mark_processed(self, item_id, index):
        self.progress["processed"].append(item_id)
        self.progress["last_index"] = index
        self.save_progress()

# 使用
tracker = ProgressTracker()

for index, item in enumerate(items):
    # 跳过已处理的项
    if tracker.is_processed(item['id']):
        print(f"跳过已处理: {item['id']}")
        continue

    # 处理
    process(item)

    # 记录进度
    tracker.mark_processed(item['id'], index)

print("处理完成")
```

---

## 6.3 安全性

### 6.3.1 凭据管理

```python
# ❌ 硬编码密码 (危险)
password = "admin123"

# ✅ 使用环境变量
import os
password = os.getenv("SYSTEM_PASSWORD")

# ✅ 使用影刀加密存储
password = glv.get_encrypted_variable("system_password")

# ✅ 使用密钥管理服务
from azure.keyvault.secrets import SecretClient
client = SecretClient(...)
password = client.get_secret("system-password").value
```

---

### 6.3.2 输入校验

```python
def run_dify_workflow_safe(input_data):
    """带输入校验的版本"""

    # 1. 类型校验
    if not isinstance(input_data, dict):
        raise TypeError("输入必须是字典")

    # 2. 必需参数校验
    if "query" not in input_data:
        raise ValueError("缺少 query 参数")

    # 3. 长度校验
    if len(input_data["query"]) > 10000:
        raise ValueError("query 长度超限 (最大 10000 字符)")

    # 4. SQL 注入防护 (如果参数用于数据库查询)
    for key, value in input_data.items():
        if contains_sql_injection(value):
            raise ValueError(f"检测到 SQL 注入: {key}")

    # 5. XSS 防护 (如果参数用于 Web 展示)
    for key, value in input_data.items():
        input_data[key] = escape_html(value)

    # 调用 API
    return RPA.run_dify_workflow(input_data)

def contains_sql_injection(text):
    """简单的 SQL 注入检测"""
    dangerous_patterns = [
        "'; DROP TABLE",
        "'; DELETE FROM",
        "UNION SELECT",
        "' OR '1'='1"
    ]
    text_upper = str(text).upper()
    return any(pattern in text_upper for pattern in dangerous_patterns)

def escape_html(text):
    """HTML 转义"""
    import html
    return html.escape(str(text))
```

---

# 第七部分：问题排查与调试

## 7.1 常见问题

### 问题 1: API 调用失败 (401 Unauthorized)

**原因**: API Key 无效或过期

**排查步骤**:
```python
# 1. 检查 API Key 格式
api_key = "app-xxxxx"
if not api_key.startswith("app-"):
    print("× API Key 格式错误")

# 2. 测试 API Key
def test_api_key(api_key):
    url = "https://api.dify.ai/v1/info"  # 测试端点
    headers = {'Authorization': f'Bearer {api_key}'}

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        print("✓ API Key 有效")
        return True
    elif response.status_code == 401:
        print("× API Key 无效")
        return False
    else:
        print(f"? 未知状态: {response.status_code}")
        return False

test_api_key(api_key)

# 3. 重新生成 API Key
# 在 Dify 控制台 → 应用设置 → API Key → 重新生成
```

---

### 问题 2: 响应超时

**原因**: 工作流执行时间过长或网络问题

**解决方案**:
```python
# 1. 增加超时时间
response = requests.post(
    url,
    headers=headers,
    json=data,
    timeout=120  # 从 60 秒增加到 120 秒
)

# 2. 使用流式响应 (适合长时间任务)
data['response_mode'] = 'streaming'

response = requests.post(url, headers=headers, json=data, stream=True)

for line in response.iter_lines():
    if line:
        # 实时接收数据，避免超时
        process_line(line)

# 3. 分解工作流 (拆分为多个步骤)
# 步骤 1: 数据预处理
result1 = call_dify({"query": "预处理", "data": data})

# 步骤 2: 分析
result2 = call_dify({"query": "分析", "preprocessed": result1})
```

---

### 问题 3: 返回结果格式不一致

**原因**: Dify 工作流配置变更

**解决方案**:
```python
def parse_dify_result_robust(result):
    """健壮的结果解析"""

    # 尝试多种可能的结构
    # 情况 1: result['data']['outputs']['answer']
    try:
        return result['data']['outputs']['answer']
    except (KeyError, TypeError):
        pass

    # 情况 2: result['data']['answer']
    try:
        return result['data']['answer']
    except (KeyError, TypeError):
        pass

    # 情况 3: result['answer']
    try:
        return result['answer']
    except (KeyError, TypeError):
        pass

    # 情况 4: result 本身就是字符串
    if isinstance(result, str):
        return result

    # 都失败: 返回整个结果
    print("⚠️  无法解析结果，返回原始数据")
    return result
```

---

## 7.2 调试技巧

### 7.2.1 详细日志

```python
import logging

# 配置详细日志
logging.basicConfig(
    level=logging.DEBUG,  # DEBUG 级别
    format='%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s',
    handlers=[
        logging.FileHandler('rpa_debug.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def run_dify_workflow_debug(input_data):
    """带详细日志的版本"""

    logger.info("=" * 50)
    logger.info("开始调用 Dify API")
    logger.debug(f"输入参数: {json.dumps(input_data, ensure_ascii=False, indent=2)}")

    # 构造请求
    data = {...}
    logger.debug(f"请求体: {json.dumps(data, ensure_ascii=False, indent=2)}")

    # 发送请求
    logger.info(f"发送 POST 请求: {url}")
    response = requests.post(url, headers=headers, json=data)

    logger.info(f"响应状态码: {response.status_code}")
    logger.debug(f"响应头: {dict(response.headers)}")
    logger.debug(f"响应体: {response.text}")

    # 解析响应
    result = response.json()
    logger.debug(f"解析结果: {json.dumps(result, ensure_ascii=False, indent=2)}")

    logger.info("调用完成")
    logger.info("=" * 50)

    return result
```

---

### 7.2.2 单步调试

```python
# 在影刀 RPA 中使用断点

def main(args):
    # 步骤 1
    xbot.debug.breakpoint()  # 设置断点
    data = extract_data()

    # 步骤 2
    xbot.debug.breakpoint()
    result = RPA.run_dify_workflow(data)

    # 步骤 3
    xbot.debug.breakpoint()
    submit_result(result)

# 或使用 Python 原生断点
import pdb; pdb.set_trace()
```

---

### 7.2.3 Mock 测试

```python
# 不调用真实 API，使用模拟数据测试

class MockDifyAPI:
    """模拟 Dify API"""

    def run_workflow(self, input_data):
        # 返回固定的模拟数据
        return {
            "answer": "这是模拟回复",
            "category": "测试分类"
        }

# 使用
if os.getenv("DEBUG_MODE") == "true":
    # 调试模式: 使用 Mock
    mock_api = MockDifyAPI()
    result = mock_api.run_workflow(input_data)
else:
    # 生产模式: 调用真实 API
    result = RPA.run_dify_workflow(input_data)
```

---

## 7.3 监控与告警

```python
# 监控 RPA 执行状态

import time
from datetime import datetime

class RPAMonitor:
    def __init__(self):
        self.metrics = {
            "total_runs": 0,
            "success_count": 0,
            "fail_count": 0,
            "total_time": 0,
            "errors": []
        }

    def record_execution(self, success, duration, error=None):
        self.metrics["total_runs"] += 1
        self.metrics["total_time"] += duration

        if success:
            self.metrics["success_count"] += 1
        else:
            self.metrics["fail_count"] += 1
            self.metrics["errors"].append({
                "time": datetime.now().isoformat(),
                "error": str(error)
            })

    def get_stats(self):
        success_rate = 0
        if self.metrics["total_runs"] > 0:
            success_rate = self.metrics["success_count"] / self.metrics["total_runs"]

        avg_time = 0
        if self.metrics["total_runs"] > 0:
            avg_time = self.metrics["total_time"] / self.metrics["total_runs"]

        return {
            "success_rate": f"{success_rate*100:.2f}%",
            "average_time": f"{avg_time:.2f}s",
            "total_runs": self.metrics["total_runs"],
            "recent_errors": self.metrics["errors"][-5:]  # 最近 5 个错误
        }

    def send_alert_if_needed(self):
        """检查是否需要告警"""
        stats = self.get_stats()

        # 告警条件
        if float(stats["success_rate"].rstrip('%')) < 80:
            send_alert(f"成功率过低: {stats['success_rate']}")

        if self.metrics["fail_count"] >= 5:
            send_alert(f"连续失败 {self.metrics['fail_count']} 次")

# 使用
monitor = RPAMonitor()

for task in tasks:
    start_time = time.time()
    try:
        process_task(task)
        duration = time.time() - start_time
        monitor.record_execution(success=True, duration=duration)
    except Exception as e:
        duration = time.time() - start_time
        monitor.record_execution(success=False, duration=duration, error=e)

# 输出统计
print(json.dumps(monitor.get_stats(), ensure_ascii=False, indent=2))

# 检查告警
monitor.send_alert_if_needed()
```

---

## 总结

本文档详细介绍了 RPA 与 Dify AI 工作流的集成方案，包括：

✅ **理论基础**: RPA 概念、影刀平台、Dify 工作流
✅ **核心实现**: API 调用、错误处理、日志记录
✅ **实战案例**: 4 个完整的业务场景实现
✅ **最佳实践**: 性能优化、可靠性保障、安全性
✅ **问题排查**: 常见问题、调试技巧、监控告警

通过 RPA + AI 的结合，可以实现：
- **效率提升**: 10-50 倍
- **准确率提升**: 人工 95% → RPA+AI 99%+
- **成本节省**: 60-80% 人力成本

---

**文档版本**: v1.0 (Complete)
**最后更新**: 2025-12-15
**基于源文件**: RPA.py (07_agent_memory_and_advanced_capabilities/foundations)