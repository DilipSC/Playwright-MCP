from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import asyncio

async def main():
    async with async_playwright() as p:
        # Launch browser in non-headless mode to observe
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=100
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        
        page = await context.new_page()
        
        try:
            # STEP 1: Navigate directly to YouTube
            print("Step 1: Navigating to YouTube...")
            await page.goto('https://www.youtube.com', wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)  # Wait for page to fully load
            
            # STEP 2: Handle consent if it appears
            print("Step 2: Checking for consent dialog...")
            try:
                # Try multiple consent button selectors
                consent_selectors = [
                    'button[aria-label*="Accept"]',
                    'button[aria-label*="Reject"]',
                    'button:has-text("Accept all")',
                    'tp-yt-paper-button:has-text("Accept")'
                ]
                
                for selector in consent_selectors:
                    try:
                        consent_btn = page.locator(selector).first
                        if await consent_btn.is_visible(timeout=3000):
                            print(f"   - Found consent button, clicking...")
                            await consent_btn.click()
                            await asyncio.sleep(2)
                            break
                    except:
                        continue
                else:
                    print("   - No consent dialog found, continuing...")
            except Exception as e:
                print(f"   - Consent handling skipped: {e}")
            
            # STEP 3: Click the search icon to activate search box
            print("Step 3: Activating YouTube search...")
            try:
                # Try to click search icon in header
                search_icon = page.locator('button#search-icon-legacy, ytd-masthead button#search-icon-legacy').first
                await search_icon.wait_for(state='visible', timeout=10000)
                await search_icon.click()
                await asyncio.sleep(1)
            except:
                print("   - Search already active or using different layout...")
            
            # STEP 4: Type in search box
            print("Step 4: Searching for video...")
            video_title = "I Survived 1000 Days in Minecraft Hardcore"
            
            # Try multiple search input selectors
            search_input = page.locator('input[name="search_query"], input#search, ytd-searchbox input').first
            await search_input.wait_for(state='visible', timeout=15000)
            await search_input.fill(video_title)
            await asyncio.sleep(1)
            
            # STEP 5: Press Enter or click search button
            print("Step 5: Submitting search...")
            await page.keyboard.press('Enter')
            await page.wait_for_load_state('domcontentloaded')
            await asyncio.sleep(3)  # Wait for search results
            
            # STEP 6: Click first video result
            print("Step 6: Clicking on video from search results...")
            # Use nth(0) instead of .first to avoid the callable issue
            video_link = page.locator('a#video-title').nth(0)
            await video_link.wait_for(state='visible', timeout=15000)
            await video_link.click()
            
            # STEP 7: Wait for video page to load
            print("Step 7: Waiting for video page...")
            await page.wait_for_url('**/watch?v=**', timeout=30000)
            await asyncio.sleep(2)
            
            print("\n[SUCCESS] Automation completed! Video is now playing.")
            
        except PlaywrightTimeoutError as e:
            print(f"\n[TIMEOUT] Element not found in time: {e}")
            await page.screenshot(path='error.png')
            print("Screenshot saved to error.png")
            
        except Exception as e:
            print(f"\n[ERROR] {type(e).__name__}: {e}")
            await page.screenshot(path='error.png')
            
        finally:
            # Keep browser open to see result
            await asyncio.sleep(5)
            await context.close()
            await browser.close()
            print("[CLEANUP] Browser closed")

if __name__ == "__main__":
    asyncio.run(main())
