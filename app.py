import streamlit as st
import json
import os
from datetime import datetime, timedelta
import pandas as pd
import requests
from urllib.parse import urlencode
import base64
import hashlib
import secrets

# Configuración de la página
st.set_page_config(
    page_title="🛒 Gestor de Compras",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuración OAuth Google
GOOGLE_CLIENT_ID = st.secrets.get("GOOGLE_CLIENT_ID", os.getenv("GOOGLE_CLIENT_ID"))
GOOGLE_CLIENT_SECRET = st.secrets.get("GOOGLE_CLIENT_SECRET", os.getenv("GOOGLE_CLIENT_SECRET"))

if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    st.error("❌ Error de configuración: Credenciales OAuth no encontradas. Asegúrate de configurar GOOGLE_CLIENT_ID y GOOGLE_CLIENT_SECRET en .streamlit/secrets.toml o como variables de entorno.")
    st.stop()

# Sustituye directamente esta línea:
GOOGLE_REDIRECT_URI = "https://groceries-00.streamlit.app/" # Asegúrate de que esta URL coincida con la configuración en la consola de Google Cloud.

GOOGLE_OAUTH_URL = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

# Archivo para persistencia de TODOS los usuarios
ALL_USERS_DATA_FILE = "all_users_data.json"

# Categorías predefinidas
CATEGORIES = [
    "Lácteos y Huevos",
    "Carnes y Pollo",
    "Frutas y Verduras",
    "Panadería",
    "Cereales y Granos",
    "Aceites y Condimentos",
    "Bebidas",
    "Snacks y Dulces",
    "Productos de Limpieza",
    "Cuidado Personal",
    "Congelados",
    "Enlatados y Conservas",
    "Otro"
]

# Emojis para categorías
CATEGORY_EMOJIS = {
    "Lácteos y Huevos": "🥛",
    "Carnes y Pollo": "🍗",
    "Frutas y Verduras": "🥕",
    "Panadería": "🍞",
    "Cereales y Granos": "🌾",
    "Aceites y Condimentos": "🫒",
    "Bebidas": "🥤",
    "Snacks y Dulces": "🍪",
    "Productos de Limpieza": "🧽",
    "Cuidado Personal": "🧴",
    "Congelados": "🧊",
    "Enlatados y Conservas": "🥫",
    "Otro": "📦"
}

# CSS personalizado para mejorar la apariencia
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #2c3e50;
        font-size: 3em;
        margin-bottom: 20px;
        background: linear-gradient(45deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .login-container {
        background: linear-gradient(45deg, #667eea, #764ba2);
        color: white;
        padding: 40px;
        border-radius: 15px;
        text-align: center;
        margin: 50px auto;
        max-width: 500px;
    }
    
    .user-info {
        background: linear-gradient(45deg, #a8edea, #fed6e3);
        padding: 10px;
        border-radius: 10px;
        margin-bottom: 20px;
        text-align: center;
    }
    
    .metric-container {
        background: linear-gradient(45deg, #a8edea, #fed6e3);
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
        text-align: center;
    }
    
    .week-info {
        background: linear-gradient(45deg, #667eea, #764ba2);
        color: white;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 20px;
        font-size: 1.2em;
        font-weight: bold;
    }
    
    .category-header {
        background: linear-gradient(45deg, #a8edea, #fed6e3);
        padding: 10px;
        border-radius: 10px;
        margin: 10px 0;
        font-weight: bold;
        border-left: 4px solid #667eea;
    }
    
    .product-item {
        background: white;
        padding: 15px;
        border-radius: 10px;
        margin: 5px 0;
        border-left: 4px solid #667eea;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .selected-product {
        background: linear-gradient(45deg, #a8edea, #fed6e3);
        border-left-color: #00b894;
    }
    
    .stButton > button {
        background: linear-gradient(45deg, #667eea, #764ba2);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 10px 20px;
        font-weight: bold;
    }
    
    .stButton > button:hover {
        background: linear-gradient(45deg, #764ba2, #667eea);
        transform: translateY(-2px);
    }
    
    .delete-button {
        background: linear-gradient(45deg, #e74c3c, #c0392b) !important;
    }
    
    .delete-button:hover {
        background: linear-gradient(45deg, #c0392b, #e74c3c) !important;
    }

    .quantity-input {
        width: 80px;
        display: inline-block;
        margin-left: 10px;
    }
</style>
""", unsafe_allow_html=True)

def generate_state():
    """Generar estado aleatorio para OAuth"""
    return secrets.token_urlsafe(32)

def get_google_auth_url():
    """Generar URL de autorización de Google"""
    state = generate_state()
    st.session_state.oauth_state = state
    
    params = {
        'client_id': GOOGLE_CLIENT_ID,
        'redirect_uri': GOOGLE_REDIRECT_URI,
        'scope': 'openid email profile',
        'response_type': 'code',
        'state': state,
        'access_type': 'offline',
        'prompt': 'consent'
    }
    
    return f"{GOOGLE_OAUTH_URL}?{urlencode(params)}"

def exchange_code_for_token(code):
    """Intercambiar código de autorización por token de acceso (sin validar state)"""
    data = {
        'client_id': GOOGLE_CLIENT_ID,
        'client_secret': GOOGLE_CLIENT_SECRET,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': GOOGLE_REDIRECT_URI,
    }

    try:
        response = requests.post(GOOGLE_TOKEN_URL, data=data)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error al obtener token: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error en la solicitud: {str(e)}")
        return None

def get_user_info(access_token):
    """Obtener información del usuario"""
    headers = {'Authorization': f'Bearer {access_token}'}
    try:
        response = requests.get(GOOGLE_USERINFO_URL, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error al obtener información del usuario: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error en la solicitud: {str(e)}")
        return None

def load_all_users_data():
    """Cargar los datos de todos los usuarios desde un archivo JSON."""
    if os.path.exists(ALL_USERS_DATA_FILE):
        try:
            with open(ALL_USERS_DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            st.warning("Advertencia: El archivo de datos de usuario está corrupto o vacío. Se iniciará con datos vacíos.")
            return {}
    return {}

def save_all_users_data(all_data):
    """Guardar los datos de todos los usuarios en un archivo JSON."""
    with open(ALL_USERS_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

def get_user_data(user_email):
    """Obtener los datos específicos de un usuario o inicializarlos si no existen."""
    if 'all_users_data' not in st.session_state:
        st.session_state.all_users_data = load_all_users_data()

    if user_email not in st.session_state.all_users_data:
        st.session_state.all_users_data[user_email] = {
            "master_list": {},
            "weekly_selections": {}
        }
    return st.session_state.all_users_data[user_email]

def save_user_data():
    """Guardar los datos actualizados de todos los usuarios."""
    save_all_users_data(st.session_state.all_users_data)


def handle_oauth_callback():
    """Manejar el callback de OAuth simplificado (sin state)"""
    query_params = st.query_params

    if 'code' in query_params:
        code = query_params['code']

        # Intercambiar código por token
        token_data = exchange_code_for_token(code)  # Nota: ya no recibe state
        if token_data and 'access_token' in token_data:
            # Obtener información del usuario
            user_info = get_user_info(token_data['access_token'])
            if user_info and 'email' in user_info:
                st.session_state.user_authenticated = True
                st.session_state.user_info = user_info
                st.session_state.access_token = token_data['access_token']
                st.session_state.user_email = user_info['email'] # Guarda el email del usuario

                # Limpiar parámetros de la URL
                st.query_params.clear()
                st.rerun()
            else:
                st.error("Error obteniendo información del usuario o el email no está disponible.")
        else:
            st.error("Error al autenticar con Google")

def get_current_date():
    """Obtener la fecha actual en formato string"""
    return datetime.now().strftime("%Y-%m-%d")

def get_date_display(date_key):
    """Convertir la clave de fecha a formato legible"""
    date = datetime.strptime(date_key, "%Y-%m-%d")
    return date.strftime("%d de %B, %Y")

def get_products_by_category(master_list):
    """Organizar productos por categoría"""
    products_by_category = {}
    for product, category in master_list.items():
        if category not in products_by_category:
            products_by_category[category] = []
        products_by_category[category].append(product)
    return products_by_category

def format_product_with_quantity(product, quantity):
    if quantity:
        return f"{product} (x{quantity})"
    return product

def parse_product_quantity(product_text):
    """Extraer producto y cantidad del texto formateado"""
    if " (x" in product_text and product_text.endswith(")"):
        product = product_text.split(" (x")[0]
        quantity = product_text.split(" (x")[1][:-1]
        return product, quantity
    return product_text, "" # Devuelve cadena vacía si no hay cantidad explícita

def login_screen():
    """Pantalla de login"""
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown("# 🛒 Gestor de Compras")
    st.markdown("### ¡Bienvenido!")
    st.markdown("Inicia sesión con tu cuenta de Google para acceder a tu lista de compras personalizada.")
    
    auth_url = get_google_auth_url()
    st.markdown(f'<a href="{auth_url}" target="_self" rel="noopener noreferrer" style="text-decoration: none;"><button style="background: linear-gradient(45deg, #007bff, #0056b3); color: white; padding: 15px 30px; border: none; border-radius: 8px; font-size: 1.2em; cursor: pointer; transition: background 0.3s ease;">🔐 Iniciar Sesión con Google</button></a>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def main():
    # Inicializar session state para autenticación
    if 'user_authenticated' not in st.session_state:
        st.session_state.user_authenticated = False
    
    # Manejar callback de OAuth
    handle_oauth_callback()
    
    # Si no está autenticado, mostrar pantalla de login
    if not st.session_state.user_authenticated:
        login_screen()
        return
    
    # Si está autenticado, cargar los datos específicos del usuario
    user_email = st.session_state.user_info['email']
    user_data = get_user_data(user_email)
    
    # Título principal
    st.markdown('<h1 class="main-header">🛒 Gestor de Compras del Supermercado</h1>', 
                 unsafe_allow_html=True)
    
    # Mostrar información del usuario
    user_name = st.session_state.user_info.get('name', 'Usuario')
    st.markdown(f'<div class="user-info">👋 ¡Hola {user_name}! ({user_email})</div>', 
                unsafe_allow_html=True)
    
    # Inicializar state del usuario actual
    if 'current_date' not in st.session_state:
        st.session_state.current_date = get_current_date()
    
    # Usar las listas específicas del usuario
    master_list = user_data["master_list"]
    weekly_selections = user_data["weekly_selections"]

    if 'current_selection_data' not in st.session_state:
        date_key = st.session_state.current_date
        if date_key in weekly_selections:
            st.session_state.current_selection_data = weekly_selections[date_key]["products"]
        else:
            st.session_state.current_selection_data = {}
    
    # current_selection es solo una lista de nombres de productos para facilitar el manejo de los checkboxes
    st.session_state.current_selection = list(st.session_state.current_selection_data.keys())

    # Información de la fecha actual
    date_display = get_date_display(st.session_state.current_date)
    st.markdown(f'<div class="week-info">Lista del {date_display}</div>', 
                unsafe_allow_html=True)
    
    # Sidebar para controles
    with st.sidebar:
        st.header("🎛️ Controles")
        
        # Botón para cerrar sesión
        if st.button("🚪 Cerrar Sesión"):
            st.session_state.user_authenticated = False
            if 'user_info' in st.session_state:
                del st.session_state.user_info
            if 'access_token' in st.session_state:
                del st.session_state.access_token
            if 'user_email' in st.session_state:
                del st.session_state.user_email
            # No eliminamos ALL_USERS_DATA_FILE, solo las variables de sesión del usuario actual
            st.rerun()
        
        st.divider()
        
        # Botón para nueva fecha
        if st.button("🔄 Nueva Lista", help="Reinicia la selección para una nueva fecha"):
            st.session_state.current_date = get_current_date()
            st.session_state.current_selection_data = {}
            st.session_state.current_selection = []
            st.rerun()
        
        # Botón para guardar selección
        if st.button("💾 Guardar Selección", help="Guarda la selección actual"):
            # Guardar con cantidades incluidas
            weekly_selections[st.session_state.current_date] = {
                "timestamp": datetime.now().isoformat(),
                "products": st.session_state.current_selection_data
            }
            save_user_data() # Guardar todos los datos de usuario
            st.success("✅ Selección guardada!")
        
        st.divider()
                        
        # Agregar nuevo producto
        st.header("➕ Agregar Producto")

        # Ingreso individual
        new_product = st.text_input("Nombre del producto:", key="new_product_input")
        product_category = st.selectbox("Categoría:", CATEGORIES, key="single_category")
        
        if st.button("Agregar a Lista Maestra", key="add_single"):
            if new_product.strip() and new_product.strip() not in master_list:
                master_list[new_product.strip()] = product_category
                save_user_data()
                st.success(f"✅ '{new_product.strip()}' agregado en {product_category}!")
                st.rerun()
            elif new_product.strip() in master_list:
                st.warning("⚠️ El producto ya existe en la lista")
            else:
                st.warning("⚠️ Por favor ingresa un nombre válido")

        st.divider()

        # Ingreso en bulk
        bulk_input = st.text_area("Productos en bulk (separados por coma o salto de línea):", key="bulk_product_input")
        bulk_category = st.selectbox("Categoría para todos:", CATEGORIES, key="bulk_category")
        
        if st.button("Agregar Productos en Bulk"):
            if bulk_input.strip():
                # Procesar entrada: split por coma o salto de línea
                bulk_products = [p.strip() for line in bulk_input.splitlines() for p in line.split(",")]
                added = []
                for prod in bulk_products:
                    if prod and prod not in master_list:
                        master_list[prod] = bulk_category
                        added.append(prod)
                if added:
                    save_user_data()
                    st.success(f"✅ Agregados en {bulk_category}: {', '.join(added)}")
                    st.rerun()
                else:
                    st.info("ℹ️ No se agregaron productos nuevos")
            else:
                st.warning("⚠️ Ingresa al menos un producto")
                
        # Estadísticas
        st.header("📊 Estadísticas")
        total_products = len(master_list)
        selected_products = len(st.session_state.current_selection)
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total", total_products, help="Productos en lista maestra")
        with col2:
            st.metric("Seleccionados", selected_products, help="Productos seleccionados hoy")
        
        if total_products > 0:
            percentage = (selected_products / total_products) * 100
            st.progress(percentage / 100)
            st.caption(f"{percentage:.1f}% de productos seleccionados")
        
        # Estadísticas por categoría
        st.subheader("Por Categoría")
        products_by_category = get_products_by_category(master_list)
        for category in sorted(products_by_category.keys()):
            count = len(products_by_category[category])
            selected_count = len([p for p in products_by_category[category] if p in st.session_state.current_selection])
            emoji = CATEGORY_EMOJIS.get(category, "📦")
            st.caption(f"{emoji} {category}: {selected_count}/{count}")
        
        st.divider()
        
        # Gestión de la lista maestra
        st.header("🗂️ Gestión de Lista")
        
        if st.session_state.current_selection:
            if st.button("🗑️ Eliminar Seleccionados (de la Lista Maestra)", help="Elimina todos los productos seleccionados de la lista maestra"):
                products_to_delete_from_master = st.session_state.current_selection.copy()
                for product in products_to_delete_from_master:
                    if product in master_list:
                        del master_list[product]
                st.session_state.current_selection_data = {} # Limpia la selección actual
                st.session_state.current_selection = [] # Actualiza la lista de seleccionados
                save_user_data()
                st.success("✅ Productos seleccionados eliminados de la lista maestra!")
                st.rerun()
        
        if st.button("🗑️ Limpiar Lista Maestra (todos los productos)", help="Elimina todos los productos de tu lista maestra"):
            if master_list:
                master_list.clear() # Vacía el diccionario
                st.session_state.current_selection_data = {}
                st.session_state.current_selection = []
                save_user_data()
                st.success("✅ Lista maestra limpiada!")
                st.rerun()
        
        # Exportar lista de compras
        if st.session_state.current_selection:
            st.header("📋 Exportar Lista")
            
            # Organizar por categorías para exportar
            selected_by_category = {}
            for product, data in st.session_state.current_selection_data.items():
                category = master_list.get(product, "Otro")
                if category not in selected_by_category:
                    selected_by_category[category] = []
                quantity = data.get("quantity", "")
                formatted_product = format_product_with_quantity(product, quantity)
                selected_by_category[category].append(formatted_product)
            
            shopping_list = f"Lista de Compras - {get_date_display(st.session_state.current_date)}\n"
            shopping_list += "=" * 50 + "\n\n"
            
            for category in sorted(selected_by_category.keys()):
                emoji = CATEGORY_EMOJIS.get(category, "📦")
                shopping_list += f"{emoji} {category.upper()}\n"
                shopping_list += "-" * 30 + "\n"
                for product in sorted(selected_by_category[category]):
                    shopping_list += f"• {product}\n"
                shopping_list += "\n"
            
            st.download_button(
                label="📥 Descargar Lista de Compras",
                data=shopping_list,
                file_name=f"lista_compras_{st.session_state.current_date}.txt",
                mime="text/plain"
            )

    # Contenido principal
    if not master_list:
        st.info("👋 ¡Bienvenido! Tu lista maestra está vacía. Agrega algunos productos usando el panel lateral.")
    else:
        # Pestañas para organizar el contenido
        tab1, tab2, tab3 = st.tabs(["🛒 Selección Semanal", "📋 Lista Maestra", "📅 Historial"])
        
        with tab1:
            st.header("Selecciona productos para esta semana")
            
            # Filtros
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                search_term = st.text_input("🔍 Buscar productos:", placeholder="Escribe para filtrar...", key="search_term_tab1")
            with col2:
                category_filter = st.selectbox("📂 Filtrar por categoría:", ["Todas"] + sorted(CATEGORIES), key="category_filter_tab1")
            with col3:
                show_only_selected = st.checkbox("Solo seleccionados", key="show_selected_tab1")
            
            # Organizar productos por categoría
            products_by_category = get_products_by_category(master_list)
            
            # Aplicar filtros
            if category_filter != "Todas":
                products_by_category = {category_filter: products_by_category.get(category_filter, [])}
            
            # Filtrar por búsqueda
            if search_term:
                filtered_products_by_category = {}
                for category, products in products_by_category.items():
                    filtered_products = [p for p in products if search_term.lower() in p.lower()]
                    if filtered_products:
                        filtered_products_by_category[category] = filtered_products
                products_by_category = filtered_products_by_category
            
            # Filtrar por seleccionados
            if show_only_selected:
                filtered_products_by_category = {}
                for category, products in products_by_category.items():
                    filtered_products = [p for p in products if p in st.session_state.current_selection]
                    if filtered_products:
                        filtered_products_by_category[category] = filtered_products
                products_by_category = filtered_products_by_category
            
            # Mostrar productos por categoría
            if products_by_category:
                # Botones para seleccionar/deseleccionar todo lo visible
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Seleccionar Todo Visible", key="select_all_visible"):
                        for products in products_by_category.values():
                            for product in products:
                                if product not in st.session_state.current_selection_data:
                                    st.session_state.current_selection_data[product] = {"quantity": "", "timestamp": datetime.now().isoformat()}
                        st.session_state.current_selection = list(st.session_state.current_selection_data.keys())
                        st.rerun()
                with col2:
                    if st.button("❌ Deseleccionar Todo Visible", key="deselect_all_visible"):
                        for products in products_by_category.values():
                            for product in products:
                                if product in st.session_state.current_selection_data:
                                    del st.session_state.current_selection_data[product]
                        st.session_state.current_selection = list(st.session_state.current_selection_data.keys())
                        st.rerun()
                
                st.divider()
                
                # Mostrar por categorías
                for category in sorted(products_by_category.keys()):
                    products = products_by_category[category]
                    if products:
                        emoji = CATEGORY_EMOJIS.get(category, "📦")
                        selected_in_category = [p for p in products if p in st.session_state.current_selection]
                        
                        st.markdown(f'<div class="category-header">{emoji} {category} ({len(selected_in_category)}/{len(products)})</div>', 
                                     unsafe_allow_html=True)
                        
                        # Lista de productos con checkboxes y cantidades
                        for product in sorted(products):
                            is_selected = product in st.session_state.current_selection_data
                            checkbox_key = f"checkbox_{product}_{st.session_state.current_date}" # Unique key for checkbox
                            quantity_key = f"quantity_{product}_{st.session_state.current_date}" # Unique key for quantity input
                            
                            col1_prod, col2_qty = st.columns([3, 1])
                            
                            with col1_prod:
                                # Usamos un callback para actualizar st.session_state.current_selection_data inmediatamente
                                def update_selection(prod):
                                    if st.session_state[f"checkbox_{prod}_{st.session_state.current_date}"]:
                                        if prod not in st.session_state.current_selection_data:
                                            st.session_state.current_selection_data[prod] = {
                                                "quantity": st.session_state[f"quantity_{prod}_{st.session_state.current_date}"],
                                                "timestamp": datetime.now().isoformat()
                                            }
                                    else:
                                        if prod in st.session_state.current_selection_data:
                                            del st.session_state.current_selection_data[prod]
                                    st.session_state.current_selection = list(st.session_state.current_selection_data.keys())

                                st.checkbox(
                                    product, 
                                    value=is_selected, 
                                    key=checkbox_key,
                                    on_change=update_selection,
                                    args=(product,),
                                    help=f"{'✅ Seleccionado' if is_selected else '⬜ No seleccionado'}"
                                )
                            
                            with col2_qty:
                                current_quantity = st.session_state.current_selection_data.get(product, {}).get("quantity", "")
                                
                                def update_quantity(prod):
                                    if prod in st.session_state.current_selection_data:
                                        st.session_state.current_selection_data[prod]["quantity"] = st.session_state[f"quantity_{prod}_{st.session_state.current_date}"]

                                st.text_input(
                                    "Cantidad", 
                                    value=current_quantity,
                                    placeholder="ej: 2, 1kg, 500g",
                                    key=quantity_key,
                                    label_visibility="collapsed",
                                    disabled=not is_selected, # Deshabilitar si no está seleccionado
                                    on_change=update_quantity,
                                    args=(product,)
                                )
                            st.divider()
            else:
                st.info("No se encontraron productos que coincidan con tu búsqueda.")
        
        with tab2:
            st.header("Lista Maestra de Productos")
            
            if master_list:
                # Mostrar productos en formato de tabla
                products_data = []
                for product, category in master_list.items():
                    emoji = CATEGORY_EMOJIS.get(category, "📦")
                    quantity = st.session_state.current_selection_data.get(product, {}).get("quantity", "")
                    
                    products_data.append({
                        'Producto': product,
                        'Categoría': f"{emoji} {category}",
                        'En lista actual': '✅' if product in st.session_state.current_selection else '⬜',
                        'Cantidad (en selección actual)': quantity
                    })
                
                df = pd.DataFrame(products_data)
                df = df.sort_values(['Categoría', 'Producto'])
                
                st.dataframe(df, use_container_width=True)
                
                # Opción para editar productos
                st.subheader("✏️ Editar Producto")
                col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                
                with col1:
                    product_to_edit = st.selectbox("Selecciona producto:", list(master_list.keys()), key="edit_product_select")
                
                if product_to_edit:
                    with col2:
                        new_name = st.text_input("Nuevo nombre:", value=product_to_edit, key="new_product_name_input")
                    
                    with col3:
                        current_category = master_list.get(product_to_edit, "Otro")
                        new_category = st.selectbox("Nueva categoría:", CATEGORIES, index=CATEGORIES.index(current_category), key="new_category_select")
                    
                    with col4:
                        st.text("") # Spacer
                        if st.button("Guardar Cambios", key="save_product_changes"):
                            if new_name.strip() and new_name.strip() != product_to_edit:
                                # If name changed, create new entry and delete old
                                master_list[new_name.strip()] = new_category
                                del master_list[product_to_edit]
                                # Update current selection data if the product was selected
                                if product_to_edit in st.session_state.current_selection_data:
                                    temp_data = st.session_state.current_selection_data[product_to_edit]
                                    del st.session_state.current_selection_data[product_to_edit]
                                    st.session_state.current_selection_data[new_name.strip()] = temp_data
                                    st.session_state.current_selection = list(st.session_state.current_selection_data.keys()) # Refresh current selection
                                st.success(f"✅ Producto '{product_to_edit}' actualizado a '{new_name.strip()}' y categoría '{new_category}'!")
                            elif new_name.strip() == product_to_edit and new_category != current_category:
                                # Only category changed
                                master_list[product_to_edit] = new_category
                                st.success(f"✅ Categoría de '{product_to_edit}' actualizada a '{new_category}'!")
                            else:
                                st.info("ℹ️ No se realizaron cambios o el nombre ya existe.")
                            save_user_data()
                            st.rerun()

                    st.divider()
                    st.subheader("🗑️ Eliminar Producto de Lista Maestra")
                    st.warning(f"⚠️ Estás a punto de eliminar '{product_to_edit}' permanentemente de tu lista maestra. Esta acción no se puede deshacer.")
                    if st.button(f"Eliminar '{product_to_edit}'", key="delete_specific_product", type="secondary"):
                        if product_to_edit in master_list:
                            del master_list[product_to_edit]
                            if product_to_edit in st.session_state.current_selection_data:
                                del st.session_state.current_selection_data[product_to_edit]
                                st.session_state.current_selection = list(st.session_state.current_selection_data.keys())
                            save_user_data()
                            st.success(f"✅ '{product_to_edit}' eliminado de la lista maestra.")
                            st.rerun()
            else:
                st.info("Tu lista maestra está vacía. Agrega productos desde la pestaña 'Selección Semanal' o el panel lateral.")

        with tab3:
            st.header("Historial de Listas de Compras")
            if weekly_selections:
                # Ordenar por fecha descendente
                sorted_dates = sorted(weekly_selections.keys(), reverse=True)
                
                for date_key in sorted_dates:
                    selection_data = weekly_selections[date_key]
                    products_selected = selection_data.get("products", {})
                    timestamp_str = selection_data.get("timestamp", "N/A")
                    
                    st.markdown(f"#### 📅 {get_date_display(date_key)}")
                    st.caption(f"Guardado el: {datetime.fromisoformat(timestamp_str).strftime('%d/%m/%Y %H:%M')}")
                    
                    if products_selected:
                        # Organizar productos del historial por categoría
                        history_products_by_category = {}
                        for product, data in products_selected.items():
                            category = master_list.get(product, "Otro") # Usar la categoría actual de la lista maestra
                            if category not in history_products_by_category:
                                history_products_by_category[category] = []
                            history_products_by_category[category].append(format_product_with_quantity(product, data.get("quantity", "")))
                        
                        for category in sorted(history_products_by_category.keys()):
                            emoji = CATEGORY_EMOJIS.get(category, "📦")
                            st.markdown(f"**{emoji} {category}:**")
                            for prod_display in sorted(history_products_by_category[category]):
                                st.write(f"- {prod_display}")
                        
                        col_hist1, col_hist2 = st.columns(2)
                        with col_hist1:
                            if st.button(f"➕ Cargar Lista del {get_date_display(date_key)}", key=f"load_{date_key}"):
                                st.session_state.current_date = date_key
                                st.session_state.current_selection_data = products_selected
                                st.session_state.current_selection = list(products_selected.keys())
                                st.success(f"✅ Lista del {get_date_display(date_key)} cargada a la selección actual.")
                                st.rerun()
                        with col_hist2:
                            if st.button(f"🗑️ Eliminar Historial de {get_date_display(date_key)}", key=f"delete_history_{date_key}", type="secondary"):
                                del weekly_selections[date_key]
                                save_user_data()
                                st.success(f"🗑️ Historial del {get_date_display(date_key)} eliminado.")
                                st.rerun()
                    else:
                        st.info("Esta lista no contiene productos.")
                    st.markdown("---")
            else:
                st.info("No hay historial de listas de compras. Guarda tu primera selección semanal.")

if __name__ == "__main__":
    main()