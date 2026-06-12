<!-- Converted from llamaindex_03_node_basics.ipynb -->

```python
from dotenv import load_dotenv
load_dotenv()
```

```python

import os
from llama_index.core import Settings
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.llms.openai_like import OpenAILike
from llama_index.embeddings.dashscope import DashScopeEmbedding, DashScopeTextEmbeddingModels

# 增加调试日志
import logging
import sys
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logging.getLogger("llama_index").addHandler(logging.StreamHandler(stream=sys.stdout))


Settings.llm = OpenAILike(
    model="qwen-plus",
    api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    is_chat_model=True
)

Settings.embed_model = DashScopeEmbedding(
    model_name=DashScopeTextEmbeddingModels.TEXT_EMBEDDING_V3,
    embed_batch_size=6,
    embed_input_length=8192
)

documents = SimpleDirectoryReader("data").load_data()

```

输出：

```text
d:\miniconda3\envs\MLOps\Lib\site-packages\tqdm\auto.py:21: TqdmWarning: IProgress not found. Please update jupyter and ipywidgets. See https://ipywidgets.readthedocs.io/en/stable/user_install.html
  from .autonotebook import tqdm as notebook_tqdm
None of PyTorch, TensorFlow >= 2.0, or Flax have been found. Models won't be available and only tokenizers, configuration and file/data utilities can be used.
> [SimpleDirectoryReader] Total files added: 1
DEBUG:llama_index.core.readers.file.base:> [SimpleDirectoryReader] Total files added: 1
DEBUG:fsspec.local:open file: e:/AI工程化训练营/workspace/03_rag_and_retrieval/llamaindex_and_ragas/data/公司员工休假福利管理制度.txt
```

```python
print(documents)
```

输出：

```text
[Document(id_='82a93754-2ef1-4258-8067-019de2d4b1b7', embedding=None, metadata={'file_path': 'e:\\AI工程化训练营\\workspace\\03_rag_and_retrieval/llamaindex_and_ragas\\data\\公司员工休假福利管理制度.txt', 'file_name': '公司员工休假福利管理制度.txt', 'file_type': 'text/plain', 'file_size': 6294, 'creation_date': '2025-08-27', 'last_modified_date': '2025-08-27'}, excluded_embed_metadata_keys=['file_name', 'file_type', 'file_size', 'creation_date', 'last_modified_date', 'last_accessed_date'], excluded_llm_metadata_keys=['file_name', 'file_type', 'file_size', 'creation_date', 'last_modified_date', 'last_accessed_date'], relationships={}, metadata_template='{key}: {value}', metadata_separator='\n', text_resource=MediaResource(embeddings=None, data=None, text='# 公司员工休假福利管理制度\r\n\r\n## 第一章 总则\r\n\r\n**第一条 目的**  \r\n为规范公司员工休假管理，保障员工合法权益，维护正常的工作秩序，提升员工满意度与工作效率，根据《中华人民共和国劳动法》《职工带薪年休假条例》《女职工劳动保护特别规定》等国家相关法律法规，结合公司实际情况，制定本制度。\r\n\r\n**第二条 适用范围**  \r\n本制度适用于公司所有与公司签订劳动合同的正式员工（含试用期员工），劳务派遣人员参照执行，具体以劳务派遣协议为准。\r\n\r\n**第三条 基本原则**  \r\n1. 依法合规：严格遵守国家法律法规及相关政策规定。  \r\n2. 公平公正：各类休假权利平等对待，程序公开透明。  \r\n3. 合理安排：兼顾员工个人需求与公司运营需要，确保工作连续性。\r\n\r\n---\r\n\r\n## 第二章 休假类型及规定\r\n\r\n### 第四条 法定节假日  \r\n国家规定的法定节假日，公司统一安排休假，具体如下（共11天）：  \r\n- 元旦：1天  \r\n- 春节：3天  \r\n- 清明节：1天  \r\n- 劳动节：1天  \r\n- 端午节：1天  \r\n- 中秋节：1天  \r\n- 国庆节：3天  \r\n\r\n如遇调休安排，公司将根据国务院发布的节假日安排通知执行。\r\n\r\n### 第五条 带薪年休假  \r\n1. 员工连续工作满1年以上的，享受带薪年休假。  \r\n2. 年休假天数标准：  \r\n   - 累计工作满1年不满10年的，年休假5天；  \r\n   - 满10年不满20年的，年休假10天；  \r\n   - 满20年及以上的，年休假15天。  \r\n3. 年休假可分次使用，但原则上不跨年度安排。确因工作需要未能休完的，经公司批准可延至次年第一季度补休，逾期视为自动放弃。  \r\n4. 年休假期间工资照常发放。\r\n\r\n> 注：员工入职当年按在本公司工作时间折算年休假天数，计算公式：（当年度在本公司剩余日历天数 ÷ 365）× 全年应休天数，折算后不足1天的部分不享受。\r\n\r\n### 第六条 病假  \r\n1. 员工因病或非因工负伤需停止工作治疗的，可申请病假。  \r\n2. 申请病假须提供二级以上医院出具的诊断证明或病假条。  \r\n3. 病假期间工资发放标准：  \r\n   - 连续病假在30天以内（含），按基本工资的80%发放；  \r\n   - 超过30天的，按当地最低工资标准的80%发放；  \r\n   - 病假超过6个月的，按国家规定进入医疗期管理。  \r\n4. 医疗期按国家规定执行，医疗期满仍不能工作的，公司有权依法解除劳动合同。\r\n\r\n### 第七条 事假  \r\n1. 员工因私事必须本人处理的，可申请事假。  \r\n2. 事假需提前申请并获直属主管批准，紧急情况可事后补办手续。  \r\n3. 事假为无薪假，按日扣除相应工资。  \r\n4. 每月事假原则上不超过3天，全年累计不超过15天，特殊情况需经人力资源部及公司领导审批。\r\n\r\n### 第八条 婚假  \r\n1. 员工依法登记结婚的，可享受婚假。  \r\n2. 婚假为连续10天（含法定3天+公司福利7天），自结婚登记之日起6个月内有效。  \r\n3. 婚假期间工资全额发放。\r\n\r\n### 第九条 产假与陪产假  \r\n1. **产假**：  \r\n   - 符合国家生育政策的女员工，享受产假158天（含国家规定98天+地方延长60天，具体以当地政策为准）。  \r\n   - 难产增加15天，多胞胎每多一胎增加15天。  \r\n   - 产假期间工资按国家生育保险规定发放，公司依法协助办理生育津贴申领。  \r\n\r\n2. **陪产假**：  \r\n   - 男员工在配偶生育期间可享受陪产假15天（含周末，不可拆分）。  \r\n   - 陪产假期间工资全额发放。\r\n\r\n3. 员工须提供结婚证、出生证明等相关材料。\r\n\r\n### 第十条 丧假  \r\n1. 员工直系亲属（父母、配偶、子女）去世，可享受丧假3天。  \r\n2. 若亲属在外地，可根据实际情况给予1-2天路程假，路程假为无薪假。  \r\n3. 丧假期间工资照常发放。\r\n\r\n### 第十一条 其他假期  \r\n1. **哺乳假**：  \r\n   - 女员工生育后一年内，每天可享受1小时哺乳时间（含往返），多胞胎每多一婴增加1小时。  \r\n   - 可将每天哺乳时间合并使用，如需调整，需提前申请。  \r\n\r\n2. **工伤假**：  \r\n   - 因工负伤的员工，经认定后享受工伤假，待遇按国家工伤保险条例执行。  \r\n\r\n3. **育儿假**（如地方政策支持）：  \r\n   - 符合条件的父母在子女3周岁前，每年可享受10天育儿假，工资照发。\r\n\r\n---\r\n\r\n## 第三章 休假申请与审批流程\r\n\r\n**第十二条 申请方式**  \r\n1. 所有休假均需通过公司OA系统或书面填写《员工请假申请表》提交。  \r\n2. 请假需提前申请：  \r\n   - 年休假、婚假、产假等至少提前7个工作日申请；  \r\n   - 事假、病假至少提前1个工作日申请（突发病假可事后补交材料）。  \r\n\r\n**第十三条 审批权限**  \r\n- 3天以内（含）：直属主管审批；  \r\n- 3-7天：部门负责人审批；  \r\n- 7天以上：人力资源部审核，分管领导审批；  \r\n- 产假、婚假等特殊假期需人力资源部备案。\r\n\r\n**第十四条 调休与加班**  \r\n1. 因工作需要安排员工在法定节假日加班的，应优先安排补休，无法补休的按国家规定支付加班工资。  \r\n2. 员工加班可申请调休，调休应在加班后30日内使用，逾期视为放弃。\r\n\r\n---\r\n\r\n## 第四章 附则\r\n\r\n**第十五条 违规处理**  \r\n1. 伪造病假证明或提供虚假材料的，一经查实，按旷工处理，并视情节给予警告、扣薪或解除劳动合同。  \r\n2. 未经批准擅自离岗的，按旷工处理，旷工1天扣3天工资，连续旷工3天及以上视为自动离职。\r\n\r\n**第十六条 制度解释与修订**  \r\n1. 本制度由公司人力资源部负责解释。  \r\n2. 公司可根据国家政策变化及经营需要，对本制度进行修订，修订后经公示生效。\r\n\r\n**第十七条 生效日期**  \r\n本制度自发布之日起施行，原有相关规定与本制度不一致的，以本制度为准。\r\n\r\n---\r\n\r\n**公司名称**：________________________  \r\n**发布日期**：_______年___月___日  \r\n**人力资源部（盖章）**：  \r\n\r\n', path=None, url=None, mimetype=None), image_resource=None, audio_resource=None, video_resource=None, text_template='{metadata_str}\n\n{content}')]
```

```python
# 添加一个新的 Document
from llama_index.core import Document
text = "CEO 可以直接请假，无需向直接领导汇报"

doc = Document(
    text = text,
    metadata = {
        "author": "wilson yin",
        "title": "CEO 请假申请",
        "id": "1234567890"
    }
)
```

```python
print(doc)
```

输出：

```text
Doc ID: 717e30e9-260e-4c99-afdd-2b7e5462211d
Text: CEO 可以直接请假，无需向直接领导汇报
```

```python
#  手动切分Documents

from  llama_index.core.schema import TextNode

n1 = TextNode(text=doc.text[0:8],doc_id=doc.id_)
n2 = TextNode(text=doc.text[9:16],doc_id=doc.id_)

print(n1)
print(n2)
```

输出：

```text
Node ID: 8a8d453c-54c7-48c5-878d-960cdc1e1377
Text: CEO 可以直接
Node ID: 73303cda-7273-4cab-a88a-6208eed00852
Text: 假，无需向直接
```

```python
from llama_index.core.node_parser import TokenTextSplitter
from llama_index.core import Document

doc = Document(
    text=("""
    ### 第七条 事假
    1. 员工因私事必须本人处理的，可申请事假。
    2. 事假需提前申请并获直属主管批准，紧急情况可事后补办手续。
    3. 事假为无薪假，按日扣除相应工资。
    4. 每月事假原则上不超过3天，全年累计不超过15天，特殊情况需经人力资源部及公司领导审批。
    """
    ),
    metadata={"title": "Vacation Questions"}
)

# 内置切分器

splitter = TokenTextSplitter(
    chunk_size=64,
    chunk_overlap=4,
    separator="\n"
)

nodes = splitter.get_nodes_from_documents([doc])

for node in nodes:
    print(node.text)
    print(node.metadata)
```

输出：

```text
### 第七条 事假
    1. 员工因私事必须本人处理的，可申请事假。
{'title': 'Vacation Questions'}
2. 事假需提前申请并获直属主管批准，紧急情况可事后补办手续。
{'title': 'Vacation Questions'}
3. 事假为无薪假，按日扣除相应工资。
{'title': 'Vacation Questions'}
4. 每月事假原则上不超过3天，全年累计不超过15天，特殊情况需经人力资源部及公司领导审批。
{'title': 'Vacation Questions'}
```
