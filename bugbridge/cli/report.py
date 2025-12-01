"""
CLI Commands for Report Generation

Command-line interface for manually triggering report generation.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from click import Context

from bugbridge.agents.reporting import get_reporting_agent
from bugbridge.models.report_filters import ReportFilters
from bugbridge.utils.logging import get_logger
from bugbridge.workflows.reporting import execute_reporting_workflow

logger = get_logger(__name__)


@click.group(name="report")
def report_group() -> None:
    """Report generation commands."""
    pass


@report_group.command(name="generate")
@click.option(
    "--date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Date for which to generate report (YYYY-MM-DD). Defaults to yesterday.",
)
@click.option(
    "--start-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Start date for date range filter (YYYY-MM-DD).",
)
@click.option(
    "--end-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="End date for date range filter (YYYY-MM-DD).",
)
@click.option(
    "--board-ids",
    multiple=True,
    help="Filter by board IDs (can be specified multiple times).",
)
@click.option(
    "--tags",
    multiple=True,
    help="Filter by tags (can be specified multiple times).",
)
@click.option(
    "--statuses",
    multiple=True,
    help="Filter by post statuses (can be specified multiple times).",
)
@click.option(
    "--sentiment",
    multiple=True,
    help="Filter by sentiment categories (can be specified multiple times).",
)
@click.option(
    "--bug-only",
    is_flag=True,
    help="Only include items identified as bugs.",
)
@click.option(
    "--feature-only",
    is_flag=True,
    help="Only include feature requests (non-bugs).",
)
@click.option(
    "--min-priority",
    type=int,
    help="Minimum priority score (0-100).",
)
@click.option(
    "--min-votes",
    type=int,
    help="Minimum number of votes.",
)
@click.option(
    "--jira-projects",
    multiple=True,
    help="Filter by Jira project keys (can be specified multiple times).",
)
@click.option(
    "--jira-statuses",
    multiple=True,
    help="Filter by Jira ticket statuses (can be specified multiple times).",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    help="Output file path to save report content (optional).",
)
@click.option(
    "--json-output",
    is_flag=True,
    help="Output results as JSON instead of formatted text.",
)
@click.pass_context
def generate_report(
    ctx: Context,
    date: Optional[datetime],
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    board_ids: tuple[str, ...],
    tags: tuple[str, ...],
    statuses: tuple[str, ...],
    sentiment: tuple[str, ...],
    bug_only: bool,
    feature_only: bool,
    min_priority: Optional[int],
    min_votes: Optional[int],
    jira_projects: tuple[str, ...],
    jira_statuses: tuple[str, ...],
    output: Optional[Path],
    json_output: bool,
) -> None:
    """
    Generate a custom report with optional filters.

    Examples:
        # Generate report for yesterday
        bugbridge report generate

        # Generate report for specific date
        bugbridge report generate --date 2025-01-15

        # Generate report with date range
        bugbridge report generate --start-date 2025-01-01 --end-date 2025-01-31

        # Generate bug-only report
        bugbridge report generate --bug-only --min-priority 70

        # Generate report for specific board and tags
        bugbridge report generate --board-ids board1 --tags urgent --tags bug

        # Save report to file
        bugbridge report generate --output report.md
    """
    try:
        # Build filters if any filter options are provided
        filters = None
        if (
            start_date
            or end_date
            or board_ids
            or tags
            or statuses
            or sentiment
            or bug_only
            or feature_only
            or min_priority is not None
            or min_votes is not None
            or jira_projects
            or jira_statuses
        ):
            filters = ReportFilters(
                start_date=start_date,
                end_date=end_date,
                board_ids=list(board_ids) if board_ids else [],
                tags=list(tags) if tags else [],
                statuses=list(statuses) if statuses else [],
                sentiment_filter=list(sentiment) if sentiment else [],
                bug_only=bug_only,
                feature_only=feature_only,
                min_priority_score=min_priority,
                min_votes=min_votes,
                jira_project_keys=list(jira_projects) if jira_projects else [],
                jira_statuses=list(jira_statuses) if jira_statuses else [],
            )

        # Convert date to datetime if provided
        report_date = date

        click.echo("Generating report...", err=True)

        # Execute report generation
        result = asyncio.run(
            _generate_report_async(
                report_date=report_date,
                filters=filters,
            )
        )

        if json_output:
            # Output as JSON
            output_data = {
                "report_id": result.get("report_id"),
                "report_date": result.get("report_date").isoformat() if result.get("report_date") else None,
                "metrics": result.get("metrics"),
                "summary": result.get("summary"),
                "delivery": result.get("delivery"),
            }
            click.echo(json.dumps(output_data, indent=2, default=str))
        else:
            # Output formatted text
            click.echo(f"\n{'='*60}")
            click.echo("Report Generation Complete")
            click.echo(f"{'='*60}\n")
            click.echo(f"Report ID: {result.get('report_id')}")
            if result.get("report_date"):
                click.echo(f"Report Date: {result['report_date'].strftime('%Y-%m-%d')}")
            click.echo(f"\nMetrics:")
            metrics = result.get("metrics", {})
            click.echo(f"  - New Issues: {metrics.get('new_issues_count', 0)}")
            click.echo(f"  - Bugs: {metrics.get('bugs_count', 0)} ({metrics.get('bugs_percentage', 0):.1f}%)")
            click.echo(f"  - Feature Requests: {metrics.get('feature_requests_count', 0)}")
            click.echo(f"  - Tickets Created: {metrics.get('tickets_created', 0)}")
            click.echo(f"  - Tickets Resolved: {metrics.get('tickets_resolved', 0)}")
            click.echo(f"  - Resolution Rate: {metrics.get('resolution_rate', 0):.1f}%")

            # Delivery status
            delivery = result.get("delivery", {})
            if delivery:
                click.echo(f"\nDelivery Status:")
                if delivery.get("email", {}).get("success"):
                    click.echo(f"  ✓ Email sent successfully")
                elif delivery.get("email", {}).get("error"):
                    click.echo(f"  ✗ Email failed: {delivery['email']['error']}")
                if delivery.get("file_storage", {}).get("success"):
                    click.echo(f"  ✓ File saved: {delivery['file_storage'].get('file_path')}")
                elif delivery.get("file_storage", {}).get("error"):
                    click.echo(f"  ✗ File storage failed: {delivery['file_storage']['error']}")

        # Save report content to file if requested
        if output and result.get("content"):
            output.write_text(result["content"], encoding="utf-8")
            click.echo(f"\nReport content saved to: {output}", err=True)

    except Exception as e:
        logger.error(f"Failed to generate report: {str(e)}", exc_info=True)
        click.echo(f"Error: {str(e)}", err=True)
        ctx.exit(1)


async def _generate_report_async(
    report_date: Optional[datetime] = None,
    filters: Optional[ReportFilters] = None,
) -> dict:
    """
    Async wrapper for report generation.

    Args:
        report_date: Date for which to generate report.
        filters: Optional filters to apply.

    Returns:
        Report generation result dictionary.
    """
    agent = get_reporting_agent()
    result = await agent.generate_daily_report(report_date=report_date, filters=filters)
    return result


@report_group.command(name="workflow")
@click.option(
    "--date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Date for which to generate report (YYYY-MM-DD). Defaults to yesterday.",
)
@click.option(
    "--json-output",
    is_flag=True,
    help="Output results as JSON instead of formatted text.",
)
@click.pass_context
def generate_report_workflow(
    ctx: Context,
    date: Optional[datetime],
    json_output: bool,
) -> None:
    """
    Generate a report using the LangGraph workflow.

    This command uses the full reporting workflow instead of just the agent.
    """
    try:
        click.echo("Generating report via workflow...", err=True)

        result = asyncio.run(execute_reporting_workflow(report_date=date))

        if json_output:
            click.echo(json.dumps(result, indent=2, default=str))
        else:
            click.echo(f"\n{'='*60}")
            click.echo("Workflow Report Generation Complete")
            click.echo(f"{'='*60}\n")
            click.echo(f"Report ID: {result.get('report_id')}")
            if result.get("report_date"):
                click.echo(f"Report Date: {result['report_date'].strftime('%Y-%m-%d')}")
            if result.get("errors"):
                click.echo(f"\nErrors: {result['errors']}", err=True)

    except Exception as e:
        logger.error(f"Failed to generate report via workflow: {str(e)}", exc_info=True)
        click.echo(f"Error: {str(e)}", err=True)
        ctx.exit(1)


__all__ = [
    "report_group",
    "generate_report",
    "generate_report_workflow",
]

