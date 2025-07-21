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
    st.error("❌ Error de configuración: Credenciales OAuth no encontradas")
    st.stop()

# Sustituye directamente esta línea:
GOOGLE_REDIRECT_URI = "https://groceries-00.streamlit.app/"

GOOGLE_OAUTH_URL = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

# Archivos para persistencia
MASTER_LIST_FILE = "lista_maestra.json"
WEEKLY_SELECTIONS_FILE = "selecciones_semanales.json"
USER_DATA_FILE = "user_data.json"

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
            if user_info:
                st.session_state.user_authenticated = True
                st.session_state.user_info = user_info
                st.session_state.access_token = token_data['access_token']

                # Limpiar parámetros de la URL
                st.query_params.clear()
                st.rerun()
            else:
                st.error("Error obteniendo información del usuario")
        else:
            st.error("Error al autenticar con Google")

def load_master_list():
    """Cargar la lista maestra desde archivo JSON"""
    if os.path.exists(MASTER_LIST_FILE):
        try:
            with open(MASTER_LIST_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Manejar tanto formato antiguo (lista) como nuevo (diccionario)
                if isinstance(data, list):
                    # Convertir formato antiguo a nuevo
                    return {product: "Otro" for product in data}
                return data
        except:
            return {}
    else:
        # Lista inicial de ejemplo con categorías
        initial_list = {
            "Leche": "Lácteos y Huevos",
            "Pan": "Panadería",
            "Huevos": "Lácteos y Huevos",
            "Arroz": "Cereales y Granos",
            "Pollo": "Carnes y Pollo",
            "Tomates": "Frutas y Verduras",
            "Cebolla": "Frutas y Verduras",
            "Pasta": "Cereales y Granos",
            "Aceite de oliva": "Aceites y Condimentos",
            "Yogur": "Lácteos y Huevos",
            "Manzanas": "Frutas y Verduras",
            "Plátanos": "Frutas y Verduras",
            "Queso": "Lácteos y Huevos",
            "Jamón": "Carnes y Pollo",
            "Lechuga": "Frutas y Verduras"
        }
        save_master_list(initial_list)
        return initial_list

def save_master_list(master_list):
    """Guardar la lista maestra en archivo JSON"""
    with open(MASTER_LIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(master_list, f, ensure_ascii=False, indent=2)

def load_weekly_selections():
    """Cargar las selecciones semanales desde archivo JSON"""
    if os.path.exists(WEEKLY_SELECTIONS_FILE):
        try:
            with open(WEEKLY_SELECTIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_weekly_selections(selections):
    """Guardar las selecciones semanales en archivo JSON"""
    with open(WEEKLY_SELECTIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(selections, f, ensure_ascii=False, indent=2)

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
        return f"{product} ({quantity})"
    return product

def parse_product_quantity(product_text):
    """Extraer producto y cantidad del texto formateado"""
    if " (x" in product_text and product_text.endswith(")"):
        product = product_text.split(" (x")[0]
        quantity = product_text.split(" (x")[1][:-1]
        return product, quantity
    return product_text, "1"

def login_screen():
    """Pantalla de login"""
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown("# 🛒 Gestor de Compras")
    st.markdown("### ¡Bienvenido!")
    st.markdown("Inicia sesión con tu cuenta de Google para acceder a tu lista de compras personalizada.")
    
    auth_url = get_google_auth_url()
    st.markdown(f'<a href="{auth_url}" target="_blank" rel="noopener noreferrer"><button style="...">🔐 Iniciar Sesión con Google</button></a>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def main():
    # Inicializar session state para autenticación
    if 'user_authenticated' not in st.session_state:
        st.session_state.user_authenticated = False
    
    # Cargar datos de usuario guardados
    if 'user_authenticated' not in st.session_state or not st.session_state.user_authenticated:
        st.session_state.user_authenticated = False
    
    # Manejar callback de OAuth
    handle_oauth_callback()
    
    # Si no está autenticado, mostrar pantalla de login
    if not st.session_state.user_authenticated:
        login_screen()
        return
    
    # Título principal
    st.markdown('<h1 class="main-header">🛒 Gestor de Compras del Supermercado</h1>', 
                unsafe_allow_html=True)
    
    # Mostrar información del usuario
    if 'user_info' in st.session_state:
        user_name = st.session_state.user_info.get('name', 'Usuario')
        user_email = st.session_state.user_info.get('email', '')
        st.markdown(f'<div class="user-info">👋 ¡Hola {user_name}! ({user_email})</div>', 
                    unsafe_allow_html=True)
    
    # Inicializar state
    if 'master_list' not in st.session_state:
        st.session_state.master_list = load_master_list()
    
    if 'weekly_selections' not in st.session_state:
        st.session_state.weekly_selections = load_weekly_selections()
    
    if 'current_date' not in st.session_state:
        st.session_state.current_date = get_current_date()
    
    if 'current_selection' not in st.session_state:
        date_key = st.session_state.current_date
        if date_key in st.session_state.weekly_selections:
            st.session_state.current_selection = st.session_state.weekly_selections[date_key]
        else:
            st.session_state.current_selection = {}
    
    if 'product_quantities' not in st.session_state:
        st.session_state.product_quantities = {}

    if 'current_selection_data' not in st.session_state:
        st.session_state.current_selection_data = {}
    
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
            if os.path.exists(USER_DATA_FILE):
                os.remove(USER_DATA_FILE)
            st.rerun()
        
        st.divider()
        
        # Botón para nueva fecha
        if st.button("🔄 Nueva Lista", help="Reinicia la selección para una nueva fecha"):
            st.session_state.current_date = get_current_date()
            st.session_state.current_selection = {}
            st.session_state.product_quantities = {}
            st.rerun()
        
        # Botón para guardar selección
        if st.button("💾 Guardar Selección", help="Guarda la selección actual"):
            # Guardar con cantidades incluidas
            selection_with_quantities = {}
            for product in st.session_state.current_selection:
                # Obtén la cantidad directamente de current_selection_data si existe
                product_data = st.session_state.current_selection_data.get(product, {})
                quantity = product_data.get("quantity", "").strip()
                
                formatted_product = format_product_with_quantity(product, quantity)
                selection_with_quantities[product] = {
                    'quantity': quantity,
                    'formatted': formatted_product
                }
            
            st.session_state.weekly_selections[st.session_state.current_date] = {
                "timestamp": datetime.now().isoformat(),
                "products": selection_with_quantities
            }
            save_weekly_selections(st.session_state.weekly_selections)
            st.success("✅ Selección guardada!")
        
        st.divider()
                
        # Agregar nuevo producto
        st.header("➕ Agregar Producto")

        # Ingreso individual
        new_product = st.text_input("Nombre del producto:")
        product_category = st.selectbox("Categoría:", CATEGORIES, key="single_category")
        
        if st.button("Agregar a Lista Maestra", key="add_single"):
            if new_product and new_product not in st.session_state.master_list:
                st.session_state.master_list[new_product] = product_category
                save_master_list(st.session_state.master_list)
                st.success(f"✅ '{new_product}' agregado en {product_category}!")
                st.rerun()
            elif new_product in st.session_state.master_list:
                st.warning("⚠️ El producto ya existe en la lista")
            else:
                st.warning("⚠️ Por favor ingresa un nombre válido")

        st.divider()

        # Ingreso en bulk
        bulk_input = st.text_area("Productos en bulk (separados por coma o salto de línea):")
        bulk_category = st.selectbox("Categoría para todos:", CATEGORIES, key="bulk_category")
        
        if st.button("Agregar Productos en Bulk"):
            if bulk_input.strip():
                # Procesar entrada: split por coma o salto de línea
                bulk_products = [p.strip() for line in bulk_input.splitlines() for p in line.split(",")]
                added = []
                for prod in bulk_products:
                    if prod and prod not in st.session_state.master_list:
                        st.session_state.master_list[prod] = bulk_category
                        added.append(prod)
                if added:
                    save_master_list(st.session_state.master_list)
                    st.success(f"✅ Agregados en {bulk_category}: {', '.join(added)}")
                    st.rerun()
                else:
                    st.info("ℹ️ No se agregaron productos nuevos")
            else:
                st.warning("⚠️ Ingresa al menos un producto")
                
        # Estadísticas
        st.header("📊 Estadísticas")
        total_products = len(st.session_state.master_list)
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
        products_by_category = get_products_by_category(st.session_state.master_list)
        for category in sorted(products_by_category.keys()):
            count = len(products_by_category[category])
            selected_count = len([p for p in products_by_category[category] if p in st.session_state.current_selection])
            emoji = CATEGORY_EMOJIS.get(category, "📦")
            st.caption(f"{emoji} {category}: {selected_count}/{count}")
        
        st.divider()
        
        # Gestión de la lista maestra
        st.header("🗂️ Gestión de Lista")
        
        # Eliminar productos seleccionados
        if st.session_state.current_selection:
            if st.button("🗑️ Eliminar Seleccionados", help="Elimina todos los productos seleccionados de la lista maestra"):
                for product in st.session_state.current_selection:
                    if product in st.session_state.master_list:
                        del st.session_state.master_list[product]
                st.session_state.current_selection = {}
                st.session_state.product_quantities = {}
                save_master_list(st.session_state.master_list)
                st.success("✅ Productos seleccionados eliminados!")
                st.rerun()
        
        if st.button("🗑️ Limpiar Lista Maestra", help="Elimina todos los productos"):
            if st.session_state.master_list:
                st.session_state.master_list = {}
                st.session_state.current_selection = {}
                st.session_state.product_quantities = {}
                save_master_list(st.session_state.master_list)
                st.success("✅ Lista limpiada!")
                st.rerun()
        
        # Exportar lista de compras
        if st.session_state.current_selection:
            st.header("📋 Exportar Lista")
            
            # Organizar por categorías para exportar
            selected_by_category = {}
            for product in st.session_state.current_selection:
                category = st.session_state.master_list.get(product, "Otro")
                if category not in selected_by_category:
                    selected_by_category[category] = []
                quantity = st.session_state.product_quantities.get(product, "1")
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
    if not st.session_state.master_list:
        st.info("👋 ¡Bienvenido! Tu lista maestra está vacía. Agrega algunos productos usando el panel lateral.")
    else:
        # Pestañas para organizar el contenido
        tab1, tab2, tab3 = st.tabs(["🛒 Selección Semanal", "📋 Lista Maestra", "📅 Historial"])
        
        with tab1:
            st.header("Selecciona productos para esta semana")
            
            # Filtros
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                search_term = st.text_input("🔍 Buscar productos:", placeholder="Escribe para filtrar...")
            with col2:
                category_filter = st.selectbox("📂 Filtrar por categoría:", ["Todas"] + sorted(CATEGORIES))
            with col3:
                show_only_selected = st.checkbox("Solo seleccionados")
            
            # Organizar productos por categoría
            products_by_category = get_products_by_category(st.session_state.master_list)
            
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
                    if st.button("✅ Seleccionar Todo Visible"):
                        for products in products_by_category.values():
                            for product in products:
                                product_info = st.session_state.current_selection_data.get(product, {})
                                if not product_info:  # Solo agregar si no existe
                                    st.session_state.current_selection_data[product] = {"quantity": "", "timestamp": datetime.now().isoformat()}
                        st.session_state.current_selection = list(st.session_state.current_selection_data.keys())
                        st.rerun()
                with col2:
                    if st.button("❌ Deseleccionar Todo Visible"):
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
                            is_selected = product in st.session_state.current_selection
                            checkbox_key = f"checkbox_{product}"
                            quantity_key = f"quantity_{product}"
                            
                            col1, col2 = st.columns([3, 1])
                            
                            with col1:
                                checkbox_changed = st.checkbox(
                                    product, 
                                    value=is_selected, 
                                    key=checkbox_key,
                                    help=f"{'✅ Seleccionado' if is_selected else '⬜ No seleccionado'}"
                                )
                            
                            with col2:
                                current_quantity = ""
                                if product in st.session_state.current_selection_data:
                                    current_quantity = st.session_state.current_selection_data[product].get("quantity", "")
                                
                                quantity = st.text_input(
                                    "Cantidad", 
                                    value=current_quantity,
                                    placeholder="ej: 2, 1kg, 500g",
                                    key=quantity_key,
                                    label_visibility="collapsed",
                                    disabled=not checkbox_changed
                                )
                            
                            # Manejar cambios
                            if checkbox_changed:
                                if product not in st.session_state.current_selection_data:
                                    st.session_state.current_selection_data[product] = {
                                        "quantity": quantity,
                                        "timestamp": datetime.now().isoformat()
                                    }
                                else:
                                    st.session_state.current_selection_data[product]["quantity"] = quantity
                            else:
                                if product in st.session_state.current_selection_data:
                                    del st.session_state.current_selection_data[product]
                            
                            # Actualizar lista de selección
                            st.session_state.current_selection = list(st.session_state.current_selection_data.keys())
                        
                        st.divider()
                
                # Botón para eliminar todos los productos seleccionados (al final)
                if st.session_state.current_selection:
                    st.markdown("### 🗑️ Eliminar Productos")
                    st.warning(f"⚠️ Esto eliminará permanentemente {len(st.session_state.current_selection)} productos seleccionados de la lista maestra.")
                    
                    if st.button("🗑️ Eliminar Todos los Seleccionados", help="Elimina permanentemente todos los productos seleccionados"):
                        # Confirmar eliminación
                        products_to_delete = st.session_state.current_selection.copy()
                        for product in products_to_delete:
                            if product in st.session_state.master_list:
                                del st.session_state.master_list[product]
                        
                        st.session_state.current_selection = []
                        st.session_state.current_selection_data = {}
                        save_master_list(st.session_state.master_list)
                        st.success(f"✅ {len(products_to_delete)} productos eliminados de la lista maestra!")
                        st.rerun()
            else:
                st.info("No se encontraron productos que coincidan con tu búsqueda.")
        
        with tab2:
            st.header("Lista Maestra de Productos")
            
            if st.session_state.master_list:
                # Mostrar productos en formato de tabla
                products_data = []
                for product, category in st.session_state.master_list.items():
                    emoji = CATEGORY_EMOJIS.get(category, "📦")
                    quantity = ""
                    if product in st.session_state.current_selection_data:
                        quantity = st.session_state.current_selection_data[product].get("quantity", "")
                    
                    products_data.append({
                        'Producto': product,
                        'Categoría': f"{emoji} {category}",
                        'En lista actual': '✅' if product in st.session_state.current_selection else '⬜',
                        'Cantidad': quantity
                    })
                
                df = pd.DataFrame(products_data)
                df = df.sort_values(['Categoría', 'Producto'])
                
                st.dataframe(df, use_container_width=True)
                
                # Opción para editar productos
                st.subheader("✏️ Editar Producto")
                col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                
                with col1:
                    product_to_edit = st.selectbox("Selecciona producto:", list(st.session_state.master_list.keys()))
                
                with col2:
                    new_name = st.text_input("Nuevo nombre:", value=product_to_edit)
                
                with col3:
                    current_category = st.session_state.master_list.get(product_to_edit, "Otro")
                    new_category = st.selectbox("Nueva categoría:", CATEGORIES, index=CATEGORIES.index(current_category))
                
                with col4:
                    if st.button("💾 Actualizar"):
                        if new_name and (new_name != product_to_edit or new_category != current_category):
                            # Eliminar producto anterior
                            del st.session_state.master_list[product_to_edit]
                            
                            # Agregar producto actualizado
                            st.session_state.master_list[new_name] = new_category
                            
                            # Actualizar selección actual si es necesario
                            if product_to_edit in st.session_state.current_selection_data:
                                product_data = st.session_state.current_selection_data[product_to_edit]
                                del st.session_state.current_selection_data[product_to_edit]
                                st.session_state.current_selection_data[new_name] = product_data
                                st.session_state.current_selection = list(st.session_state.current_selection_data.keys())
                            
                            save_master_list(st.session_state.master_list)
                            st.success(f"✅ Producto actualizado!")
                            st.rerun()
            else:
                st.info("No hay productos en la lista maestra.")
        
        with tab3:
            st.header("Historial de Compras")
            
            if st.session_state.weekly_selections:
                # Mostrar historial ordenado por fecha más reciente
                sorted_selections = sorted(st.session_state.weekly_selections.items(), 
                                         key=lambda x: x[1].get('timestamp', ''), reverse=True)
                
                for timestamp, selection_data in sorted_selections:
                    # Extraer información
                    selection_timestamp = selection_data.get('timestamp', timestamp)
                    products_data = selection_data.get('products', {})
                    
                    # Convertir timestamp a fecha legible
                    try:
                        if isinstance(selection_timestamp, str):
                            date_obj = datetime.fromisoformat(selection_timestamp.replace('Z', '+00:00'))
                        else:
                            date_obj = datetime.strptime(selection_timestamp, "%Y-%m-%d")
                        date_display = date_obj.strftime("%d de %B, %Y a las %H:%M")
                    except:
                        date_display = selection_timestamp
                    
                    total_items = len(products_data) if isinstance(products_data, dict) else len(products_data) if isinstance(products_data, list) else 0
                    
                    with st.expander(f"{date_display} ({total_items} productos)"):
                        if products_data:
                            # Organizar por categorías
                            products_by_category = {}
                            
                            # Manejar tanto formato nuevo (dict) como antiguo (list)
                            if isinstance(products_data, dict):
                                for product, product_info in products_data.items():
                                    category = st.session_state.master_list.get(product, "Otro")
                                    if category not in products_by_category:
                                        products_by_category[category] = []
                                    quantity = ""
                                    if isinstance(product_info, dict):
                                        quantity = product_info.get("quantity", "")
                                    products_by_category[category].append((product, quantity))
                            else:  # Lista antigua sin cantidades
                                for product in products_data:
                                    category = st.session_state.master_list.get(product, "Otro")
                                    if category not in products_by_category:
                                        products_by_category[category] = []
                                    products_by_category[category].append((product, ""))
                            
                            # Crear texto para copiar
                            copy_text = f"Lista de Compras - {date_display}\n{'='*50}\n\n"
                            
                            for category in sorted(products_by_category.keys()):
                                emoji = CATEGORY_EMOJIS.get(category, "📦")
                                copy_text += f"{emoji} {category.upper()}\n"
                                copy_text += "-" * 30 + "\n"
                                for product, quantity in sorted(products_by_category[category]):
                                    if quantity:
                                        copy_text += f"• {product} ({quantity})\n"
                                    else:
                                        copy_text += f"• {product}\n"
                                copy_text += "\n"
                            
                            # Mostrar visualmente
                            for category in sorted(products_by_category.keys()):
                                emoji = CATEGORY_EMOJIS.get(category, "📦")
                                st.write(f"**{emoji} {category}**")
                                for product, quantity in sorted(products_by_category[category]):
                                    if quantity:
                                        st.write(f"• {product} ({quantity})")
                                    else:
                                        st.write(f"• {product}")
                                st.write("")
                            
                            # Botones de acción
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                if st.button(f"🔄 Reutilizar selección", key=f"reuse_{timestamp}"):
                                    if isinstance(products_data, dict):
                                        st.session_state.current_selection_data = products_data.copy()
                                    else:  # Lista antigua
                                        st.session_state.current_selection_data = {product: {"quantity": "", "timestamp": datetime.now().isoformat()} for product in products_data}
                                    st.session_state.current_selection = list(st.session_state.current_selection_data.keys())
                                    st.success("✅ Selección reutilizada!")
                                    st.rerun()
                            
                            with col2:
                                st.download_button(
                                    label="📥 Descargar Lista",
                                    data=copy_text,
                                    file_name=f"historial_compras_{timestamp.replace(':', '-')}.txt",
                                    mime="text/plain",
                                    key=f"download_{timestamp}"
                                )
                            
                            with col3:
                                if st.button(f"🗑️ Eliminar", key=f"delete_{timestamp}"):
                                    del st.session_state.weekly_selections[timestamp]
                                    save_weekly_selections(st.session_state.weekly_selections)
                                    st.success("✅ Registro eliminado!")
                                    st.rerun()
                            
                            # Mostrar texto para copiar
                            st.text_area("Texto para copiar:", value=copy_text, height=200, key=f"text_{timestamp}")
                        else:
                            st.write("No se seleccionaron productos en esta fecha.")
            else:
                st.info("No hay historial de compras guardado.")

if __name__ == "__main__":
    main()