from plugin_hot_reload_demo.models import PluginSpec


def greet(query: str) -> str:
    return f"greeting-v2:{query}"


PLUGIN = PluginSpec(name="greeting", description="Greeting plugin", handler=greet)
