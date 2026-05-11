# LangGraph 工作流学习路径

本目录已按学习顺序整理文件名，便于顺序阅读与查找。Notebook 内容已转换为 Markdown 与 Python 脚本，根目录不再保留 `.ipynb` 文件。

## 推荐学习顺序

- `01_基础对话链意图识别_设计.pdf`
  - 基础链路与意图识别设计资料
- `02_工作流编排_讲师文稿.txt`
  - 讲师主讲稿
- `03_工作流编排_讲师笔记.txt`
  - 讲师笔记与补充说明
- `04_人机协同_HITL.md` / `04_人机协同_HITL.py`
  - 人机协同与中断恢复
- `05_记忆机制_基础.md` / `05_记忆机制_基础.py`
  - LangGraph 记忆基础
- `06_记忆机制_Mem0.md` / `06_记忆机制_Mem0.py`
  - Mem0 记忆方案
- `07_LangGraph_入门示例.md` / `07_LangGraph_入门示例.py`
  - LangGraph 最小入门示例
- `08_LangGraph_核心概念_状态与节点.md` / `08_LangGraph_核心概念_状态与节点.py`
  - 状态、节点、边与图执行模型
- `09_RAG工作流_基础.md` / `09_RAG工作流_基础.py`
  - RAG 工作流基础
- `10_快照机制_Snapshot.md` / `10_快照机制_Snapshot.py`
  - 快照与检查点
- `11_LangGraph_Studio.md` / `11_LangGraph_Studio.py`
  - LangGraph Studio 使用方式
- `12_参考论文_2510.11967v1.pdf`
  - 参考论文
- `13_智能客服系统架构设计.pdf`
  - 智能客服架构资料
- `14_深度思考总结.md`
  - 课程总结与扩展思考

## 资料导航（建议）

- LangGraph 工程化笔记：`docs/langgraph.md`
- LangGraph 工程模板：
  - `app/`：LangGraph Server + Studio（适合演示/可视化调试）
  - `app2/`：工作流工程化示例（分层 + pytest）

## 开始使用

以下说明将帮助您在本地机器上设置和运行此项目，以便进行开发和学习。

### 环境要求

*   Python 3.11 或更高版本
*   已安装 [uv](https://github.com/astral-sh/uv)。`uv` 是一个极速的 Python 包安装工具。

### 安装步骤

1.  **安装依赖:**
    在项目根目录中打开终端，然后运行：
    ```bash
	cd 06_langgraph_basics/21_langgraph_workflows
	pip install uv
    uv sync --locked
    ```
    这将自动安装依赖并在当前目录下创建一个名为 `.venv` 的虚拟环境目录。

2.  **激活虚拟环境:**
    *   在 macOS 和 Linux 上:
        ```bash
        source .venv/bin/activate
        ```
    *   在 Windows 上:
        ```bash
        .venv\Scripts\activate
        ```

## 设置项目专属的 Jupyter 内核

为了确保您的 notebook 使用本项目定义的特定 Python 环境和依赖项，您可以将其注册为自定义的 Jupyter 内核。

1.  **激活虚拟环境:**
    首先，请确保您已经激活了项目的虚拟环境。
    ```bash
    source .venv/bin/activate
    ```

2.  **注册内核:**
    运行以下命令，将当前环境注册为一个新的 Jupyter 内核：
    ```bash
    python -m ipykernel install --user --name=workflow_orchestration --display-name="AI工程化(Workflow)"
    ```

	运行下面的命令查看当前的 kernel 列表：
	```bash
	jupyter kernelspec list
	```
	应该能看到类似下面的输出:
	```bash
	Available kernels:
	workflow_orchestration     /Users/your_username/Library/Jupyter/kernels/workflow_orchestration
	python3    /usr/local/share/jupyter/kernels/python3
	```
	如果看到 `workflow_orchestration` 在列表中，则说明注册成功。
	

## 运行 JupyterLab

安装完成后，您可以运行 JupyterLab。

1.  **启动 JupyterLab:**
    在您的终端中（确保虚拟环境仍处于激活状态），运行：
    ```bash
    jupyter lab
    ```
    这将启动 Jupyter 服务，并在您的默认网络浏览器中打开一个新标签页。

2.  **打开学习材料:**
    优先阅读根目录下按 `01_` 到 `14_` 编号整理好的 `.md`、`.py`、`.txt` 和 `.pdf` 文件。

3.  **选择内核:**
    如果你需要在 Jupyter 中自行实验代码，可以在 **Kernel > Change kernel** 菜单中看到并选择 **"AI工程化(Workflow)"**。这可以确保代码在正确的项目环境中运行。
