"""LangGraph Studio 使用命令备忘。

这个文件不是可执行工作流，而是把 Studio 相关的常用命令按学习顺序整理出来，
方便在终端里逐条执行。
"""

# 1. 安装 LangGraph CLI
# pip install -U "langgraph-cli[inmem]"

# 2. 可选：安装 debugpy，用于节点级断点调试
# pip install debugpy

# 3. 从模板创建一个新的 LangGraph 项目
# langgraph new "/absolute/path/to/my_graph_app" --template new-langgraph-project-python

# 4. 在本仓库的最小服务化示例里启动本地 API
# cd /Users/songxijun/workspace/otherProject/ai-training/02_langgraph_basics/03_service_apps/projects/02_langgraph_server_minimal
# langgraph dev

# 5. 或者在更接近业务流程的示例里启动
# cd /Users/songxijun/workspace/otherProject/ai-training/02_langgraph_basics/03_service_apps/projects/03_order_workflow_app
# langgraph dev

# 6. 启动后，终端通常会输出：
#    - API 地址
#    - OpenAPI /docs 地址
#    - LangGraph Studio 的浏览器链接

# 7. 调试时优先观察：
#    - 图结构
#    - 输入状态
#    - 节点输出
#    - 条件边路由结果
