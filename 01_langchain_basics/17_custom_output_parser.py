"""Custom output parser example for project reports."""

from typing import List

from langchain_core.output_parsers import BaseOutputParser
from langchain_core.prompts import StringPromptTemplate
from pydantic import BaseModel, Field


class ProjectReport(BaseModel):
    """项目报告数据模型。"""

    project_name: str = Field(description="项目名称")
    progress: str = Field(description="进度状态")
    completed_tasks: List[str] = Field(description="已完成任务")
    pending_tasks: List[str] = Field(description="待完成任务")
    risks: List[str] = Field(description="风险点")


class ProjectReportTemplate(StringPromptTemplate):
    """自定义项目报告提示模板。"""

    language_style: str = Field(default="professional", description="语言风格")

    def format(self, **kwargs) -> str:
        return (
            f"请用{self.language_style}风格生成项目报告。\n"
            f"项目名称：{kwargs['project_name']}\n"
            f"进度：{kwargs['progress']}\n"
            f"已完成任务：{kwargs['completed_tasks']}\n"
            f"待完成任务：{kwargs['pending_tasks']}\n"
            f"风险点：{kwargs['risks']}\n"
        )

    @property
    def input_variables(self) -> List[str]:
        return [
            "project_name",
            "progress",
            "completed_tasks",
            "pending_tasks",
            "risks",
        ]


class ProjectReportParser(BaseOutputParser[ProjectReport]):
    """把文本解析为项目报告对象。"""

    def parse(self, text: str) -> ProjectReport:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        data = {}
        for line in lines:
            if "：" not in line:
                continue
            key, value = line.split("：", 1)
            data[key] = value

        return ProjectReport(
            project_name=data.get("项目名称", ""),
            progress=data.get("进度", ""),
            completed_tasks=[
                item.strip() for item in data.get("已完成任务", "").split("、") if item.strip()
            ],
            pending_tasks=[
                item.strip() for item in data.get("待完成任务", "").split("、") if item.strip()
            ],
            risks=[item.strip() for item in data.get("风险点", "").split("、") if item.strip()],
        )


if __name__ == "__main__":
    template = ProjectReportTemplate()
    parser = ProjectReportParser()

    # 这里用手工文本代替真实 LLM 输出，方便先理解“模板 + 解析器”的关系。
    raw_text = template.format(
        project_name="智能客服项目",
        progress="开发中",
        completed_tasks="登录功能、FAQ检索",
        pending_tasks="多轮对话、监控看板",
        risks="需求变更、接口延迟",
    )
    print(raw_text)
    print(parser.parse(raw_text))
