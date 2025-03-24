import httpx
import asyncio
import datetime
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup
from typing import List, Dict, Union


async def fetch_page(url: str, headers: dict) -> Union[str, None]:
    """Fetch a webpage content with error handling and follow redirects."""
    async with httpx.AsyncClient(follow_redirects=True) as client:  # Tambahkan follow_redirects=True
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.text
        except httpx.TimeoutException:
            st.error(f"Timeout: unable to connect to {url}. Please try again.")
            return None
        except httpx.HTTPStatusError as e:
            st.error(f"HTTP error: {str(e)}")
            return None

async def parse_content(url: str, headers: dict) -> str:
    """Extract content from a given news article URL."""
    html = await fetch_page(url, headers)
    if not html:
        return "Error fetching content."
    
    soup = BeautifulSoup(html, "html.parser")
    paragraphs = [p.get_text(strip=True) for p in soup.select('div.detail__body-text p')]

    return "\n".join(paragraphs) if paragraphs else "No content available."

async def parse_item(result, headers: dict) -> Dict[str, str]:
    """Extract information from a single news item."""
    title_element = result.select_one('h3.media__title a')
    title = title_element.get_text(strip=True) if title_element else "No Title"

    url = title_element['href'] if title_element else "#"

    date_element = result.select_one('.media__date span')
    date = date_element['title'] if date_element else "No Date"
    
    # Fetch content for each item
    content = await parse_content(url, headers)
    
    return {
        'title': title, 
        'url': url, 
        'date': date, 
        'content': content
        }

async def parse(url: str, headers: dict) -> List[Dict[str, str]]:
    """Parse news articles from the finance index page."""
    html = await fetch_page(url, headers)
    if not html:
        return []
    
    soup = BeautifulSoup(html, 'html.parser')
    news_results = soup.select('article')

    return await asyncio.gather(*[parse_item(result, headers) for result in news_results])

async def main():
    """Main Streamlit application function."""
    base_url = "https://finance.detik.com/indeks"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/244.178.44.111 Safari/537.36",
    }

    with st.container():
        st.title("Detik Finance Scraper")
        pages = int(st.text_input("Total Pages", value="1"))
        export_format = st.selectbox("Export to", ["CSV", "XLSX", "JSON"])
        scrape_button = st.button("Scrape")

    if scrape_button:
        with st.spinner("Scraping news articles..."):
            now = datetime.datetime.now()
            formatted_time = now.strftime("%Y%m%d_%H%M%S")

            all_items = []
            for page in range(1, pages + 1):
                url = f"{base_url}?page={page}"
                items = await parse(url, headers)
                all_items.extend(items)
                if page % 20 == 0:
                    st.write(f"✅ Completed Page {page}")

            if all_items:
                data = pd.DataFrame(all_items)
                data.index += 1
                st.dataframe(data)
                file_name = f"{formatted_time}_finance_{pages}.{export_format.lower()}"

                if export_format == "CSV":
                    csv_data = data.to_csv(index=False)
                    st.download_button("Download CSV", data=csv_data, file_name=file_name, mime="text/csv")
                elif export_format == "XLSX":
                    xlsx_data = data.to_excel(index=False, engine='openpyxl')
                    st.download_button("Download XLSX", data=xlsx_data, file_name=file_name, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                else:
                    json_data = data.to_json(orient='records')
                    st.download_button("Download JSON", data=json_data, file_name=file_name, mime="application/json")

                st.success("Scraping completed!")
            else:
                st.error("No data scraped.")

if __name__ == '__main__':
    asyncio.run(main())
