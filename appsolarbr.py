# -*- coding: utf-8 -*-
"""Untitled0.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1oJzKDi7oakflTfnUDf9Sphl7eXqfjHwM
"""

#R$/kWh=0.81
import streamlit as st
import geocoder
import requests
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
from PIL import Image

GOOGLE_SOLAR_KEY = st.secrets.GOOGLE_SOLAR_KEY
SOLAR_INSIGHTS_ENDPOINT = 'https://solar.googleapis.com/v1/buildingInsights:findClosest?location.latitude={}&location.longitude={}&requiredQuality=LOW&key={}'

# streamlit_app.py

import streamlit as st

def check_password():
    """Retorna `True` se o usuário inseriu a senha correta."""

    def password_entered():
        """Verifica se a senha inserida pelo usuário está correta."""
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # não armazena a senha
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Primeira execução, mostra a entrada da senha.
        st.text_input(
            "Senha", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Senha incorreta, mostra a entrada + erro.
        st.text_input(
            "Senha", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Senha incorreta")
        return False
    else:
        # Senha correta.
        return True

@st.cache_data
def get_lat_lng(endereco):
    g = geocoder.bing(endereco, key=BING_KEY)
    return g.latlng

@st.cache_data
def get_solar_insights(lat, lng):
    resposta = requests.get(SOLAR_INSIGHTS_ENDPOINT.format(lat, lng, GOOGLE_SOLAR_KEY))
    return resposta.json()

def get_google_maps_image(lat, lon, zoom=20, size="600x600", maptype="satellite", api_key=GOOGLE_SOLAR_KEY):
    base_url = "https://maps.googleapis.com/maps/api/staticmap?"
    params = {
        "center": f"{lat},{lon}",
        "zoom": zoom,
        "size": size,
        "maptype": maptype,
        "key": api_key
    }
    resposta = requests.get(base_url, params=params)
    resposta.raise_for_status()
    imagem = Image.open(BytesIO(resposta.content))
    return imagem

# Calculadora

def get_energia_anual(data, num_paineis):
    for config in data['solarPotential']['solarPanelConfigs']:
        if config['panelsCount'] == num_paineis:
            return config['yearlyEnergyDcKwh']
    return None

def calculadora_solar(data):
    st.subheader('Calculadora de Economia Solar')

    # Extrair número mínimo e máximo de painéis do resultado da API
    num_min_paineis = data['solarPotential']['solarPanelConfigs'][0]['panelsCount']
    num_max_paineis = data['solarPotential']['maxArrayPanelsCount']

    # Widgets de entrada com valores padrão
    #if 'num_paineis' not in st.session_state:
     #   st.session_state.num_paineis = num_max_paineis

    if 'kw_por_painel' not in st.session_state:
        st.session_state.kw_por_painel = 0.3

    if 'preco_eletricidade' not in st.session_state:
        st.session_state.preco_eletricidade = 0.12

    if 'area_painel_m2' not in st.session_state:
        st.session_state.area_painel_m2 = 1.5

    #st.session_state.num_paineis = st.number_input('Número de Painéis Solares', value=st.session_state.num_paineis)
    #st.session_state.kw_por_painel = st.number_input('kW por Painel Solar', value=st.session_state.kw_por_painel)
    #st.session_state.preco_eletricidade = st.number_input('Preço da Eletricidade (por kWh)', value=st.session_state.preco_eletricidade)
    #st.session_state.area_painel_m2 = st.number_input('Área por Painel Solar (em m^2)', value=st.session_state.area_painel_m2)

    # Cálculos
    # Entradas
    num_paineis = st.slider('Número de Painéis Solares', min_value=num_min_paineis, max_value=num_max_paineis, value=num_max_paineis)
    watt_usuario = st.number_input('Potência do Painel Solar (Watt)', value=430.0, step=10.0)  # Usuário pode ajustar a potência
    preco_eletricidade = st.number_input('Preço da Eletricidade (R$/kWh)', value=0.81, step=0.01)

    # Calcular
    energia_api = get_energia_anual(data, num_paineis)
    energia_ajustada = energia_api * (watt_usuario / 250.0)  # Ajustado com base na potência especificada pelo usuário
    economia_anual = energia_ajustada * preco_eletricidade

    # Exibir
    st.write(f"Geração Anual de Energia Estimada: {energia_ajustada:.2f} kWh")
    st.write(f"Economia Anual Estimada: R${economia_anual:.2f}")

def main():
    st.title('Insights de Painéis Solares')

    endereco = st.text_input("Digite seu endereço:")

    # Verificar se o endereço está na session_state
    if 'endereco' not in st.session_state:
        st.session_state.endereco = ''

    # Verificar se os dados já estão na session_state e se o endereço mudou
    if 'dados' not in st.session_state or st.session_state.endereco != endereco:
        if st.button('Obter Insights'):
            lat, lng = get_lat_lng(endereco)
            dados = get_solar_insights(lat, lng)
            st.session_state.dados = dados
            st.session_state.endereco = endereco

    # Se os dados estiverem na session_state, exibi-los
    if 'dados' in st.session_state:
        dados = st.session_state.dados
        lat, lng = get_lat_lng(st.session_state.endereco)

        # Exibir a imagem da casa
        imagem = get_google_maps_image(lat, lng)
        st.image(imagem, caption=f"Imagem da Casa de {dados['imageryDate']['year']}-{dados['imageryDate']['month']}-{dados['imageryDate']['day']}", use_column_width=True)

        # Exibir dados solares
        st.subheader('Potencial Solar')
        # Adicionar uma observação usando st.markdown
        st.markdown("_Aviso: Com base nos dados da API Solar do Google (altura do painel - 1,65m, largura do painel - 0,99m, 250 Watts)._")
        st.markdown(f"_Coordenadas do endereço: {lat} {lng}_")
        st.write(f"Número Máximo de Painéis: {dados['solarPotential']['maxArrayPanelsCount']}")
        st.write(f"Área Máxima do Painel Solar (m^2): {dados['solarPotential']['maxArrayAreaMeters2']}")
        st.write(f"Área Total do Telhado (m^2): {dados['solarPotential']['wholeRoofStats']['areaMeters2']}")
        st.write(f"Segmentos do Telhado: {len(dados['solarPotential']['roofSegmentStats'])}")
        st.write(f"Máximo de Horas de Sol por Ano: {dados['solarPotential']['maxSunshineHoursPerYear']}")

        # Calculadora
        calculadora_solar(dados)

        # Expansor com o JSON completo
        with st.expander("Clique para expandir a resposta JSON completa", expanded=False):
            st.write(dados)

if __name__ == '__main__':
    if check_password():
        main()