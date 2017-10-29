##
## WebScraper to extract google ads from sites which have google ads.
##

import codecs
import hashlib
import os
from PIL import Image
from bs4 import BeautifulSoup
from selenium import webdriver
import re

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver import DesiredCapabilities


def element_screenshot(driver, element, filename):
    bounding_box = (
        element.location['x'],  # left
        element.location['y'],  # upper
        (element.location['x'] + element.size['width']),  # right
        (element.location['y'] + element.size['height'])  # bottom
    )
    return bounding_box_screenshot(driver, bounding_box, filename)


def bounding_box_screenshot(driver, bounding_box, filename):
    driver.save_screenshot(filename)
    base_image = Image.open(filename)
    cropped_image = base_image.crop(bounding_box)
    base_image = base_image.resize(cropped_image.size)
    base_image.paste(cropped_image, (0, 0))
    base_image.save(filename)
    return base_image


# Check for a list of blacklisted url domain names that could not be the company name.
# If it is any of them, then look for the next url.
def get_company_name(html, index):
    company_name = 'ads-' + index
    blacklisted_url = ['doubleclick', 'mdn', 'dartsearch', 'google', 'geeksforgeeks']
    try:
        links = re.findall('(https?://.*?/)', html)
        i = 0
        company_name = links[i].split('.')[-2]
        while True:
            is_blacklisted_url = True
            for url in blacklisted_url:
                if url in links[i]:
                    i += 1
                    company_name = links[i].split('.')[-2]
                    is_blacklisted_url = False
            if is_blacklisted_url: break
        file_name = company_name + '.html'
    except IndexError:
        print("Error, No company name found for:" + html)
    return company_name


def get_file_name(html):
    return hashlib.md5(html).hexdigest()


# Get the ads file. The driver sent
# should be already at the site where
# the ads are to be scraped.
# Logic:
# 1. go to geeksforgeeks.org
# 2. look for ins tag with class 'adsbygoogle'
# 3. look for 2 iframes within
# TODO: Currently scraping only 1 ads per page. Need to scrape all ads
# TODO: Generalise for ads from other websites too.
def get_ads_file(browser, root_url, index):
    try:
        # Wait for page to be rendered
        browser.implicitly_wait(10)  # seconds

        # Save path
        save_path = os.path.expanduser('./sample-run')

        # Switch to google ad frame
        actual_ad_iframe_element = browser.find_element_by_xpath('//ins[contains(@class, "adsbygoogle")]')
        browser.switch_to.frame(actual_ad_iframe_element.find_element_by_xpath('//iframe'))

        # URL of google ad.
        # url = browser.find_element_by_xpath('//iframe[contains(@id, "google_ads")]').get_attribute('src')
        # browser.get(url)
        browser.switch_to.frame(browser.find_element_by_xpath('//iframe[contains(@id, "google_ads")]'))

        # Wait for the ad iframe to be rendered after the switch.
        browser.implicitly_wait(5)

        ad_iframe_element = browser.find_element_by_xpath('//iframe[@id="ad_iframe"]')
        name = ad_iframe_element.get_attribute('src')

        browser.switch_to.frame(ad_iframe_element)

        try:
            name = browser.find_element_by_tag_name('img').get_attribute('src')
        except NoSuchElementException:
            print('Not a single image ad. Find for first iframe src.')

        html = browser.execute_script("return document.getElementsByTagName('html')[0].innerHTML")

        try:
            browser.implicitly_wait(15)
            actual_ad_iframe_element = browser.find_element_by_xpath('//iframe[@allowfullscreen="true"]')
            name = actual_ad_iframe_element.get_attribute('src')
            browser.switch_to.frame(actual_ad_iframe_element)
            html = browser.execute_script("return document.getElementsByTagName('html')[0].innerHTML")
        except NoSuchElementException:
            print('No fullscreen tag iframe inside. Going with the parent.')

        # Extract all script tags
        soup = BeautifulSoup(html, 'html.parser')
        [x.extract() for x in soup.findAll('script')]

        # File name where to save.
        name = name.encode('utf-8')
        file_name = 'ads-' + get_file_name(name) + '.html'

        print(name, file_name)

        # Save HTML file
        complete_name = os.path.join(save_path, file_name)
        file_object = codecs.open(complete_name, "w", "utf-8")
        file_object.write(str(soup))
        file_object.close()
    except NoSuchElementException:
        print('Error: element not found exception. Page structure for the ad may be different:' + root_url)
    finally:
        print('Finished')


if __name__ == '__main__':
    # Initialise the webdriver for selenium
    # TODO: Need to use PhantomJS for scraping on a server.
    # dcap = dict(DesiredCapabilities.PHANTOMJS)
    # dcap["phantomjs.page.settings.userAgent"] = (
    #     "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/53 "
    #     "(KHTML, like Gecko) Chrome/15.0.87")
    # driver = webdriver.PhantomJS(executable_path='/Users/anupam/Python/Ads_Scraper/phantomjs', desired_capabilities=dcap)
    driver = webdriver.Chrome(executable_path='./chromedriver')

    # Seed URL
    url_list = ['http://www.geeksforgeeks.org/']
    driver.get(url_list[0])
    links = driver.find_elements_by_tag_name('a')
    # for link in links:
    #     href = link.get_attribute('href')
    #     if href is not None and href not in url_list and 'www.geeksforgeeks.org' in href:
    #         # print(href)
    #         url_list.append(href)

    print(len(url_list))
    i = 0
    for url in url_list:
        driver.get(url)
        get_ads_file(driver, url, i)
        i += 1
        # driver.quit()
