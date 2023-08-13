from bs4 import BeautifulSoup
import requests
import pandas as pd
from unidecode import unidecode
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service

# Este url contiene todas las ciudades
url_principal = "https://www.portalinmobiliario.com/venta/casa/propiedades-usadas/valparaiso_FiltersAvailableSidebar?filter=city"


# Función para obtener información de la página de manera desorganizada.
def data(url_principal):
    html_texto = requests.get(url_principal).text
    soup_principal = BeautifulSoup(html_texto, "lxml")
    return soup_principal


# Función para determinar la url de cada una de las ciudades de la RM
def urls_por_ciudad(soup_principal):
    # Lista de ciudades de la región de valparaíso
    ciudades = soup_principal.find("div", class_="ui-search-search-modal-grid-columns")
    # ciudades = soup_principal.find('a', class_ = 'ui-search-search-modal-filter ui-search-link')
    urls_x_ciudad = []
    for ciudad in ciudades:
        # Se aplica unidecode para quitar acentos y se reemplazan los espacios de los nombres de las ciudades por - para obtener la url correspondiente
        nombre_ciudad = unidecode(
            ciudad.find(
                "span", class_="ui-search-search-modal-filter-name"
            ).text.replace(" ", "-")
        )
        # Se obtiene la url de cada una
        url_cada_ciudad = (
            "https://www.portalinmobiliario.com/venta/casa/propiedades-usadas/"
            + nombre_ciudad
            + "-valparaiso/_NoIndex_True"
        )
        # Se genera una restricción para separar por filtro de precios si las páginas tienen mas de 2000 resultados
        soup_x_ciudad = data(url_cada_ciudad)
        # La idea es extraer toda la data y no un máximo de 2000
        resultados_x_ciudad = soup_x_ciudad.find(
            "span",
            class_="ui-search-search-result__quantity-results shops-custom-secondary-font",
        ).text.replace(".", "")
        # Se extrae el número de la oración
        resultados = [int(x) for x in resultados_x_ciudad.split() if x.isdigit()]
        # total = total + resultados[0]
        if resultados[0] > 2000:
            # Se aplica otro filtro a las urls x ciudad, al cual se le agrega el precio
            ciudades_con_filtro = soup_x_ciudad.find_all(
                "li", class_="ui-search-money-picker__li"
            )
            for city in ciudades_con_filtro:
                url_casa_filtro = city.a["href"]
                urls_x_ciudad.append(url_casa_filtro)
        else:
            # Se guardan las urls en esta variable
            urls_x_ciudad.append(url_cada_ciudad)

    return urls_x_ciudad


# Función para obtener la página siguiente
def pag_sig(soup_principal):
    page_principal = soup_principal.find(
        "ul", class_="ui-search-pagination andes-pagination shops__pagination"
    )
    # Si no existe, es porque la pagina tiene menos de 50 ofertas o estamos en la última página
    if not page_principal or not page_principal.find(
        "li",
        class_="andes-pagination__button andes-pagination__button--next shops__pagination-button",
    ):
        return
    # Regresamos la url de la pagina siguiente
    else:
        url_principal = page_principal.find(
            "li",
            class_="andes-pagination__button andes-pagination__button--next shops__pagination-button",
        ).a["href"]
        return url_principal


# Función para obtener los datos de cada casa de una url (página web)
def variables(soup_principal):
    options = webdriver.ChromeOptions()
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    service = Service("driver/chromedriver.exe")
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(5)

    # Se ubican todas las casas dentro de la página
    casas = soup_principal.find_all(
        "li", class_="ui-search-layout__item shops__layout-item"
    )

    # Se define la variable donde se almacenaran todos los datos
    datos_casas = []

    # Se define esta tabla de encabezados de la sección 1 para poder compararlos con los encabezados que no encuentra en la pagina y asi poder rellenar con cero
    tabla_s1 = [
        "Superficie total",
        "Superficie útil",
        "Dormitorios",
        "Baños",
        "Estacionamientos",
        "Bodegas",
        "Cantidad de pisos",
        "Tipo de casa",
        "Antigüedad",
        "Gastos comunes",
    ]

    # Se define esta tabla de encabezados de la sección 2 para poder
    # compararlos con los encabezados que no encuentra en la pagina
    # y asi poder rellenar con cero
    tabla_s2 = [
        "Estaciones de metro",
        "Paraderos",
        "Jardines infantiles",
        "Colegios",
        "Universidades",
        "Plazas",
        "Supermercados",
        "Farmacias",
        "Centros comerciales",
        "Hospitales",
        "Clínicas",
    ]

    # Se reccore la raw data de cada casa
    for casa in casas:
        # Se obtiene la url de cada casa
        url_cada_casa = casa.div.div.a["href"]
        # Mediante el Try se evita el error TooManyRedirects de páginas que no abren
        try:
            driver.get(url_cada_casa)

            # Este tiempo es porque aveces no alcanza a cargar la pagina y es necesario fijar un tiempo de espera
            content = driver.page_source.encode("utf-8").strip()
            soup = BeautifulSoup(content, "lxml")

            # Se obtiene el precio de cada casa
            cada_casa = soup.find("div", class_="ui-pdp-price__second-line")
            precio_casa = cada_casa.span.span.text

            # Se obtiene la comuna donde esta cada casa
            comuna = soup.find_all("a", class_="andes-breadcrumb__link")
            comuna_x_casa = comuna[4].text

            # Se genera una nueva variable para posicionar la pantalla en donde esta la tabla
            wait = WebDriverWait(driver, 10)
            scroll = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "ui-pdp-specs__table"))
            )
            driver.execute_script("arguments[0].scrollIntoView();", scroll)

            # Info de la sección 1
            datos_s1 = soup.find_all("tr", class_="andes-table__row")

            encabezados_s1 = []
            for datos in datos_s1:
                encabezado = datos.find(
                    "th",
                    class_="andes-table__header andes-table__header--left ui-pdp-specs__table__column ui-pdp-specs__table__column-title",
                ).text

                encabezados_s1.append(encabezado)
                if encabezado == "Superficie total":
                    superficie_t = datos.td.span.text

                elif encabezado == "Superficie útil":
                    superficie_u = datos.td.span.text

                elif encabezado == "Dormitorios":
                    dormitorio = datos.td.span.text

                elif encabezado == "Baños":
                    baño = datos.td.span.text

                elif encabezado == "Estacionamientos":
                    estacionamiento = datos.td.span.text

                elif encabezado == "Bodegas":
                    bodega = datos.td.span.text

                elif encabezado == "Cantidad de pisos":
                    piso = datos.td.span.text

                elif encabezado == "Tipo de casa":
                    tipo = datos.td.span.text

                elif encabezado == "Antigüedad":
                    antiguedad = datos.td.span.text

                elif encabezado == "Gastos comunes":
                    gasto = datos.td.span.text

                else:
                    continue
            # Cuando no encuentra uno de los elementos, se rellena con 0 o 1 respectivamente
            elementos_s1 = list(set(tabla_s1) ^ set(encabezados_s1))

            for elemento in elementos_s1:
                if elemento == "Superficie total":
                    superficie_t = 0

                elif elemento == "Superficie útil":
                    superficie_u = 0

                elif elemento == "Dormitorios":
                    dormitorio = 0

                elif elemento == "Baños":
                    baño = 0

                elif elemento == "Estacionamientos":
                    estacionamiento = 0

                elif elemento == "Bodegas":
                    bodega = 0

                elif elemento == "Cantidad de pisos":
                    piso = 1

                elif elemento == "Tipo de casa":
                    tipo = "casa"

                elif elemento == "Antigüedad":
                    antiguedad = " "

                elif elemento == "Gastos comunes":
                    gasto = 0

                else:
                    continue

            # Se obtiene la dirección de la casa
            direccion = soup.find_all(
                "p",
                class_="ui-pdp-color--BLACK ui-pdp-size--SMALL ui-pdp-family--REGULAR ui-pdp-media__title",
            )
            direccion_x_casa = direccion[6].text

            descripcion = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "ui-pdp-description"))
            )
            driver.execute_script("arguments[0].scrollIntoView();", descripcion)
            # La descripción es separada en una lista de palabras
            palabras = (descripcion.text).split()

            for palabra in palabras:
                palabra_l = palabra.lower()
                if (
                    palabra_l == "generador"
                    or palabra_l == "paneles"
                    or palabra_l == "solares"
                    or palabra_l == "solar"
                    or palabra_l == "generadores"
                ):
                    paneles = 1
                    break
                else:
                    paneles = 0

            # Info de la sección 2 de la página
            # Se definen los elementos a ser clickeados, en este caso el titulo de la pestaña
            botones = driver.find_elements(By.CLASS_NAME, "ui-vip-poi__tab-title")
            encabezados_s2 = []
            for boton in botones:
                # Se define el encabezado por sección
                encabezado = boton.text

                # Se mueve la pantalla para que carguen los datos al hacer click
                driver.execute_script("arguments[0].scrollIntoView();", boton)
                boton.click()

                if encabezado == "Transporte":
                    s2 = driver.find_elements(
                        By.XPATH, "//div[@class='ui-vip-poi__subsection']"
                    )

                    for s in s2:
                        # Estos son los sub-encabezados de cada sección de transporte
                        sub_encabezado = s.find_element(
                            By.XPATH,
                            ".//span[@class='ui-pdp-color--BLACK ui-pdp-size--SMALL ui-pdp-family--SEMIBOLD ui-vip-poi__subsection-title']",
                        )
                        sub_encabezado_t = sub_encabezado.text
                        encabezados_s2.append(sub_encabezado_t)

                        if sub_encabezado_t == "Estaciones de metro":
                            estaciones = s.find_elements(
                                By.CLASS_NAME, "ui-vip-poi__item"
                            )
                            n_estaciones = len(estaciones)

                        elif sub_encabezado_t == "Paraderos":
                            paraderos = s.find_elements(
                                By.CLASS_NAME, "ui-vip-poi__item"
                            )
                            n_paraderos = len(paraderos)

                        else:
                            continue

                elif encabezado == "Educación":
                    s2 = driver.find_elements(
                        By.XPATH, "//div[@class='ui-vip-poi__subsection']"
                    )

                    for s in s2:
                        # Estos son los sub-encabezados de cada sección de educación
                        sub_encabezado = s.find_element(
                            By.XPATH,
                            ".//span[@class='ui-pdp-color--BLACK ui-pdp-size--SMALL ui-pdp-family--SEMIBOLD ui-vip-poi__subsection-title']",
                        )
                        sub_encabezado_e = sub_encabezado.text
                        encabezados_s2.append(sub_encabezado_e)

                        if sub_encabezado_e == "Jardines infantiles":
                            jardines = s.find_elements(
                                By.CLASS_NAME, "ui-vip-poi__item"
                            )
                            n_jardines = len(jardines)

                        elif sub_encabezado_e == "Colegios":
                            colegios = s.find_elements(
                                By.CLASS_NAME, "ui-vip-poi__item"
                            )
                            n_colegios = len(colegios)

                        elif sub_encabezado_e == "Universidades":
                            universidades = s.find_elements(
                                By.CLASS_NAME, "ui-vip-poi__item"
                            )
                            n_universidades = len(universidades)

                        else:
                            continue

                # Para este caso no es necesario definir el for y el if, pero de igual manera se usarán por si en alguna futuro se agrega otra sub-sección
                elif encabezado == "Áreas verdes":
                    s2 = driver.find_elements(
                        By.XPATH, "//div[@class='ui-vip-poi__subsection']"
                    )

                    for s in s2:
                        # Estos son los sub-encabezados de cada sección de Áreas verdes, en este caso solo hay 1
                        sub_encabezado = s.find_element(
                            By.XPATH,
                            ".//span[@class='ui-pdp-color--BLACK ui-pdp-size--SMALL ui-pdp-family--SEMIBOLD ui-vip-poi__subsection-title']",
                        )
                        sub_encabezado_a = sub_encabezado.text
                        encabezados_s2.append(sub_encabezado_a)

                        if sub_encabezado_a == "Plazas":
                            plazas = s.find_elements(By.CLASS_NAME, "ui-vip-poi__item")
                            n_plazas = len(plazas)

                        else:
                            continue

                elif encabezado == "Comercios":
                    s2 = driver.find_elements(
                        By.XPATH, "//div[@class='ui-vip-poi__subsection']"
                    )

                    for s in s2:
                        # Estos son los sub-encabezados de cada sección de comercios
                        sub_encabezado = s.find_element(
                            By.XPATH,
                            ".//span[@class='ui-pdp-color--BLACK ui-pdp-size--SMALL ui-pdp-family--SEMIBOLD ui-vip-poi__subsection-title']",
                        )
                        sub_encabezado_c = sub_encabezado.text
                        encabezados_s2.append(sub_encabezado_c)

                        if sub_encabezado_c == "Supermercados":
                            supermercados = s.find_elements(
                                By.CLASS_NAME, "ui-vip-poi__item"
                            )
                            n_supermercados = len(supermercados)

                        elif sub_encabezado_c == "Farmacias":
                            farmacias = s.find_elements(
                                By.CLASS_NAME, "ui-vip-poi__item"
                            )
                            n_farmacias = len(farmacias)

                        elif sub_encabezado_c == "Centros comerciales":
                            centros_comerciales = s.find_elements(
                                By.CLASS_NAME, "ui-vip-poi__item"
                            )
                            n_centros_comerciales = len(centros_comerciales)

                        else:
                            continue
                elif encabezado == "Salud":
                    s2 = driver.find_elements(
                        By.XPATH, "//div[@class='ui-vip-poi__subsection']"
                    )

                    for s in s2:
                        # Estos son los sub-encabezados de cada sección de salud
                        sub_encabezado = s.find_element(
                            By.XPATH,
                            ".//span[@class='ui-pdp-color--BLACK ui-pdp-size--SMALL ui-pdp-family--SEMIBOLD ui-vip-poi__subsection-title']",
                        )
                        sub_encabezado_s = sub_encabezado.text
                        encabezados_s2.append(sub_encabezado_s)

                        if sub_encabezado_s == "Hospitales":
                            hospitales = s.find_elements(
                                By.CLASS_NAME, "ui-vip-poi__item"
                            )
                            n_hospitales = len(hospitales)

                        elif sub_encabezado_s == "Clínicas":
                            clinicas = s.find_elements(
                                By.CLASS_NAME, "ui-vip-poi__item"
                            )
                            n_clinicas = len(clinicas)

                        else:
                            continue
                else:
                    continue

            # Cuando no encuentra uno de los elementos, se rellena con 0 o 1 respectivamente
            elementos_s2 = list(set(tabla_s2) ^ set(encabezados_s2))

            for elemento in elementos_s2:
                # Sección Transporte
                if elemento == "Estaciones de metro":
                    n_estaciones = 0

                elif elemento == "Paraderos":
                    n_paraderos = 0

                # Sección Educación
                elif elemento == "Jardines infantiles":
                    n_jardines = 0

                elif elemento == "Colegios":
                    n_colegios = 0

                elif elemento == "Universidades":
                    n_universidades = 0

                # Sección Áreas verdes
                elif elemento == "Plazas":
                    n_plazas = 0

                # Sección Comercios
                elif elemento == "Supermercados":
                    n_supermercados = 0

                elif elemento == "Farmacias":
                    n_farmacias = 0

                elif elemento == "Centros comerciales":
                    n_centros_comerciales = 0

                # Sección Salud
                elif elemento == "Hospitales":
                    n_hospitales = 0

                elif elemento == "Clínicas":
                    n_clinicas = 0
                else:
                    continue

            dict_datos = {
                # Sección 0
                "Precio": precio_casa,
                "Comuna": comuna_x_casa,
                # Sección 1
                "Superficie total": superficie_t,
                "Superficie útil": superficie_u,
                "Dormitorios": dormitorio,
                "Baños": baño,
                "Estacionamientos": estacionamiento,
                "Bodega": bodega,
                "Cantidad de pisos": piso,
                "Tipo de casa": tipo,
                "Antiguedad": antiguedad,
                "Gastos comunes": gasto,
                # Sección 2
                # Transporte
                "Estaciones de metro": n_estaciones,
                "Paraderos": n_paraderos,
                # Educación
                "Jardines infantiles": n_jardines,
                "Colegios": n_colegios,
                "Universidades": n_universidades,
                # Áreas verdes
                "Plazas": n_plazas,
                # Comercios
                "Supermercados": n_supermercados,
                "Farmacias": n_farmacias,
                "Centros comerciales": n_centros_comerciales,
                # Salud
                "Hospitales": n_hospitales,
                "Clínicas": n_clinicas,
                # Paneles solares o generador
                "PS o G": paneles,
                # Direccion
                "Dirección": direccion_x_casa,
                # URLS
                "Url": url_cada_casa,
            }

            datos_casas.append(dict_datos)
        except requests.TooManyRedirects:
            continue
        except AttributeError:
            continue
        except TimeoutException:
            continue
        except IndexError:
            continue
    driver.quit()
    return datos_casas


# Se define la lista en donde se guardaran todos los datos
datos_casas = []

# Página principal
soup_principal = data(url_principal)
urls_ciudad = urls_por_ciudad(soup_principal)

# Recorriendo las ciudades
for url_ciudad in urls_ciudad:
    # Recorriendo las páginas de cada ciudad
    while True:
        # Extraer data de la página de la ciudad
        soup_x_ciudad = data(url_ciudad)

        # Guardar la url de la pagina siguiente de la misma ciudad
        url_ciudad = pag_sig(soup_x_ciudad)

        # Guardar los datos de todas las variables
        datos_casa = variables(soup_x_ciudad)
        datos_casas += datos_casa

        df = pd.DataFrame(datos_casas)
        print(df)

        if not url_ciudad:
            break

# El archivo es generado en la carpeta donde se encuentra el código
df.to_csv("casas_valparaiso_base.csv", encoding="latin1", index=False)
