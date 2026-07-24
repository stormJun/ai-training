<!-- Converted from p24-LLMRouterChain.ipynb -->

```python
##  一个售前和售后的 langchain  LLMRouterChain 模版

from langchain.chains.router import MultiPromptChain
from langchain_community.llms import Tongyi
from langchain.chains import ConversationChain
from langchain.chains.llm import LLMChain
from langchain.prompts import PromptTemplate
from langchain.chains.router.llm_router import (
    LLMRouterChain,
    RouterOutputParser
)
from langchain.chains.router.multi_prompt_prompt import (
    MULTI_PROMPT_ROUTER_TEMPLATE
)

# 售前咨询模板
presales_prompt_tpl = PromptTemplate.from_template(
    '你是一位专业的售前顾问，擅长产品介绍、方案推荐和商务咨询。'
    '你需要热情、专业地回答客户的产品咨询、价格询问、功能介绍等售前问题。'
    '请使用中文帮我解答下列售前咨询问题：\n{input}'
)

# 售后服务模板
aftersales_prompt_tpl = PromptTemplate.from_template(
    '你是一位耐心的售后服务专员，擅长解决客户的使用问题、技术支持和投诉处理。'
    '你需要耐心、细致地帮助客户解决产品使用中遇到的问题，提供技术支持和服务指导。'
    '请使用中文帮我解答下列售后服务问题：\n{input}'
)

# 创建模板信息列表
prompt_infos = [
    {
        'name': 'presales',
        'description': '用于处理售前咨询，包括产品介绍、价格询问、功能说明、方案推荐等',
        'prompt_template': presales_prompt_tpl,
    },
    {
        'name': 'aftersales',
        'description': '用于处理售后服务，包括使用问题、技术支持、故障排除、投诉处理等',
        'prompt_template': aftersales_prompt_tpl,
    },
]

llm = Tongyi(
    temperature=0.1,
)

# 生成键为模板名称、值为Chain的字典
destination_chains = {}
for p_info in prompt_infos:
    name = p_info['name']
    prompt = p_info['prompt_template']
    chain = LLMChain(llm=llm, prompt=prompt)
    destination_chains[name] = chain

# 将模板名称和模板描述通过MULTI_PROMPT_ROUTER_TEMPLATE生成模板
destinations = [f'{p["name"]}: {p["description"]}'
                for p in prompt_infos]
destinations_str = "\n".join(destinations)

router_template = MULTI_PROMPT_ROUTER_TEMPLATE.format(
    destinations=destinations_str
)
router_prompt = PromptTemplate(
    template=router_template,
    input_variables=['input'],
    output_parser=RouterOutputParser(),
)
router_chain = LLMRouterChain.from_llm(llm, router_prompt)

# 这里创建了一个default_chain
# 为了防止提的问题类型并没有包含在prompt_infos中
default_chain = ConversationChain(llm=llm, output_key='text')
chain = MultiPromptChain(
    router_chain=router_chain,
    destination_chains=destination_chains,
    default_chain=default_chain,
    verbose=True,
)

# 测试售前咨询问题
print("=== 售前咨询测试 ===")
print(chain.run("你们的产品有什么功能？价格是多少？"))

print("\n=== 售后服务测试 ===")
print(chain.run("我的产品出现故障了，无法正常启动，该怎么办？"))

print("\n=== 其他问题测试 ===")
print(chain.run("今天天气怎么样？"))
```

输出：

```text
C:\Users\Administrator\AppData\Local\Temp\ipykernel_21616\30894139.py:51: LangChainDeprecationWarning: The class `LLMChain` was deprecated in LangChain 0.1.17 and will be removed in 1.0. Use :meth:`~RunnableSequence, e.g., `prompt | llm`` instead.
  chain = LLMChain(llm=llm, prompt=prompt)
C:\Users\Administrator\AppData\Local\Temp\ipykernel_21616\30894139.py:71: LangChainDeprecationWarning: The class `ConversationChain` was deprecated in LangChain 0.2.7 and will be removed in 1.0. Use :class:`~langchain_core.runnables.history.RunnableWithMessageHistory` instead.
  default_chain = ConversationChain(llm=llm, output_key='text')
d:\software\miniconda3\envs\MLOps\Lib\site-packages\pydantic\main.py:253: LangChainDeprecationWarning: Please see the migration guide at: https://python.langchain.com/docs/versions/migrating_memory/
  validated_self = self.__pydantic_validator__.validate_python(data, self_instance=self)
C:\Users\Administrator\AppData\Local\Temp\ipykernel_21616\30894139.py:72: LangChainDeprecationWarning: Please see migration guide here for recommended implementation: https://python.langchain.com/docs/versions/migrating_chains/multi_prompt_chain/
  chain = MultiPromptChain(
C:\Users\Administrator\AppData\Local\Temp\ipykernel_21616\30894139.py:81: LangChainDeprecationWarning: The method `Chain.run` was deprecated in langchain 0.1.0 and will be removed in 1.0. Use :meth:`~invoke` instead.
  print(chain.run("你们的产品有什么功能？价格是多少？"))
=== 售前咨询测试 ===


[1m> Entering new MultiPromptChain chain...[0m
presales: {'input': '你们的产品有什么功能？价格是多少？'}
[1m> Finished chain.[0m
您好，感谢您对我们产品的关注！为了更好地为您介绍产品功能和价格信息，能否请您先告知您感兴趣的是哪一类产品或具体的产品名称呢？

我们的产品线覆盖多个领域，包括但不限于：

- 企业级软件解决方案（如CRM、ERP、OA系统等）
- 网络与安全设备
- 数据中心与云计算服务
- 智能办公设备
- 行业定制化解决方案（如教育、医疗、制造等）

不同产品的功能和价格体系差异较大，因此我需要了解您更具体的需求，以便为您提供准确的产品介绍、功能说明及报价方案。

期待您的回复，我将第一时间为您服务！

=== 售后服务测试 ===


[1m> Entering new MultiPromptChain chain...[0m
aftersales: {'input': '我的产品出现故障了，无法正常启动，该怎么办？'}
[1m> Finished chain.[0m
您好，非常抱歉听到您的产品出现了无法正常启动的问题。我是您的售后服务专员，将耐心为您解答并提供帮助。为了更好地判断问题原因并找到解决方案，请您配合我完成以下几步排查：

---

### 一、初步检查（请您逐一确认）：

1. **电源连接是否正常？**
   - 请确认电源线是否插好，插座是否有电（可以尝试插其他电器测试插座）。
   - 如果是使用电池供电的产品，请确认电池是否安装正确、电量是否充足。

2. **开关是否正常开启？**
   - 检查产品开关是否处于“ON”或启动位置，部分设备可能有多个开关（例如主机和显示屏分别有开关）。

3. **是否有指示灯或声音提示？**
   - 产品通电后是否有任何指示灯亮起、风扇转动声或提示音？这些信息对我们判断问题非常关键。

4. **是否有异味、异响或异常发热？**
   - 如果有烧焦味、冒烟、明显发热等现象，请**立即断电**，并避免继续使用，可能存在安全隐患。

---

### 二、尝试以下操作：

- **重启操作：**
  - 拔掉电源线或取出电池，等待10秒后重新连接，尝试再次启动。

- **检查配件或连接线：**
  - 如果产品由多个部件组成（如主机、显示器、外接设备等），请确认所有连接线是否插紧，尝试逐一断开排查是否某部件导致无法启动。

---

### 三、请您提供以下信息以便我们进一步协助：

1. 产品的**品牌和型号**（例如：XX品牌 XX-123型号）
2. 出现问题前是否进行过**软件升级、更换配件或搬运**？
3. 故障发生时的具体情况（例如：突然断电后无法启动？使用过程中自动关机？）
4. 是否有保修卡或购买凭证？购买时间是？

---

### 四、根据情况，我们可能建议：

✅ **如果为简单问题**（如接触不良、误操作）：我们会提供详细操作指导，协助您自行解决。

✅ **如果为硬件故障或需要检测**：我们将为您安排：
- **远程技术支持**（如支持联网检测）
- **就近维修点送修**或**上门服务**（视产品类型和保修政策而定）

---

### 五、温馨提示：

- 若产品在保修期内，请保留好购买凭证，避免自行拆机以免影响保修。
- 若已超出保修期，我们仍可为您提供有偿维修服务。

---

请您将上述信息反馈给我，我会尽快为您制定解决方案。如果您方便的话，也可以发送产品型号和故障现象的照片，这将有助于我们更快定位问题。

期待您的回复！祝您生活愉快！

=== 其他问题测试 ===


[1m> Entering new MultiPromptChain chain...[0m
None: {'input': '今天天气怎么样？'}
[1m> Finished chain.[0m
今天天气怎么样呢？我这边的信息显示，如果你在中国北京的话，今天的天气是晴朗的，气温在20到26摄氏度之间，微风，非常适合外出活动！如果你在别的城市，天气可能会有所不同哦。你所在的城市天气如何呢？
```

```python
# 整合链的语法

from langchain.chains.router import MultiPromptChain
from langchain_community.llms import Tongyi
from langchain.chains import ConversationChain
from langchain.chains.llm import LLMChain
from langchain.prompts import PromptTemplate
from langchain.chains.router.llm_router import (
    LLMRouterChain,
    RouterOutputParser
)
from langchain.chains.router.multi_prompt_prompt import (
    MULTI_PROMPT_ROUTER_TEMPLATE
)
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnablePassthrough

# 初始化LLM
llm = Tongyi(temperature=0.1)

# 售前咨询链 - 使用新式语法
presales_prompt = PromptTemplate.from_template(
    '你是一位专业的售前顾问，擅长产品介绍、方案推荐和商务咨询。'
    '你需要热情、专业地回答客户的产品咨询、价格询问、功能介绍等售前问题。'
    '请使用中文帮我解答下列售前咨询问题：\n{input}'
)
presales_chain = presales_prompt | llm | StrOutputParser()

# 售后服务链 - 使用新式语法
aftersales_prompt = PromptTemplate.from_template(
    '你是一位耐心的售后服务专员，擅长解决客户的使用问题、技术支持和投诉处理。'
    '你需要耐心、细致地帮助客户解决产品使用中遇到的问题，提供技术支持和服务指导。'
    '请使用中文帮我解答下列售后服务问题：\n{input}'
)
aftersales_chain = aftersales_prompt | llm | StrOutputParser()

# 意图识别链 - 使用新式语法
intent_prompt = PromptTemplate.from_template(
    """请分析以下用户问题的意图，判断是售前咨询还是售后服务：

售前咨询：产品介绍、功能说明、价格询问、方案推荐、购买咨询等
售后服务：使用问题、技术支持、故障排除、投诉处理、维修服务等

用户问题：{input}

请只回答"售前"或"售后"，不要添加其他内容。"""
)
intent_chain = intent_prompt | llm | StrOutputParser()

# 创建路由函数
def route_question(input_dict):
    question = input_dict["input"]
    intent = intent_chain.invoke({"input": question})

    print(f"识别意图: {intent.strip()}")

    if "售前" in intent:
        return presales_chain.invoke({"input": question})
    elif "售后" in intent:
        return aftersales_chain.invoke({"input": question})
    else:
        # 默认处理
        default_prompt = PromptTemplate.from_template(
            "我是一个智能助手，很高兴为您服务。请问有什么可以帮助您的吗？\n问题：{input}"
        )
        default_chain = default_prompt | llm | StrOutputParser()
        return default_chain.invoke({"input": question})

# 创建完整的路由链
router_chain = RunnablePassthrough() | RunnableLambda(route_question)

# 方法二：更简洁的条件路由实现
from langchain_core.runnables import RunnableBranch

# 创建条件判断函数
def is_presales(input_dict):
    intent = intent_chain.invoke(input_dict)
    return "售前" in intent

def is_aftersales(input_dict):
    intent = intent_chain.invoke(input_dict)
    return "售后" in intent

# 使用 RunnableBranch 创建条件路由
branch_chain = RunnableBranch(
    (is_presales, presales_chain),
    (is_aftersales, aftersales_chain),
    # 默认链
    PromptTemplate.from_template("我是智能助手，请问有什么可以帮助您的？\n{input}") | llm | StrOutputParser()
)

# 测试代码
if __name__ == "__main__":
    print("=== 方法一：自定义路由函数 ===")

    # 测试售前问题
    print("\n--- 售前咨询测试 ---")
    result1 = router_chain.invoke({"input": "你们的产品有什么功能？价格是多少？"})
    print(f"回答: {result1}")

    # 测试售后问题
    print("\n--- 售后服务测试 ---")
    result2 = router_chain.invoke({"input": "我的产品出现故障了，无法正常启动，该怎么办？"})
    print(f"回答: {result2}")

    print("\n=== 方法二：RunnableBranch 条件路由 ===")

    # 测试售前问题
    print("\n--- 售前咨询测试 ---")
    result3 = branch_chain.invoke({"input": "我想了解一下你们的服务套餐和收费标准"})
    print(f"回答: {result3}")

    # 测试售后问题
    print("\n--- 售后服务测试 ---")
    result4 = branch_chain.invoke({"input": "产品使用过程中遇到了错误提示，需要技术支持"})
    print(f"回答: {result4}")
```

输出：

```text
=== 方法一：自定义路由函数 ===

--- 售前咨询测试 ---
识别意图: 售前
回答: 您好！感谢您对我们产品的关注。我将为您详细介绍我们的产品功能及价格相关信息。

一、产品核心功能介绍：

我们的产品是一套集成化、智能化的解决方案，主要功能包括：

1. **高效数据管理**
   - 支持多源数据接入与整合
   - 提供数据清洗、存储、分析全流程管理
   - 实时数据可视化展示

2. **智能分析与决策支持**
   - 内置AI算法模型，支持预测分析、趋势判断
   - 自定义报表生成与多维度数据分析
   - 智能预警与异常检测功能

3. **灵活部署与扩展**
   - 支持本地部署、云端部署或混合部署模式
   - 可根据企业需求进行模块化扩展
   - 与主流系统（如ERP、CRM）无缝集成

4. **安全与权限管理**
   - 多级权限控制，保障数据安全
   - 完善的日志记录与审计机制
   - 支持数据加密与灾备恢复

5. **用户友好体验**
   - 简洁直观的操作界面
   - 支持多终端访问（PC、移动端）
   - 提供在线帮助与操作引导

二、产品价格说明：

我们的产品采用**模块化定价+订阅制/永久授权**的灵活收费模式，具体价格根据以下因素确定：

- 所选功能模块（基础版 / 专业版 / 定制版）
- 用户数量与并发访问需求
- 部署方式（云端 / 本地）
- 是否需要定制开发与系统集成
- 服务支持等级（标准支持 / 金牌服务）

为方便您了解，以下为大致的价格区间（具体以实际报价为准）：

| 产品版本     | 适用对象       | 起始价格（年费/授权） |
|--------------|----------------|------------------------|
| 基础版       | 中小型企业     | ￥50,000 起           |
| 专业版       | 中大型企业     | ￥150,000 起          |
| 定制版       | 大型企业/集团  | ￥300,000 起          |

我们还提供**免费试用**、**POC验证**和**定制演示**服务，欢迎您预约体验。

如需更详细的报价方案，请告知您的企业规模、行业、使用场景及具体需求，我可以为您推荐最适合的配置与价格方案。

期待您的进一步沟通！

--- 售后服务测试 ---
识别意图: 售后
回答: 您好，非常抱歉听到您的产品出现了无法正常启动的问题。为了更好地帮助您解决问题，请您先不要着急，我们一步步来排查。以下是一些初步的排查步骤和建议，希望能帮到您：

---

### 一、请确认以下基本问题：

1. **电源是否正常连接？**
   - 请检查电源线是否插好，插座是否有电。
   - 如果使用的是电池供电，请确认电池是否安装正确，电量是否充足。

2. **开关是否正常开启？**
   - 确认产品开关是否已经打开，有些产品可能有多个开关（如主电源开关和功能开关）。

3. **是否有指示灯或声音提示？**
   - 通电后是否有指示灯亮起、蜂鸣声或其他反应？这些信息对我们判断问题非常重要。

---

### 二、尝试以下操作：

1. **断电重启**
   - 将产品完全断电（拔掉电源线或取出电池），等待1-2分钟后重新连接电源，尝试再次启动。

2. **检查保险丝或断路器（如适用）**
   - 某些电器设备内部或插头处配有保险丝，如果保险丝熔断会导致无法启动。

3. **使用其他插座尝试**
   - 排除当前插座供电异常的可能性。

---

### 三、请您提供以下信息，以便我们进一步判断：

- 产品品牌和型号：
- 购买时间（是否在保修期内）：
- 故障发生前是否有异常情况（如进水、摔落、电压不稳等）：
- 是否有错误代码、指示灯状态或异常声响：

---

### 四、根据情况的后续建议：

- 如果您已完成上述排查但问题仍未解决，**建议尽快联系我们的售后服务中心**，我们可以为您安排进一步的技术支持或维修服务。
- 如果产品仍在保修期内，且确认为非人为损坏，我们将为您提供**免费维修或更换服务**。

---

请您回复以上信息，或拨打我们的客服热线：**400-XXX-XXXX**（服务时间：9:00-18:00），也可以发送邮件至：**service@company.com**，我们将第一时间为您处理。

感谢您的理解与配合，祝您生活愉快！

—— 您的售后服务团队

=== 方法二：RunnableBranch 条件路由 ===

--- 售前咨询测试 ---
回答: 当然可以！感谢您对我们服务的关注。为了更好地为您介绍我们的服务套餐和收费标准，我需要先简单了解一下您的需求背景：

- 您是企业用户还是个人用户？
- 您主要想了解哪一类服务（例如：软件服务、IT解决方案、云服务、技术支持、定制开发等）？
- 您所在的行业或具体应用场景是否有特殊需求？

在了解这些基本信息后，我可以为您更精准地推荐适合的套餐和价格方案。以下是我们常见服务类型的通用套餐分类和收费模式，供您初步参考：

---

### 一、服务套餐分类（示例）

#### 1. 基础服务套餐（适合中小企业或入门级用户）
- **服务内容**：
  - 标准功能使用权限
  - 在线技术支持（工作日8小时响应）
  - 每月1次远程培训
  - 有限的数据存储与并发访问能力
- **收费模式**：按用户数/设备数订阅制（月付或年付）
- **适用场景**：日常办公、基础系统使用

#### 2. 标准服务套餐（适合中大型企业或有定制需求的用户）
- **服务内容**：
  - 完整功能权限 + 个性化配置
  - 7×24小时在线支持 + 优先响应机制
  - 定制化培训与部署服务
  - 数据备份、安全防护、API接口开放
- **收费模式**：年费制 + 基础实施费用
- **适用场景**：系统集成、业务流程优化、数据对接

#### 3. 高级定制服务套餐（适合大型企业或行业客户）
- **服务内容**：
  - 完全定制开发 + 系统集成
  - 专属客户经理 + 技术顾问团队
  - 高可用部署方案（私有云/混合云）
  - SLA保障服务（服务等级协议）
- **收费模式**：项目制报价（按功能模块、开发量、部署规模等）
- **适用场景**：行业解决方案、系统迁移、平台重构

---

### 二、收费模式说明

- **订阅制**：按月或按年支付，适合标准化产品，灵活可扩展
- **项目制**：一次性开发费用 + 年度维护费，适合定制化需求
- **增值服务**：如数据迁移、系统集成、培训等，可按需选配

---

### 三、如何获取详细报价？

如果您愿意，我可以为您准备一份详细的报价方案，包括：
- 推荐的服务套餐
- 具体的功能清单
- 对应的价格明细（含优惠信息）
- 合同服务条款摘要

只需告诉我：
1. 您的公司规模与行业
2. 具体的应用场景或目标
3. 是否已有竞品或现有系统
4. 预算范围（如有）

---

期待您的回复，我将为您量身推荐最合适的方案。如果您希望我们安排一次线上沟通，我们也可以为您预约专业顾问进行一对一讲解。😊

祝您工作顺利！

--- 售后服务测试 ---
回答: 您好！感谢您联系我们的售后服务。关于您在使用产品过程中遇到的错误提示，我会尽力为您提供帮助。为了更好地解决问题，请您提供以下信息：

1. **错误提示的具体内容**：请尽量完整地描述屏幕上显示的错误信息或代码（例如：“错误代码：0012 – 无法连接服务器”）。

2. **产品型号及版本信息**：包括产品名称、型号、软件版本号等（可以在产品说明书或设置中找到）。

3. **操作步骤**：在出现错误前，您进行了哪些操作？是开机时出现问题，还是在使用某个功能时出现？

4. **是否为首次出现**：这个错误是第一次出现，还是重复发生？如果重复发生，请说明频率。

5. **是否有其他异常现象**：例如设备卡顿、无响应、自动重启等。

---

### 常见问题处理建议（可先尝试以下方法）：

✅ **重启设备**：关闭设备电源，等待1分钟后重新启动，观察是否仍然报错。

✅ **检查网络连接**：如涉及联网功能，请确认Wi-Fi或数据连接是否正常。

✅ **更新系统/软件**：前往设置中查看是否有可用的系统或应用程序更新。

✅ **清除缓存数据**：进入设置 > 应用管理 > 找到对应应用 > 清除缓存和数据（适用于软件类问题）。

---

在您提供更多信息后，我将为您进一步分析问题原因，并提供具体解决方案。如果您不方便文字描述，也可以提供截图（如在支持上传的平台上），我会根据图片内容为您分析。

期待您的回复！我们将尽快帮您解决问题。
```

## EmbeddingRouterChain

不仅可以使用 LLMRouteChain 来智能选择合适的处理链，还可以采用 EmbeddingRouterChain，该组件通过计算各 Chain 描述与用户问题之间的语义相关性，实现更精准的路由决策。

```python
!pip install chromadb
```

输出：

```text
Collecting chromadb
  Downloading chromadb-1.0.20-cp39-abi3-win_amd64.whl.metadata (7.4 kB)
Collecting build>=1.0.3 (from chromadb)
  Downloading build-1.3.0-py3-none-any.whl.metadata (5.6 kB)
Requirement already satisfied: pydantic>=1.9 in d:\software\miniconda3\envs\mlops\lib\site-packages (from chromadb) (2.11.7)
Collecting pybase64>=1.4.1 (from chromadb)
  Downloading pybase64-1.4.2-cp312-cp312-win_amd64.whl.metadata (9.0 kB)
Requirement already satisfied: uvicorn>=0.18.3 in d:\software\miniconda3\envs\mlops\lib\site-packages (from uvicorn[standard]>=0.18.3->chromadb) (0.35.0)
Requirement already satisfied: numpy>=1.22.5 in d:\software\miniconda3\envs\mlops\lib\site-packages (from chromadb) (1.26.4)
Collecting posthog<6.0.0,>=2.4.0 (from chromadb)
  Downloading posthog-5.4.0-py3-none-any.whl.metadata (5.7 kB)
Requirement already satisfied: typing-extensions>=4.5.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from chromadb) (4.15.0)
Collecting onnxruntime>=1.14.1 (from chromadb)
  Downloading onnxruntime-1.22.1-cp312-cp312-win_amd64.whl.metadata (5.1 kB)
Requirement already satisfied: opentelemetry-api>=1.2.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from chromadb) (1.36.0)
Collecting opentelemetry-exporter-otlp-proto-grpc>=1.2.0 (from chromadb)
  Downloading opentelemetry_exporter_otlp_proto_grpc-1.36.0-py3-none-any.whl.metadata (2.4 kB)
Collecting opentelemetry-sdk>=1.2.0 (from chromadb)
  Downloading opentelemetry_sdk-1.36.0-py3-none-any.whl.metadata (1.5 kB)
Requirement already satisfied: tokenizers>=0.13.2 in d:\software\miniconda3\envs\mlops\lib\site-packages (from chromadb) (0.22.0)
Collecting pypika>=0.48.9 (from chromadb)
  Downloading PyPika-0.48.9.tar.gz (67 kB)
  Installing build dependencies: started
  Installing build dependencies: finished with status 'done'
  Getting requirements to build wheel: started
  Getting requirements to build wheel: finished with status 'done'
  Preparing metadata (pyproject.toml): started
  Preparing metadata (pyproject.toml): finished with status 'done'
Requirement already satisfied: tqdm>=4.65.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from chromadb) (4.67.1)
Collecting overrides>=7.3.1 (from chromadb)
  Downloading overrides-7.7.0-py3-none-any.whl.metadata (5.8 kB)
Collecting importlib-resources (from chromadb)
  Downloading importlib_resources-6.5.2-py3-none-any.whl.metadata (3.9 kB)
Collecting grpcio>=1.58.0 (from chromadb)
  Downloading grpcio-1.74.0-cp312-cp312-win_amd64.whl.metadata (4.0 kB)
Collecting bcrypt>=4.0.1 (from chromadb)
  Downloading bcrypt-4.3.0-cp39-abi3-win_amd64.whl.metadata (10 kB)
Requirement already satisfied: typer>=0.9.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from chromadb) (0.17.3)
Collecting kubernetes>=28.1.0 (from chromadb)
  Downloading kubernetes-33.1.0-py2.py3-none-any.whl.metadata (1.7 kB)
Requirement already satisfied: tenacity>=8.2.3 in d:\software\miniconda3\envs\mlops\lib\site-packages (from chromadb) (8.5.0)
Requirement already satisfied: pyyaml>=6.0.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from chromadb) (6.0.2)
Collecting mmh3>=4.0.1 (from chromadb)
  Downloading mmh3-5.2.0-cp312-cp312-win_amd64.whl.metadata (14 kB)
Requirement already satisfied: orjson>=3.9.12 in d:\software\miniconda3\envs\mlops\lib\site-packages (from chromadb) (3.11.3)
Requirement already satisfied: httpx>=0.27.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from chromadb) (0.28.1)
Requirement already satisfied: rich>=10.11.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from chromadb) (14.1.0)
Collecting jsonschema>=4.19.0 (from chromadb)
  Using cached jsonschema-4.25.1-py3-none-any.whl.metadata (7.6 kB)
Requirement already satisfied: requests<3.0,>=2.7 in d:\software\miniconda3\envs\mlops\lib\site-packages (from posthog<6.0.0,>=2.4.0->chromadb) (2.32.5)
Requirement already satisfied: six>=1.5 in d:\software\miniconda3\envs\mlops\lib\site-packages (from posthog<6.0.0,>=2.4.0->chromadb) (1.17.0)
Requirement already satisfied: python-dateutil>=2.2 in d:\software\miniconda3\envs\mlops\lib\site-packages (from posthog<6.0.0,>=2.4.0->chromadb) (2.9.0.post0)
Collecting backoff>=1.10.0 (from posthog<6.0.0,>=2.4.0->chromadb)
  Using cached backoff-2.2.1-py3-none-any.whl.metadata (14 kB)
Requirement already satisfied: distro>=1.5.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from posthog<6.0.0,>=2.4.0->chromadb) (1.9.0)
Requirement already satisfied: charset_normalizer<4,>=2 in d:\software\miniconda3\envs\mlops\lib\site-packages (from requests<3.0,>=2.7->posthog<6.0.0,>=2.4.0->chromadb) (3.4.3)
Requirement already satisfied: idna<4,>=2.5 in d:\software\miniconda3\envs\mlops\lib\site-packages (from requests<3.0,>=2.7->posthog<6.0.0,>=2.4.0->chromadb) (3.10)
Requirement already satisfied: urllib3<3,>=1.21.1 in d:\software\miniconda3\envs\mlops\lib\site-packages (from requests<3.0,>=2.7->posthog<6.0.0,>=2.4.0->chromadb) (2.5.0)
Requirement already satisfied: certifi>=2017.4.17 in d:\software\miniconda3\envs\mlops\lib\site-packages (from requests<3.0,>=2.7->posthog<6.0.0,>=2.4.0->chromadb) (2025.8.3)
Requirement already satisfied: packaging>=19.1 in d:\software\miniconda3\envs\mlops\lib\site-packages (from build>=1.0.3->chromadb) (25.0)
Collecting pyproject_hooks (from build>=1.0.3->chromadb)
  Downloading pyproject_hooks-1.2.0-py3-none-any.whl.metadata (1.3 kB)
Requirement already satisfied: colorama in d:\software\miniconda3\envs\mlops\lib\site-packages (from build>=1.0.3->chromadb) (0.4.6)
Requirement already satisfied: anyio in d:\software\miniconda3\envs\mlops\lib\site-packages (from httpx>=0.27.0->chromadb) (4.10.0)
Requirement already satisfied: httpcore==1.* in d:\software\miniconda3\envs\mlops\lib\site-packages (from httpx>=0.27.0->chromadb) (1.0.9)
Requirement already satisfied: h11>=0.16 in d:\software\miniconda3\envs\mlops\lib\site-packages (from httpcore==1.*->httpx>=0.27.0->chromadb) (0.16.0)
Requirement already satisfied: attrs>=22.2.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from jsonschema>=4.19.0->chromadb) (25.3.0)
Collecting jsonschema-specifications>=2023.03.6 (from jsonschema>=4.19.0->chromadb)
  Downloading jsonschema_specifications-2025.9.1-py3-none-any.whl.metadata (2.9 kB)
Collecting referencing>=0.28.4 (from jsonschema>=4.19.0->chromadb)
  Using cached referencing-0.36.2-py3-none-any.whl.metadata (2.8 kB)
Collecting rpds-py>=0.7.1 (from jsonschema>=4.19.0->chromadb)
  Downloading rpds_py-0.27.1-cp312-cp312-win_amd64.whl.metadata (4.3 kB)
Collecting google-auth>=1.0.1 (from kubernetes>=28.1.0->chromadb)
  Downloading google_auth-2.40.3-py2.py3-none-any.whl.metadata (6.2 kB)
Requirement already satisfied: websocket-client!=0.40.0,!=0.41.*,!=0.42.*,>=0.32.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from kubernetes>=28.1.0->chromadb) (1.8.0)
Collecting requests-oauthlib (from kubernetes>=28.1.0->chromadb)
  Downloading requests_oauthlib-2.0.0-py2.py3-none-any.whl.metadata (11 kB)
Collecting oauthlib>=3.2.2 (from kubernetes>=28.1.0->chromadb)
  Downloading oauthlib-3.3.1-py3-none-any.whl.metadata (7.9 kB)
Collecting durationpy>=0.7 (from kubernetes>=28.1.0->chromadb)
  Downloading durationpy-0.10-py3-none-any.whl.metadata (340 bytes)
Collecting cachetools<6.0,>=2.0.0 (from google-auth>=1.0.1->kubernetes>=28.1.0->chromadb)
  Using cached cachetools-5.5.2-py3-none-any.whl.metadata (5.4 kB)
Collecting pyasn1-modules>=0.2.1 (from google-auth>=1.0.1->kubernetes>=28.1.0->chromadb)
  Downloading pyasn1_modules-0.4.2-py3-none-any.whl.metadata (3.5 kB)
Collecting rsa<5,>=3.1.4 (from google-auth>=1.0.1->kubernetes>=28.1.0->chromadb)
  Downloading rsa-4.9.1-py3-none-any.whl.metadata (5.6 kB)
Collecting pyasn1>=0.1.3 (from rsa<5,>=3.1.4->google-auth>=1.0.1->kubernetes>=28.1.0->chromadb)
  Downloading pyasn1-0.6.1-py3-none-any.whl.metadata (8.4 kB)
Collecting coloredlogs (from onnxruntime>=1.14.1->chromadb)
  Using cached coloredlogs-15.0.1-py2.py3-none-any.whl.metadata (12 kB)
Collecting flatbuffers (from onnxruntime>=1.14.1->chromadb)
  Using cached flatbuffers-25.2.10-py2.py3-none-any.whl.metadata (875 bytes)
Requirement already satisfied: protobuf in d:\software\miniconda3\envs\mlops\lib\site-packages (from onnxruntime>=1.14.1->chromadb) (5.29.5)
Requirement already satisfied: sympy in d:\software\miniconda3\envs\mlops\lib\site-packages (from onnxruntime>=1.14.1->chromadb) (1.14.0)
Requirement already satisfied: importlib-metadata<8.8.0,>=6.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from opentelemetry-api>=1.2.0->chromadb) (8.7.0)
Requirement already satisfied: zipp>=3.20 in d:\software\miniconda3\envs\mlops\lib\site-packages (from importlib-metadata<8.8.0,>=6.0->opentelemetry-api>=1.2.0->chromadb) (3.23.0)
Collecting googleapis-common-protos~=1.57 (from opentelemetry-exporter-otlp-proto-grpc>=1.2.0->chromadb)
  Downloading googleapis_common_protos-1.70.0-py3-none-any.whl.metadata (9.3 kB)
Collecting opentelemetry-exporter-otlp-proto-common==1.36.0 (from opentelemetry-exporter-otlp-proto-grpc>=1.2.0->chromadb)
  Downloading opentelemetry_exporter_otlp_proto_common-1.36.0-py3-none-any.whl.metadata (1.8 kB)
Collecting opentelemetry-proto==1.36.0 (from opentelemetry-exporter-otlp-proto-grpc>=1.2.0->chromadb)
  Downloading opentelemetry_proto-1.36.0-py3-none-any.whl.metadata (2.3 kB)
Collecting opentelemetry-semantic-conventions==0.57b0 (from opentelemetry-sdk>=1.2.0->chromadb)
  Downloading opentelemetry_semantic_conventions-0.57b0-py3-none-any.whl.metadata (2.4 kB)
Requirement already satisfied: annotated-types>=0.6.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from pydantic>=1.9->chromadb) (0.7.0)
Requirement already satisfied: pydantic-core==2.33.2 in d:\software\miniconda3\envs\mlops\lib\site-packages (from pydantic>=1.9->chromadb) (2.33.2)
Requirement already satisfied: typing-inspection>=0.4.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from pydantic>=1.9->chromadb) (0.4.1)
Requirement already satisfied: markdown-it-py>=2.2.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from rich>=10.11.0->chromadb) (4.0.0)
Requirement already satisfied: pygments<3.0.0,>=2.13.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from rich>=10.11.0->chromadb) (2.19.2)
Requirement already satisfied: mdurl~=0.1 in d:\software\miniconda3\envs\mlops\lib\site-packages (from markdown-it-py>=2.2.0->rich>=10.11.0->chromadb) (0.1.2)
Requirement already satisfied: huggingface-hub<1.0,>=0.16.4 in d:\software\miniconda3\envs\mlops\lib\site-packages (from tokenizers>=0.13.2->chromadb) (0.34.4)
Requirement already satisfied: filelock in d:\software\miniconda3\envs\mlops\lib\site-packages (from huggingface-hub<1.0,>=0.16.4->tokenizers>=0.13.2->chromadb) (3.19.1)
Requirement already satisfied: fsspec>=2023.5.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from huggingface-hub<1.0,>=0.16.4->tokenizers>=0.13.2->chromadb) (2024.12.0)
Requirement already satisfied: click>=8.0.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from typer>=0.9.0->chromadb) (8.2.1)
Requirement already satisfied: shellingham>=1.3.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from typer>=0.9.0->chromadb) (1.5.4)
Collecting httptools>=0.6.3 (from uvicorn[standard]>=0.18.3->chromadb)
  Downloading httptools-0.6.4-cp312-cp312-win_amd64.whl.metadata (3.7 kB)
Requirement already satisfied: python-dotenv>=0.13 in d:\software\miniconda3\envs\mlops\lib\site-packages (from uvicorn[standard]>=0.18.3->chromadb) (1.1.1)
Collecting watchfiles>=0.13 (from uvicorn[standard]>=0.18.3->chromadb)
  Downloading watchfiles-1.1.0-cp312-cp312-win_amd64.whl.metadata (5.0 kB)
Requirement already satisfied: websockets>=10.4 in d:\software\miniconda3\envs\mlops\lib\site-packages (from uvicorn[standard]>=0.18.3->chromadb) (15.0.1)
Requirement already satisfied: sniffio>=1.1 in d:\software\miniconda3\envs\mlops\lib\site-packages (from anyio->httpx>=0.27.0->chromadb) (1.3.1)
Collecting humanfriendly>=9.1 (from coloredlogs->onnxruntime>=1.14.1->chromadb)
  Using cached humanfriendly-10.0-py2.py3-none-any.whl.metadata (9.2 kB)
Collecting pyreadline3 (from humanfriendly>=9.1->coloredlogs->onnxruntime>=1.14.1->chromadb)
  Using cached pyreadline3-3.5.4-py3-none-any.whl.metadata (4.7 kB)
Requirement already satisfied: mpmath<1.4,>=1.1.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from sympy->onnxruntime>=1.14.1->chromadb) (1.3.0)
Downloading chromadb-1.0.20-cp39-abi3-win_amd64.whl (19.8 MB)
   ---------------------------------------- 0.0/19.8 MB ? eta -:--:--
   ---------------------------------------- 0.0/19.8 MB ? eta -:--:--
   ---------------------------------------- 0.0/19.8 MB ? eta -:--:--
   ---------------------------------------- 0.0/19.8 MB ? eta -:--:--
    --------------------------------------- 0.3/19.8 MB ? eta -:--:--
    --------------------------------------- 0.3/19.8 MB ? eta -:--:--
   - -------------------------------------- 0.5/19.8 MB 699.0 kB/s eta 0:00:28
   - -------------------------------------- 0.5/19.8 MB 699.0 kB/s eta 0:00:28
   - -------------------------------------- 0.8/19.8 MB 699.0 kB/s eta 0:00:28
   - -------------------------------------- 0.8/19.8 MB 699.0 kB/s eta 0:00:28
   -- ------------------------------------- 1.0/19.8 MB 671.0 kB/s eta 0:00:28
   -- ------------------------------------- 1.3/19.8 MB 657.8 kB/s eta 0:00:29
   -- ------------------------------------- 1.3/19.8 MB 657.8 kB/s eta 0:00:29
   --- ------------------------------------ 1.6/19.8 MB 682.0 kB/s eta 0:00:27
   --- ------------------------------------ 1.6/19.8 MB 682.0 kB/s eta 0:00:27
   --- ------------------------------------ 1.8/19.8 MB 671.0 kB/s eta 0:00:27
   ---- ----------------------------------- 2.1/19.8 MB 699.0 kB/s eta 0:00:26
   ---- ----------------------------------- 2.1/19.8 MB 699.0 kB/s eta 0:00:26
   ---- ----------------------------------- 2.4/19.8 MB 699.0 kB/s eta 0:00:25
   ---- ----------------------------------- 2.4/19.8 MB 699.0 kB/s eta 0:00:25
   ----- ---------------------------------- 2.6/19.8 MB 695.8 kB/s eta 0:00:25
   ----- ---------------------------------- 2.6/19.8 MB 695.8 kB/s eta 0:00:25
   ----- ---------------------------------- 2.9/19.8 MB 693.1 kB/s eta 0:00:25
   ----- ---------------------------------- 2.9/19.8 MB 693.1 kB/s eta 0:00:25
   ------ --------------------------------- 3.1/19.8 MB 680.9 kB/s eta 0:00:25
   ------ --------------------------------- 3.1/19.8 MB 680.9 kB/s eta 0:00:25
   ------ --------------------------------- 3.4/19.8 MB 673.3 kB/s eta 0:00:25
   ------- -------------------------------- 3.7/19.8 MB 690.1 kB/s eta 0:00:24
   ------- -------------------------------- 3.9/19.8 MB 711.7 kB/s eta 0:00:23
   -------- ------------------------------- 4.2/19.8 MB 738.0 kB/s eta 0:00:22
   --------- ------------------------------ 4.7/19.8 MB 790.0 kB/s eta 0:00:20
   ---------- ----------------------------- 5.0/19.8 MB 818.3 kB/s eta 0:00:19
   ----------- ---------------------------- 5.5/19.8 MB 867.0 kB/s eta 0:00:17
   ------------ --------------------------- 6.3/19.8 MB 955.1 kB/s eta 0:00:15
   ------------- -------------------------- 6.8/19.8 MB 1.0 MB/s eta 0:00:13
   --------------- ------------------------ 7.6/19.8 MB 1.1 MB/s eta 0:00:12
   ---------------- ----------------------- 8.4/19.8 MB 1.2 MB/s eta 0:00:10
   ------------------- -------------------- 9.4/19.8 MB 1.3 MB/s eta 0:00:09
   --------------------- ------------------ 10.5/19.8 MB 1.4 MB/s eta 0:00:07
   ---------------------- ----------------- 11.3/19.8 MB 1.5 MB/s eta 0:00:06
   ------------------------- -------------- 12.6/19.8 MB 1.6 MB/s eta 0:00:05
   --------------------------- ------------ 13.6/19.8 MB 1.7 MB/s eta 0:00:04
   ------------------------------ --------- 15.2/19.8 MB 1.8 MB/s eta 0:00:03
   --------------------------------- ------ 16.5/19.8 MB 1.9 MB/s eta 0:00:02
   ------------------------------------ --- 17.8/19.8 MB 2.0 MB/s eta 0:00:01
   -------------------------------------- - 18.9/19.8 MB 2.1 MB/s eta 0:00:01
   ---------------------------------------  19.7/19.8 MB 2.2 MB/s eta 0:00:01
   ---------------------------------------- 19.8/19.8 MB 2.1 MB/s eta 0:00:00
Downloading posthog-5.4.0-py3-none-any.whl (105 kB)
Using cached backoff-2.2.1-py3-none-any.whl (15 kB)
Downloading bcrypt-4.3.0-cp39-abi3-win_amd64.whl (152 kB)
Downloading build-1.3.0-py3-none-any.whl (23 kB)
Downloading grpcio-1.74.0-cp312-cp312-win_amd64.whl (4.5 MB)
   ---------------------------------------- 0.0/4.5 MB ? eta -:--:--
   ------- -------------------------------- 0.8/4.5 MB 11.4 MB/s eta 0:00:01
   ---------------- ----------------------- 1.8/4.5 MB 5.6 MB/s eta 0:00:01
   ------------------------- -------------- 2.9/4.5 MB 4.9 MB/s eta 0:00:01
   ------------------------------------- -- 4.2/4.5 MB 5.5 MB/s eta 0:00:01
   ---------------------------------------- 4.5/4.5 MB 5.4 MB/s eta 0:00:00
Using cached jsonschema-4.25.1-py3-none-any.whl (90 kB)
Downloading jsonschema_specifications-2025.9.1-py3-none-any.whl (18 kB)
Downloading kubernetes-33.1.0-py2.py3-none-any.whl (1.9 MB)
   ---------------------------------------- 0.0/1.9 MB ? eta -:--:--
   ---------------- ----------------------- 0.8/1.9 MB 5.6 MB/s eta 0:00:01
   -------------------------------- ------- 1.6/1.9 MB 4.2 MB/s eta 0:00:01
   ---------------------------------------- 1.9/1.9 MB 4.7 MB/s eta 0:00:00
Downloading durationpy-0.10-py3-none-any.whl (3.9 kB)
Downloading google_auth-2.40.3-py2.py3-none-any.whl (216 kB)
Using cached cachetools-5.5.2-py3-none-any.whl (10 kB)
Downloading rsa-4.9.1-py3-none-any.whl (34 kB)
Downloading mmh3-5.2.0-cp312-cp312-win_amd64.whl (41 kB)
Downloading oauthlib-3.3.1-py3-none-any.whl (160 kB)
Downloading onnxruntime-1.22.1-cp312-cp312-win_amd64.whl (12.7 MB)
   ---------------------------------------- 0.0/12.7 MB ? eta -:--:--
   ---------------------------------------- 0.0/12.7 MB ? eta -:--:--
   ---------------------------------------- 0.0/12.7 MB ? eta -:--:--
    --------------------------------------- 0.3/12.7 MB ? eta -:--:--
   ----- ---------------------------------- 1.8/12.7 MB 5.0 MB/s eta 0:00:03
   ----------- ---------------------------- 3.7/12.7 MB 7.0 MB/s eta 0:00:02
   -------------- ------------------------- 4.5/12.7 MB 6.4 MB/s eta 0:00:02
   --------------- ------------------------ 5.0/12.7 MB 4.9 MB/s eta 0:00:02
   ------------------- -------------------- 6.0/12.7 MB 5.0 MB/s eta 0:00:02
   --------------------- ------------------ 6.8/12.7 MB 5.0 MB/s eta 0:00:02
   ------------------------- -------------- 8.1/12.7 MB 4.9 MB/s eta 0:00:01
   ---------------------------- ----------- 8.9/12.7 MB 4.9 MB/s eta 0:00:01
   ------------------------------ --------- 9.7/12.7 MB 4.7 MB/s eta 0:00:01
   --------------------------------- ------ 10.5/12.7 MB 4.6 MB/s eta 0:00:01
   ---------------------------------- ----- 11.0/12.7 MB 4.5 MB/s eta 0:00:01
   -------------------------------------- - 12.1/12.7 MB 4.4 MB/s eta 0:00:01
   ---------------------------------------- 12.7/12.7 MB 4.3 MB/s eta 0:00:00
Downloading opentelemetry_exporter_otlp_proto_grpc-1.36.0-py3-none-any.whl (18 kB)
Downloading opentelemetry_exporter_otlp_proto_common-1.36.0-py3-none-any.whl (18 kB)
Downloading opentelemetry_proto-1.36.0-py3-none-any.whl (72 kB)
Downloading googleapis_common_protos-1.70.0-py3-none-any.whl (294 kB)
Downloading opentelemetry_sdk-1.36.0-py3-none-any.whl (119 kB)
Downloading opentelemetry_semantic_conventions-0.57b0-py3-none-any.whl (201 kB)
Downloading overrides-7.7.0-py3-none-any.whl (17 kB)
Downloading pyasn1-0.6.1-py3-none-any.whl (83 kB)
Downloading pyasn1_modules-0.4.2-py3-none-any.whl (181 kB)
Downloading pybase64-1.4.2-cp312-cp312-win_amd64.whl (35 kB)
Using cached referencing-0.36.2-py3-none-any.whl (26 kB)
Downloading rpds_py-0.27.1-cp312-cp312-win_amd64.whl (232 kB)
Downloading httptools-0.6.4-cp312-cp312-win_amd64.whl (88 kB)
Downloading watchfiles-1.1.0-cp312-cp312-win_amd64.whl (292 kB)
Using cached coloredlogs-15.0.1-py2.py3-none-any.whl (46 kB)
Using cached humanfriendly-10.0-py2.py3-none-any.whl (86 kB)
Using cached flatbuffers-25.2.10-py2.py3-none-any.whl (30 kB)
Downloading importlib_resources-6.5.2-py3-none-any.whl (37 kB)
Downloading pyproject_hooks-1.2.0-py3-none-any.whl (10 kB)
Using cached pyreadline3-3.5.4-py3-none-any.whl (83 kB)
Downloading requests_oauthlib-2.0.0-py2.py3-none-any.whl (24 kB)
Building wheels for collected packages: pypika
  Building wheel for pypika (pyproject.toml): started
  Building wheel for pypika (pyproject.toml): finished with status 'done'
  Created wheel for pypika: filename=pypika-0.48.9-py2.py3-none-any.whl size=53916 sha256=7f3dfb28a8ced6f8567e6f0ad771a2495ec91aecc8f4a23a10390e2eb50dc8ee
  Stored in directory: c:\users\administrator\appdata\local\pip\cache\wheels\d5\3d\69\8d68d249cd3de2584f226e27fd431d6344f7d70fd856ebd01b
Successfully built pypika
Installing collected packages: pypika, flatbuffers, durationpy, rpds-py, pyreadline3, pyproject_hooks, pybase64, pyasn1, overrides, opentelemetry-proto, oauthlib, mmh3, importlib-resources, httptools, grpcio, googleapis-common-protos, cachetools, bcrypt, backoff, watchfiles, rsa, requests-oauthlib, referencing, pyasn1-modules, posthog, opentelemetry-exporter-otlp-proto-common, humanfriendly, build, opentelemetry-semantic-conventions, jsonschema-specifications, google-auth, coloredlogs, opentelemetry-sdk, onnxruntime, kubernetes, jsonschema, opentelemetry-exporter-otlp-proto-grpc, chromadb

   ---- -----------------------------------  4/38 [pyreadline3]
   ------- --------------------------------  7/38 [pyasn1]
   ---------- ----------------------------- 10/38 [oauthlib]
   ------------ --------------------------- 12/38 [importlib-resources]
   -------------- ------------------------- 14/38 [grpcio]
   --------------- ------------------------ 15/38 [googleapis-common-protos]
   --------------------- ------------------ 20/38 [rsa]
   ------------------------ --------------- 23/38 [pyasn1-modules]
   ------------------------ --------------- 23/38 [pyasn1-modules]
   ------------------------- -------------- 24/38 [posthog]
   ---------------------------- ----------- 27/38 [build]
   ------------------------ -------- 28/38 [opentelemetry-semantic-conventions]
   ------------------------------- -------- 30/38 [google-auth]
   --------------------------------- ------ 32/38 [opentelemetry-sdk]
   ---------------------------------- ----- 33/38 [onnxruntime]
   ---------------------------------- ----- 33/38 [onnxruntime]
   ---------------------------------- ----- 33/38 [onnxruntime]
   ---------------------------------- ----- 33/38 [onnxruntime]
   ---------------------------------- ----- 33/38 [onnxruntime]
   ---------------------------------- ----- 33/38 [onnxruntime]
   ----------------------------------- ---- 34/38 [kubernetes]
   ----------------------------------- ---- 34/38 [kubernetes]
   ----------------------------------- ---- 34/38 [kubernetes]
   ----------------------------------- ---- 34/38 [kubernetes]
   ----------------------------------- ---- 34/38 [kubernetes]
   ----------------------------------- ---- 34/38 [kubernetes]
   ----------------------------------- ---- 34/38 [kubernetes]
   ----------------------------------- ---- 34/38 [kubernetes]
   ----------------------------------- ---- 34/38 [kubernetes]
   ----------------------------------- ---- 34/38 [kubernetes]
   ----------------------------------- ---- 34/38 [kubernetes]
   ----------------------------------- ---- 34/38 [kubernetes]
   -------------------------------------- - 37/38 [chromadb]
   -------------------------------------- - 37/38 [chromadb]
   -------------------------------------- - 37/38 [chromadb]
   -------------------------------------- - 37/38 [chromadb]
   -------------------------------------- - 37/38 [chromadb]
   ---------------------------------------- 38/38 [chromadb]

Successfully installed backoff-2.2.1 bcrypt-4.3.0 build-1.3.0 cachetools-5.5.2 chromadb-1.0.20 coloredlogs-15.0.1 durationpy-0.10 flatbuffers-25.2.10 google-auth-2.40.3 googleapis-common-protos-1.70.0 grpcio-1.74.0 httptools-0.6.4 humanfriendly-10.0 importlib-resources-6.5.2 jsonschema-4.25.1 jsonschema-specifications-2025.9.1 kubernetes-33.1.0 mmh3-5.2.0 oauthlib-3.3.1 onnxruntime-1.22.1 opentelemetry-exporter-otlp-proto-common-1.36.0 opentelemetry-exporter-otlp-proto-grpc-1.36.0 opentelemetry-proto-1.36.0 opentelemetry-sdk-1.36.0 opentelemetry-semantic-conventions-0.57b0 overrides-7.7.0 posthog-5.4.0 pyasn1-0.6.1 pyasn1-modules-0.4.2 pybase64-1.4.2 pypika-0.48.9 pyproject_hooks-1.2.0 pyreadline3-3.5.4 referencing-0.36.2 requests-oauthlib-2.0.0 rpds-py-0.27.1 rsa-4.9.1 watchfiles-1.1.0
WARNING: Retrying (Retry(total=4, connect=None, read=None, redirect=None, status=None)) after connection broken by 'ProxyError('Cannot connect to proxy.', ConnectionAbortedError(10053, '你的主机中的软件中止了一个已建立的连接。', None, 10053, None))': /simple/chromadb/
WARNING: Retrying (Retry(total=3, connect=None, read=None, redirect=None, status=None)) after connection broken by 'ProxyError('Cannot connect to proxy.', ConnectionAbortedError(10053, '你的主机中的软件中止了一个已建立的连接。', None, 10053, None))': /simple/chromadb/
WARNING: Retrying (Retry(total=2, connect=None, read=None, redirect=None, status=None)) after connection broken by 'ProxyError('Cannot connect to proxy.', ConnectionAbortedError(10053, '你的主机中的软件中止了一个已建立的连接。', None, 10053, None))': /simple/chromadb/
  WARNING: Retrying (Retry(total=4, connect=None, read=None, redirect=None, status=None)) after connection broken by 'ProxyError('Cannot connect to proxy.', ConnectionAbortedError(10053, '你的主机中的软件中止了一个已建立的连接。', None, 10053, None))': /packages/6f/81/6decbd21c67572d67707f7e168851f10404e2857897456c6ba220e9b09be/chromadb-1.0.20-cp39-abi3-win_amd64.whl.metadata
```

```python
from langchain_community.vectorstores import Chroma    # # pip install chroma
from langchain_community.embeddings import DashScopeEmbeddings # pip install dashscope
from langchain.chains import LLMRouterChain, MultiPromptChain
from langchain_core.language_models import BaseLLM
from langchain_core.prompts import PromptTemplate
from langchain_community.llms import Tongyi  # 或你使用的 LLM
import os

# 1. 定义任务名称与描述
names_and_descriptions = [
    ("physics", ["用于解答物理相关问题，例如力学、电磁学等"]),
    ("math", ["用于解答数学相关问题，例如代数、几何、微积分等"]),
]

# 2. 使用通义千问的 Embedding 模型
embeddings = DashScopeEmbeddings(model="text-embedding-v2")

# 3. 构建向量数据库（用于路由匹配）
descriptions = []
names = []
for name, desc_list in names_and_descriptions:
    for desc in desc_list:
        descriptions.append(desc)
        names.append(name)

# 创建 Chroma 向量库
vectorstore = Chroma(embedding_function=embeddings)
# 批量添加文档
vectorstore.add_texts(texts=descriptions, metadatas=[{"name": name} for name in names])

# 4. 自定义 Embedding 路由链（LangChain 没有直接 from_names_and_descriptions）
def get_relevant_chain_name(question: str) -> str:
    docs = vectorstore.similarity_search(question, k=1)
    return docs[0].metadata["name"]

# 5. 定义各个目标链的 prompt 和 LLM
llm = Tongyi(model_name="qwen-plus", temperature=0.1)  # 可替换为你用的 LLM

physics_prompt = PromptTemplate(
    template="你是一个物理专家，请回答以下问题：\n{input}",
    input_variables=["input"]
)
math_prompt = PromptTemplate(
    template="你是一个数学专家，请回答以下问题：\n{input}",
    input_variables=["input"]
)

destination_chains = {
    "physics": physics_prompt | llm,
    "math": math_prompt | llm,
}

default_chain = PromptTemplate.from_template("请回答以下问题：{input}") | llm

# 6. 定义运行逻辑（模拟 MultiPromptChain）
def run_router_chain(question: str):
    chain_name = get_relevant_chain_name(question)
    print(f"路由到: {chain_name}")
    if chain_name in destination_chains:
        return destination_chains[chain_name].invoke({"input": question})
    else:
        return default_chain.invoke({"input": question})

# 7. 测试
result = run_router_chain("牛顿第一定律是什么？")
print(result)
```

输出：

```text
路由到: physics
牛顿第一定律，也称为**惯性定律**，其内容是：

> **任何物体在不受外力作用时，总保持静止状态或匀速直线运动状态。**

换句话说，如果一个物体没有受到**净外力**（即合外力为零）的作用，那么它的**速度**将保持不变。这意味着：

- 原来静止的物体将继续保持静止；
- 原来运动的物体将以恒定速度沿直线运动。

---

### 补充说明：

- 牛顿第一定律最早由伽利略提出思想基础，后来由牛顿系统地总结为经典力学的第一条定律。
- 这条定律定义了**惯性参考系**的概念：在这样的参考系中，物体在没有受力时能保持匀速直线运动或静止。
- 定律强调了**惯性**的概念：物体具有保持当前运动状态的倾向。

---

### 举例说明：

- 当你在一辆快速行驶的汽车中突然刹车时，你的身体会向前倾。这是因为你的身体“想要”保持原来的运动状态（惯性），而车已经减速。
- 在太空中，如果一个物体以一定速度运动且不受引力或其他力作用，它会一直以这个速度沿直线运动。

---

### 总结公式表达（虽然牛顿第一定律本身没有直接公式，但可表示为）：

若
$$
\sum \vec{F} = 0
$$
则
$$
\vec{v} = \text{常量}
$$

即：当合外力为零时，速度矢量保持不变。
```
