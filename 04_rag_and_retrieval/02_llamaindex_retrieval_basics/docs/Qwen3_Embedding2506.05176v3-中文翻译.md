# Qwen3 Embedding：通过基础模型推进文本嵌入和重排序

张彦照\* 明欣 $\mathrm { L i ^ { * } }$ 龙定坤\* 张欣\* 林焕 宝松 杨鹏军 谢安 杨大一恒 刘俊阳 林飞 黄敬仁 周统一实验室 阿里巴巴集团

https://huggingface.co/Qwen https://modelscope.cn/organization/qwen https://github.com/QwenLM/Qwen3-Embedding

# 摘要

在这项工作中，我们介绍了 Qwen3 Embedding 系列，它在文本嵌入和重排序功能方面比其前身 GTE-Qwen 系列取得了重大进步，建立在 Qwen3 基础模型的基础上。利用 Qwen3 LLM在多语言文本理解和生成方面的强大能力，我们创新的多阶段训练流程将大规模无监督预训练与高质量数据集的监督微调相结合。有效的模型合并策略进一步保证了Qwen3 Embedding系列的鲁棒性和适应性。在训练过程中，Qwen3 LLM不仅充当骨干模型，而且在合成跨多个领域和语言的高质量、丰富且多样化的训练数据方面发挥着至关重要的作用，从而增强了训练管道。 Qwen3 Embedding 系列为嵌入和重排序任务提供了一系列模型大小（0.6B、4B、8B），解决了用户可以优化效率或效果的不同部署场景。实证评估表明，Qwen3 Embedding 系列在不同的基准测试中均取得了最先进的结果。值得注意的是，它在文本嵌入的多语言评估基准 MTEB 以及各种检索任务（包括代码检索、跨语言检索和多语言检索）上表现出色。为了促进可重复性并促进社区驱动的研究和开发，Qwen3 嵌入模型在 Apache 2.0 许可证下公开可用。

# 1 简介

文本嵌入和重排序是许多自然语言处理和信息检索应用程序的基本组成部分，包括网络搜索、问答、推荐系统等（Karpukhin 等人，2020；Huang 等人，2020；Zhao 等人，2023；2024）。高质量的嵌入使模型能够捕获文本之间的语义关系，而有效的重排序机制可确保优先考虑最相关的结果。最近，在大型语言模型（例如Qwen3（Yang et al.，2025）、GPT-4o（Hurst et al.，2024））进步的推动下，诸如检索增强生成（RAG）和代理系统等新兴应用范式，在模型训练范式和应用场景方面都对文本嵌入和重排序提出了新的要求和挑战。尽管取得了重大进步，但训练在可扩展性、上下文理解以及与特定下游任务保持一致方面表现良好的嵌入和重排序模型仍然具有挑战性。

大型语言模型（LLM）的出现极大地推动了文本嵌入和重排序模型的发展。在引入LLM之前，主要方法涉及使用仅编码器预训练的语言模型（如 BERT）作为训练的基础模型（Reimers & Gurevych，2019）。LLM固有的更丰富的世界知识、文本理解和推理能力导致了在这些架构上训练的模型的进一步增强。此外，还有大量研究促进LLM融入训练数据合成和质量数据过滤等流程（Wang 等人，2024 年；Lee 等人，2024 年；2025b）。LLM的基本特征也激发了新培训模式的引入。例如，在嵌入模型训练过程中，将指令类型、领域和语言等方面的差异化任务结合起来，可以提高下游任务的性能（Su et al., 2023）。同样，对于重排序模型训练，基于用户提示的零样本方法和结合监督微调的方法都取得了进步（Ma et al., 2023; Pradeep et al., 2023; Zhuang et al., 2024a; Zhuang et al., 2024）。

在这项工作中，我们介绍了 Qwen3 Embedding 系列模型，它们是在 Qwen3 基础模型之上构建的。 Qwen3 基础模型同时发布了基础模型和指导模型版本，我们利用这些模型强大的多语言文本理解和生成能力，充分发挥它们在训练嵌入和重排序模型方面的潜力。为了训练嵌入模型，我们实现了一个多阶段训练管道，其中涉及大规模无监督预训练，然后对高质量数据集进行监督微调。我们还采用模型与各种模型检查点合并来增强鲁棒性和泛化性。 Qwen3 指令模型可以有效地合成大量、高质量、多语言和多任务的文本相关性数据集。该合成数据用于初始无监督训练阶段，而高质量、小规模数据的子集被选择用于监督训练的第二阶段。对于重排序模型，我们以类似的方式采用两阶段训练方案，包括高质量监督微调和模型合并阶段。基于不同大小的Qwen3主干模型（包括0.6B、4B和8B），我们最终训练了三个文本嵌入模型和三个文本重排序模型。为了促进其在下游任务中的应用，Qwen3 Embedding 系列支持多种实用功能，例如嵌入模型的灵活维度表示以及嵌入和重排序模型的可定制指令。

我们通过一套涵盖多个任务和领域的综合基准测试来评估 Qwen3 Embedding 系列。实验结果表明，我们的嵌入和重排序模型实现了最先进的性能，在多个检索任务中与领先的专有模型相比具有竞争力。例如，旗舰模型 Qwen3-8B-Embedding 在 MTEB 多语言基准测试（Enevoldsen et al., 2025）上获得 70.58 分，在 MTEB Code 基准测试（Enevoldsen et al., 2025）上获得 80.68 分，超越了之前最先进的专有嵌入模型 Gemini-Embedding（Lee et al., 2025）。 2025b）。此外，我们的重排序模型在一系列检索任务中提供了有竞争力的结果。 Qwen3-Reranker-0.6B 模型在众多检索任务中超越了之前表现最好的模型，而更大的 Qwen3-Reranker-8B 模型表现出更优越的性能，在多个任务中比 0.6B 模型提高了 3.0 个点的排名结果。此外，我们还开展了一项建设性消融研究，以阐明 Qwen3 Embedding 系列卓越性能的关键因素，并深入了解其有效性。

在接下来的部分中，我们将描述模型架构的设计，详细介绍训练过程，介绍 Qwen3 嵌入系列的嵌入和重排序模型的实验结果，并通过总结主要发现和概述未来研究的潜在方向来结束本技术报告。

# 2 模型架构

嵌入和重排序模型背后的核心思想是以任务感知的方式评估相关性。给定查询 $q$ 和文档 $d ,$ 嵌入和重排序模型根据指令 $I$ 定义的相似性标准评估它们的相关性。为了使模型能够进行任务感知相关性估计，训练数据通常被组织为 $\{ I _ { i } , q _ { i } , d _ { i } ^ { + } , d _ { i , 1 } ^ { - } , \cdot \cdot \cdot , d _ { i , n } ^ { - } \} ,$ ，其中 $d _ { i } ^ { + }$ 表示查询的正（相关）文档，$q _ { i } ,$ 和 $d _ { i , j } ^ { - }$ 是负（不相关）文档。在不同的文本对上训练模型可以扩大其对一系列下游任务的适用性，包括检索、语义文本相似性、分类和聚类。

![](Qwen3_Embedding2506.05176v3.pdf-ec5c4c97-7dc9-4436-8744-439f752f3e40/images/61da535763a80adc8e45cb681be5c94f05c06f1e262b5a8aa14060226000ae0b.jpg)  
图 1：Qwen3-Embedding（左）和 Qwen3-Reranker（右）的模型架构。

架构 Qwen3 嵌入和重排序模型建立在 Qwen3 基础模型的密集版本之上，并提供三种尺寸：0.6B、4B 和 8B 参数。我们使用 Qwen3 基础模型初始化这些模型，以利用它们在文本建模和指令跟踪方面的功能。表 1 详细介绍了每个模型配置的模型层、隐藏大小和上下文长度。

嵌入模型对于文本嵌入，我们利用具有因果注意力的LLM，在输入序列的末尾附加一个[EOS]标记。最终的嵌入源自与该[EOS]代币对应的最后一层的隐藏状态。

为了确保嵌入在下游任务期间遵循指令，我们将指令和查询连接到单个输入上下文中，同时在使用 LLM 处理之前保持文档不变。查询的输入格式如下：

{指令} {查询}<|endoftext|>

重排序模型 为了更准确地评估文本相似性，我们采用 LLM 在单个上下文中进行逐点重排序。与嵌入模型类似，为了启用指令跟踪功能，我们将指令包含在输入上下文中。我们使用 LLM 聊天模板，并将相似性评估任务构建为二元分类问题。 LLM 的输入遵循如下所示的模板：

<table><tr><td>Model Type</td><td>Models</td><td>Size</td><td>Layers</td><td>Sequence Length</td><td>Embedding Dimension</td><td>MRL Support</td><td>Instruction Aware</td></tr><tr><td>Text Embedding</td><td>Qwen3-Embedding-0.6B Qwen3-Embedding-4B Qwen3-Embedding-8B</td><td>0.6B 4B 8B</td><td>28 36 36</td><td>32K 32K 32K</td><td>1024 2560 4096</td><td>Yes Yes Yes</td><td>Yes Yes Yes</td></tr><tr><td>Text Reranking</td><td>Qwen3-Reranker-0.6B Qwen3-Reranker-4B Qwen3-Reranker-8B</td><td>0.6B 4B 8B</td><td>28 36 36</td><td>32K 32K 32K</td><td>- =</td><td>1</td><td>Yes Yes Yes</td></tr></table>

表 1：Qwen3 嵌入模型的模型架构。 “MRL Support”表示嵌入模型是否支持最终嵌入的自定义维度。 “指令感知”指出嵌入或重排序模型是否支持根据不同任务自定义输入指令。

![](Qwen3_Embedding2506.05176v3.pdf-ec5c4c97-7dc9-4436-8744-439f752f3e40/images/99b5c49d497c9a8a225b285887f2a1a42483adc36d9347178dab3a001faf856c.jpg)  
图 2：Qwen3 嵌入和重排序模型的训练流程。

为了根据给定的输入计算相关性得分，我们评估下一个标记为“yes”或 ${ } ^ { \prime \prime } \mathrm { n o }$ 的可能性。这在数学上表达如下：

$$
\mathrm { s c o r e } ( q , d ) = \frac { e ^ { P ( \mathrm { y e s } | I , q , d ) } } { e ^ { P ( \mathrm { y e s } | I , q , d ) } + e ^ { P ( \mathrm { n o } | I , q , d ) } }
$$

# 3 模型训练

在本节中，我们描述了所采用的多阶段训练流程，并介绍了该训练方案的关键要素，包括训练目标、训练数据合成和高质量训练数据的过滤。

# 3.1 训练目标

在介绍我们的训练流程之前，我们首先概述训练过程中用于嵌入和重排序模型的优化损失函数。对于嵌入模型，我们利用基于 InfoNCE 框架的改进对比损失（Oord 等人，2018）。给定一批 $N$ 训练实例，损失定义为：

$$
L _ { \mathrm { e m b e d d i n g } } = - \frac { 1 } { N } \sum _ { i } ^ { N } \log \frac { e ^ { ( s ( q _ { i } , d _ { i } ^ { + } ) / \tau ) } } { Z _ { i } } ,
$$

其中 $s ( \cdot , \cdot )$ 是相似度函数（我们使用余弦相似度），$\tau$ 是温度参数，$Z _ { i }$ 是聚合正对与各种负对的相似度得分的归一化因子：

$$
Z _ { i } = e ^ { ( s ( q _ { i } , d _ { i } ^ { + } ) / \tau ) } + \sum _ { k } ^ { K } m _ { i k } e ^ { ( s ( q _ { i } , d _ { i , k } ^ { - } ) / \tau ) } + \sum _ { j \neq i } m _ { i j } e ^ { ( s ( q _ { i } , q _ { j } ) / \tau ) } + \sum _ { j \neq i } m _ { i j } e ^ { ( s ( d _ { i } ^ { + } , d _ { j } ) / \tau ) } + \sum _ { j \neq i } m _ { i j } e ^ { ( s ( q _ { i } , d _ { j } ) / \tau ) }
$$

其中这些术语表示与以下项的相似性：(1) 正样本文档 $d _ { i } ^ { + }$ ，(2) $K$ 硬否定 $d _ { i , k } ^ { - } ,$ (3) 其他批内查询 $q _ { j } ,$ (4) 其他批内文档 $d _ { j }$ 与正样本文档 $d _ { i } ^ { + }$ 进行比较。 (5) 其他批处理文档 $d _ { j }$ 与查询 $q _ { i }$ 进行比较。掩模因子 $m _ { i j }$ 旨在减轻误负样本的影响，定义为：

$$
m _ { i j } = \left\{ \begin{array} { l l } { { 0 } } & { { \mathrm { i f } s _ { i j } > s ( q _ { i } , d _ { i } ^ { + } ) + 0 . 1 \mathrm { o r } d _ { j } = = d _ { i } ^ { + } , } } \\ { { 1 } } & { { \mathrm { o t h e r w i s e , } } } \end{array} \right.
$$

其中 $s _ { i j }$ 为 $q _ { i } , d _ { j }$ 或 $q _ { i } , q _ { j }$ 对应的分数。

对于重排序模型，我们优化了监督微调（SFT）损失，定义为：

$$
L _ { \mathrm { r e r a n k i n g } } = - \log p ( l | \mathcal { P } ( q , d ) ) ,
$$

其中 $p ( \cdot | * )$ 表示 LLM 分配的概率。对于正面文档，标签 $l$ 为“是”，对于负面文档，标签 $" \mathrm { n o } ^ { \prime \prime }$ 为“是”。这种损失函数鼓励模型为正确标签分配更高的概率，从而提高排名性能。

# 3.2 多阶段训练

多阶段训练方法是训练文本嵌入模型的常见做法（Li et al., 2023；Wang et al., 2022；Chen et al., 2024）。该策略通常从对包含噪声的大规模半监督数据进行初始训练开始，然后使用较小的高质量监督数据集进行微调。这个两步过程增强了嵌入模型的性能和泛化能力。大规模弱监督训练数据对模型的泛化能力有显着贡献，而后续阶段利用高质量数据进行微调则进一步提高模型性能。嵌入模型训练的两个阶段都使用等式 1 中定义的优化目标，而重排序模型训练则使用等式 2 中定义的损失函数作为优化目标。

Qwen3 Embedding 系列基于现有的多阶段训练框架，引入了以下关键创新：

大规模合成数据驱动的弱监督训练：与之前的工作（例如GTE、E5、BGE模型）不同，弱监督训练数据主要从问答论坛或学术论文等开源社区收集，我们建议利用基础模型的文本理解和生成能力来直接合成对数据。这种方法允许任意定义所需配对数据的各个维度，例如合成提示中的任务、语言、长度和难度。与来自开放域源的数据收集相比，基础模型驱动的数据合成提供了更大的可控性，能够精确管理生成数据的质量和多样性，特别是在资源匮乏的场景和语言中。   
• 监督微调中的高质量合成数据利用：由于Qwen3 Foundation 模型的卓越性能，合成数据的质量非常高。因此，在监督训练的第二阶段，选择性地合并这种高质量的合成数据进一步增强了模型的整体性能和泛化能力。   
• 模型合并：受之前工作（Li et al., 2024）的启发，在完成监督微调后，我们应用了基于球面线性插值（slerp）的模型合并技术。该技术涉及合并微调过程中保存的多个模型检查点。此步骤旨在提高模型在各种数据分布上的稳健性和泛化性能。

需要注意的是，重排序模型的训练过程不包括第一阶段的弱监督训练阶段。

# 3.3 综合数据集

为了创建一个强大的合成数据集来训练各种相似性任务的模型，我们生成了跨越检索、双文本挖掘、分类和语义文本相似性 (STS) 等类别的不同文本对。通过利用 Qwen3-32B 模型作为数据合成的基础模型，确保了这些合成数据对的质量。我们设计了多样化的提示策略来提高生成数据的多样性和真实性。例如，在文本检索任务中，我们使用 Qwen3 的多语言预训练语料库来合成数据。在数据合成过程中，会为每个文档分配特定角色，以模拟潜在用户查询该文档。用户视角的注入增强了综合查询的多样性和真实性。具体来说，我们利用检索模型从角色库中识别每个文档的前五个角色候选者，并将这些文档及其角色候选者呈现给提示。这指导模型输出最适合查询生成的角色配置。此外，提示还包含查询类型（例如关键字、事实、摘要、判断）、查询长度、难度和语言等各种维度。这种多维方法确保了合成数据的质量和多样性。

最后，我们总共创建了大约 1.5 亿对多任务弱监督训练数据。我们的实验表明，使用这些合成数据训练的嵌入模型在下游评估中表现得非常好，特别是在 MTEB 多语言基准测试中超越了许多先前监督的模型。这促使我们过滤合成数据，以识别高质量的配对，以便将其纳入监督训练的第二阶段。我们采用简单的余弦相似度计算来选择数据对，从随机采样的数据中保留余弦相似度大于 0.7 的数据对。最终，选择约1200万个高质量的监督训练数据对进行进一步训练。

<table><tr><td>Model</td><td>Size</td><td>Mean (Task)</td><td>Mean (Type)</td><td>Bitext Mining ification tering Retrieval</td><td>Class-</td><td>Clus-</td><td>Inst.</td><td>Multilabel Class.</td><td>Pair Class.</td><td>Rerank Retrieval STS</td><td></td><td></td></tr><tr><td colspan="10">Selected Open-Source Models</td></tr><tr><td>NV-Embed-v2</td><td>7B</td><td>56.29</td><td>49.58</td><td>57.84</td><td>57.29</td><td>40.80</td><td>1.04</td><td>18.63</td><td>78.94</td><td>63.82</td><td>56.72</td><td>71.10</td></tr><tr><td>GritLM-7B</td><td>7B</td><td>60.92</td><td>53.74</td><td>70.53</td><td>61.83</td><td>49.75</td><td>3.45</td><td>22.77</td><td>79.94</td><td>63.78</td><td>58.31</td><td>73.33</td></tr><tr><td>BGE-M3</td><td>0.6B</td><td>59.56</td><td>52.18</td><td>79.11</td><td>60.35</td><td>40.88</td><td>-3.11</td><td>20.1</td><td>80.76</td><td>62.79</td><td>54.60</td><td>74.12</td></tr><tr><td>multilingual-e5-large-instruct</td><td>0.6B</td><td>63.22</td><td>55.08</td><td>80.13</td><td>64.94</td><td>50.75</td><td>-0.40</td><td>22.91</td><td>80.86</td><td>62.61</td><td>57.12</td><td>76.81</td></tr><tr><td>gte-Qwen2-1.5B-instruct</td><td>1.5B</td><td>59.45</td><td>52.69</td><td>62.51</td><td>58.32</td><td>52.05</td><td>0.74</td><td>24.02</td><td>81.58</td><td>62.58</td><td>60.78</td><td>71.61</td></tr><tr><td>gte-Qwen2-7b-Instruct</td><td>7B</td><td>62.51</td><td>55.93</td><td>73.92</td><td>61.55</td><td>52.77</td><td>4.94</td><td>25.48</td><td>85.13</td><td>65.55</td><td>60.08</td><td>73.98</td></tr><tr><td colspan="10">Commercial APIs</td><td></td><td></td><td></td></tr><tr><td>text-embedding-3-large</td><td></td><td>58.93</td><td>51.41</td><td>62.17</td><td>60.27</td><td>46.89</td><td>-2.68</td><td>22.03</td><td>79.17</td><td>63.89</td><td>59.27</td><td>71.68</td></tr><tr><td>Cohere-embed-multilingual-v3.0</td><td></td><td>61.12</td><td>53.23</td><td>70.50</td><td>62.95</td><td>46.89</td><td>-1.89</td><td>22.74</td><td>79.88</td><td>64.07</td><td>59.16</td><td>74.80</td></tr><tr><td>Gemini Embedding</td><td></td><td>68.37</td><td>59.59</td><td>79.28</td><td>71.82</td><td>54.59</td><td>5.18</td><td>29.16</td><td>83.63</td><td>65.58</td><td>67.71</td><td>79.40</td></tr><tr><td colspan="10">Qwen3 Embedding Models</td></tr><tr><td>Qwen3-Embedding-0.6B</td><td>0.6B</td><td>64.33</td><td>56.00</td><td>72.22</td><td>66.83</td><td>52.33</td><td>5.09</td><td>24.59</td><td>80.83</td><td>61.41</td><td>64.64</td><td>76.17</td></tr><tr><td>Qwen3-Embedding-4B</td><td>4B</td><td>69.45</td><td>60.86</td><td>79.36</td><td>72.33</td><td>57.15</td><td>11.56</td><td>26.77</td><td>85.05</td><td>65.08</td><td>69.60</td><td>80.86</td></tr><tr><td>Qwen3-Embedding-8B</td><td>8B</td><td>70.58</td><td>61.69</td><td>80.89</td><td>74.00</td><td>57.65</td><td>10.06</td><td>28.66</td><td>86.40</td><td>65.63</td><td>70.88</td><td>81.08</td></tr></table>

表 2：MTEB 多语言性能（Enevoldsen 等人，2025）。对于比较模型，分数取自 2025 年 6 月 4 日的 MTEB 在线排行榜。

# 4 评价

我们在多个基准上进行全面、公平的评估，以评估 Qwen3 Embedding 模型的能力。

# 4.1 设置

对于文本嵌入模型，我们利用大规模多语言文本嵌入基准（MMTEB）（Enevoldsen 等人，2025）进行评估。 MMTEB 是 MTEB 的大规模、社区驱动的扩展（Muennighoff et al., 2023），涵盖 250 多种语言的 500 多个质量控制评估任务。除了各种检索、分类和语义文本相似性等经典文本任务外，MMTEB 还包括一系列具有挑战性和新颖性的任务，例如指令跟踪、长文档检索和代码检索，代表了迄今为止最大的嵌入模型多语言评估任务集合。我们的 MMTEB 评估包含 216 个单独的评估任务，其中包括 131 个 MTEB（多语言）任务（Enevoldsen et al., 2025）、41 个 MTEB 任务（英语，v2）（Muennighoff et al., 2023）、32 个 CMTEB 任务（Xiao et al., 2024）和 12 个 MTEB 代码检索任务（代码） （Enevoldsen 等人，2025）。

表 3：MTEB 英语、MTEB 中文、MTEB 代码的性能。 α 取自（Enevoldsen 等人，2025）。 γ 取自（Lee 等人，2025b）。对于其他比较模型，分数取自 2025 年 6 月 4 日的 MTEB 在线排行榜。   

<table><tr><td>Model</td><td>Size|Dim</td><td></td><td>MTEB (Eng, v2)</td><td colspan="2">CMTEB</td><td>MTEB (Code)</td></tr><tr><td colspan="7">|Mean (Task) Mean (Type)|Mean (Task) Mean (Type)|</td></tr><tr><td colspan="7">Selected Open-Source Models</td></tr><tr><td>NV-Embed-v2</td><td>7B</td><td>|4096 69.81</td><td>65.00</td><td>63.0</td><td>62.0</td><td></td></tr><tr><td>GritLM-7B</td><td>7B</td><td>4096</td><td>67.07 63.22 61.21</td><td>- -</td><td>1</td><td>73.6a</td></tr><tr><td>multilingual-e5-large-instruct</td><td>0.6B</td><td>1024</td><td>65.53</td><td></td><td>1</td><td>65.0a</td></tr><tr><td>gte-Qwen2-1.5b-instruct gte-Qwen2-7b-instruct</td><td>1.5B</td><td>1536</td><td>67.20 63.26 70.72</td><td>67.12</td><td>67.79</td><td>56.417</td></tr><tr><td></td><td>7B</td><td>3584</td><td>65.77</td><td>71.62</td><td>72.19</td><td></td></tr><tr><td colspan="7">Commercial APIs 66.43</td></tr><tr><td>text-embedding-3-large</td><td></td><td>3072</td><td>62.15</td><td></td><td></td><td>58.957</td></tr><tr><td>cohere-embed-multilingual-v3.0 Gemini Embedding</td><td></td><td>1024</td><td>66.01 61.43</td><td></td><td></td><td>51.94Y</td></tr><tr><td></td><td></td><td>3072</td><td>73.30 67.67</td><td></td><td></td><td>74.66Y</td></tr><tr><td colspan="7">Qwen3 Embedding Models</td></tr><tr><td>Qwen3-Embedding-0.6B</td><td>0.6B</td><td>1024</td><td>70.70 64.88</td><td>66.33 72.26</td><td>67.44</td><td>75.41</td></tr><tr><td>Qwen3-Embedding-4B</td><td>4B</td><td>2560</td><td>74.60</td><td>68.09</td><td>73.50</td><td>80.06</td></tr><tr><td>Qwen3-Embedding-8B</td><td>8B</td><td>4096</td><td>75.22</td><td>68.70 73.83</td><td>75.00</td><td>80.68</td></tr></table>

此外，我们选择了一系列文本检索任务来评估我们模型的文本重排序能力。我们探索了三种类型的检索任务：（1）基本相关性检索，分为英语、中文和多语言，分别在 MTEB (Muennighoff et al., 2023)、CMTEB (Xiao et al., 2024)、MMTEB (Enevoldsen et al., 2025) 和 MLDR (Chen et al., 2024) 上进行评估； (2) 代码检索，在 MTEB-Code 上评估（Enevoldsen et al., 2025），仅包含与代码相关的检索数据； (3) 复杂指令检索，在 FollowIR 上进行评估（Weller 等人，2024）。

比较方法 我们将我们的模型与最著名的开源文本嵌入模型和商业 API 服务进行比较。开源模型包括GTE（Li等人，2023；Zhang等人，2024b）、E5（Wang等人，2022）和BGE（Xiao等人，2024）系列，以及NVEmbed-v2（Lee等人，2025a）、GritLM-7B Muennighoff等人。 （2025）。评估的商业 API 包括来自 OpenAI 的 text-embedding-3-large、来自 Google 的 Gemini-embedding 和 Cohere-embedmultilingual- $\cdot \mathrm { v } 3 . 0$ 。对于重新排名，我们与 jina1、mGTE (Zhang et al., 2024b) 和 BGE- $\mathbf { \cdot m } 3$ (Chen et al., 2024) 的重新排名进行比较。

# 4.2 主要结果

嵌入 在表 2 中，我们展示了 MMTEB 的评估结果（Enevoldsen et al., 2025），它全面涵盖了跨多种语言的广泛嵌入任务。我们的 Qwen3-Embedding-4B/8B 模型实现了最佳性能，而我们最小的模型 Qwen3-Embedding-0.6B 尽管只有 0.6B 参数，但仅落后于性能最佳的基线方法 (Gemini-Embedding)。在表3中，我们列出了MTEB（英语，v2）（Muennighoff等人，2023）、CMTEB（Xiao等人，2024）和MTEB（代码）（Enevoldsen等人，2025）的评估结果。这些分数反映了与 MMTEB 类似的趋势，我们的 Qwen3-Embedding-4B/8B 模型始终优于其他模型。值得注意的是，Qwen3-Embedding-0.6B 模型排名仅落后于 Gemini-Embedding，同时与 gte-Qwen2-7B-instruct 具有竞争力。

表 4：重排序模型的评估结果。我们使用MTEB(eng, v2)、MTEB(cmn, v1)和MMTEB的检索子集，即MTEB-R、CMTEB-R和MMTEM-R。剩下的都是检索任务。所有分数都是我们根据第一行检索前 100 个结果得出的结果。   

<table><tr><td></td><td colspan="5">Basic Relevance Retrieval</td><td></td></tr><tr><td>Model</td><td></td><td colspan="5">Param|MTEB-R CMTEB-R MMTEB-R MLDR MTEB-Code FollowIR</td></tr><tr><td>Qwen3-Embedding-0.6B</td><td>0.6B</td><td>61.82</td><td>64.64</td><td>50.26</td><td>75.41</td><td>5.09</td></tr><tr><td>Jina-multilingual-reranker-v2-base</td><td>0.3B</td><td>58.22</td><td>63.73</td><td>39.66</td><td>58.98</td><td>-0.68</td></tr><tr><td>gte-multilingual-reranker-base</td><td>0.3B</td><td>59.51</td><td>59.44</td><td>66.33</td><td>54.18</td><td>-1.64</td></tr><tr><td>BGE-reranker-v2-m3</td><td>0.6B</td><td>57.03</td><td>58.36</td><td>59.51</td><td>41.38</td><td>-0.01</td></tr><tr><td>Qwen3-Reranker-0.6B</td><td>0.6B</td><td>65.80</td><td>66.36</td><td>67.28</td><td>73.42</td><td>5.41</td></tr><tr><td>Qwen3-Reranker-4B</td><td>4B</td><td>69.76</td><td>72.74</td><td>69.97</td><td>81.20</td><td>14.84</td></tr><tr><td>Qwen3-Reranker-8B</td><td>8B</td><td>69.02</td><td>75.94 77.45 72.94</td><td>70.19</td><td>81.22</td><td>8.05</td></tr></table>

<table><tr><td>Model</td><td>MMTEB</td><td>|MTEB (Eng,v2)|</td><td>CMTEB</td><td>|MTEB (Code, v1)</td></tr><tr><td>Qwen3-Embedding-0.6B w/ only synthetic data</td><td>58.49</td><td>60.63</td><td>59.78</td><td>66.79</td></tr><tr><td>Qwen3-Embedding-0.6B w/o synthetic data</td><td>61.21</td><td>65.59</td><td>63.37</td><td>74.58</td></tr><tr><td>Qwen3-Embedding-0.6B w/o model merge</td><td>62.56</td><td>68.18</td><td>64.76</td><td>74.89</td></tr><tr><td>Qwen3-Embedding-0.6B</td><td>64.33</td><td>70.70</td><td>66.33</td><td>75.41</td></tr></table>

表 5：不同训练设置下 Qwen3-Embedding-0.6B 模型在 MMTEB、MTEB(eng, v2)、CMTEB 和 MTEB(code, v1) 上的性能（平均任务）。

重排序 在表 4 中，我们展示了各种重排序任务的评估结果（第 4.1 节）。我们利用 Qwen3-Embedding-0.6B 模型来检索前 100 个候选者，然后应用不同的重排序模型进行进一步细化。这种方法确保了重排序模型的公平评估。我们的结果表明，与嵌入模型相比，所有三个 Qwen3-Reranker 模型都提高了性能，并超越了所有基线重排序方法，其中 Qwen3-Reranker-8B 在大多数任务中实现了最高性能。

# 4.3 分析

为了进一步分析和探讨Qwen3 Embedding模型训练框架的关键要素，我们从以下几个维度进行分析：

大规模弱监督预训练的有效性我们首先分析嵌入模型的大规模弱监督训练阶段的有效性。如表 5 所示，与最终的 Qwen3-Embedding-0.6B 模型（如最后一行所示）相比，仅在合成数据上训练的 Qwen3-Embedding- $\cdot 0 . 6 \mathrm { B }$ 模型（没有后续训练阶段，如第一行所示）实现了合理且强大的性能。如果我们进一步删除弱监督训练阶段（即没有合成数据训练，如第二行所示），最终性能会出现明显下降。这表明大规模弱监督训练阶段对于实现优异的性能至关重要。

模型合并的有效性接下来，我们比较模型合并阶段产生的性能差异。如表 5 所示，在没有模型合并技术的情况下训练的模型（第三行，使用数据采样来平衡各种任务）的性能比最终的 Qwen3-Embedding-0.6B 模型（采用模型合并，如最后一行所示）要差得多。这表明模型合并阶段对于开发强大的模型也至关重要。

# 5 结论

在本技术报告中，我们介绍了 Qwen3-Embedding 系列，这是一套基于 Qwen3 基础模型的综合文本嵌入和重排序模型。这些模型旨在擅长执行各种文本嵌入和重排序任务，包括多语言检索、代码检索和复杂指令跟踪。 Qwen3-Embedding 模型建立在强大的多阶段训练管道之上，该管道将合成数据上的大规模弱监督预训练与高质量数据集上的监督微调和模型合并相结合。 Qwen3 LLM在综合多种语言和任务的多样化训练数据方面发挥着至关重要的作用，从而增强了模型的能力。我们的综合评估表明，Qwen3-Embedding 模型在各种基准测试中实现了最先进的性能，包括 MTEB、CMTEB、MMTEB 和多个检索基准测试。我们很高兴开源 Qwen3-Embedding 和 Qwen3-Reranker 模型（0.6B、4B 和 8B），使它们可供社区使用和构建。

# 参考

陈建吕、肖世涛、张培田、罗昆、连德福和刘正。 M3-embedding：通过自我知识蒸馏实现多语言、多功能、多粒度的文本嵌入。计算语言学协会的调查结果：ACL 2024，第 2318–2335 页，泰国曼谷，2024 年 8 月。计算语言学协会。网址 https://aclanthology.org/2024.findings-acl.137/。   
Kenneth Enevoldsen、Isaac Chung、Imene Kerboua、Marton Kardos、Ashwin Mathur、David Stap、Jay Gala、Wissam Siblini、Dominik Krzeminski、Genta Indra Winata 等。 MMTEB：大规模多语言文本嵌入基准。第十三届学习表征国际会议，2025 年。URL https://openreview.net/forum?id=zl3pfz4VCV.   
葛涛、陈鑫、王晓阳、于殿、米海涛、于冬。使用 1,000,000,000 个角色扩展合成数据创建。 arXiv 预印本 arXiv:2406.20094, 2024。   
Jui-Ting Huang、Ashish Sharma、Shuying Sun、Li Xia、David 张、Philip Pronin、Janani Padmanabhan、Giuseppe Ottaviano 和 Linjun Yang。 Facebook 搜索中基于嵌入的检索。第 26 届 ACM SIGKDD 国际知识发现与数据挖掘会议论文集，第 2553-2561 页，2020 年。   
Aaron Hurst、Adam Lerer、Adam P Goucher、Adam Perelman、Aditya Ramesh、Aidan Clark、AJ Ostrow、Akila Welihinda、Alan Hayes、Alec Radford 等。 Gpt-4o系统卡。 arXiv 预印本 arXiv:2410.21276, 2024。   
Vladimir Karpukhin、Barlas Oguz、Sewon Min、Patrick SH Lewis、Ledell Wu、Sergey Edunov、Danqi Chen 和 Wen-tau Yih。用于开放域问答的密集段落检索。载于 EMNLP (1)，第 6769–6781 页，2020 年。   
Chankyu Lee、Rajarshi Roy、Mengyao Xu、Jonathan Raiman、Mohammad Shoeybi、Bryan Catanzaro 和 Wei Ping。 Nv-embed：改进了将 llms 训练为通用嵌入模型的技术。 arXiv 预印本 arXiv:2405.17428, 2024。   
Chankyu Lee、Rajarshi Roy、Mengyao Xu、Jonathan Raiman、Mohammad Shoeybi、Bryan Catanzaro 和 Wei Ping。 NV-embed：改进了将 LLM 训练为通用嵌入模型的技术。第十三届学习表征国际会议，2025a。网址 https://openreview.net/forum?id=lgsyLSsDRe。   
Jinhyuk Lee、Feiyang Chen、Sahil Dua、Daniel Cer、Madhuri Shanbhogue、Iftekhar Naim、Gustavo Hernandez ´ Abrego、Zhe Li、Kaifeng Chen、Henrique Schechter Vera 等。 Gemini 嵌入：来自 Gemini 的可泛化嵌入。 arXiv 预印本 arXiv:2503.07891, 2025b。

李明欣、聂志杰、张艳照、龙定坤、张日冲、谢鹏军。改进通用文本嵌入模型：通过模型合并解决任务冲突和数据不平衡。 arXiv 预印本 arXiv:2410.15035, 2024。

李泽涵、张鑫、张艳照、龙定坤、谢鹏军和张美山。通过多阶段对比学习实现一般文本嵌入，2023。URL https://arxiv.org/ abs/2308.03281。

马学光、张新宇、罗纳克·普拉迪普和林吉米。使用大型语言模型进行零样本列表文档重排序。 arXiv 预印本 arXiv:2305.02156, 2023。

尼克拉斯·穆尼尼霍夫 (Niklas Muennighoff)、努阿曼·塔齐 (Nouamane Tazi)、卢伊克·马涅 (Loic Magne) 和尼尔斯·雷默斯 (Nils Reimers)。 MTEB：海量文本嵌入基准。计算语言学协会欧洲分会第 17 届会议记录，第 2014-2037 页，克罗地亚杜布罗夫尼克，2023 年 5 月。计算语言学协会。网址https://aclanthology.org/2023.eacl-main.148/.

Niklas Muennighoff、Su Hongjin、Liang Wang、Nan Yang、Furu Wei、Tao Yu、Amanpreet Singh 和 Douwe Kiela。生成代表性指令调整。第十三届学习表征国际会议，2025 年。URL https://openreview.net/forum?id $\cdot ^ { = }$ BC4lIvfSzv。

亚伦·范登奥尔德、李亚哲和奥里奥尔·维尼亚尔斯。具有对比预测编码的表示学习。 arXiv 预印本 arXiv:1807.03748, 2018。

罗纳克·普拉迪普 (Ronak Pradeep)、萨赫勒·沙里菲莫加达姆 (Sahel Sharifymoghaddam) 和林志颖 (Jimmy Lin)。 Rankvicuna：使用开源大型语言模型进行零样本列表文档重新排名。 arXiv 预印本 arXiv:2309.15088, 2023。

尼尔斯·雷默斯和伊琳娜·古列维奇。 Sentence-BERT：使用 Siamese BERT 网络的句子嵌入。 2019 年自然语言处理经验方法会议和第九届自然语言处理国际联合会议 (EMNLP-IJCNLP) 论文集，第 3982–3992 页，中国香港，2019 年 11 月。计算语言学协会。网址https://aclanthology.org/D19-1410/.

Hongjin Su、Weijia Shi、Jungo Kasai、王一中、Yushi Hu、Mari Ostendorf、Wen-tau Yih、Noah A Smith、Luke Zettlemoyer 和Tao Yu。一台嵌入器，任何任务：指令微调文本嵌入。计算语言学协会的调查结果：ACL 2023，第 1102–1121 页，2023 年。

王亮、杨南、黄小龙、焦滨兴、杨林军、姜大新、Rangan Majumder 和 Furu Wei。通过弱监督对比预训练进行文本嵌入，2022 年。URL https://arxiv.org/abs/2212.03533.

王亮、杨南、黄小龙、杨林军、Rangan Majumder 和 Furu Wei。使用大型语言模型改进文本嵌入。计算语言学协会第 62 届年会论文集（第一卷：长论文），第 11897–11916 页，泰国曼谷，2024 年 8 月。计算语言学协会。网址 https://aclanthology.org/2024.acl-long.642/。

Orion Weller、Benjamin Chang、Sean MacAvaney、Kyle Lo、Arman Cohan、Benjamin Van Durme、Dawn Lawrie 和 Luca Soldaini。 Followir：评估和教授信息检索模型以遵循指令。 arXiv 预印本 arXiv:2403.15246, 2024。

肖世涛、刘峥、张培田、Niklas Muennighoff、连德福、聂建云。 C-pack：一般中文嵌入的打包资源。第 47 届国际 ACM SIGIR 信息检索研究与开发会议论文集，SIGIR ’24，第 641–649 页，美国纽约州纽约，2024 年。计算机协会。网址https://doi.org/10.1145/ 3626772.3657878。

安阳，李安峰，杨宝松，张北辰，惠斌源，郑波，于博文，高昌，黄承恩，吕晨旭，等。 Qwen3技术报告。 arXiv 预印本 arXiv:2505.09388, 2025。

张龙辉、张艳照、龙定坤、谢鹏军、张美山、张敏。用于文本排名的大型语言模型的两阶段改编。摘自计算语言学协会 ACL 2024 的调查结果，第 11880–11891 页，2024a。

张鑫、张艳照、龙定坤、谢文、戴子奇、唐家龙、林焕、杨宝松、谢鹏军、黄飞、张美山、李文杰和张敏。 mGTE：用于多语言文本检索的通用长上下文文本表示和重排序模型。载于 Franck Dernoncourt、Daniel Preot¸iuc-Pietro 和 Anastasia Shimorina（编辑），2024 年自然语言处理经验方法会议论文集：行业轨迹，第 1393-1412 页，美国佛罗里达州迈阿密，2024 年 11 月b。计算语言学协会。 doi：10.18653/v1/2024.emnlp-industry.103。网址https://aclanthology.org/2024.emnlp-industry.103/.

赵鑫、刘静、任瑞阳和文继荣。基于预训练语言模型的密集文本检索：一项调查。 ACM 信息系统学报，42(4):1–60，2024 年。

赵翔宇、王茂林、赵新建、李建生、周树成、尹大伟、李庆、唐吉良和郭若成。嵌入推荐系统：一项调查。 arXiv 预印本 arXiv:2310.18608, 2023。

庄盛耀、庄红雷、Bevan Koopman 和 Guido Zuccon。一种使用大型语言模型进行有效且高效的零样本排名的集合方法。第 47 届国际 ACM SIGIR 信息检索研究与开发会议论文集，第 38-47 页，2024 年。

# 附录

# A.1 综合数据

我们构建了四种类型的合成数据——检索、双文本挖掘、语义文本相似性和分类，使模型能够在预训练期间适应各种相似性任务。为了确保多语言和跨语言的多样性，数据是使用 Qwen3 32B 生成的。以下是合成检索文本对的示例。检索数据是使用文档查询方法合成的。我们从Qwen3基础模型的预训练语料中收集多语言语料作为文档源。然后应用两阶段生成管道，包括：(1) 配置和 (2) 查询生成。在配置阶段，我们使用大型语言模型（LLM）来确定综合查询的“问题类型”、“难度”和“特征”。从 Persona Hub 中检索候选字符（Ge et al., 2024），选择与给定文档最相关的前五个字符。此步骤旨在增强生成的查询的多样性。使用的模板如下：

给定 \*\*Passage\*\* 和 $\hookrightarrow$ 三个字段：Character、Question_Type、Difficulty，并返回输出 $^ { * * }$ Character\*\*，从 JSON 格式的 $\hookrightarrow$ 中选择适当的选项。

首先，从候选者中选择可能对$\hookrightarrow$段落感兴趣的角色。然后选择角色 $\hookrightarrow$ 可能会询问该段落的 Question_Type；最后，根据文章、人物和 $\hookrightarrow$ 问题类型选择 $\hookrightarrow$ 可能问题的难度。

字符：由输入\*\*字符\*\*给出

问题类型：

- 关键词： ... 获取知识： ... 摘要： ...   
- 是还是不是： ...   
- 背景： ...

困难：

- 高中：... - 大学：... - 博士：

以下是一些示例 <示例1> <示例2> <示例3>

现在，根据 $\hookrightarrow$ 用户的 \*\*Passage\*\* 和 $^ { * * }$ 字符 $^ { * * }$ 生成 \*\* 输出 \*\*，\*\*Passage\*\* 将采用 {language} 语言，而 $^ { * * }$ 字符 \*\* $\hookrightarrow$ 将采用英语。

确保仅生成包含英文内容的 JSON 输出。

\*\*段落\*\*: {段落} \*\*字符\*\*: {字符}

在查询生成阶段，我们使用第一阶段选择的配置来指导查询的生成。此外，我们还明确指定生成的查询所需的长度和语言。使用的模板如下：

给定 $^ { * * }$ 字符\*\*、\*\*通道\*\* 和 $^ { * * }$ 要求\*\*，从 $\hookrightarrow$ 的 \*\* 字符\*\* 视角生成满足 \*\* 要求\*\* 的查询，并且可以使用 $\hookrightarrow$ 检索 \*\*通道\*\*。请以 JSON $\hookrightarrow$ 格式返回结果。

这是一个示例：<示例>

现在，根据用户的\*\*Character\*\*、\*\*Passage\*\* 和 $\hookrightarrow$ \*\*Requirement\*\* 生成\*\*output\*\*，\*\*Passage\*\* 将采用 {corpus_language} $\hookrightarrow$ 语言，\*\*Character\*\* 和 \*\*Requirement\*\* 将采用英语。确保仅生成 JSON 输出，键为英语，值 $\hookrightarrow$ 为 {queries_language} 语言。

$^ { * * }$ 人物\*\* {人物} \*\*段落\*\* {段落} \*\*要求\*\*

- 类型：{类型}；   
难度：{难度}；   
长度：生成句子的长度应为{length}个单词；   
Languange：生成结果的语言应为$\hookrightarrow$ {language}语言；

表6：各阶段使用的训练数据统计。   

<table><tr><td>Stage</td><td>Dataset</td><td>Size</td></tr><tr><td>Weakly Supervised Pre-Training</td><td>Synthetic Data</td><td>~ 150M</td></tr><tr><td>Supervised Fine Tuning</td><td>MS MARCO, NQ, HotpotQA, NLI, Dureader, T²-Ranking, SimCLUE, MIRACL,MLDR, Mr.TyDi, Multi-CPR, CodeSearchNet .etc + High-quality Synthetic Data</td><td>Labeled Data:~ 7M Synthetic Data: ~ 12M</td></tr></table>

# A.2 详细结果

<table><tr><td>MTEB(eng, v2)</td><td>Param</td><td>Mean (Task)</td><td>Mean (Type)</td><td>Class- ification</td><td>Clus- tering</td><td>Pair Class.</td><td>Rerank</td><td>Retrieval</td><td>STS</td><td>Summ.</td></tr><tr><td>multilingual-e5-large-instruct</td><td>0.6B</td><td>65.53</td><td>61.21</td><td>75.54</td><td>49.89</td><td>86.24</td><td>48.74</td><td>53.47</td><td>84.72</td><td>29.89</td></tr><tr><td>NV-Embed-v2</td><td>7.8B</td><td>69.81</td><td>65.00</td><td>87.19</td><td>47.66</td><td>88.69</td><td>49.61</td><td>62.84</td><td>83.82</td><td>35.21</td></tr><tr><td>GritLM-7B</td><td>7.2B</td><td>67.07</td><td>63.22</td><td>81.25</td><td>50.82</td><td>87.29</td><td>49.59</td><td>54.95</td><td>83.03</td><td>35.65</td></tr><tr><td>gte-Qwen2-1.5B-instruct</td><td>1.5B</td><td>67.20</td><td>63.26</td><td>85.84</td><td>53.54</td><td>87.52</td><td>49.25</td><td>50.25</td><td>82.51</td><td>33.94</td></tr><tr><td>stella_en_1.5B_v5</td><td>1.5B</td><td>69.43</td><td>65.32</td><td>89.38</td><td>57.06</td><td>88.02</td><td>50.19</td><td>52.42</td><td>83.27</td><td>36.91</td></tr><tr><td>gte-Qwen2-7B-instruct</td><td>7.6B</td><td>70.72</td><td>65.77</td><td>88.52</td><td>58.97</td><td>85.9</td><td>50.47</td><td>58.09</td><td>82.69</td><td>35.74</td></tr><tr><td>gemini-embedding-exp-03-07</td><td>-</td><td>73.3</td><td>67.67</td><td>90.05</td><td>59.39</td><td>87.7</td><td>48.59</td><td>64.35</td><td>85.29</td><td>38.28</td></tr><tr><td>Qwen3-Embedding-0.6B</td><td>0.6B</td><td>70.70</td><td>64.88</td><td>85.76</td><td>54.05</td><td>84.37</td><td>48.18</td><td>61.83</td><td>86.57</td><td>33.43</td></tr><tr><td>Qwen3-Embedding-4B</td><td>4B</td><td>74.60</td><td>68.09</td><td>89.84</td><td>57.51</td><td>87.01</td><td>50.76</td><td>68.46</td><td>88.72</td><td>34.39</td></tr><tr><td>Qwen3-Embedding-8B</td><td>8B</td><td>75.22</td><td>68.70</td><td>90.43</td><td>58.57</td><td>87.52</td><td>51.56</td><td>69.44</td><td>88.58</td><td>34.83</td></tr></table>

表 7：MTEB(eng, v2) 结果（Muennighoff 等人，2023）。我们比较在线排行榜上的模型。

表 8：C-MTEB 结果（Xiao 等人，2024）（MTEB（cmn，v1）。  

<table><tr><td>MTEB(cmn, v1)</td><td>Param</td><td>Mean (Task)</td><td>Mean (Type)</td><td>Class- ification</td><td>Clus- tering</td><td>Pair Class.</td><td>Rerank</td><td>Retrieval</td><td>STS</td></tr><tr><td>multilingual-e5-large-instruct</td><td>0.6B</td><td>58.08</td><td>58.24</td><td>69.80</td><td>48.23</td><td>64.52</td><td>57.45</td><td>63.65</td><td>45.81</td></tr><tr><td>gte-Qwen2-7B-instruct</td><td>7.6B</td><td>71.62</td><td>72.19</td><td>75.77</td><td>66.06</td><td>81.16</td><td>69.24</td><td>75.70</td><td>65.20</td></tr><tr><td>gte-Qwen2-1.5B-instruct</td><td>1.5B</td><td>67.12</td><td>67.79</td><td>72.53</td><td>54.61</td><td>79.5</td><td>68.21</td><td>71.86</td><td>60.05</td></tr><tr><td>Qwen3-Embedding-0.6B</td><td>0.6B</td><td>66.33</td><td>67.44</td><td>71.40</td><td>68.74</td><td>76.42</td><td>62.58</td><td>71.03</td><td>54.52</td></tr><tr><td>Qwen3-Embedding-4B</td><td>4B</td><td>72.26</td><td>73.50</td><td>75.46</td><td>77.89</td><td>83.34</td><td>66.05</td><td>77.03</td><td>61.26</td></tr><tr><td>Qwen3-Embedding-8B</td><td>8B</td><td>73.84</td><td>75.00</td><td>76.97</td><td>80.08</td><td>84.23</td><td>66.99</td><td>78.21</td><td>63.53</td></tr></table>

<table><tr><td>MTEB(Code,v1)</td><td>Avg.</td><td>Apps</td><td>COIR- CodeSearch- Net</td><td>Code- Edit- Search</td><td>Code- Feedback- MT</td><td>Code- Feedback- ST</td><td>Code- SearchNet- CCR</td><td>Code- SearchNet</td><td>Code- Trans- Ocean- Contest</td><td>Code- Trans- Ocean-DL</td><td></td><td>Stack- CosQA Overflow- QA</td><td>Synthetic- Text2SQL</td></tr><tr><td>BGEmultilingual</td><td>62.04</td><td>22.93</td><td>68.14</td><td>60.48</td><td>60.52</td><td>76.70</td><td>73.23</td><td>83.43</td><td>86.84</td><td>32.64</td><td>27.93</td><td>92.93</td><td>58.67</td></tr><tr><td>NV-Embed-v2</td><td>63.74</td><td>29.72</td><td>61.85</td><td>73.96</td><td>60.27</td><td>81.72</td><td>68.82</td><td>86.61</td><td>89.14</td><td>33.40</td><td>34.82</td><td>92.36</td><td>60.90</td></tr><tr><td>gte-Qwen2-7B-instruct</td><td>62.17</td><td>28.39</td><td>71.79</td><td>67.06</td><td>57.66</td><td>85.15</td><td>66.24</td><td>86.96</td><td>81.83</td><td>32.17</td><td>31.26</td><td>84.34</td><td>53.22</td></tr><tr><td>gteQwestrct68</td><td></td><td>28.91</td><td>71.56</td><td>59.60</td><td>49.92</td><td>81.92</td><td>72.08</td><td>91.08</td><td>79.02</td><td>32.73</td><td>32.23</td><td>90.27</td><td>54.49</td></tr><tr><td>BGE-M3 (Dense)</td><td>58.22</td><td>14.77</td><td>58.07</td><td>59.83</td><td>47.86</td><td>69.27</td><td>53.55</td><td>61.98</td><td>86.22</td><td>29.37</td><td>27.36</td><td>80.71</td><td>49.65</td></tr><tr><td>Jina-v3</td><td>58.85</td><td>28.99</td><td>67.83</td><td>57.24</td><td>59.66</td><td>78.13</td><td>54.17</td><td>85.50</td><td>77.37</td><td>30.91</td><td>35.15</td><td>90.79</td><td>41.49</td></tr><tr><td>Qwen3-Embedding-0.6B 75.41</td><td></td><td>75.34</td><td>84.69</td><td>64.42</td><td>90.82</td><td>86.39</td><td>91.72</td><td>91.01</td><td>86.05</td><td>31.36</td><td>36.48</td><td>89.99</td><td>76.74</td></tr><tr><td>Qwen3-Embedding-4B</td><td>80.06</td><td>89.18</td><td>87.93</td><td>76.49</td><td>93.21</td><td>89.51</td><td>95.59</td><td>92.34</td><td>90.99</td><td>35.04</td><td>37.98</td><td>94.32</td><td>78.21</td></tr><tr><td>Qwen3-Embedding-8B</td><td>80.68</td><td>91.07</td><td>89.51</td><td>76.97</td><td>93.70</td><td>89.93</td><td>96.35</td><td>92.66</td><td>93.73</td><td>32.81</td><td>38.04</td><td>94.75</td><td>78.75</td></tr><tr><td>Qwen3-Reranker-0.6B</td><td>73.42</td><td>69.43</td><td>85.09</td><td>72.37</td><td>83.83</td><td>78.05</td><td>94.76</td><td>88.8</td><td>84.69</td><td>33.94</td><td>36.83</td><td>93.24</td><td>62.48</td></tr><tr><td>Qwen3-Reranker-4B</td><td>81.20</td><td>94.25</td><td>90.91</td><td>82.53</td><td>95.25</td><td>88.54</td><td>97.58</td><td>92.48</td><td>93.66</td><td>36.78</td><td>35.14</td><td>97.11</td><td>75.06</td></tr><tr><td>Qwen3-Reranker-8B</td><td>81.22</td><td>94.55</td><td>91.88</td><td>84.58</td><td>95.64</td><td>88.43</td><td>95.67</td><td>92.78</td><td>90.83</td><td>34.89</td><td>37.43</td><td>97.3</td><td>73.4</td></tr></table>

表 9：MTEB（代码，v1）上的性能（Enevoldsen 等人，2025）。我们报告 nDCG@10 分数。
