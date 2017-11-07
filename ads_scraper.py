##
## WebScraper to extract google ads from sites which have google ads.
##

import codecs
import hashlib
import os
import urllib
import urllib.request as urlrequest
from os.path import splitext
from urllib.parse import urlparse

import pickle
from PIL import Image
from bs4 import BeautifulSoup
from selenium import webdriver
import re
from bloom_filter import BloomFilter
from selenium.common.exceptions import NoSuchElementException
import logging

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
def get_ads_file(browser, root_url, index, bloom):
    global logger
    try:
        # Wait for page to be rendered
        browser.implicitly_wait(10)  # seconds
        # Save path
        save_path = os.path.expanduser('./sample-run')

        # Switch to google ad frame. If it is a google normal ads
        # Works in geeksforgeeks.org browser.find_element_by_xpath('//ins[contains(@class, "adsbygoogle")]')
        actual_ad_ins_element = browser.find_element_by_xpath('//*[contains(@class, "googlead")]')
        browser.switch_to.frame(actual_ad_ins_element.find_element_by_tag_name('iframe'))

        # Google Ad Frame main layout with id google_ads_frame<number>.
        # Currently only getting the first layout
        count = 0
        ad_src_url = ""
        browser.implicitly_wait(15)
        for element in browser.find_elements_by_tag_name('iframe'):
            if element.get_attribute('allowfullscreen') is not None:
                if (element.get_attribute('src') is not None):
                    count = 15
                    ad_src_url = element.get_attribute('src')
                else:
                    browser.switch_to.frame(element)
                    count = 1
                break
        while count > 0:
            if ad_src_url is not "":
                browser.get(ad_src_url)

            browser.save_screenshot('current-ad.png')
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
                try:
                    ad_href_link = browser.find_element_by_tag_name('a')
                    type = 3
                    name = ad_href_link.get_attribute('href')
                    try:
                        name_list = name.split('&')
                        for x in name_list:
                            if 'adurl=' in x:
                                x = x.split('=')[1]
                                x = urllib.parse.unquote(x)
                                name = x.split('?')[0]
                                break

                    except:
                        print(name)
                except:
                    continue

            finally:
                html = browser.execute_script("return document.getElementsByTagName('html')[0].innerHTML")

            # File name where to save.
            utf8_name = name.encode('utf-8')
            file_name = 'ads-' + str(type) + '-' + get_file_name(utf8_name) + '.html'

            if name in bloom:
                # print(name, 'already present')
                logger.info('already present: ' + name)
                continue
            else:
                bloom.add(name)

            logger.info(str(name) + " : " + file_name)

            # Remove all script tags
            soup = BeautifulSoup(html, 'html.parser')
            [x.extract() for x in soup.findAll('script')]

            print(file_name, name)

            # Save HTML file
            complete_name = os.path.join(save_path, file_name)
            file_object = codecs.open(complete_name, "w", "utf-8")
            file_object.write(str(soup))
            file_object.close()
            count -= 1
    # Didnot find any iframe with google_ads_frame<number> id.
    except Exception as e:
        # print(e.msg)
        browser.save_screenshot('error.png')
        logger.error('google_ads_frame<num> not found exception:' + e.msg)


if __name__ == '__main__':
    # Initialise the webdriver for selenium
    # TODO: Need to use PhantomJS for scraping on a server.
    dcap = dict(DesiredCapabilities.PHANTOMJS)
    dcap["phantomjs.page.settings.userAgent"] = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36")
    driver = webdriver.PhantomJS(executable_path='./phantomjs', desired_capabilities=dcap, service_args=['--ignore-ssl-errors=true', '--ssl-protocol=TLSv1'])
    # driver = webdriver.Chrome(executable_path='./chromedriver')
    driver.set_window_size(1280, 628)

    bloom = BloomFilter(max_elements=1000000, error_rate=0.1)
    pickle_file = 'filter.pickle'
    if os.path.exists(pickle_file):
        print('%s already present - Loading saved filter.' % pickle_file)
        try:
            with open(pickle_file, 'rb') as f:
                bloom = pickle.load(f)
        except Exception as e:
            print("Unable to read data from %s" % pickle_file)

    # Seed URL
    base_url = 'https://www.tutorialspoint.com/'
    url_list = [base_url]
    driver.get(url_list[0])
    links = driver.find_elements_by_tag_name('a')
    for link in links:
        href = link.get_attribute('href')
        if href is not None and href not in url_list and base_url in href:
            url_list.append(href)

    logger = logging.getLogger('ads_scraper')
    hdlr = logging.FileHandler('scraper.log')
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(logging.WARNING)

    print(len(url_list))
    i = 0
    while i<len(url_list) or i<5000:
        url = url_list[i]
        driver.get(url)
        links = driver.find_elements_by_tag_name('a')
        for link in links:
            href = link.get_attribute('href')
            if href is not None and href not in url_list and base_url in href:
                url_list.append(href)
        logger = logging.getLogger('ads_scraper')
        hdlr = logging.FileHandler('scraper.log')
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        hdlr.setFormatter(formatter)
        logger.addHandler(hdlr)
        logger.setLevel(logging.WARNING)
        get_ads_file(driver, url, i, bloom)
        try:
            f = open(pickle_file, 'wb')
            pickle.dump(bloom, f, pickle.HIGHEST_PROTOCOL)
            f.close()
        except Exception as e:
            print('Unable to save data to', pickle_file, ':', e)
            raise
        i += 1
    print('Finished')
    driver.quit()
