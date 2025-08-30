"""
Daytona Sandbox Health Checks

This module provides health checks for the Daytona sandbox environment:
- Basic connectivity and command execution
- Workspace directory setup and verification
- Filesystem operations testing
- Integration with tool runtime system
"""

import os
import logging
import tempfile
from typing import Dict, Any, Optional
from sandbox.sandbox import Sandbox

logger = logging.getLogger(__name__)

class SandboxHealthError(Exception):
    """Exception raised when sandbox health checks fail."""
    pass

class SandboxHealthChecker:
    """
    Health checker for Daytona sandbox environment.

    Performs comprehensive checks to ensure the sandbox is ready for tool execution:
    - Basic command execution (echo test)
    - Workspace directory setup
    - File operations (create, read, delete)
    - Network connectivity if needed
    """

    def __init__(self, sandbox: Sandbox):
        self.sandbox = sandbox
        self.workspace_path = "~/workspace"
        self.test_timeout = 30  # seconds

    async def assert_daytona_ready(self) -> Dict[str, Any]:
        """
        Perform comprehensive health checks on the Daytona sandbox.

        Returns:
            Dictionary with health check results

        Raises:
            SandboxHealthError: If any critical health check fails
        """
        results = {
            "checks": {},
            "overall_status": "unknown",
            "errors": []
        }

        try:
            # Check 1: Basic command execution
            echo_result = await self._check_basic_command_execution()
            results["checks"]["basic_command"] = echo_result

            # Check 2: Workspace directory setup
            workspace_result = await self._check_workspace_directory()
            results["checks"]["workspace_directory"] = workspace_result

            # Check 3: Filesystem operations
            fs_result = await self._check_filesystem_operations()
            results["checks"]["filesystem_operations"] = fs_result

            # Determine overall status
            failed_checks = [k for k, v in results["checks"].items() if not v.get("success", False)]
            if failed_checks:
                results["overall_status"] = "failed"
                results["errors"] = [f"{k}: {results['checks'][k].get('error', 'Unknown error')}" for k in failed_checks]
                raise SandboxHealthError(f"Sandbox health checks failed: {', '.join(results['errors'])}")
            else:
                results["overall_status"] = "healthy"
                logger.info("All sandbox health checks passed")

        except Exception as e:
            results["overall_status"] = "failed"
            results["errors"].append(str(e))
            logger.error(f"Sandbox health check failed: {e}")
            raise

        return results

    async def _check_basic_command_execution(self) -> Dict[str, Any]:
        """Test basic command execution in the sandbox."""
        try:
            # Try to execute a simple echo command
            response = self.sandbox.process.exec("echo 'DAYTONA_OK'", timeout=self.test_timeout)

            if response.exit_code == 0 and "DAYTONA_OK" in response.result:
                return {
                    "success": True,
                    "message": "Basic command execution works",
                    "output": response.result.strip()
                }
            else:
                return {
                    "success": False,
                    "error": f"Command failed with exit code {response.exit_code}: {response.result}",
                    "output": response.result
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Exception during command execution: {str(e)}"
            }

    async def _check_workspace_directory(self) -> Dict[str, Any]:
        """Ensure workspace directory exists and is accessible."""
        try:
            # First try to create the workspace directory
            create_result = self.sandbox.process.exec(
                f"mkdir -p {self.workspace_path} && cd {self.workspace_path} && pwd",
                timeout=self.test_timeout
            )

            if create_result.exit_code != 0:
                return {
                    "success": False,
                    "error": f"Failed to create workspace directory: {create_result.result}"
                }

            # Verify we can list the directory
            list_result = self.sandbox.process.exec(
                f"ls -la {self.workspace_path}",
                timeout=self.test_timeout
            )

            if list_result.exit_code == 0:
                return {
                    "success": True,
                    "message": f"Workspace directory {self.workspace_path} is accessible",
                    "output": list_result.result.strip()
                }
            else:
                return {
                    "success": False,
                    "error": f"Cannot list workspace directory: {list_result.result}"
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Exception during workspace check: {str(e)}"
            }

    async def _check_filesystem_operations(self) -> Dict[str, Any]:
        """Test basic filesystem operations (create, read, delete files)."""
        try:
            test_file = f"{self.workspace_path}/.iris_health_test"
            test_content = "IRIS_SANDBOX_HEALTH_CHECK_OK"

            # Create a test file
            create_result = self.sandbox.process.exec(
                f"echo '{test_content}' > {test_file}",
                timeout=self.test_timeout
            )

            if create_result.exit_code != 0:
                return {
                    "success": False,
                    "error": f"Failed to create test file: {create_result.result}"
                }

            # Read back the file
            read_result = self.sandbox.process.exec(
                f"cat {test_file}",
                timeout=self.test_timeout
            )

            if read_result.exit_code != 0:
                return {
                    "success": False,
                    "error": f"Failed to read test file: {read_result.result}"
                }

            if test_content not in read_result.result:
                return {
                    "success": False,
                    "error": f"File content mismatch. Expected: '{test_content}', Got: '{read_result.result.strip()}'"
                }

            # Delete the test file
            delete_result = self.sandbox.process.exec(
                f"rm {test_file}",
                timeout=self.test_timeout
            )

            if delete_result.exit_code != 0:
                return {
                    "success": False,
                    "error": f"Failed to delete test file: {delete_result.result}"
                }

            return {
                "success": True,
                "message": "Filesystem operations (create, read, delete) work correctly"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Exception during filesystem test: {str(e)}"
            }

    async def ensure_workspace_ready(self) -> None:
        """
        Ensure workspace is ready for tool operations.

        This is a lightweight version that can be called before each tool operation
        without the full health check overhead.
        """
        try:
            # Quick check if workspace exists
            result = self.sandbox.process.exec(
                f"test -d {self.workspace_path} || mkdir -p {self.workspace_path}",
                timeout=10
            )

            if result.exit_code != 0:
                raise SandboxHealthError(f"Cannot ensure workspace directory: {result.result}")

        except Exception as e:
            logger.error(f"Failed to ensure workspace ready: {e}")
            raise SandboxHealthError(f"Workspace preparation failed: {str(e)}")

def create_health_checker(sandbox: Sandbox) -> SandboxHealthChecker:
    """Factory function to create a health checker instance."""
    return SandboxHealthChecker(sandbox)

# Global health check function for easy access
async def assert_daytona_ready(sandbox: Sandbox) -> Dict[str, Any]:
    """
    Convenience function to run full sandbox health checks.

    Args:
        sandbox: The sandbox instance to check

    Returns:
        Health check results dictionary

    Raises:
        SandboxHealthError: If health checks fail
    """
    checker = create_health_checker(sandbox)
    return await checker.assert_daytona_ready()

async def ensure_workspace_ready(sandbox: Sandbox) -> None:
    """
    Convenience function to ensure workspace is ready.

    Args:
        sandbox: The sandbox instance to prepare

    Raises:
        SandboxHealthError: If workspace preparation fails
    """
    checker = create_health_checker(sandbox)
    await checker.ensure_workspace_ready()

logger.info("Sandbox health check system initialized")
