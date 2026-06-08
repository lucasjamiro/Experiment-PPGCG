# -*- coding: utf-8 -*-
"""
Aplicação Streamlit: Consulta de Municípios do Entorno
Estrutura baseada no modelo acadêmico ga155_aula11
"""

import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium  # Substitui o folium_static para melhor performance web

# Configuração da Página igual ao seu modelo, mas com layout 'wide' para caber melhor o mapa e os dados
PAGE_CONFIG = {"page_title": "Aplicação de Mapas - Geoprocessamento", "page_icon": "🗺️", "layout": "wide"}
st.set_page_config(**PAGE_CONFIG)

def main():
    st.title("🗺️ Ferramenta de Análise Espacial")
    st.subheader("Consulta de municípios interiores a uma determinada distância")
    
    # Menu lateral idêntico à estrutura do seu exemplo
    menu = ["Home", "Carregar Dados", "Visualizar & Analisar"]
    choice = st.sidebar.selectbox('Menu de Navegação', menu)
    
    # -------------------------------------------------------------------------
    # GERENCIAMENTO DE ESTADO (Session State)
    # [Fato] Necessário no Streamlit para os dados não sumirem ao alternar de aba/menu
    # -------------------------------------------------------------------------
    if 'lyr_mun' not in st.session_state:
        st.session_state['lyr_mun'] = None
    if 'lyr_cid' not in st.session_state:
        st.session_state['lyr_cid'] = None
    if 'nomes_cidades' not in st.session_state:
        st.session_state['nomes_cidades'] = []
    if 'resultado_analise' not in st.session_state:
        st.session_state['resultado_analise'] = None

    # --- ITEM DO MENU: HOME ---
    if choice == 'Home':
        st.markdown("""
        ### Bem-vindo à aplicação de Consulta de Entorno!
        Esta ferramenta foi convertida de um plugin do QGIS Desktop para uma aplicação web puramente em Python.
        
        **Fluxo de utilização:**
        1. Vá até o menu **Carregar Dados** na barra lateral e envie seus arquivos geográficos.
        2. Prossiga para o menu **Visualizar & Analisar** para definir as distâncias e gerar o relatório de saída.
        
        *Desenvolvido para fins didáticos e acadêmicos.*
        """)
        
    # --- ITEM DO MENU: CARREGAR DADOS ---
    elif choice == 'Carregar Dados':
        st.subheader("📂 Upload das Camadas Vetoriais")
        st.info("Formatos aceitos: .geojson, .gpkg ou Shapefiles compactados em .zip")
        
        col1, col2 = st.columns(2)
        with col1:
            file_mun = st.file_uploader("Camada de Municípios (Polígonos)", type=["geojson", "zip", "gpkg"])
        with col2:
            file_cid = st.file_uploader("Camada de Cidades (Pontos)", type=["geojson", "zip", "gpkg"])
            
        if st.button("🚀 Processar e Validar Arquivos", use_container_width=True):
            if file_mun and file_cid:
                with st.spinner("Carregando dados na memória..."):
                    try:
                        st.session_state['lyr_mun'] = gpd.read_file(file_mun)
                        st.session_state['lyr_cid'] = gpd.read_file(file_cid)
                        
                        # Validação do campo de atributos 'nm_nng' do seu script ex_aula05
                        if 'nm_nng' in st.session_state['lyr_cid'].columns:
                            nomes = st.session_state['lyr_cid']['nm_nng'].dropna().unique().tolist()
                            nomes.sort()
                            st.session_state['nomes_cidades'] = nomes
                            st.success(f"Sucesso! {len(nomes)} feições carregadas e prontas para análise.")
                        else:
                            st.error("Erro Crítico: A coluna 'nm_nng' não foi encontrada no arquivo de cidades.")
                    except Exception as e:
                        st.error(f"Erro ao ler os dados geográficos: {e}")
            else:
                st.warning("Aviso: Selecione ambos os arquivos antes de clicar em carregar.")

    # --- ITEM DO MENU: MAPA E ANÁLISE ---
    elif choice == 'Visualizar & Analisar':
        st.subheader("⚙️ Executar Parâmetros do Buffer e Clip")
        
        # Bloqueio de segurança se o usuário não carregou os dados antes
        if st.session_state['lyr_mun'] is None or st.session_state['lyr_cid'] is None:
            st.warning("⚠️ Nenhuma base de dados ativa. Por favor, carregue os arquivos no menu 'Carregar Dados' primeiro.")
            return
            
        # Inputs equivalentes aos do PyQt da sua aula
        cidade_selecionada = st.selectbox("Escolha a Cidade de Referência:", st.session_state['nomes_cidades'])
        
        col_input1, col_input2 = st.columns([2, 1])
        with col_input1:
            dist_valor = st.number_input("Distância do Entorno:", min_value=0.0, value=10000.0, step=500.0)
        with col_input2:
            tipo_metrica = st.radio("Unidade:", ["Metros (Divide por 111111)", "Graus Decimais"])

        if st.button("📊 Rodar Análise Geográfica", use_container_width=True):
            with st.spinner("Calculando áreas de influência..."):
                
                # Conversão métrica do seu plugin original do QGIS
                distancia = dist_valor / 111111.0 if tipo_metrica == "Metros (Divide por 111111)" else dist_valor
                
                lyr_mun = st.session_state['lyr_mun']
                lyr_cid = st.session_state['lyr_cid']
                
                # Encontrar a coluna de municípios de forma dinâmica caso mude o nome
                col_busca_mun = 'NM_MUNICIP' if 'NM_MUNICIP' in lyr_mun.columns else lyr_mun.columns[0]
                mun_selecionado = lyr_mun[lyr_mun[col_busca_mun].str.upper() == cidade_selecionada.upper()]
                
                if mun_selecionado.empty:
                    st.error(f"Município '{cidade_selecionada}' não pôde ser encontrado na coluna '{col_busca_mun}'.")
                else:
                    # Execução das Geometrias (Buffer + Clips equivalentes ao processing.run do QGIS)
                    buffer_gdf = gpd.GeoDataFrame(geometry=mun_selecionado.geometry.buffer(distancia), crs=lyr_mun.crs)
                    mun_entorno = gpd.clip(lyr_mun, buffer_gdf)
                    cid_entorno = gpd.clip(lyr_cid, buffer_gdf)
                    
                    st.session_state['resultado_analise'] = {
                        'mun_entorno': mun_entorno,
                        'cid_entorno': cid_entorno,
                        'cidade_ref': cidade_selecionada
                    }
                    st.success("Cálculos espaciais gerados!")

        # Exibição dos resultados e renderização do Mapa Interativo
        if st.session_state['resultado_analise'] is not None:
            res = st.session_state['resultado_analise']
            
            st.markdown("---")
            st.subheader(f"Visualização Espacial no Entorno de {res['cidade_ref']}")
            
            # Reprojetando temporariamente para WGS84 para exibição correta no mapa Leaflet/Web
            mun_mapa = res['mun_entorno'].to_crs(epsg=4326)
            cid_mapa = res['cid_entorno'].to_crs(epsg=4326)
            
            # Centralização dinâmica do mapa com base no centróide da análise
            centroid = mun_mapa.geometry.unary_union.centroid
            m = folium.Map(location=[centroid.y, centroid.x], zoom_start=10, tiles="OpenStreetMap")
            
            # Plot dos polígonos (Municípios interceptados)
            folium.GeoJson(
                mun_mapa,
                name="Municípios Próximos",
                style_function=lambda x: {'fillColor': '#3186cc', 'color': '#000000', 'weight': 1.5, 'fillOpacity': 0.3}
            ).add_to(m)
            
            # Plot dos pontos (Cidades/Sedes interceptadas)
            for _, row in cid_mapa.iterrows():
                geom = row.geometry
                if geom.type == 'Point':
                    folium.CircleMarker(
                        location=[geom.y, geom.x],
                        radius=6,
                        popup=f"Cidade: {row['nm_nng']}",
                        color="#E53E3E",
                        fill=True,
                        fill_color="#E53E3E"
                    ).add_to(m)
            
            # Renderização moderna do mapa (evita usar o folium_static antigo)
            st_folium(m, width="100%", height=500)
            
            # -----------------------------------------------------------------
            # EXPORTAÇÃO DO RELATÓRIO TXT NATIVO (Antigo clique do botão OK)
            # -----------------------------------------------------------------
            st.subheader("📥 Download do Relatório Analítico")
            
            texto_saida = f"CIDADES NO ENTORNO DE {res['cidade_ref'].upper()}\n"
            texto_saida += "=" * 60 + "\n"
            
            for idx, row in res['cid_entorno'].iterrows():
                geom = row.geometry
                coord_x = geom.x if geom.type == 'Point' else 0
                coord_y = geom.y if geom.type == 'Point' else 0
                texto_saida += f"ID: {idx} | Nome: {row['nm_nng']} | Long: {coord_x:.4f} | Lat: {coord_y:.4f}\n"
                
            st.download_button(
                label="Clique para baixar o arquivo .txt",
                data=texto_saida,
                file_name=f"Resultado_Consulta_{res['cidade_ref'].upper()}.txt",
                mime="text/plain",
                use_container_width=True
            )

if __name__ == '__main__':
    main()
