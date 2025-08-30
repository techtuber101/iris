import os
from dotenv import load_dotenv
from agentpress.tool import ToolResult, openapi_schema, xml_schema
from sandbox.sandbox import SandboxToolsBase, Sandbox
from utils.files_utils import clean_path
from agent.tools.sb_shell_tool import SandboxShellTool

# Load environment variables
load_dotenv()

class SandboxDeployTool(SandboxToolsBase):
    """Tool for deploying static websites from a Daytona sandbox to Cloudflare Pages."""

    def __init__(self, sandbox: Sandbox):
        super().__init__(sandbox)
        # For shell commands we operate from $HOME/workspace; keep paths relative
        self.workspace_path = "workspace"
        self.cloudflare_api_token = os.getenv("CLOUDFLARE_API_TOKEN")
        self.shell_tool = SandboxShellTool(sandbox)

    def clean_path(self, path: str) -> str:
        """Clean and normalize a path under user workspace (returns 'workspace/...')."""
        return clean_path(path, "workspace")

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "deploy",
            "description": "Deploy a static website (HTML+CSS+JS) from a directory in the sandbox to Cloudflare Pages. Only use this tool when permanent deployment to a production environment is needed. The directory path must be relative to /workspace. The website will be deployed to {name}.kortix.cloud.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name for the deployment, will be used in the URL as {name}.kortix.cloud"
                    },
                    "directory_path": {
                        "type": "string",
                        "description": "Path to the directory containing the static website files to deploy, relative to /workspace (e.g., 'build')"
                    }
                },
                "required": ["name", "directory_path"]
            }
        }
    })
    @xml_schema(
        tag_name="deploy",
        mappings=[
            {"param_name": "name", "node_type": "attribute", "path": "name"},
            {"param_name": "directory_path", "node_type": "attribute", "path": "directory_path"}
        ],
        example='''
        <!-- 
        IMPORTANT: Only use this tool when:
        1. The user explicitly requests permanent deployment to production
        2. You have a complete, ready-to-deploy directory 
        
        NOTE: If the same name is used, it will redeploy to the same project as before
                -->

        <deploy name="my-site" directory_path="website">
        </deploy>
        '''
    )
    async def deploy(self, name: str, directory_path: str) -> ToolResult:
        """
        Deploy a static website (HTML+CSS+JS) from the sandbox to Cloudflare Pages.
        Only use this tool when permanent deployment to a production environment is needed.
        
        Args:
            name: Name for the deployment, will be used in the URL as {name}.kortix.cloud
            directory_path: Path to the directory to deploy, relative to /workspace
            
        Returns:
            ToolResult containing:
            - Success: Deployment information including URL
            - Failure: Error message if deployment fails
        """
        try:
            # Normalize to Daytona SDK-relative path (e.g., 'workspace/site')
            rel_workspace_path = self.clean_path(directory_path)
            # For shell commands we cd into $HOME/workspace, so use folder path relative to that
            deploy_subdir = rel_workspace_path[len("workspace/"):] if rel_workspace_path.startswith("workspace/") else rel_workspace_path
            
            # Verify the directory exists
            try:
                dir_info = self.sandbox.fs.get_file_info(rel_workspace_path)
                if not dir_info.is_dir:
                    return self.fail_response(f"'{directory_path}' is not a directory")
            except Exception as e:
                return self.fail_response(f"Directory '{directory_path}' does not exist: {str(e)}")
            
            # Deploy to Cloudflare Pages directly from the container
            try:
                # Get Cloudflare API token from environment
                if not self.cloudflare_api_token:
                    return self.fail_response("CLOUDFLARE_API_TOKEN environment variable not set")
                    
                # Single command that creates the project if it doesn't exist and then deploys
                project_name = f"{self.sandbox_id}-{name}"
                deploy_cmd = f'''export CLOUDFLARE_API_TOKEN={self.cloudflare_api_token} && 
                    (npx wrangler pages deploy {deploy_subdir} --project-name {project_name} || 
                    (npx wrangler pages project create {project_name} --production-branch production && 
                    npx wrangler pages deploy {deploy_subdir} --project-name {project_name}))'''

                # Execute command using shell_tool.execute_command
                response = await self.shell_tool.execute_command(
                    command=deploy_cmd,
                    folder=None,  # Use the workspace root
                    timeout=300   # Increased timeout for deployments
                )
                
                print(f"Deployment response: {response}")
                
                if response.success:
                    return self.success_response({
                        "message": f"Website deployed successfully",
                        "output": response.output
                    })
                else:
                    return self.fail_response(f"Deployment failed: {response.output}")
            except Exception as e:
                return self.fail_response(f"Error during deployment: {str(e)}")
        except Exception as e:
            return self.fail_response(f"Error deploying website: {str(e)}")

if __name__ == "__main__":
    import asyncio
    import sys
    
    async def test_deploy():
        # Replace these with actual values for testing
        sandbox_id = "sandbox-ccb30b35"
        password = "test-password"
        
        # Initialize the deploy tool
        deploy_tool = SandboxDeployTool(sandbox_id, password)
        
        # Test deployment - replace with actual directory path and site name
        result = await deploy_tool.deploy(
            name="test-site-1x",
            directory_path="website"  # Directory containing static site files
        )
        print(f"Deployment result: {result}")
            
    asyncio.run(test_deploy())
