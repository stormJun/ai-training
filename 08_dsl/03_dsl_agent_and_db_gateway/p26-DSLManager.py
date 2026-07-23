# -*- coding: utf-8 -*-
# Converted from p26-DSLManager.ipynb

# %% [markdown]
# Step 1：设计一个 DSL 管理器，用于管理和执行 DSL 规则。
#
# ```python
# import threading
# from typing import Dict, Callable
#
# class DSLManager:
#     def __init__(self):
#         self.workflows: Dict[str, Callable] = {}
#         self.lock = threading.Lock()
#         self.load_all_workflows()
#
#     def load_workflow(self, name: str, dsl_code: str):
#         """解析 DSL 并编译为可执行工作流"""
#         try:
#             ast = parse_with_antlr(dsl_code)
#             workflow = create_coffee_workflow(ast)  # 返回 LangGraph App
#             with self.lock:
#                 self.workflows[name] = workflow
#             logger.info(f" 已加载工作流: {name}")
#         except Exception as e:
#             logger.error(f" 加载失败 {name}: {e}")
#
#     def get_workflow(self, name: str):
#         with self.lock:
#             return self.workflows.get(name)
#
#     def reload_from_db(self):
#         """从数据库加载所有最新 DSL"""
#         for row in db.query("SELECT name, dsl_code FROM dsl_rules WHERE enabled=1"):
#             self.load_workflow(row.name, row.dsl_code)
# ```
# Step 2：支持热更新 API
#
# ```python
# from fastapi import FastAPI, HTTPException
#
# app = FastAPI()
# dsl_manager = DSLManager()
#
# @app.post("/reload")
# async def reload_dsl():
#     try:
#         dsl_manager.reload_from_db()
#         return {"status": "success", "message": "所有 DSL 规则已热更新"}
#     except Exception as e:
#         raise HTTPException(500, str(e))
#
# @app.post("/update_rule")
# async def update_rule(name: str, dsl_code: str):
#     # 先验证语法
#     try:
#         validate_with_antlr(dsl_code)
#     except Exception as e:
#         raise HTTPException(400, f"DSL 语法错误: {e}")
#
#     # 更新数据库
#     db.execute("UPDATE dsl_rules SET dsl_code=?, updated_at=CURRENT_TIMESTAMP WHERE name=?",
#                [dsl_code, name])
#
#     # 热加载
#     dsl_manager.load_workflow(name, dsl_code)
#     return {"status": "success", "message": f"{name} 已更新并生效"}
# ```
#
# Step 3：LangGraph 中无缝切换
# ```python
# def execute_workflow(state: CoffeeState):
#     # 每次都从最新管理器获取工作流（支持热更新）
#     app = dsl_manager.get_workflow(state["workflow_name"])
#     if not app:
#         return {"response": " 找不到该工作流"}
#
#     for output in app.stream(...):
#         pass
#     return output
# ```

# %% [markdown]
# Step 1：数据库表设计
#
# ```sql
# CREATE TABLE dsl_rules (
#     id INTEGER PRIMARY KEY,
#     name TEXT NOT NULL,
#     version TEXT NOT NULL,  -- 1.2.3
#     dsl_code TEXT NOT NULL,
#     author TEXT,
#     description TEXT,
#     enabled BOOLEAN DEFAULT 1,
#     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#     updated_at TIMESTAMP,
#     is_latest BOOLEAN DEFAULT 1
# );
# ```
#
# Step 2：版本操作接口
#
# ```python
# class DSLVersionControl:
#     @staticmethod
#     def save_new_version(name: str, dsl_code: str, author: str, desc: str = ""):
#         # 获取当前最新版本
#         latest = db.get(f"SELECT version FROM dsl_rules WHERE name=? AND is_latest=1", [name])
#         old_ver = latest[0] if latest else "1.0.0"
#
#         # 递增版本号（简单实现）
#         major, minor, patch = map(int, old_ver.split('.'))
#         new_ver = f"{major}.{minor}.{patch + 1}"
#
#         # 插入新版本
#         db.execute("""
#             INSERT INTO dsl_rules (name, version, dsl_code, author, description, is_latest)
#             VALUES (?, ?, ?, ?, ?, 1)
#         """, [name, new_ver, dsl_code, author, desc])
#
#         # 标记旧版本非最新
#         db.execute("UPDATE dsl_rules SET is_latest=0 WHERE name=? AND version=?", [name, old_ver])
#
#         return new_ver
#
#     @staticmethod
#     def rollback_to(name: str, version: str):
#         """回滚到指定版本"""
#         # 检查版本是否存在
#         row = db.get("SELECT * FROM dsl_rules WHERE name=? AND version=?", [name, version])
#         if not row:
#             raise ValueError("版本不存在")
#
#         # 禁用当前版本，启用目标版本
#         db.execute("UPDATE dsl_rules SET is_latest=0 WHERE name=? AND is_latest=1", [name])
#         db.execute("UPDATE dsl_rules SET is_latest=1 WHERE name=? AND version=?", [name, version])
#
#         # 热加载
#         dsl_manager.load_workflow(name, row.dsl_code)
#         return f"已回滚 {name} 到 {version}"
# ```
#
# Step 3：集成到 Web 控制台
#
# ```python
# @app.get("/rules/{name}/versions")
# async def list_versions(name: str):
#     rows = db.all("SELECT version, author, description, created_at FROM dsl_rules WHERE name=? ORDER BY created_at DESC", [name])
#     return {"versions": rows}
#
# @app.post("/rules/{name}/rollback")
# async def rollback(name: str, version: str):
#     result = DSLVersionControl.rollback_to(name, version)
#     return {"message": result}
# ```
