# Ads_scraper
A google ads scraper project.  
I aim to extract google ads from webpages for creating a dataset of online ads. The aim of the dataset is to collect static html to capture design cues from any online ad campaign.  
I am using selenium web driver and phantom js for this. Major challenge is that ads are stored in nested iframes which are hard to capture in selenium or phantom js. So I looked into different ads and was able to categorise it into 3 types of ads:
1. iframe with static html code.  
2. iframe with images.  
3. iframe with url

First 2 were simple and could be easily saved offline. Third was tough to save as I was not able to find a common html skeleton among different types of ads. Yet there were a few ads that had a particular iframe with a particular div tag that could be found and saved.

I also used a bloom filter to prevent saving of duplicate ads, with different types of input to the bloom filter for each type mentioned above. 

I was able to gather 700 ads, after which there was repetition in the ads that occurred in the website that were being scraped.
