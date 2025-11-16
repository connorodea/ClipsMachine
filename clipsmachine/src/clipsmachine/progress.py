"""
Rich CLI progress tracking and beautiful output for clipsmachine.
"""

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
    TimeElapsedColumn,
)
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich import box

console = Console()


def print_header(title: str, subtitle: str = ""):
    """Print a beautiful header."""
    text = Text()
    text.append(title, style="bold cyan")
    if subtitle:
        text.append(f"\n{subtitle}", style="dim")

    console.print(Panel(text, border_style="cyan", box=box.DOUBLE))


def print_step(step_num: int, total_steps: int, title: str):
    """Print a step header."""
    text = Text()
    text.append(f"[{step_num}/{total_steps}] ", style="bold magenta")
    text.append(title, style="bold white")
    console.print(f"\n{text}")


def print_success(message: str):
    """Print a success message."""
    console.print(f"✓ {message}", style="bold green")


def print_warning(message: str):
    """Print a warning message."""
    console.print(f"⚠ {message}", style="bold yellow")


def print_error(message: str):
    """Print an error message."""
    console.print(f"✗ {message}", style="bold red")


def print_info(message: str):
    """Print an info message."""
    console.print(f"ℹ {message}", style="cyan")


def create_progress_bar() -> Progress:
    """Create a beautiful progress bar."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(complete_style="cyan", finished_style="green"),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    )


def print_summary_table(clips: list, subtitle_type: str = None):
    """Print a summary table of generated clips."""
    table = Table(
        title="Generated Clips Summary",
        box=box.ROUNDED,
        title_style="bold cyan",
        header_style="bold magenta",
    )

    table.add_column("#", style="cyan", justify="right")
    table.add_column("Duration", style="yellow")
    table.add_column("Title", style="white")
    if subtitle_type:
        table.add_column("Subtitles", style="green")

    for clip in clips:
        duration = f"{clip.get('duration', 0):.1f}s"
        title = clip.get('title', 'Untitled')[:50]
        if len(clip.get('title', '')) > 50:
            title += "..."

        row = [str(clip.get('clip_index', 0)), duration, title]
        if subtitle_type:
            row.append(subtitle_type.capitalize())

        table.add_row(*row)

    console.print("\n")
    console.print(table)


def print_completion_message(
    video_id: str,
    clip_count: int,
    total_time: float,
):
    """Print a beautiful completion message."""
    text = Text()
    text.append("🎉 Processing Complete!\n\n", style="bold green")
    text.append(f"Video ID: ", style="bold white")
    text.append(f"{video_id}\n", style="cyan")
    text.append(f"Clips Generated: ", style="bold white")
    text.append(f"{clip_count}\n", style="green")
    text.append(f"Total Time: ", style="bold white")
    text.append(f"{total_time:.1f}s", style="yellow")

    console.print("\n")
    console.print(Panel(text, border_style="green", box=box.DOUBLE))
