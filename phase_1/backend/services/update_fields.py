import asyncio
import os
import sys
from typing import Dict, List, Tuple
from urllib.parse import quote_plus, parse_qs, unquote, urlparse
import pandas as pd
from playwright.async_api import Page, BrowserContext, TimeoutError as PlaywrightTimeoutError

sys.path.append(os.path.abspath("d:/Caprae Capital/Work/LeadGenAI/phase_1/backend"))
from config.browser_config import PlaywrightManager

# from backend.config.browser_config import PlaywrightManager

''' --------------------- MANAGEMENT DETAILS ------------------------------- '''
async def get_management_details(page: Page, company_name: str, state: str) -> List[str]:
    """Fetches management details from BBB page."""
    query = f"{company_name} {state} bbb"
    url = f"https://www.bing.com/search?q={quote_plus(query)}"
    await page.goto(url)
    await page.evaluate("""
            const contentDiv = document.querySelector('#b_content');
            if (contentDiv && contentDiv.style.visibility === 'hidden') {
                contentDiv.style.visibility = 'visible';
            }
        """)
    await asyncio.sleep(1)

    management_data = []
    
    try:
        bbb_link_elem = await page.query_selector('li.b_algo > h2 > a[href*="bbb.org/us/"]:has-text("BBB")')
        if bbb_link_elem:
            href = await bbb_link_elem.get_attribute("href")
            if href:
                try:
                    await page.goto(href, wait_until="domcontentloaded")
                    await page.wait_for_selector("div.bpr-details-section", timeout=10000)
                    
                except PlaywrightTimeoutError:
                    await page.goto(href, wait_until="domcontentloaded")
                    await page.wait_for_url(href, timeout=15000)  # Confirm URL match
                    await page.wait_for_selector("div.bpr-details-section", timeout=10000)
                
            else:
                print(f"BBB link element has no href for {company_name}.")
                return ["NA"]
            
            management_divs = await page.query_selector_all('.bpr-details-dl-data[data-type="on-separate-lines"]')
            for div in management_divs:
                dt_elem = await div.query_selector('dt')
                if dt_elem:
                    dt_text = await dt_elem.inner_text()
                    if "Business Management" in dt_text:
                        dd_elems = await div.query_selector_all('dd')
                        for dd_elem in dd_elems:
                            dd_text = await dd_elem.inner_text()
                            if dd_text.strip():
                                try:
                                    name, title = dd_text.split(",", 1)
                                    management_data.append({"name": name.strip(), "title": title.strip()})
                                except ValueError as e:
                                    management_data.append({"name": dd_text.strip(), "title": "NA"})
                        break
        
        if not management_data:
            return ["NA"]
        return management_data
    
    except Exception as e:
        print(f"Error in get_management_details for {company_name}: {e}")
        return ["NA"]
    
async def fetch_management(data: List[Tuple[str, str]], context: BrowserContext, batch_size: int = 5) -> List[str]:
    """Processes companies in batches to fetch management details in parallel."""
    
    async def process_company(page: Page, name: str, location: str) -> str:
        state = location.split(",")[1].strip()
        return await get_management_details(page, name, state)

    results = []
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        pages = [await context.new_page() for _ in batch]

        tasks = [
            process_company(pages[j], name, location)
            for j, (name, location) in enumerate(batch)
        ]

        batch_results = await asyncio.gather(*tasks)
        
        # print(batch_results)
        # Collect results from the batch
        results.extend(batch_results)

        await asyncio.gather(*[p.close() for p in pages])

    return results

async def enrich_management(data: List[Tuple[str,str]]) -> List[str]:
    """Enriches lead data with website and management details."""
    manager = PlaywrightManager(headless=True)
    await manager.start_browser(stealth_on=True)
    try:
        results = await fetch_management(data, manager.context)
        return results
    except Exception as e:
        print(f"Error in enriching managment: {e}")
        return []
    finally:
        await manager.stop_browser()


''' --------------------- BBB RATING AND WEBSITE ------------------------------- '''
async def get_rating_and_website(page: Page, company_name: str, state: str) -> Tuple[str, str]:
    query = f'{company_name} bbb {state} business profile'
    url = f"https://www.bing.com/search?q={quote_plus(query)}"
    await page.goto(url)
    await page.evaluate("""
            const contentDiv = document.querySelector('#b_content');
            if (contentDiv && contentDiv.style.visibility === 'hidden') {
                contentDiv.style.visibility = 'visible';
            }
        """)
    await asyncio.sleep(1)

    website = "NA"
    rating = "NA"

    # Try extracting website from Bing sidebar (b_sideBleed)
    try:
        side_bleed = page.locator("div.b_localDesktopInfoCard")
        if await side_bleed.is_visible():
            website_link = side_bleed.locator("a", has_text="Website")
            if await website_link.count() == 0:
                website_link = side_bleed.locator("a").first
                
            if await website_link.count() > 0:
                href = await website_link.get_attribute("href")
                parsed_url = parse_qs(urlparse(href).query)
                actual_url = parsed_url.get("url", [""])[0]
                website = unquote(actual_url)
                # return website, rating
        # else:
        #     print(f"No sidebar for {company_name}.")

    except Exception:
        print(f"Error in Bing sidebar scraping... going to BBB")

    # If sidebar didn't help, proceed to open BBB page
    try:
        bbb_link_elem = await page.query_selector('li.b_algo > h2 > a[href*="bbb.org/us/"]:has-text("Profile")')
        if bbb_link_elem:
            href = await bbb_link_elem.get_attribute("href")
            if href:
                try:
                    await page.goto(href, wait_until="domcontentloaded")
                    await page.wait_for_selector("div.bpr-header", timeout=10000)
                    
                except PlaywrightTimeoutError:
                    print(f"Timeout while waiting for page to load for {company_name}.")
                    await page.goto(href, wait_until="domcontentloaded")
                    await page.wait_for_url(href, timeout=15000)  # Confirm URL match
                    await page.wait_for_selector("div.bpr-header", timeout=10000)
            # else:
            #     print(f"BBB link element has no href for {company_name}.")
            
            if website == "NA":
                try:
                    website_elem = await page.query_selector('a:has-text("Visit Website")')
                    # print(f"Website element found: {website_elem} {company_name}")
                    if website_elem:
                        website = await website_elem.get_attribute("href")
                except Exception as e:
                    print(f"Website extraction failed on BBB page: {e}")

            # Try getting rating
            try:
                # rating_elem_div = await page.wait_for_selector('.bpr-header-accreditation-rating', timeout=10000)
                is_accredited = await page.query_selector('.bpr-header-accreditation-rating[data-accredited="true"]')
                if is_accredited:
                    # print(f"Rating status div found: {company_name} is accredited")
                    rating_elem = await page.query_selector('span.bpr-header-rating')
                    if rating_elem:
                        rating = await rating_elem.inner_text()    
                
            except Exception as e:
                print(f"Rating extraction failed on BBB page: {e}")
                
        else:
            print(f"No BBB link for {company_name}.")

    except Exception as e:
        print(f"Error handling BBB link navigation for {company_name}: {e}")
    
    return website, rating


async def update_data(data: List[Dict[str, str]], state: str, context: BrowserContext, batch_size: int = 5) -> List[Dict[str, str]]:
    async def process_company(page, index, company):
        website, rating = await get_rating_and_website(page, company["Company"], state)
        return {"Website": website, "BBB_rating": rating}

    # Collect companies with missing website
    to_update = [(i, item) for i, item in enumerate(data) if not item.get("Website") or item["Website"] == "NA"]

    # Process in batches
    for i in range(0, len(to_update), batch_size):
        batch = to_update[i:i + batch_size]
        pages = [await context.new_page() for _ in batch]

        # Process all companies in parallel on separate pages
        results = await asyncio.gather(
            *[process_company(pages[j], idx, company) for j, (idx, company) in enumerate(batch)]
        )

        # print(results)    
        # Update the data
        for (idx, _), result in zip(batch, results):
            if result["Website"]:  # Update only if a valid website is returned
                data[idx]["Website"] = result["Website"]
            data[idx]["BBB_rating"] = result["BBB_rating"]

        # Close all pages
        await asyncio.gather(*[p.close() for p in pages])

    return data

async def enrich_contact(data: List[Dict[str,str]], location: str) -> List[Dict[str, str]]:
    """Enriches lead data with website and management details."""
    manager = PlaywrightManager(headless=True)
    await manager.start_browser(stealth_on=True)
    state = location.split(",")[1].strip()
    try:
        updated_data = await update_data(data, state, manager.context, batch_size=5)
        return updated_data
    except Exception as e:
        print(f"Error in enriching lead: {e}")
        return data
    finally:
        await manager.stop_browser()    


''' --------------------- COMBINED ------------------------------- '''
async def enrich_leads(df: pd.DataFrame, location: str) -> pd.DataFrame:
    records = df.to_dict(orient="records")
    updated_records = await enrich_contact(records, location)

    company_tuples = [(rec["Company"], rec.get("Address", location)) for rec in updated_records]
    management_info = await enrich_management(company_tuples)

    for i, rec in enumerate(updated_records):
        people = management_info[i] if i < len(management_info) else "NA"
        if isinstance(people, list) and people and people != ["NA"]:
            rec["Management"] = "; ".join(
                [f'{p["name"]} ({p["title"]})' for p in people if isinstance(p, dict)]
            ) if people else "NA"
        else:
            rec["Management"] = "NA"
            
    return pd.DataFrame(updated_records)

if __name__ == "__main__":
    companies0 = [
        # ("ASI The White Glove Guys", "San Deigo, CA"),
        # ("All Valley Pools AZ", "Phoenix, AZ"),
        # ("Remodel Your Pool", "Glendale, AZ"),
        # ("Sun State Pools", "Glendale, AZ"),
        # ("Thunderbird Pools & Spas", "Glendale, AZ"),
        ("APEX Firearms", "Glendale, AZ")
    ] 
    # companies1 = [
    #     ("Atwater Restoration, LLC", "Glendale, AZ"),
    #     ("Nasco Construction LLC", "Glendale, AZ"),
    #     ("Service Master All Care Restoration", "Glendale, AZ"),
    #     ("Servpro of Central Glendale/Thunderbird", "Glendale, AZ"),
    #     ("Servpro Of Mesa East", "Glendale, AZ"),
    #     ("Westwind Builders", "Glendale, AZ")
    # ]
    
    # companies2 = [
    #     ("Epic Fire & Water Restoration, LLC", "Glendale, AZ"),
    #     ("Granite Mountain Restoration", "Carmel, IN"),
    #     ("K.A.T.N. Enterprises", "Carmel, IN"),
    #     ("Native Phoenician, LLC", "Glendale, AZ"),
    #     ("Precision Remodeling and Rennovation, Inc.", "Carmel, IN")
    # ]
    
    # test0 = [
    #     {
    #         'Name': 'ASI The White Glove Guys',
    #         'Website': '',
    #         'Rating': ''
    #     },
    #     {
    #         'Name': 'Fast Plumber',
    #         'Website': '',
    #         'Rating': ''
    #     },
    #     {
    #         'Name': 'Pro Plumber San Diego Inc',
    #         'Website': '',
    #         'Rating': ''   
    #     }
    # ]
    
    # test1 = [
    #     {
    #         'Name': 'A and C Sales Company Inc',
    #         'Website': '',
    #         'Rating': ''
    #     },
    #     {
    #         'Name': 'Carrier Ken Heating & Cooling',
    #         'Website': '',
    #         'Rating': ''
    #     },
    #     {
    #         'Name': 'Fellowship Refrigeration Htg',
    #         'Website': '',
    #         'Rating': ''   
    #     },
    #     {
    #         'Name': 'Trane Co',
    #         'Website': '',
    #         'Rating': ''
    #     },
    #     {
    #         'Name': 'True Home Heating/Cooling Inc',
    #         'Website': '',
    #         'Rating': ''
    #     }
    # ]

    # test2 = [
    #     {
    #         "Name": "Epic Fire & Water Restoration, LLC",
    #         "Website": "",
    #         "Rating": ""
    #     },
    #     {
    #         "Name": "Granite Mountain Restoration",
    #         "Website": "",
    #         "Rating": ""
    #     },
    #     {
    #         "Name": "K.A.T.N. Enterprises",
    #         "Website": "",
    #         "Rating": ""
    #     },
    #     {
    #         "Name": "Native Phoenician, LLC",
    #         "Website": "",
    #         "Rating": ""
    #     },
    #     {
    #         "Name": "Precision Remodeling and Rennovation, Inc.",
    #         "Website": "",
    #         "Rating": ""
    #     }
    # ]
    
    print(asyncio.run(enrich_management(companies0)))
    # asyncio.run(enrich_contact(test0, "Glendale, AZ"))
    # asyncio.run(enrich_contact(test1, "Carmel, IN"))
    # asyncio.run(enrich_contact(test2, "Glendale, AZ"))