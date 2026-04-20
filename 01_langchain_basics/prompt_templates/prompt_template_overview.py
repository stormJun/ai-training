"""Overview script for prompt template examples."""

from pathlib import Path


def main() -> None:
    base_dir = Path(__file__).resolve().parent / "examples"

    print("Prompt 模板相关脚本：")
    print(f"- {base_dir / 'simple_demo.py'}")
    print(f"- {base_dir / 'custom_prompt_template_engineering.py'}")
    print(f"- {base_dir / 'test_template.py'}")
    print(f"- {base_dir / 'ext_template.py'}")
    print()
    print("建议阅读顺序：")
    print("1. simple_demo.py")
    print("2. custom_prompt_template_engineering.py")
    print("3. test_template.py")
    print("4. ext_template.py")


if __name__ == "__main__":
    main()
