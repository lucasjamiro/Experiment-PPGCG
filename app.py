# -*- coding: utf-8 -*-
"""
Aplicação Streamlit: Consulta de Municípios do Entorno
Estrutura baseada no modelo acadêmico da Profa. Silvana Camboim com filtros de atributos
"""

import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import unicodedata

# Configuração da Página
PAGE_CONFIG = {"page_title": "Aplicação de Mapas - Geoprocessamento", "page_icon": "🗺️", "layout": "wide"}
st.set_page_config(**PAGE_CONFIG)

# Função auxiliar para remover acentos e padronizar strings para comparação pesada
def remover_acentos(txt):
    if not isinstance(txt, str):
        return ""
    return "".join(c for c in unicodedata.normalize('NFKD', txt) if unicodedata.category(c) != 'Mn').upper().strip()

def main():
    st.title("🗺️ Ferramenta de Análise Espacial Avançada")
    st.subheader("Consulta de municípios com filtros rígidos de atributos e raio em KM")
    
    # Menu lateral
    menu = ["Home", "Carregar Dados", "Visualizar & Analisar"]
    choice = st.sidebar.selectbox('Menu de Navegação', menu)
    
    # Gerenciamento de Estado
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
        ### Regras de Negócio Aplicadas nesta Versão:
        * **Coluna Padrão:** Busca automatizada pela coluna `NM_MUN` em ambas as camadas.
        * **Robustez Textual:** Tratamento contra encoding quebrado (`Latin-1`/`UTF-8`) e remoção de acentos em tempo de execução.
        * **Filtro de Duplicidade:** Filtra os pontos mantendo apenas registros onde `SCT_LOCALI == 'Sede Municipal'`.
        * **Geometria de Precisão:** Buffer calculado em metros reais (reprojeção dinâmica via EPSG:3857) a partir do input do usuário em **Quilômetros (km)**.
        """)
        
    # --- ITEM DO MENU: CARREGAR DADOS ---
    elif choice == 'Carregar Dados':
        st.subheader("📂 Upload das Camadas Vetoriais")
        
        col1, col2 = st.columns(2)
        with col1:
            file_mun = st.file_uploader("Camada de Municípios (Polígonos)", type=["geojson", "zip", "gpkg"])
        with col2:
            file_cid = st.file_uploader("Camada de Cidades (Pontos)", type=["geojson", "zip", "gpkg"])
            
        if st.button("🚀 Processar e Filtrar Arquivos", use_container_width=True):
            if file_mun and file_cid:
                with st.spinner("Lendo e higienizando dados geográficos..."):
                    try:
                        # [Inferido] Tratamento de Encoding de tabelas brasileiras antigas
                        try:
                            df_mun = gpd.read_file(file_mun, encoding='utf-8')
                            df_cid = gpd.read_file(file_cid, encoding='utf-8')
                        except Exception:
                            df_mun = gpd.read_file(file_mun, encoding='latin-1')
                            df_cid = gpd.read_file(file_cid, encoding='latin-1')
                        
                        # Verificar se a coluna unificada NM_MUN existe nos arquivos
                        if 'NM_MUN' not in df_mun.columns or 'NM_MUN' not in df_cid.columns:
                            st.error("Erro: A coluna 'NM_MUN' precisa existir em ambos os arquivos carregados.")
                            return
                        
                        # Aplicar filtro rígido de Sede Municipal se a coluna SCT_LOCALI existir
                        if 'SCT_LOCALI' in df_cid.columns:
                            linhas_antes = len(df_cid)
                            # Remove espaços extras e força validação string
                            df_cid = df_cid[df_cid['SCT_LOCALI'].astype(str).str.strip() == 'Sede Municipal']
                            linhas_depois = len(df_cid)
                            st.info(f"Filtro aplicado: {linhas_antes - linhas_depois} pontos ignorados por não serem Sedes Municipais.")
                        else:
                            st.warning("Aviso: Coluna 'SCT_LOCALI' não encontrada no arquivo de pontos. Nenhum filtro de duplicidade foi executado.")

                        # Guardar no session state os dados limpos
                        st.session_state['lyr_mun'] = df_mun
                        st.session_state['lyr_cid'] = df_cid
                        
                        # Extrair lista limpa de nomes para o dropdown do usuário
                        nomes = df_mun['NM_MUN'].dropna().unique().tolist()
                        nomes = [str(n).strip() for n in nomes]
                        nomes.sort()
                        st.session_state['nomes_cidades'] = nomes
                        
                        st.success(f"Sucesso! {len(nomes)} municípios listados e prontos para processamento.")
                        
                    except Exception as e:
                        st.error(f"Erro crítico no processamento dos arquivos: {e}")
            else:
                st.warning("Aviso: Selecione ambos os arquivos antes de clicar em carregar.")

    # --- ITEM DO MENU: MAPA E ANÁLISE ---
    elif choice == 'Visualizar & Analisar':
        st.subheader("⚙️ Executar Análise Geográfica")
        
        if st.session_state['lyr_mun'] is None or st.session_state['lyr_cid'] is None:
            st.warning("⚠️ Nenhuma base de dados ativa. Vá ao menu 'Carregar Dados' primeiro.")
            return
            
        cidade_selecionada = st.selectbox("Escolha a Cidade de Referência (NM_MUN):", st.session_state['nomes_cidades'])
        dist_km = st.number_input("Insira o Raio do Entorno em Quilômetros (km):", min_value=0.1, value=20.0, step=5.0)

        if st.button("📊 Rodar Buffer e Intersecção", use_container_width=True):
            with st.spinner("Realizando cálculos métricos reprojetados..."):
                
                lyr_mun = st.session_state['lyr_mun']
                lyr_cid = st.session_state['lyr_cid']
                
                # Procura robusta imune a acentos e espaços vazios
                lyr_mun['_busca_col'] = lyr_mun['NM_MUN'].apply(remover_acentos)
                cidade_busca_limpa = remover_acentos(cidade_selecionada)
                
                mun_selecionado = lyr_mun[lyr_mun['_busca_col'] == cidade_busca_limpa]
                
                if mun_selecionado.empty:
                    st.error(f"Erro: O município '{cidade_selecionada}' não foi localizado via indexador limpo.")
                else:
                    # Guardamos o CRS original da sua base para devolver o dado na mesma projeção
                    crs_original = lyr_mun.crs
                    
                    # Passamos para uma projeção métrica (Web Mercator) para calcular o buffer real em metros
                    mun_projetado = mun_selecionado.to_crs(epsg=3857)
                    distancia_metros = dist_km * 1000.0
                    
                    # Executa o buffer exato
                    buffer_geom = mun_projetado.geometry.buffer(distancia_metros)
                    buffer_gdf = gpd.GeoDataFrame(geometry=buffer_geom, crs=3857).to_crs(crs_original)
                    
                    # Clips espaciais usando o buffer corrigido
                    mun_entorno = gpd.clip(lyr_mun, buffer_gdf)
                    cid_entorno = gpd.clip(lyr_cid, buffer_gdf)
                    
                    # Remove a coluna temporária de busca para não poluir o relatório final
                    if '_busca_col' in mun_entorno.columns:
                        mun_entorno = mun_entorno.drop(columns=['_busca_col'])
                    
                    st.session_state['resultado_analise'] = {
                        'mun_entorno': mun_entorno,
                        'cid_entorno': cid_entorno,
                        'cidade_ref': cidade_selecionada
                    }
                    st.success("Análise espacial concluída!")

        # Visualização no Mapa
        if st.session_state['resultado_analise'] is not None:
            res = st.session_state['resultado_analise']
            
            st.markdown("---")
            st.subheader(f"Visualização Espacial no Entorno de {res['cidade_ref']}")
            
            mun_mapa = res['mun_entorno'].to_crs(epsg=4326)
            cid_mapa = res['cid_entorno'].to_crs(epsg=4326)
            
            centroid = mun_mapa.geometry.unary_union.centroid
            m = folium.Map(location=[centroid.y, centroid.x], zoom_start=10, tiles="OpenStreetMap")
            
            folium.GeoJson(
                mun_mapa,
                name="Municípios Próximos",
                style_function=lambda x: {'fillColor': '#10B981', 'color': '#111827', 'weight': 1.5, 'fillOpacity': 0.3}
            ).add_to(m)
            
            for _, row in cid_mapa.iterrows():
                geom = row.geometry
                if geom.type == 'Point':
                    folium.CircleMarker(
                        location=[geom.y, geom.x],
                        radius=6,
                        popup=f"Cidade: {row['NM_MUN']}",
                        color="#EF4444",
                        fill=True,
                        fill_color="#EF4444"
                    ).add_to(m)
            
            st_folium(m, width="100%", height=500)
            
            # Exportação de relatório TXT limpo
            st.subheader("📥 Download do Relatório Analítico")
            
            texto_saida = f"CIDADES NO ENTORNO DE {res['cidade_ref'].upper()} (RAIO DE {dist_km} KM)\n"
            texto_saida += "=" * 65 + "\n"
            
            for idx, row in res['cid_entorno'].iterrows():
                geom = row.geometry
                coord_x = geom.x if geom.type == 'Point' else 0
                coord_y = geom.y if geom.type == 'Point' else 0
                texto_saida += f"ID: {idx} | Nome: {row['NM_MUN']} | Long: {coord_x:.4f} | Lat: {coord_y:.4f}\n"
                
            st.download_button(
                label="Clique para baixar o arquivo .txt",
                data=texto_saida.encode('utf-8'),
                file_name=f"Resultado_Consulta_{remover_acentos(res['cidade_ref'])}.txt",
                mime="text/plain",
                use_container_width=True
            )

if __name__ == '__main__':
    main()
