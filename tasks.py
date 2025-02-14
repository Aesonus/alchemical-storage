"""Cli tools for managing this project."""

import time

import click
import invoke
import watchdog.events
import watchdog.observers


@invoke.task
def build_docs(ctx: invoke.Context, clean=False) -> None:
    """Build the project documentation."""
    if clean:
        ctx.run("rm -rfv docs/build")
    ctx.run("poetry run sphinx-build docs/source docs/build")


@invoke.task(build_docs)
def watch_docs(ctx: invoke.Context) -> None:
    """Watch the project documentation for changes and rebuild on change."""

    class _Handler(watchdog.events.FileSystemEventHandler):
        last_event = 0

        def on_modified(self, event):
            last_event = self.last_event
            now = time.time()
            self.last_event = now
            if now - last_event < 5:
                click.secho(f"Ignoring change in {event} due to DEBOUNCE", fg="yellow")
                return
            if not (event.src_path.endswith(".rst") or event.src_path.endswith(".py")):
                click.secho(f"Ignoring change in {event}", fg="yellow")
                return
            click.secho(f"Detected change in {event}", fg="green")
            ctx.run("poetry run sphinx-build docs/source docs/build")

    observer = watchdog.observers.Observer()
    handler = _Handler()
    for dir_ in ["docs/source", "alchemical_storage"]:
        observer.schedule(
            handler,
            dir_,
            recursive=True,
            event_filter=[watchdog.events.FileModifiedEvent],
        )
    click.secho("Watching docs and module for changes...", fg="magenta")

    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        click.secho("Stopping watcher...", fg="red")
        observer.stop()
    observer.join()
