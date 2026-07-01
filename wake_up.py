import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

URL = "https://x4good.streamlit.app"  

options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(options=options)

try:
    print(f"Acessando {URL}...")
    driver.get(URL)
    
    #Aguarda a página carregar
    time.sleep(5)
    
    #Procura pelo botão de "Wake up"
    buttons = driver.find_elements(By.XPATH, "//button[contains(., 'app back up') or contains(., 'Wake up')]")
    
    if buttons:
        print("App detectado como dormindo! Clicando no botão para acordar...")
        buttons[0].click()
        
        #Aguarda até 60 segundos para o container principal do Streamlit renderizar o dashboard
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.DATA_TESTID, "stAppViewContainer"))
        )
        print("App acordado e carregado com sucesso!")
    else:
        print("O app já está online.")

except Exception as e:
    print(f"Erro durante a execução: {e}")
finally:
    driver.quit()