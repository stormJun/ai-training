from plugin_hot_reload_demo.models import PluginSpec


def invoice(query: str) -> str:
    return f"invoice-ok:{query}"


PLUGIN = PluginSpec(name="invoice", description="Invoice plugin", handler=invoice)
