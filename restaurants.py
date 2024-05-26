from selenium import webdriver
from bs4 import BeautifulSoup
import pandas as pd
import jsonlines
import gzip
import os
import time

class GrabFoodScraper:
    """
            Initializes the GrabFoodScraper with the given URL and scroll count.

            Args:
                url (str): The URL to scrape.
                scroll_count (int): Number of times to scroll the page to load more content.
    """
    def __init__(self, url, scroll_count=20):
        self.url = url
        self.scroll_count = scroll_count
        self.driver = webdriver.Chrome()
        self.data = []

    def visit_site(self):
        self.driver.get(self.url)

    def scroll_page(self):
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        count = 0

        while count < self.scroll_count:
            self.driver.execute_script("window.scrollTo(0, 1000);")
            time.sleep(15)

            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break

            last_height = new_height
            count += 1

        return self.driver.page_source

    def parse_html(self, html):
        """
                Parses the HTML content and extracts restaurant data.

                Args:
                    html (str): The HTML content of the page.
        """
        soup = BeautifulSoup(html, "html.parser")
        restaurant_divs = soup.findAll('div', class_='ant-col-24')

        for dv in restaurant_divs:
            restaurant_name = dv.find('p', class_='name___2epcT').text.strip() if dv.find('p', class_='name___2epcT') else 'RestaurantName'
            restaurant_cuisine = dv.find('div', class_='basicInfoRow___UZM8d cuisine___T2tCh').text.strip() if dv.find('div', class_='basicInfoRow___UZM8d cuisine___T2tCh') else 'RestaurantCuisine'
            temp_div = dv.findAll('div', class_='numbersChild___2qKMV')

            if len(temp_div) == 2:
                restaurant_rating = temp_div[0].text.strip()
                delivery_info = temp_div[1].text.strip()
            else:
                restaurant_rating = None
                delivery_info = temp_div[0].text.strip() if temp_div else None

            delivery_time, delivery_distance = self.extract_delivery_info(delivery_info)
            image_url = dv.find('img')['src'] if dv.find('img') and dv.find('img').has_attr('src') else None

            '''image_element = dv.find('img')
            if image_element and image_element.has_attr('src'):
                image_url = WebDriverWait(self.driver, 10).until(
                    EC.visibility_of(image_element)
                ).get_attribute('src')
            else:
                image_url = None'''

            promo_available = bool(dv.find('span', class_='discountText___GQCkj'))
            promotional_offers = dv.find('span', class_='discountText___GQCkj').text.strip() if promo_available else None
            restaurant_id = dv.find('a')['href'].split('/')[-1].rstrip('?') if dv.find('a') else None
            estimate_delivery_fee = self.calculate_delivery_fee(delivery_distance)
            restaurant_notice = dv.find_all('span')[1].text.strip() if len(dv.find_all('span')) > 1 else None

            self.data.append({
                "restaurant_name": restaurant_name,
                "restaurant_cuisine": restaurant_cuisine,
                "restaurant_rating": restaurant_rating,
                "delivery_time": delivery_time,
                "delivery_distance": delivery_distance,
                "promo_available": promo_available,
                "promotional_offers": promotional_offers,
                "restaurant_notice": restaurant_notice,
                "image_url": image_url,
                "restaurant_id": restaurant_id,
                "estimateDeliveryFee": estimate_delivery_fee
            })

    def extract_delivery_info(self, delivery_info):
        #Extracts delivery time and distance from the delivery information.
        if delivery_info:
            cleaned_text = delivery_info.replace('\xa0', ' ').strip()
            parts = cleaned_text.split('•')

            if len(parts) == 2:
                return parts[0].strip(), parts[1].strip()
        return '0 min', '0 km'

    def calculate_delivery_fee(self, delivery_distance):
        #Calculates the estimated delivery fee based on delivery distance.
        return float(delivery_distance.split()[0]) * 5 if delivery_distance else 0

    # Saves the scraped data to a compressed NDJSON file.
    def save_data(self, filename='data.ndjson'):

        # Convert the list of dictionaries to a DataFrame and remove duplicates
        df = pd.DataFrame(self.data).drop_duplicates(subset=['restaurant_name'], keep='first')
        data_dicts = df.to_dict(orient='records')

        # Write the data to an NDJSON file
        with jsonlines.open(filename, mode='w') as writer:
            writer.write_all(data_dicts)

        # Compress the NDJSON file using gzip
        with open(filename, 'rb') as f_in:
            with gzip.open(f'{filename}.gz', 'wb') as f_out:
                f_out.writelines(f_in)

        #os.remove(filename)
        print(f"Data saved and compressed to {filename}.gz")

    def scrape(self):

        #entire scraping process
        self.visit_site()
        html = self.scroll_page()
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        count = 0

        while count < self.scroll_count:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(100) # Wait for the page to load

            html = self.driver.page_source
            self.parse_html(html)

            new_height = self.driver.execute_script("return document.body.scrollHeight")
            # Break if no new content is loaded
            if new_height == last_height:
                break

            last_height = new_height
            count += 1


        self.save_data()
        self.driver.quit()

if __name__ == "__main__":
    url = 'https://food.grab.com/sg/en/restaurants?search=chinese-food&support-deeplink=true&searchParameter=chinese-food'
    scraper = GrabFoodScraper(url)
    scraper.scrape()
