from flask import Flask, render_template, request
import pandas as pd
import urllib.parse
import time
import os
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

app = Flask(__name__)

driver = None

def get_driver():
    global driver
    if driver is None:
        chrome_options = Options()
        current_dir = os.path.dirname(os.path.abspath(__file__))
        user_data_dir = os.path.join(current_dir, 'whatsapp_session')
        chrome_options.add_argument(f"user-data-dir={user_data_dir}")
        
        chrome_options.binary_location = "/usr/bin/chromium-browser"
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        
        driver = webdriver.Chrome(options=chrome_options)
    return driver

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/send', methods=['POST'])
def send_messages():
    global driver
    if 'file' not in request.files:
        return "No file uploaded!"
    
    file = request.files['file']
    message_template = request.form['message']
    phone_col_name = request.form['phone_col']
    name_col_name = request.form['name_col']
    date_col_name = request.form['date_col']
    
    df = pd.read_excel(file)
    success_count = 0
    
    try:
        drv = get_driver()
        
        for index, row in df.iterrows():
            # 1. Phone number clean karein
            phone = str(row[phone_col_name])
            if '.' in phone:
                phone = phone.split('.')[0]
            phone = phone.replace("+", "").replace(" ", "").strip()
            
            # 2. Excel se Name uthayein
            person_name = str(row.get(name_col_name, 'Ji'))
            
            # 3. Excel se Date uthayein
            raw_date = row.get(date_col_name, '')
            if pd.notna(raw_date):
                if isinstance(raw_date, pd.Timestamp):
                    msg_date = raw_date.strftime('%d-%m-%Y')
                else:
                    msg_date = str(raw_date)
            else:
                msg_date = ''
            
            # 4. Message format karein
            personalized_message = message_template.format(name=person_name, date=msg_date)
            
            if len(phone) >= 10:
                try:
                    encoded_msg = urllib.parse.quote(personalized_message)
                    chat_url = f"https://web.whatsapp.com/send?phone={phone}&text={encoded_msg}"
                    
                    # URL load karein
                    drv.get(chat_url)
                    
                    # pehle number par WhatsApp load hone ke liye 4-5 second ka proper wait dein
                    time.sleep(4) 
                    
                    wait = WebDriverWait(drv, 15)
                    
                    # 5. Invalid number check karein
                    try:
                        ok_button_xpath = '//div[@role="button"]//div[text()="OK" or text()="Ok"]'
                        invalid_popup = WebDriverWait(drv, 2).until(
                            EC.element_to_be_clickable((By.XPATH, ok_button_xpath))
                        )
                        invalid_popup.click()
                        time.sleep(1)
                        continue 
                    except Exception:
                        pass
                    
                    # 6. Message box load hone ka wait karein
                    input_box_xpath = '//div[@contenteditable="true"][@data-tab="10"]'
                    input_box = wait.until(EC.element_to_be_clickable((By.XPATH, input_box_xpath)))
                    
                    time.sleep(1.5) # Box stable hone dein
                    
                    # 7. Message bhejne ke liye Enter press karein (yeh draft ko turant send kar dega)
                    input_box.send_keys(Keys.ENTER)
                    
                    # 8. Extra safety ke liye Send Button par bhi click karein agar available ho
                    try:
                        send_button_xpath = '//span[@data-icon="send"]'
                        send_btn = drv.find_element(By.XPATH, send_button_xpath)
                        send_btn.click()
                    except Exception:
                        pass
                    
                    # 9. Message poori tarah send hone ke liye 3 second ka wait aur fir agla number
                    time.sleep(3) 
                    success_count += 1
                    
                except Exception as inner_e:
                    print(f"Skipping {phone} due to error: {inner_e}")
                    continue
                        
    except Exception as outer_e:
        return f"<h3>Execution Error: {str(outer_e)}</h3>"
            
    return f"<h3>🎉 Process Complete! Safalata purvak {success_count} messages bhej diye gaye hain.</h3><a href='/'>Wapas Jayein</a>"

if __name__ == '__main__':
    app.run(debug=True, port=5000)