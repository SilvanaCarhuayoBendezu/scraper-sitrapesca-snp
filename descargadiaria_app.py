# Descarga Diaria (Ultimos 3 días)

import os, time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo  # py>=3.9
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# === PARÁMETROS & TZ ===
LIMA = ZoneInfo("America/Lima")

fecha_base = os.environ.get("FECHA_BASE")

# Fecha fijada para test
if fecha_base:
    fecha_inicio = (datetime.strptime(fecha_base, "%d/%m/%Y") - timedelta(days=2)).strftime("%d/%m/%Y") + " 00:00"
    fecha_fin = datetime.strptime(fecha_base, "%d/%m/%Y").strftime("%d/%m/%Y") + " " + str(datetime.now().hour) + ":" + f"{datetime.now().minute:02d}" 
else:
    fecha_inicio = (datetime.now(LIMA) - timedelta(days=2)).strftime("%d/%m/%Y") + " 00:00"
    fecha_fin = datetime.now(LIMA).strftime("%d/%m/%Y") + " " + str(datetime.now().hour) + ":" + f"{datetime.now().minute:02d}" 

print(fecha_inicio, "-", fecha_fin)

DOWNLOAD_DIR = os.path.abspath(os.environ.get("DOWNLOAD_DIR", "./downloads"))
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Credenciales desde variables de entorno
CRED1_RAZON = os.environ.get("CRED1_RAZON")
CRED1_RUC   = os.environ.get("CRED1_RUC")
CRED1_PASS  = os.environ.get("CRED1_PASS")
CRED2_RAZON = os.environ.get("CRED2_RAZON")
CRED2_RUC   = os.environ.get("CRED2_RUC")
CRED2_PASS  = os.environ.get("CRED2_PASS")
CRED3_RAZON = os.environ.get("CRED3_RAZON")
CRED3_RUC   = os.environ.get("CRED3_RUC")
CRED3_PASS  = os.environ.get("CRED3_PASS")

# === HELPERS PARA DESCARGAS Y DRIVER ===

def build_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-extensions")
    options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari')

    prefs = {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(options=options)
    try:
        driver.execute_cdp_cmd(
            "Page.setDownloadBehavior", 
            {"behavior": "allow", "downloadPath": DOWNLOAD_DIR}
        )
    except Exception:
        pass
    return driver

def limpiar_descargas():
    """Borra CSVs y .crdownload previos para que el conteo sea limpio."""
    for f in os.listdir(DOWNLOAD_DIR):
        if f.lower().endswith(".csv") or f.lower().endswith(".crdownload"):
            try:
                os.remove(os.path.join(DOWNLOAD_DIR, f))
            except Exception:
                pass

def contar_csv():
    return len([f for f in os.listdir(DOWNLOAD_DIR) if f.lower().endswith(".csv")])

def esperar_descargas_esperadas(esperado, timeout=120, intervalo=5):
    """
    Espera hasta que haya al menos `esperado` CSV en DOWNLOAD_DIR
    o se llegue al timeout.
    """
    inicio = time.time()
    while time.time() - inicio < timeout:
        csv_count = contar_csv()
        print(f"Archivos CSV actuales: {csv_count} / {esperado}")
        # Asegúrate también que no haya descargas en curso (.crdownload)
        crdownload = any(f.endswith(".crdownload") for f in os.listdir(DOWNLOAD_DIR))
        if csv_count >= esperado and not crdownload:
            return True
        time.sleep(intervalo)
    return False

# === UN SOLO INTENTO DE SCRAPING PARA UNA CREDENCIAL ===

def run_sitrap_once(razon_social_val, ruc_val, clave_val, card_index):
    print(f"Iniciando Descarga CSV SITRAPESCA: {razon_social_val} - card {card_index}")
    driver = build_driver()
    try:
        url = "https://sistemas.produce.gob.pe/#/administrados"
        driver.get(url)

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (By.XPATH, "/html/body/div[1]/div/div[1]/div/div/form/select")
            )
        )
        Select(
            driver.find_element(By.XPATH, "/html/body/div[1]/div/div[1]/div/div/form/select")
        ).select_by_value("2")

        WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable(
                (By.XPATH,'/html/body/div[1]/div/div[1]/div/div/form/div[2]/input')
            )
        ).send_keys(razon_social_val, Keys.ENTER)

        WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable(
                (By.XPATH,'/html/body/div[1]/div/div[1]/div/div/form/div[4]/input')
            )
        ).send_keys(ruc_val, Keys.ENTER)

        WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable(
                (By.XPATH,'/html/body/div[1]/div/div[1]/div/div/form/div[6]/input')
            )
        ).send_keys(clave_val, Keys.ENTER)

        try:
            WebDriverWait(driver, 30).until(
                EC.invisibility_of_element_located(
                    (By.XPATH, '/html/body/div[1]/div/div[1]/div/div/form')
                )
            )
        except Exception:
            print("El formulario no desapareció; continúo igual.")

        # Cierra modal si existe
        try:
            driver.execute_script("document.querySelector('.modal-dialog .btn-primary').click();")
        except Exception:
            pass

        # Click en la card correspondiente
        enlace_card = WebDriverWait(driver, 35).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, f"#ng-view > div > div > div.row > div:nth-child({card_index}) > div > a")
            )
        )
        driver.execute_script("arguments[0].click();", enlace_card)

        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(
                (By.XPATH, '/html/body/div/div[1]/nav/div/div[2]/ul[1]/li[8]/a')
            )
        )

        dropdown = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable(
                (By.XPATH, "(//ul[@class='nav navbar-nav']/li[contains(@class, 'dropdown')])[6]")
            )
        )
        dropdown.click()
        menu_option = WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.LINK_TEXT, "Faenas y Calas"))
        )
        menu_option.click()
        WebDriverWait(driver, 15).until(EC.url_contains("FaenasCalas"))

        # Checkboxes
        for css in [
            "input[type='checkbox'][data-bind='checked: Model.ListadoFaenas']",
            "input[type='checkbox'][data-bind='checked: Model.ListadoCalas']",
            "input[type='checkbox'][data-bind='checked: Model.ListadoComposicionTallas']"
        ]:
            cb = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, css))
            )
            if not cb.is_selected():
                cb.click()

        # Radio CSV
        radio = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, "//input[@type='radio' and @id='radio3' and @value='3' and @data-bind='checked:Model.TipoFormato']")
            )
        )
        if not radio.is_selected():
            radio.click()

        # Fechas
        input_fecha = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[data-bind='value: Model.FechaInicio']")
            )
        )
        input_fecha.clear()
        input_fecha.send_keys(fecha_inicio)

        end_fecha = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[data-bind='value: Model.FechaFin']")
            )
        )
        end_fecha.clear()
        end_fecha.send_keys(fecha_fin)

        print(f"Descargando archivos desde: {fecha_inicio} a {fecha_fin}")

        boton = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button[data-bind='click: fnVerReporte']")
            )
        )
        boton.click()

        # Espera base para que el servidor genere los reportes
        time.sleep(35)

    except (TimeoutException, NoSuchElementException) as e:
        # Lanzamos la excepción hacia arriba para que el caller sepa que falló este intento
        print(f"[ERROR Selenium] {e}")
        raise
    finally:
        driver.quit()

# === ENVOLTORIO CON REINTENTOS ===

def run_sitrap_with_retries(razon, ruc, pwd, card_index, expected_files, max_attempts=5):
    """
    Ejecuta run_sitrap_once hasta max_attempts veces o hasta que se descarguen
    los 'expected_files' CSV (acumulados en DOWNLOAD_DIR).
    """
    for attempt in range(1, max_attempts + 1):
        print(f"\n>>> Intento {attempt}/{max_attempts} para {razon} (card {card_index})")
        limpiar_descargas()

        try:
            run_sitrap_once(razon, ruc, pwd, card_index)
        except Exception as e:
            print(f"Intento {attempt} falló con error: {e} para {razon}")
            continue  # pasa al siguiente intento

        # Esperar las descargas
        ok = esperar_descargas_esperadas(expected_files)
        if ok:
            print(f"Descarga correcta para {razon}: {contar_csv()} archivos CSV.")
            return True
        else:
            print(f"No se alcanzaron los {expected_files} CSV esperados en el intento {attempt}.")

    print(f"[FALLO] No se pudieron conseguir los {expected_files} CSV para {razon} tras {max_attempts} intentos.")
    return False

if __name__ == "__main__":
    # Asumiendo 3 CSV por empresa (Faenas, Calas, Composición) = 9
    ok1 = run_sitrap_with_retries(CRED1_RAZON, CRED1_RUC, CRED1_PASS, 7, expected_files=3)
    ok2 = run_sitrap_with_retries(CRED2_RAZON, CRED2_RUC, CRED2_PASS, 8, expected_files=3)
    ok3 = run_sitrap_with_retries(CRED3_RAZON, CRED3_RUC, CRED3_PASS, 9, expected_files=3)

    total_csv = contar_csv()
    print(f"Total CSV finales en {DOWNLOAD_DIR}: {total_csv}")

    if not (ok1 and ok2 and ok3) or total_csv < 9:
        raise RuntimeError("No se descargaron los 9 CSV esperados.")
