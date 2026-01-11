"""
Entry Point for CrewAI Execution.
Implements Issue #72: Executable entry point for crew operations.

Usage:
    python run_crew.py --project-id PROJECT_ID --run-id RUN_ID

Per PRD Section 4, 6, 9:
- Initialize agents and tasks
- Execute crew.kickoff()
- Store run metadata in agent_memory
- Print summary to stdout
- Log events for audit trail

Example:
    $ python run_crew.py --project-id proj_demo_001 --run-id run_001
"""

import asyncio
import argparse
import logging
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

from crew import create_crew
from app.services.agent_memory_service import agent_memory_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('crew_execution.log')
    ]
)

logger = logging.getLogger(__name__)


async def store_execution_metadata(
    project_id: str,
    run_id: str,
    result: Any,
    duration_seconds: float,
    status: str
) -> None:
    """
    Store crew execution metadata in agent_memory.

    Per Issue #72:
    - Store run metadata for audit trail
    - Track execution duration and status
    - Enable replay and analysis

    Args:
        project_id: Project identifier
        run_id: Execution run identifier
        result: Crew execution result
        duration_seconds: Execution duration in seconds
        status: Execution status (success, failed, error)
    """
    try:
        metadata = {
            "duration_seconds": duration_seconds,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "agent_count": 3,
            "workflow": "sequential",
            "result_summary": str(result)[:500] if result else "No result"
        }

        await agent_memory_service.store_memory(
            project_id=project_id,
            agent_id="crew_orchestrator",
            run_id=run_id,
            memory_type="result",
            content=f"Crew execution completed with status: {status}",
            metadata=metadata
        )

        logger.info(f"Stored execution metadata for run {run_id}")
    except Exception as e:
        logger.error(f"Failed to store execution metadata: {e}", exc_info=True)


def print_summary(
    project_id: str,
    run_id: str,
    result: Any,
    duration_seconds: float,
    status: str
) -> None:
    """
    Print execution summary to stdout.

    Per Issue #72:
    - Human-readable summary output
    - Include execution metrics
    - Display agent results

    Args:
        project_id: Project identifier
        run_id: Execution run identifier
        result: Crew execution result
        duration_seconds: Execution duration
        status: Execution status
    """
    print("\n" + "=" * 80)
    print("CREW EXECUTION SUMMARY")
    print("=" * 80)
    print(f"Project ID: {project_id}")
    print(f"Run ID: {run_id}")
    print(f"Status: {status.upper()}")
    print(f"Duration: {duration_seconds:.2f} seconds")
    print(f"Timestamp: {datetime.utcnow().isoformat()}")
    print("-" * 80)

    if result:
        print("RESULTS:")
        if isinstance(result, dict):
            print(json.dumps(result, indent=2))
        else:
            print(str(result))
    else:
        print("No results generated")

    print("=" * 80 + "\n")


async def main(
    project_id: str,
    run_id: str,
    inputs: Optional[Dict[str, Any]] = None,
    verbose: bool = False
) -> Any:
    """
    Main execution function for CrewAI crew.

    Per Issue #72:
    - Initialize crew with all agents
    - Execute crew.kickoff()
    - Store metadata and results
    - Print summary

    Args:
        project_id: Project identifier
        run_id: Execution run identifier
        inputs: Optional input data for crew execution
        verbose: Enable verbose output

    Returns:
        Crew execution result

    Raises:
        Exception: If crew creation or execution fails
    """
    logger.info(f"Starting crew execution for project {project_id}, run {run_id}")

    start_time = datetime.utcnow()
    result = None
    status = "error"

    try:
        # Create crew
        logger.info("Creating crew with 3 agents...")
        crew = await create_crew(
            project_id=project_id,
            run_id=run_id,
            verbose=verbose
        )

        logger.info(f"Crew created successfully with {len(crew.agents)} agents")

        # Execute crew
        logger.info("Executing crew.kickoff()...")
        if inputs:
            result = crew.kickoff(inputs=inputs)
        else:
            result = crew.kickoff()

        logger.info("Crew execution completed successfully")
        status = "success"

    except Exception as e:
        logger.error(f"Crew execution failed: {e}", exc_info=True)
        status = "failed"
        result = {"error": str(e)}
        raise

    finally:
        # Calculate duration
        end_time = datetime.utcnow()
        duration_seconds = (end_time - start_time).total_seconds()

        # Store metadata
        try:
            await store_execution_metadata(
                project_id=project_id,
                run_id=run_id,
                result=result,
                duration_seconds=duration_seconds,
                status=status
            )
        except Exception as e:
            logger.warning(f"Failed to store metadata: {e}")

        # Print summary
        print_summary(
            project_id=project_id,
            run_id=run_id,
            result=result,
            duration_seconds=duration_seconds,
            status=status
        )

    return result


def parse_arguments():
    """
    Parse command-line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Execute CrewAI crew with 3 agent personas",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic execution
  python run_crew.py --project-id proj_demo_001 --run-id run_001

  # Verbose mode
  python run_crew.py --project-id proj_demo_001 --run-id run_001 --verbose

  # With input data
  python run_crew.py --project-id proj_demo_001 --run-id run_001 --input '{"transaction": "BTC_USDT"}'
        """
    )

    parser.add_argument(
        '--project-id',
        required=True,
        help='Project identifier (e.g., proj_demo_001)'
    )

    parser.add_argument(
        '--run-id',
        required=True,
        help='Run identifier (e.g., run_001)'
    )

    parser.add_argument(
        '--input',
        type=str,
        default=None,
        help='Input data as JSON string (optional)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )

    return parser.parse_args()


if __name__ == "__main__":
    # Parse arguments
    args = parse_arguments()

    # Parse input JSON if provided
    inputs = None
    if args.input:
        try:
            inputs = json.loads(args.input)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON input: {e}")
            sys.exit(1)

    # Run crew
    try:
        result = asyncio.run(main(
            project_id=args.project_id,
            run_id=args.run_id,
            inputs=inputs,
            verbose=args.verbose
        ))

        # Exit with success
        sys.exit(0)

    except Exception as e:
        logger.error(f"Execution failed: {e}", exc_info=True)
        sys.exit(1)
