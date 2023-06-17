from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from random import randint

class Crawler:
    def __init__(self):        
        options = webdriver.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-notifications')
        options.add_argument('--disable-infobars')
        options.add_argument('--mute-audio')
        options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36')
        
        self.driver = webdriver.Chrome(options=options)

        self.findTrip_blog_url = 'https://www.funtime.com.tw/blog/search.php?s='

        
    def FindTrip(self, location):
        print(f'（正在搜尋： {{{location}}} 行程）')
        url = self.findTrip_blog_url + location
        self.driver.get(url)

        posts = self.driver.find_elements(By.CSS_SELECTOR, '.post.clearfix')

        def GetContent(url):
            original_window = self.driver.current_window_handle
            self.driver.execute_script("window.open();")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            self.driver.get(url)
            innerPost = BeautifulSoup(self.driver.find_element(By.ID, 'content').find_element(By.CLASS_NAME, 'entry').get_attribute('innerHTML'), 'html.parser')
            texts = ' '.join(tag.text for tag in innerPost.find_all())
            self.driver.close()
            self.driver.switch_to.window(original_window)
            return texts
        
        post = posts[randint(0,len(posts)-1)]
        response = {'title': post.find_element(By.CLASS_NAME, 'post-content').find_element(By.TAG_NAME, 'h2').text,
                 'description': post.find_element(By.CLASS_NAME, 'entry').text,
                 'content': GetContent(post.find_element(By.TAG_NAME, 'a').get_attribute('href'))[:8000],
                 }
        
        self.driver.close()
        print(f'（！搜尋完成！）')
        return response


if __name__ == '__main__':
    search = "台北"
    crawler = Crawler()
    urls = crawler.FindTrip(search)
