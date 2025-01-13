import datamanager
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import re
import undetected_chromedriver as uc
import json
from firebase_admin import credentials, firestore
import firebase_admin

class PowerCutDataScrap(metaclass=datamanager.SingletonMeta):
    data_for_firebase = []
    baseUrl = 'https://lichcupdien.org/'
    service = Service()
    options = webdriver.ChromeOptions()
    driver = uc.Chrome(options = options, service = service)

    cred = credentials.Certificate('C://Users//hungt//Desktop//dataScrape//rental-room-c34cb-firebase-adminsdk-vap7d-d05ddd648a.json')
    firebase_admin.initialize_app(cred, {
        'storageBucket': 'rental-room-c34cb.appspot.com'
    })
    db = firestore.client()

    def __init__(self):
        print("powercut init")

    def scrapData(self):
        file_path = 'content/LinkPowerCut.json'
        with open(file_path, 'r') as file:
            json_list = json.load(file)
        for link in json_list:
            self.driver.get(link["link"])
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            power_cut_data = []

            date_elements = soup.find_all('h3', class_='tab-items-title-bold tab-items-red')

            # Iterate over each date
            for i, date_element in enumerate(date_elements):
                # Extract the date from the h3 text
                date_text = date_element.get_text()
                date_match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', date_text)
                
                if date_match:
                    day, month, year = date_match.groups()
                    formatted_date = f"{day} tháng {month} năm {year}"
                    
                    # Initialize list to hold all power cut details for this date
                    details_list = []
                    
                    # Get the next date_element or None if this is the last date
                    next_date_element = date_elements[i + 1] if i + 1 < len(date_elements) else None
                    
                    # Get all elements between current date_element and next date_element
                    current_element = date_element.find_next_sibling()
                    
                    while current_element and current_element != next_date_element:
                        # Process lcd_detail_wrapper elements only
                        if current_element.name == 'div' and 'lcd_detail_wrapper' in current_element.get('class', []):
                            power_cut_info = {}
                        
                            power_company = current_element.find('span', class_='content_item_content_lcd_wrapper item_txt_bold').text
                            power_cut_info['powerCompany'] = power_company

                            # Extract "Ngày"
                            date = current_element.find('span', class_='content_item_content_lcd_wrapper item_txt_bold item_txt_red').text
                            power_cut_info['date'] = date

                            # Extract "Thời gian"
                            time_period = current_element.find_all('span', class_='item_lcd_time')
                            start_time = time_period[0].text
                            end_time = time_period[1].text
                            power_cut_info['startTime'] = start_time
                            power_cut_info['endTime'] = end_time

                            # Extract "Khu vực"
                            location = current_element.find_all('div', class_='item_content_lcd_wrapper')[3].find('span', class_='content_item_content_lcd_wrapper').text
                            power_cut_info['location'] = location

                            # Extract "Lý do"
                            reason = current_element.find_all('div', class_='item_content_lcd_wrapper')[4].find('span', class_='content_item_content_lcd_wrapper').text
                            power_cut_info['reason'] = reason

                            # Extract "Trạng thái"
                            status = current_element.find_all('div', class_='item_content_lcd_wrapper')[-1].find('span', class_='content_item_content_lcd_wrapper').text
                            power_cut_info['status'] = status

                            details_list.append(power_cut_info)
                            
                        current_element = current_element.find_next_sibling()

                    power_cut_data.append({
                        "date": formatted_date,
                        "details": details_list
                    })



            self.data_for_firebase.append({
                "provinceName": link["provinceName"],
                "powerCuts": power_cut_data
            })

        with open('content/power_cut_info.json', 'w', encoding='utf-8') as json_file:
            json.dump(self.data_for_firebase, json_file, ensure_ascii=False, indent=4)

    def uploadDataToFirebase(self):
        for item in self.data_for_firebase:
            powerCutRef = self.db.collection('PowerCut').document()
            powerCutRef.set(item)

    def resetPowerCutCollection(self, col_name, batch_size):
        if batch_size == 0:
            return
        coll_ref = self.db.collection(col_name)
        docs = coll_ref.list_documents(page_size=batch_size)

        for doc in docs:
            doc.delete()
