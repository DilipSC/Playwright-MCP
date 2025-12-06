from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import asyncio

async def main():
    async with async_playwright() as p:
        # Launch browser in non-headless mode with a slight delay for observation
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=100
        )
        
        # Create a new browser context with a specific viewport and user agent
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36'
        )
        
        # Disable the "Chrome is being controlled by automated test software" infobar
        context.set_default_navigation_timeout(60000)
        
        page = await context.new_page()
        
        try:
            # STEP 1: Navigate to YouTube.com
            # The user first searches for "yt" and then clicks the link.
            # A more direct and reliable approach is to navigate directly to youtube.com.
            print("Step 1: Navigating to https://www.youtube.com...")
            await page.goto('https://www.youtube.com', wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(2)  # Wait for the page to settle

            # STEP 2: Handle YouTube Consent Pop-up (if it appears)
            # YouTube often presents a consent dialog on the first visit.
            print("Step 2: Checking for and handling consent dialog...")
            try:
                # This selector targets the "Accept all" button based on its ARIA label
                accept_button = page.locator('button[aria-label*="Accept all"]')
                await accept_button.wait_for(state='visible', timeout=5000)
                await accept_button.click()
                print("   - Consent dialog accepted.")
                await asyncio.sleep(2) # Wait for dialog to disappear
            except PlaywrightTimeoutError:
                print("   - Consent dialog not found, continuing.")

            # STEP 3: Search for the specific video
            # The video on the homepage is personalized. To ensure the script works every time,
            # we will search for the video title instead of trying to find it on the homepage.
            print("Step 3: Searching for the video 'I Survived 1000 Days in Minecraft Hardcore'...")
            
            # Click the search input field to focus it
            search_input = page.locator('input#search')
            await search_input.wait_for(state='visible', timeout=15000)
            await search_input.click()
            await asyncio.sleep(1)
            
            # Fill the search field with the video title
            await page.fill('input#search', 'I Survived 1000 Days in Minecraft Hardcore')
            await asyncio.sleep(1)
            
            # Press Enter to initiate the search
            await page.keyboard.press('Enter')
            print("   - Search initiated.")
            
            # Wait for the search results page to load
            await page.wait_for_url('**/results?search_query=*', timeout=30000)
            await asyncio.sleep(2)

            # STEP 4: Click on the correct video from the search results
            # We locate the video link by its title to ensure we click the right one.
            print("Step 4: Clicking on the video from search results...")
            
            # This locator finds a video renderer containing the specific title and channel name,
            # then targets the clickable title link within it. This is highly reliable.
            video_title = "I Survived 1000 Days in Minecraft Hardcore"
            channel_name = "ItsNotLudo"
            
            video_link = page.locator(f'ytd-video-renderer:has-text("{video_title}"):has-text("{channel_name}") a#video-title')
            await video_link.wait_for(state='visible', timeout=20000)
            await video_link.click()
            print(f"   - Clicked on video titled '{video_title}'.")
            
            # Wait for the video page to load
            await page.wait_for_url('**/watch?v=*', timeout=30000)
            print("   - Video page loaded successfully.")

            await asyncio.sleep(5) # Allow some time to see the video playing
            
            print("[SUCCESS] Automation completed!")
            
        except PlaywrightTimeoutError as e:
            print(f"[TIMEOUT] An element was not found in time: {e}")
            await page.screenshot(path='error_screenshot.png')
            
        except Exception as e:
            print(f"[ERROR] An unexpected error occurred: {type(e).__name__}: {e}")
            await page.screenshot(path='error_screenshot.png')
            
        finally:
            await asyncio.sleep(3)  # Keep browser open briefly for final review
            await context.close()
            await browser.close()
            print("[CLEANUP] Browser and context closed.")

if __name__ == "__main__":
    asyncio.run(main())