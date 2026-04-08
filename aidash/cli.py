"""Main CLI entry point with Click group."""

import click


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """aidash — Track and analyze your usage across AI coding agents."""


@cli.command()
def replay():
    """Play back any coding session as a terminal timeline."""
    click.echo("Not implemented yet")


@cli.command()
def cost():
    """Unified cost dashboard across all agents."""
    click.echo("Not implemented yet")


@cli.command()
def score():
    """Rate your sessions on a 0-100 efficiency scale."""
    click.echo("Not implemented yet")


@cli.command()
def rates():
    """Compare pricing across models and agents."""
    click.echo("Not implemented yet")


@cli.command()
def search():
    """Full-text search across all sessions."""
    click.echo("Not implemented yet")
