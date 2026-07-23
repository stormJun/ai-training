<!-- Converted from p32-SLM.ipynb -->

## 1. 权重量化（Quantization）
将 FP32 转为 INT8/INT4 等低位精度。

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import bitsandbytes as bnb

model_id = "EleutherAI/gpt-neo-125M"
model = AutoModelForCausalLM.from_pretrained(model_id, load_in_8bit=True, device_map="auto")
tokenizer = AutoTokenizer.from_pretrained(model_id)
```

## 2. 权重剪枝（Pruning）
删除不重要的权重连接以减小模型规模。可用 torch.nn.utils.prune 实现。
```python
import torch.nn.utils.prune as prune

prune.random_unstructured(model.transformer.h[0].attn.c_proj, name="weight", amount=0.3)
```

## 3. 知识蒸馏（Knowledge Distillation）
训练一个小模型 mimick 大模型的行为。
```python
# 简化伪代码
teacher_logits = teacher(input_ids).logits
student_logits = student(input_ids).logits
loss = nn.KLDivLoss()(F.log_softmax(student_logits), F.softmax(teacher_logits))
```


参考来源： https://cloud.tencent.com/developer/article/2546431
