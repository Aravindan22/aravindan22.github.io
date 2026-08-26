from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

console = Console()

def print_rich_snapshot(snapshot):
    # 1. Header Information (Step & Next Node)
    step = snapshot.metadata.get("step", "N/A")
    next_nodes = ", ".join(snapshot.next) if snapshot.next else "END"

    header_text = Text()
    header_text.append("Execution Step: ", style="bold cyan")
    header_text.append(str(step), style="bold yellow")
    header_text.append("  |  Next Node(s): ", style="bold magenta")
    header_text.append(next_nodes, style="bold red" if next_nodes == "END" else "bold green")

    console.print(Panel(header_text, title="[bold white]LangGraph StateSnapshot[/bold white]", border_style="cyan"))

    # 2. Config Table (Detailed breakdown of configurable values)
    config_table = Table(title="🔧 Snapshot Config", show_header=True, header_style="bold green", expand=True)
    config_table.add_column("Config Key", style="bold white", width=20)
    config_table.add_column("Value", style="cyan")

    configurable = snapshot.config.get("configurable", {})
    for key, val in configurable.items():
        # Highlight checkpoint_id in yellow for visibility
        val_style = "[bold yellow]" if key == "checkpoint_id" else ""
        config_table.add_row(key, f"{val_style}{val}")

    console.print(config_table)

    # 3. State Values Table
    state_table = Table(title="📦 State Values", show_header=True, header_style="bold blue", expand=True)
    state_table.add_column("Key", style="bold white", width=20)
    state_table.add_column("Value / Content", style="white")

    for key, value in snapshot.values.items():
        if key == "messages":
            msg_tree = Tree("[bold cyan]Messages Stream[/bold cyan]")
            for msg in value:
                role = msg.__class__.__name__.replace("Message", "").upper()
                role_color = {
                    "SYSTEM": "magenta",
                    "HUMAN": "green",
                    "AI": "yellow",
                    "TOOL": "blue"
                }.get(role, "white")
                msg_tree.add(f"[{role_color}][bold]{role}:[/bold] {msg.content}[/{role_color}]")
            
            state_table.add_row("messages", msg_tree)
        else:
            state_table.add_row(key, f"[yellow]{repr(value)}[/yellow]")

    console.print(state_table)
    console.print("\n" + "─" * 60 + "\n")

    
def print_rich_all_snapshots(snapshots):
    console.print("[bold green]=== FETCHING GRAPH HISTORY ===[/bold green]\n")
    for snapshot in snapshots:
        print_rich_snapshot(snapshot)