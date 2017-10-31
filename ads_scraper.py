##
## WebScraper to extract google ads from sites which have google ads.
##

import codecs
import hashlib
import os
import urllib.request as urlrequest
from os.path import splitext
from urllib.parse import urlparse
from PIL import Image
from bs4 import BeautifulSoup
from selenium import webdriver
import re
from bloom_filter import BloomFilter
from selenium.common.exceptions import NoSuchElementException
import logging


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
def get_ads_file(browser, root_url, index, bloom):
    global logger
    try:
        # Wait for page to be rendered
        browser.implicitly_wait(10)  # seconds

        # Save path
        save_path = os.path.expanduser('./sample-run')

        # Switch to google ad frame. If it is a google normal ads
        actual_ad_ins_element = browser.find_element_by_xpath('//ins[contains(@class, "adsbygoogle")]')
        browser.switch_to.frame(actual_ad_ins_element.find_element_by_tag_name('iframe'))

        # Google Ad Frame main layout with id google_ads_frame<number>.
        # Currently only getting the first layout
        browser.implicitly_wait(15)
        for element in browser.find_elements_by_tag_name('iframe'):
            if element.get_attribute('allowfullscreen') is not None:
                browser.switch_to.frame(element)
                break
        try:
            browser.implicitly_wait(10)
            browser.switch_to.frame(browser.find_element_by_id('ad_iframe'))
            # Switch to that or else look into the other type of html
            # embedded google ad.
            # Wait for the ad iframe to be rendered after the switch.
            browser.implicitly_wait(10)
            actual_ad_ins_element = None
            for element in browser.find_elements_by_tag_name('iframe'):
                if element.get_attribute('allowfullscreen') is not None:
                    actual_ad_ins_element = element
                    break
            if actual_ad_ins_element is not None:
                type = 1
                name = actual_ad_ins_element.get_attribute('src')
                browser.switch_to.frame(actual_ad_ins_element)
            else:
                type = 2
                name = browser.find_element_by_xpath('//a//img').get_attribute('src')
        except NoSuchElementException:
            ad_href_link = browser.find_element_by_tag_name('a')
            type = 3
            name = ad_href_link.get_attribute('href')

        finally:
            html = browser.execute_script("return document.getElementsByTagName('html')[0].innerHTML")

        # File name where to save.
        utf8_name = name.encode('utf-8')
        file_name = 'ads-' + str(type) + '-' + get_file_name(utf8_name) + '.html'

        if name in bloom:
            logger.info('already present: ' + name)
            return
        else:
            bloom.add(name)

        logger.info(str(name) + " : " + file_name)
        # # Save image if type 1
        # if type == 1:
        #     print(name)
        #     parsed = urlparse(url)
        #     root, ext = splitext(parsed.path)
        #     urlrequest.urlretrieve(name, file_name + '.' + ext)

        # Remove all script tags
        soup = BeautifulSoup(html, 'html.parser')
        [x.extract() for x in soup.findAll('script')]

        print(file_name, name)

        # Save HTML file
        complete_name = os.path.join(save_path, file_name)
        file_object = codecs.open(complete_name, "w", "utf-8")
        file_object.write(str(soup))
        file_object.close()
    # Didnot find any iframe with google_ads_frame<number> id.
    except NoSuchElementException as e:
        print(e.msg)
        logger.error('google_ads_frame<num> not found exception:' + e.msg)


if __name__ == '__main__':
    # Initialise the webdriver for selenium
    # TODO: Need to use PhantomJS for scraping on a server.
    # dcap = dict(DesiredCapabilities.PHANTOMJS)
    # dcap["phantomjs.page.settings.userAgent"] = (
    #     "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/53 "
    #     "(KHTML, like Gecko) Chrome/15.0.87")
    # driver = webdriver.PhantomJS(executable_path='/Users/anupam/Python/Ads_Scraper/phantomjs', desired_capabilities=dcap)
    driver = webdriver.Chrome(executable_path='./chromedriver')
    bloom = BloomFilter(max_elements=10000, error_rate=0.1)
    # Seed URL
    url_list = ['http://www.geeksforgeeks.org/']
    driver.get(url_list[0])
    links = driver.find_elements_by_tag_name('a')
    for link in links:
        href = link.get_attribute('href')
        if href is not None and href not in url_list and 'www.geeksforgeeks.org' in href:
            url_list.append(href)

    logger = logging.getLogger('ads_scraper')
    hdlr = logging.FileHandler('scraper.log')
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(logging.WARNING)

    print(len(url_list))
    i = 0
    for url in url_list:
        driver.get(url)
        get_ads_file(driver, url, i, bloom)
        i += 1

    driver.quit()
