"""Custom LLM interface notes."""

# 原 notebook 的主要信息是：
# 实际工作中可能会使用私有部署模型或公司网关，
# 因此需要掌握模型接入时的自定义参数。


def show_notes() -> None:
    print("自定义大模型接口常见参数：")
    print("- base_url")
    print("- api_key")
    print("- model")
    print("- temperature")
    print("- timeout / retries / proxy")


if __name__ == "__main__":
    show_notes()
