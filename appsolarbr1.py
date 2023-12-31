import streamlit as st
import geocoder
import requests
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from io import BytesIO
from PIL import Image
import rasterio
from rasterio.io import MemoryFile
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import matplotlib.pyplot as plt
import math


# BING_KEY = st.secrets.BING_KEY
GOOGLE_SOLAR_KEY = st.secrets.GOOGLE_SOLAR_KEY
SOLAR_INSIGHTS_ENDPOINT = 'https://solar.googleapis.com/v1/buildingInsights:findClosest?location.latitude={}&location.longitude={}&requiredQuality=LOW&key={}'

# streamlit_app.py

import streamlit as st

def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct.
        return True

@st.cache_data
def get_lat_lng_bing(address):
    g = geocoder.bing(address, key=BING_KEY)
    results = g.json
    return (results['lat'], results['lng'])

def get_lat_lng(address):
    """
    Get the latitude and longitude of a given address using Google Geocoding API.

    Parameters:
    - address: The address to geocode.
    - api_key: Your Google API key.

    Returns:
    - A tuple containing the latitude and longitude.
    """
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={GOOGLE_SOLAR_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data['status'] == 'OK':
            latitude = data['results'][0]['geometry']['location']['lat']
            longitude = data['results'][0]['geometry']['location']['lng']
            return latitude, longitude
        else:
            print(f"Error: {data['status']}")
            return None, None
    else:
        print(f"Failed to get data: {response.status_code}")
        return None, None

@st.cache_data
def get_solar_insights(lat, lng):
    response = requests.get(SOLAR_INSIGHTS_ENDPOINT.format(lat, lng, GOOGLE_SOLAR_KEY))
    return response.json()

@st.cache_data
def get_google_maps_image(lat, lon, zoom=19, size="600x600", maptype="satellite", api_key=GOOGLE_SOLAR_KEY):
    base_url = "https://maps.googleapis.com/maps/api/staticmap?"
    params = {
        "center": f"{lat},{lon}",
        "zoom": zoom,
        "size": size,
        "maptype": maptype,
        "key": api_key
    }
    response = requests.get(base_url, params=params)
    response.raise_for_status()
    image = Image.open(BytesIO(response.content))
    return image

# Function to display a specific band of a GeoTIFF file from a URL with annotation
def display_monthly_flux(data_layers, api_key):
    # For monthly flux, you need to handle multiple bands as it contains data for each month
    monthly_flux_url_with_key = f"{data_layers['monthlyFluxUrl']}&key={api_key}"
    response = requests.get(monthly_flux_url_with_key)
    if response.status_code == 200:
        with MemoryFile(response.content) as memfile:
            with memfile.open() as dataset:
                for i in range(1, dataset.count + 1):  # Loop through each band
                    fig, ax = plt.subplots()  # Create a new matplotlib figure and axes
                    band = dataset.read(i)
                    im = ax.imshow(band) #cmap='viridis')  # Store the mappable object in im
                    #plt.colorbar(im, ax=ax)  # Pass the mappable object to colorbar
                    ax.set_title(f"Monthly Solar Flux - Month {i}")
                    st.pyplot(fig)  # Pass the matplotlib figure to st.pyplot()
                    plt.close(fig)  # Close the figure
    else:
        print(f"Failed to fetch data. Status code: {response.status_code}")

# Function to display all bands of a GeoTIFF file from a URL with annotation
def display_all_geotiff_bands(url, api_key, title):
    url_with_key = f"{url}&key={api_key}"
    response = requests.get(url_with_key)
    if response.status_code == 200:
        with MemoryFile(response.content) as memfile:
            with memfile.open() as dataset:
                fig, ax = plt.subplots()  # Create a new matplotlib figure and axes
                if dataset.count > 1:
                    band = dataset.read([1, 2, 3])
                    band = np.transpose(band, (1, 2, 0))
                else:
                    band = dataset.read(1)
                    band = band.squeeze()

                im = ax.imshow(band)  # Store the mappable object in im, cmap='viridis' if dataset.count == 1 else None
                #plt.colorbar(im, ax=ax)  # Pass the mappable object to colorbar
                ax.set_title(title)
                st.pyplot(fig)  # Pass the matplotlib figure to st.pyplot()
                plt.close(fig)  # Close the figure

# Function to get data layers
@st.cache_data
def get_data_layers(lat, lon, radius=50, view="FULL_LAYERS", quality="LOW", pixel_size=0.5):
    url = f"https://solar.googleapis.com/v1/dataLayers:get"
    params = {
        "location.latitude": lat,
        "location.longitude": lon,
        "radiusMeters": radius,
        "view": view,
        "requiredQuality": quality,
        "pixelSizeMeters": pixel_size,
        "key": GOOGLE_SOLAR_KEY  # Replace with your actual Google Solar API key
    }
    response = requests.get(url, params=params)
    return response.json()


# calculator
def get_yearly_energy(data, panels_count):
    for config in data['solarPotential']['solarPanelConfigs']:
        if config['panelsCount'] == panels_count:
            return config['yearlyEnergyDcKwh']
    return None

def solar_calculator(data):
    st.subheader('Solar Savings Calculator')

    # Extract min and max panels count from the API results
    min_panels = data['solarPotential']['solarPanelConfigs'][0]['panelsCount']
    max_panels = data['solarPotential']['maxArrayPanelsCount']

    # Input widgets with default values
    #if 'num_panels' not in st.session_state:
     #   st.session_state.num_panels = max_panels

    if 'kw_per_panel' not in st.session_state:
        st.session_state.kw_per_panel = 0.3

    if 'electricity_price' not in st.session_state:
        st.session_state.electricity_price = 0.12

    if 'panel_area_m2' not in st.session_state:
        st.session_state.panel_area_m2 = 1.5

    #st.session_state.num_panels = st.number_input('Number of Solar Panels', value=st.session_state.num_panels)
    #st.session_state.kw_per_panel = st.number_input('kW per Solar Panel', value=st.session_state.kw_per_panel)
    #st.session_state.electricity_price = st.number_input('Price of Electricity (per kWh)', value=st.session_state.electricity_price)
    #st.session_state.panel_area_m2 = st.number_input('Area per Solar Panel (in m^2)', value=st.session_state.panel_area_m2)

    # Calculations
    # Inputs
    panels = st.slider('Número de painéis solares', min_value=min_panels, max_value=max_panels, value=max_panels)
    user_wattage = st.number_input('Potência do painel solar', value=430.0, step=10.0)  # User can adjust wattage
    electricity_price = st.number_input('Preço da Eletricidade (R$/kWh)', value=0.81, step=0.01)

    # Calculate
    api_energy = get_yearly_energy(data, panels)
    adjusted_energy = api_energy * (user_wattage / 250.0)  # Adjust based on user-specified wattage
    yearly_savings = adjusted_energy * electricity_price

    # Display
    st.write(f"Geração anual estimada de energia: {adjusted_energy:.2f} kWh")
    st.write(f"Economia anual estimada: R${yearly_savings:.2f}")

def main():
    st.title('SOMBREAMENTO E DADOS - ENERGIA SOLAR')

    address = st.text_input("Digite seu endereço:")

    # Check if the address is in session_state
    if 'address' not in st.session_state:
        st.session_state.address = ''

    # Check if data is already in session_state and if the address has changed
    if 'data' not in st.session_state or st.session_state.address != address:
        if st.button('Obtenha informações'):
            lat, lng = get_lat_lng(address)
            data = get_solar_insights(lat, lng)
            print(data)
            st.session_state.data = data
            st.session_state.address = address

    # If data is in session_state, display it
    if 'data' in st.session_state:
        data = st.session_state.data
        lat, lng = get_lat_lng(st.session_state.address)

        # Display the image of the house
        image = get_google_maps_image(lat, lng)
        if 'imageryDate' in data:
            st.image(image, caption=f"House Image from {data['imageryDate']['year']}-{data['imageryDate']['month']}-{data['imageryDate']['day']}", use_column_width=True)
        else:
            st.image(image, caption="House Image", use_column_width=True)

        # Display solar data
        st.subheader('Potencial Solar')
        # Add a note using st.markdown
        st.markdown("_Disclaimer: Based on Google Solar API data (panel height - 1.65m, panel width - 0.99m, 250 Watts)._")
        st.markdown(f"_Coordinates of the address: {lat} {lng}_")
        st.write(f"Contagem máxima de painéis: {data['solarPotential']['maxArrayPanelsCount']}")
        st.write(f"Área máxima do painel solar (m^2): {data['solarPotential']['maxArrayAreaMeters2']}")
        st.write(f"Área total do telhado (m^2): {data['solarPotential']['wholeRoofStats']['areaMeters2']}")
        st.write(f"Segmentos de telhado: {len(data['solarPotential']['roofSegmentStats'])}")
        st.write(f"Máximo de horas de sol por ano: {data['solarPotential']['maxSunshineHoursPerYear']}")

        # Calculator
        solar_calculator(data)

        # expander with full json
        with st.expander("Click to unfold the full solarAPI response", expanded=False):
            st.write(data)

        if st.button('Get Data Layers'):            
            # Fetch the data layers
            data_layers = get_data_layers(lat, lng)  # Make sure to implement this function to call the second API and get the data layers

            # Display the DSM, RGB, and Mask GeoTIFF files
            st.subheader('Digital Surface Model')
            display_all_geotiff_bands(data_layers['dsmUrl'], GOOGLE_SOLAR_KEY, 'Digital Surface Model')

            st.subheader('RGB Composite Layer')
            display_all_geotiff_bands(data_layers['rgbUrl'], GOOGLE_SOLAR_KEY, 'RGB Composite Layer')

            st.subheader('Building Mask')
            display_all_geotiff_bands(data_layers['maskUrl'], GOOGLE_SOLAR_KEY, 'Building Mask')

            # Display the Annual Flux GeoTIFF file
            st.subheader('Annual Flux')
            display_all_geotiff_bands(data_layers['annualFluxUrl'], GOOGLE_SOLAR_KEY, 'Annual Flux')

            # Display the Monthly Flux GeoTIFF files
            st.subheader('Monthly Flux')
            display_monthly_flux(data_layers, GOOGLE_SOLAR_KEY)

            with st.expander("Click to unfold the full dataLayer response", expanded=False):
                st.write(data_layers)

if __name__ == '__main__':
    if check_password():
        main()
