"""
Scraps information per-page
"""
from common.tokopedia_item import TokopediaItem
from service.driver.firefox import FirefoxDriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from common.base.item import Item
from bs4 import BeautifulSoup
import re

from service.dom import scrollscan_page

class TokopediaScraper:
    base_url = 'https://www.tokopedia.com'
    folder_name = "tokopedia"
    max_page = 10

    def __init__(self, min_price_threshold):
        self.min_price_threshold = min_price_threshold

    def _scrap_page_promo_item(self, soup):
        item_list = []
        all_promo_items = soup.find_all("div", {"class": "ta-product"})

        for promo_item in all_promo_items:
            try:
                product_title = ''
                product_price = 0
                product_location = ''
                shop_name = ''
                rating = 0
                product_img_url = ''
                product_detailurl = ''

                product_title_elem = promo_item.find("span", {"class": "ta-product-title"})
                if product_title_elem:
                    product_title = product_title_elem.text

                product_price_elem = promo_item.find("span", {"class": "ta-product-price"})
                if product_price_elem:
                    product_price = product_price_elem.text
                    product_price = TokopediaItem.extract_rp_price_number(product_price)

                product_location_elem = promo_item.find("span", {"class": "ta-product-location"})
                if(product_location_elem):
                    product_location = product_location_elem.text

                shop_name_elem = promo_item.find("span", {"class": "ta-product-shop"})
                if shop_name_elem:
                    shop_name = shop_name_elem.text

                rating_elem = promo_item.find("span", {"class": "ta-product-rating-count"})
                if rating_elem:
                    rating = TokopediaItem.extract_rating_from_brackets(rating_elem.text)

                product_img_elem = promo_item.find("div", {"class": "ta-product-img"}).find("img")
                if product_img_elem:
                    product_img_url = product_img_elem.attrs['src']

                product_detailurl_elem = all_promo_items[0].find("div", {"class": "ta-product-wrapper"})
                product_detailurl = product_detailurl_elem.find_all("a")[1].attrs['href']
                if(product_price >= self.min_price_threshold):
                    item_list.append(Item(product_title, product_price, shop_name, product_img_url, product_detailurl, product_location, rating))
            except Exception as e:
                print(e)

        return item_list

    def _scrap_page_nonpromo_item(self, soup):
        item_list = []

        non_promo_images = []
        for image_elem in soup.find_all("img", {"class": re.compile('.*entered.*')}):
            if len(image_elem["class"]) == 1:
                continue;
            else:
                non_promo_images.append(image_elem)

        all = soup.find_all("div", {"class": "pcr"})
        for index, product_cell in enumerate(all) :
            try:
                product_title = ''
                product_price = 0
                product_location = ''
                shop_name = ''
                rating = 0
                product_img_url = ''
                product_detailurl = ''

                product_title_elems = product_cell.find_all("h3")
                if len(product_title_elems) > 0:
                    product_title = product_title_elems[0].text

                product_price_elems = product_cell.find_all("span", {"itemprop": "price"})
                if len(product_price_elems) > 0 :
                    product_price = product_price_elems[0].find("span").text
                    price = TokopediaItem.extract_rp_price_number(product_price)

                offers_elem = product_cell.find("div", {"itemprop": "offers"})
                offers_detail_elems = offers_elem.find_all("div")
                if len(offers_detail_elems) >= 3 :
                    place_elems = offers_detail_elems[2]
                    product_location = place_elems.find_all("span")[0].text
                    shop_name = place_elems.find_all("span")[1].text
                    rating_elems = offers_detail_elems[3]
                    rating_with_brackets = rating_elems.find("span").text
                    rating = TokopediaItem.extract_rating_from_brackets(rating_with_brackets)

                details_elem = product_cell.find("div").find("a")
                if details_elem:
                    product_detailurl = details_elem.attrs['href']

                product_img_url = non_promo_images[index].attrs['src']
                if(product_price >= self.min_price_threshold):
                    item_list.append(Item(product_title, product_price, shop_name, product_img_url, product_detailurl, product_location, rating))
            except Exception as e:
                print(e)

        return item_list

    def _get_current_search_pagination_elems(self, soup):
        pagination_button_elems = soup.find_all('a', {'href': re.compile(r'/search*')})
        pagination_buttons = []
        for pagination_button_elem in pagination_button_elems :
            try:
                int(pagination_button_elem.text)
                pagination_buttons.append(pagination_button_elem)
            except ValueError:
                pass
        return pagination_buttons

    def start_crawl(self, first_page_url):
        item_list = []
        driver = FirefoxDriver().driver
        driver.get(first_page_url)

        curr_page = 1

        has_next_page = True
        while has_next_page and curr_page < TokopediaScraper.max_page :
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "fe-discovery-root")))
            scrollscan_page(driver)

            soup = BeautifulSoup(driver.page_source, "html")
            promo_item_list = self._scrap_page_promo_item(soup)
            print("Tokopedia promo item list : {}".format(promo_item_list))
            item_list.extend(promo_item_list)
            non_promo_item_list = self._scrap_page_nonpromo_item(soup)
            item_list.extend(non_promo_item_list)

            pagination_button_elems = self._get_current_search_pagination_elems(soup)
            has_next_page = False
            for pagination_button_elem in pagination_button_elems:
                if int(pagination_button_elem.text) == (curr_page + 1):
                    driver.get(TokopediaScraper.base_url + pagination_button_elem.attrs['href'])
                    curr_page += 1
                    has_next_page = True
                    break


        return item_list
