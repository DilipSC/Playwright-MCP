"""
Enhanced MCP Server for Video-to-Playwright Automation
Improved video analysis and script generation
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Optional, Any, List
import google.generativeai as genai
from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio
from apify import Actor

# Load environment variables
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

class VideoPlaywrightMCP:
    def __init__(self):
        self.server = Server(os.getenv('MCP_SERVER_NAME', 'video-playwright-automation'))
        self.model = genai.GenerativeModel(os.getenv('GEMINI_MODEL', 'gemini-2.5-pro'))
        self.conversation_history = []
        self.generated_script = None
        self.video_upload_dir = Path(os.getenv('VIDEO_UPLOAD_DIR', 'c:/Users/dilip/OneDrive/Desktop/AI/apify/playwright-mcp/videos'))
        self.video_upload_dir.mkdir(parents=True, exist_ok=True)
        self.max_video_size_mb = int(os.getenv('MAX_VIDEO_SIZE_MB', '100'))
        
        self.setup_tools()
    
    def setup_tools(self):
        """Register MCP tools"""
        
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="analyze_video",
                    description="Analyze a video and generate a Playwright automation script using Gemini AI",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "video_path": {
                                "type": "string",
                                "description": "Path to the video file (supports mp4, avi, mov, webm)"
                            },
                            "task_description": {
                                "type": "string",
                                "description": "Optional description of the task shown in the video"
                            },
                            "include_screenshots": {
                                "type": "boolean",
                                "description": "Include screenshot capture in generated script",
                                "default": False
                            },
                            "slow_mo": {
                                "type": "integer",
                                "description": "Slow motion delay in milliseconds for debugging",
                                "default": 0
                            }
                        },
                        "required": ["video_path"]
                    }
                ),
                Tool(
                    name="modify_script",
                    description="Modify the generated Playwright script based on user feedback",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "modification_request": {
                                "type": "string",
                                "description": "Natural language description of changes to make"
                            }
                        },
                        "required": ["modification_request"]
                    }
                ),
                Tool(
                    name="execute_script",
                    description="Execute the generated Playwright script",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "headless": {
                                "type": "boolean",
                                "description": "Run browser in headless mode",
                                "default": True
                            },
                            "save_output": {
                                "type": "boolean",
                                "description": "Save execution results to Apify dataset",
                                "default": False
                            }
                        }
                    }
                ),
                Tool(
                    name="get_script",
                    description="Retrieve the current generated Playwright script",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "format": {
                                "type": "string",
                                "enum": ["python", "json"],
                                "description": "Output format",
                                "default": "python"
                            }
                        }
                    }
                ),
                Tool(
                    name="save_script",
                    description="Save the generated script to Apify key-value store",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "filename": {
                                "type": "string",
                                "description": "Filename to save the script as",
                                "default": "playwright_script.py"
                            }
                        }
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent]:
            try:
                if name == "analyze_video":
                    return await self.analyze_video(
                        arguments.get("video_path"),
                        arguments.get("task_description"),
                        arguments.get("include_screenshots", False),
                        arguments.get("slow_mo", 0)
                    )
                elif name == "modify_script":
                    return await self.modify_script(arguments.get("modification_request"))
                elif name == "execute_script":
                    return await self.execute_script(
                        arguments.get("headless", True),
                        arguments.get("save_output", False)
                    )
                elif name == "get_script":
                    return await self.get_script(arguments.get("format", "python"))
                elif name == "save_script":
                    return await self.save_script(arguments.get("filename", "playwright_script.py"))
                else:
                    raise ValueError(f"Unknown tool: {name}")
            except Exception as e:
                Actor.log.error(f"Error in {name}: {str(e)}")
                return [TextContent(type="text", text=f"❌ Error: {str(e)}")]
    
    async def analyze_video(
        self, 
        video_path: str, 
        task_description: Optional[str] = None,
        include_screenshots: bool = False,
        slow_mo: int = 0
    ) -> list[TextContent]:
        """Analyze video and generate Playwright script with enhanced accuracy"""
        try:
            input_path = Path(video_path)
            if not input_path.is_absolute():
                input_path = self.video_upload_dir / input_path

            if not input_path.exists():
                raise FileNotFoundError(f"Video not found at: {input_path}")

            size_mb = input_path.stat().st_size / (1024 * 1024)
            if size_mb > self.max_video_size_mb:
                raise ValueError(f"Video size {size_mb:.1f}MB exceeds limit {self.max_video_size_mb}MB")

            Actor.log.info(f"Analyzing video: {input_path}")
            
            # Upload video to Gemini
            video_file = genai.upload_file(path=str(input_path))
            Actor.log.info("Video uploaded, waiting for processing...")
            
            # Wait for video processing
            while video_file.state.name == "PROCESSING":
                await asyncio.sleep(2)
                video_file = genai.get_file(video_file.name)
            
            if video_file.state.name == "FAILED":
                raise ValueError("Video processing failed")
            
            Actor.log.info("Video processed successfully")
            
            # Enhanced prompt with detailed instructions
            prompt = f"""
Analyze this video FRAME BY FRAME and identify EVERY single user interaction in chronological order.

{"Task Context: " + task_description if task_description else ""}

CRITICAL ANALYSIS STEPS:
1. **Watch the entire video carefully** - Note every mouse movement, click, keyboard input, scroll, and navigation
2. **Identify the starting URL** - What webpage does the video begin on?
3. **Track each interaction** - For EACH action, note:
   - What element is being interacted with? (button, input field, link, dropdown, etc.)
   - What is the visible text or label of that element?
   - What type of action? (click, type, press Enter, select, scroll, etc.)
   - What happens after the action? (page loads, dropdown opens, search results appear, etc.)
4. **Note timing** - Identify when to wait for elements, page loads, or animations
5. **Identify text inputs** - What exact text is typed into each field?

IMPORTANT RULES:
- If the user searches for something, USE THE SEARCH FUNCTIONALITY instead of expecting content on homepage
- If a specific video/content is clicked, search for it first to ensure it's available
- Use simple, reliable selectors that work across sessions
- Do NOT assume personalized content (like YouTube homepage videos) will be the same
- Add proper error handling for dynamic content

Generate a script that will ACTUALLY WORK in any session, not just replay the exact video scenario.

PLAYWRIGHT SCRIPT REQUIREMENTS:

```python
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import asyncio

async def main():
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(
            headless=False,
            slow_mo={slow_mo}
        )
        
        context = await browser.new_context(
            viewport={{'width': 1920, 'height': 1080}},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        
        page = await context.new_page()
        
        try:
            # STEP 1: Navigate to starting URL
            print("Step 1: Navigating to [URL]...")
            await page.goto('[URL]', wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(2)  # Wait for page to settle
            
            # STEP 2: [First interaction]
            print("Step 2: [Description]...")
            # Use page.locator() with CSS selector or text
            element = page.locator('[SELECTOR]')
            await element.wait_for(state='visible', timeout=15000)
            await element.click()
            await asyncio.sleep(1)
            
            # IMPORTANT: If video shows clicking on specific content (like a YouTube video):
            # - First search for it using the search box
            # - Then click on the search result
            # Example for YouTube (click search icon first to activate search):
            # await page.click('ytd-masthead #search-icon-legacy')
            # await asyncio.sleep(1)
            # await page.fill('input[name="search_query"]', 'video title')
            # await page.keyboard.press('Enter')
            # await asyncio.sleep(3)
            # video = page.locator('a#video-title').nth(0)
            # await video.wait_for(state='visible', timeout=15000)
            # await video.click()
            
            # Add more steps as needed for each action in the video
            # CORRECT PATTERNS:
            # element = page.locator('selector').nth(0)
            # await element.wait_for(state='visible', timeout=15000)
            # await element.click()
            # OR
            # await page.fill('input#id', 'text')
            # await page.click('button#id')
            
            {"# Take screenshots" if include_screenshots else ""}
            {'''await page.screenshot(path='screenshot.png')
            print("Screenshot saved")''' if include_screenshots else ""}
            
            print("[SUCCESS] Automation completed!")
            
        except PlaywrightTimeoutError as e:
            print(f"[TIMEOUT] Element not found: {{e}}")
            await page.screenshot(path='error.png')
            
        except Exception as e:
            print(f"[ERROR] {{type(e).__name__}}: {{e}}")
            await page.screenshot(path='error.png')
            
        finally:
            await asyncio.sleep(3)  # Keep browser open briefly
            await context.close()
            await browser.close()
            print("[CLEANUP] Browser closed")

if __name__ == "__main__":
    asyncio.run(main())
```

CRITICAL SELECTOR STRATEGY (MUST FOLLOW EXACTLY):
1. Use `page.locator('css-selector')` and store in a variable
2. Use `page.locator('text=Exact Text')` for buttons/links with visible text
3. Use `page.fill('#input-id', 'text')` for input fields
4. NEVER use `.first()` - instead use `.nth(0)` or make selector more specific
5. Pattern: `element = page.locator('selector'); await element.wait_for(state='visible'); await element.click()`
6. Add `await asyncio.sleep(1-2)` after major actions to let page settle

CORRECT Examples:
```python
# Click first matching element
search_btn = page.locator('button.search').nth(0)
await search_btn.wait_for(state='visible', timeout=15000)
await search_btn.click()

# Or use more specific selector
video_link = page.locator('a#video-title').filter(has_text='Minecraft')
await video_link.wait_for(state='visible', timeout=15000)
await video_link.click()

# Fill input
await page.fill('input#search', 'search term')
await asyncio.sleep(1)
```

For YouTube:
- Search box: Try clicking search icon first, then fill `input[name="search_query"]` or `input#search`
- Pattern: await page.click('button#search-icon-legacy'); await asyncio.sleep(1); await page.fill('input[name="search_query"]', 'text')
- Search button: `button#search-icon-legacy`
- Video links: `a#video-title`
- Handle consent: Check for button with aria-label containing "Accept" or "Reject"

For searches:
- If user clicks on specific content, search for it first rather than expecting it on homepage
- Example: await page.fill('input#search', 'search term'); await page.keyboard.press('Enter'); await asyncio.sleep(2)

WRONG - DO NOT USE:
- `.first()` followed by parentheses
- `.get_by_role()` without proper chaining

Generate the COMPLETE, EXECUTABLE script with ALL steps from the video. 
Include detailed comments for each step explaining what you observed in the video.
The script must work end-to-end without modifications.
"""
            
            # Generate script using Gemini
            Actor.log.info("Generating enhanced Playwright script...")
            response = self.model.generate_content([video_file, prompt])
            
            script_content = response.text
            
            # Clean up markdown code blocks
            if "```python" in script_content:
                script_content = script_content.split("```python")[1].split("```")[0].strip()
            elif "```" in script_content:
                script_content = script_content.split("```")[1].split("```")[0].strip()
            
            self.generated_script = script_content
            self.conversation_history.append({
                "role": "user",
                "content": f"Video: {video_path}, Task: {task_description or 'Not specified'}"
            })
            self.conversation_history.append({
                "role": "assistant",
                "content": script_content
            })
            
            # Auto-save the generated script
            try:
                await Actor.set_value('generated_script.py', script_content)
                Actor.log.info("Script saved to key-value store as 'generated_script.py'")
            except Exception as save_error:
                Actor.log.warning(f"Could not save script: {save_error}")
            
            Actor.log.info("Enhanced script generated successfully")
            
            return [
                TextContent(
                    type="text",
                    text=f"✅ Video analyzed with enhanced detection!\n\n**Generated Playwright Script:**\n\n```python\n{script_content}\n```\n\n**Next Steps:**\n- Review the script to ensure all steps match your video\n- Use `modify_script` if any steps are missing or incorrect\n- Use `execute_script` to test the automation\n- Use `save_script` to store in Apify KV store"
                )
            ]
        
        except Exception as e:
            Actor.log.error(f"Error analyzing video: {str(e)}")
            return [TextContent(type="text", text=f"❌ Error analyzing video: {str(e)}")]
    
    async def modify_script(self, modification_request: str) -> list[TextContent]:
        """Modify the generated script based on user feedback"""
        if not self.generated_script:
            return [TextContent(
                type="text", 
                text="❌ No script has been generated yet. Use `analyze_video` first."
            )]
        
        try:
            Actor.log.info(f"Modifying script: {modification_request}")
            
            prompt = f"""
Here is the current Playwright script:
```python
{self.generated_script}
```

User modification request: {modification_request}

Please modify the script according to the request. Ensure:
1. All actions are properly sequenced
2. Appropriate waits are added (wait_for_selector, wait_for_load_state, wait_for_timeout)
3. Selectors are robust and specific
4. Error handling is comprehensive
5. The script remains complete and executable
6. Comments explain what each step does

If the user mentions missing steps or actions that didn't work:
- Add explicit waits before interactions
- Try alternative selectors
- Add visibility/enabled checks
- Consider if consent dialogs or popups need to be handled first

Return ONLY the complete updated Python code with detailed comments.
"""
            
            response = self.model.generate_content(prompt)
            modified_script = response.text
            
            # Clean up markdown
            if "```python" in modified_script:
                modified_script = modified_script.split("```python")[1].split("```")[0].strip()
            elif "```" in modified_script:
                modified_script = modified_script.split("```")[1].split("```")[0].strip()
            
            self.generated_script = modified_script
            self.conversation_history.append({
                "role": "user",
                "content": f"Modify: {modification_request}"
            })
            self.conversation_history.append({
                "role": "assistant",
                "content": modified_script
            })
            
            Actor.log.info("Script modified successfully")
            
            return [
                TextContent(
                    type="text",
                    text=f"✅ Script modified successfully!\n\n```python\n{modified_script}\n```"
                )
            ]
        
        except Exception as e:
            Actor.log.error(f"Error modifying script: {str(e)}")
            return [TextContent(type="text", text=f"❌ Error modifying script: {str(e)}")]
    
    async def execute_script(self, headless: bool = True, save_output: bool = False) -> list[TextContent]:
        """Execute the generated Playwright script"""
        if not self.generated_script:
            return [TextContent(
                type="text", 
                text="❌ No script has been generated yet. Use `analyze_video` first."
            )]
        
        try:
            Actor.log.info("Executing Playwright script...")
            
            # Save script to temporary file (force UTF-8 to avoid Windows codec issues)
            script_path = self.video_upload_dir / "temp_playwright_script.py"
            script_path.write_text(self.generated_script, encoding="utf-8")
            
            # Execute the script
            # Ensure UTF-8 mode for Python subprocess to handle Unicode output
            env = os.environ.copy()
            env["PYTHONUTF8"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"
            process = await asyncio.create_subprocess_exec(
                "python", str(script_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            stdout, stderr = await process.communicate()
            
            # Decode with error handling for Unicode issues
            stdout_text = stdout.decode('utf-8', errors='replace')
            stderr_text = stderr.decode('utf-8', errors='replace')
            
            # Log the output
            Actor.log.info(f"Script output:\n{stdout_text}")
            if stderr_text:
                Actor.log.warning(f"Script errors:\n{stderr_text}")
            
            result = {
                "success": process.returncode == 0,
                "stdout": stdout_text,
                "stderr": stderr_text,
                "return_code": process.returncode
            }
            
            if save_output:
                await Actor.push_data(result)
                Actor.log.info("Execution results saved to dataset")
            
            if result["success"]:
                Actor.log.info("Script executed successfully")
                return [TextContent(
                    type="text", 
                    text=f"✅ Script executed successfully!\n\n**Output:**\n```\n{result['stdout']}\n```"
                )]
            else:
                Actor.log.error(f"Script execution failed: {result['stderr']}")
                return [TextContent(
                    type="text", 
                    text=f"❌ Script execution failed:\n```\n{result['stderr']}\n```\n\n**Tip:** Use `modify_script` to fix the issues. Common problems:\n- Incorrect selectors\n- Missing waits\n- Elements not visible/enabled\n- Page not loaded"
                )]
        
        except Exception as e:
            Actor.log.error(f"Error executing script: {str(e)}")
            return [TextContent(type="text", text=f"❌ Error executing script: {str(e)}")]
    
    async def get_script(self, format: str = "python") -> list[TextContent]:
        """Retrieve the current script"""
        if not self.generated_script:
            return [TextContent(type="text", text="❌ No script has been generated yet.")]
        
        if format == "json":
            script_data = {
                "script": self.generated_script,
                "conversation_history": self.conversation_history,
                "format": "python"
            }
            return [TextContent(
                type="text",
                text=f"```json\n{json.dumps(script_data, indent=2)}\n```"
            )]
        else:
            return [TextContent(
                type="text",
                text=f"**Current Playwright Script:**\n\n```python\n{self.generated_script}\n```"
            )]
    
    async def save_script(self, filename: str) -> list[TextContent]:
        """Save script to Apify key-value store"""
        if not self.generated_script:
            return [TextContent(type="text", text="❌ No script has been generated yet.")]
        
        try:
            await Actor.set_value(filename, self.generated_script)
            Actor.log.info(f"Script saved to key-value store as {filename}")
            return [TextContent(
                type="text",
                text=f"✅ Script saved to Apify key-value store as `{filename}`"
            )]
        except Exception as e:
            Actor.log.error(f"Error saving script: {str(e)}")
            return [TextContent(type="text", text=f"❌ Error saving script: {str(e)}")]
    
    async def run(self):
        """Run the MCP server"""
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )

async def main():
    """Main entry point for Apify Actor"""
    async with Actor:
        Actor.log.info("Starting Enhanced Video-to-Playwright MCP Server...")
        
        if not GEMINI_API_KEY:
            Actor.log.error("GEMINI_API_KEY not found in environment variables!")
            raise ValueError("GEMINI_API_KEY is required")
        
        mcp = VideoPlaywrightMCP()

        # Optional auto-analyze mode
        if os.getenv('AUTO_ANALYZE_VIDEO', 'false').lower() == 'true':
            video_file = os.getenv('VIDEO_FILE', 'test_1.mp4')
            include_screenshots = os.getenv('INCLUDE_SCREENSHOTS', 'false').lower() == 'true'
            execute_after = os.getenv('EXECUTE_AFTER', 'true').lower() == 'true'
            slow_mo = int(os.getenv('SLOW_MO', '0'))

            Actor.log.info(f"Auto-analyze enabled. Video: {video_file}")
            try:
                await mcp.analyze_video(
                    video_file, 
                    include_screenshots=include_screenshots,
                    slow_mo=slow_mo
                )
                if execute_after:
                    await mcp.execute_script(
                        headless=os.getenv('PLAYWRIGHT_HEADLESS', 'true').lower() == 'true'
                    )
            except Exception as e:
                Actor.log.error(f"Auto-analyze failed: {e}")
        else:
            await mcp.run()

if __name__ == "__main__":
    asyncio.run(main())