import streamlit as st
import json
import os
from datetime import datetime, timedelta
import pandas as pd
import requests
from urllib.parse import urlencode
import secrets
import base64

# --- Configuración de la página de Streamlit ---
st.set_page_config(
    page_title="🛒 Gestor de Compras del Supermercado",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS Personalizado para mejorar la interfaz ---
st.markdown("""
<style>
    /* Estilos generales */
    .stApp {
        background-color: #f0f2f6; /* Fondo claro */
        color: #333;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #4A90E2; /* Azul para títulos */
    }
    .stButton>button {
        background-color: #4A90E2; /* Azul para botones */
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 20px;
        font-size: 16px;
        transition: all 0.3s ease;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.2);
    }
    .stButton>button:hover {
        background-color: #357ABD; /* Azul más oscuro al pasar el ratón */
        transform: translateY(-2px);
        box-shadow: 4px 4px 12px rgba(0,0,0,0.3);
    }
    .stTextInput>div>div>input, .stSelectbox>div>div>select {
        border-radius: 8px;
        border: 1px solid #ccc;
        padding: 8px;
    }
    .stAlert {
        border-radius: 8px;
    }
    .sidebar .sidebar-content {
        background-color: #e0e6f0; /* Fondo de la barra lateral */
        padding: 20px;
        border-right: 1px solid #d0d6e0;
    }
    .stExpander {
        border-radius: 8px;
        border: 1px solid #ddd;
        padding: 10px;
        background-color: #fff;
        box-shadow: 1px 1px 5px rgba(0,0,0,0.1);
    }
    .stExpander > div > div > p {
        font-weight: bold;
        color: #333;
    }
    .stMarkdown a button {
        text-decoration: none;
    }
    .stCheckbox > label {
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .stProgress > div > div > div > div {
        background-color: #28a745; /* Color de la barra de progreso */
    }
    .st-emotion-cache-1r6dm1x { /* Clase para el botón de Google OAuth */
        display: flex;
        justify-content: center;
        margin-top: 20px;
    }
    .login-button {
        background-color: #4285F4; /* Color de Google */
        color: white;
        padding: 12px 25px;
        border: none;
        border-radius: 5px;
        font-size: 18px;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 10px;
        text-decoration: none;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        transition: background-color 0.3s ease;
    }
    .login-button:hover {
        background-color: #3367D6;
    }
    .login-button img {
        height: 24px;
        width: 24px;
    }
</style>
""", unsafe_allow_html=True)

# --- Configuración OAuth Google ---
# Se recomienda usar st.secrets para producción. Para desarrollo local, se puede usar variables de entorno.
GOOGLE_CLIENT_ID = st.secrets.get("GOOGLE_CLIENT_ID", os.getenv("GOOGLE_CLIENT_ID"))
GOOGLE_CLIENT_SECRET = st.secrets.get("GOOGLE_CLIENT_SECRET", os.getenv("GOOGLE_CLIENT_SECRET"))

if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    st.error("❌ Error de configuración: Credenciales OAuth no encontradas.")
    st.warning("Por favor, asegúrate de haber configurado `GOOGLE_CLIENT_ID` y `GOOGLE_CLIENT_SECRET` en `secrets.toml` o como variables de entorno.")
    st.stop()

# Redirección para Streamlit Cloud. Asegúrate de que esta URL coincida con la URL de tu app.
GOOGLE_REDIRECT_URI = "https://groceries-00.streamlit.app/" # ¡Asegúrate de cambiar esto por la URL de tu app desplegada!

GOOGLE_OAUTH_URL = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

# --- Funciones de autenticación ---

def generate_state():
    """Genera un estado aleatorio para prevenir ataques CSRF."""
    return secrets.token_urlsafe(32)

def get_google_auth_url():
    """Genera la URL de autenticación de Google."""
    state = generate_state()
    st.session_state.oauth_state = state # Guarda el estado en la sesión para validación posterior
    params = {
        'client_id': GOOGLE_CLIENT_ID,
        'redirect_uri': GOOGLE_REDIRECT_URI,
        'scope': 'openid email profile', # Solicita acceso a email y perfil
        'response_type': 'code',
        'state': state,
        'access_type': 'offline', # Permite obtener un refresh_token (útil para sesiones persistentes)
        'prompt': 'consent' # Fuerza al usuario a dar consentimiento cada vez (útil para pruebas)
    }
    return f"{GOOGLE_OAUTH_URL}?{urlencode(params)}"

def exchange_code_for_token(code):
    """Intercambia el código de autorización por un token de acceso."""
    data = {
        'client_id': GOOGLE_CLIENT_ID,
        'client_secret': GOOGLE_CLIENT_SECRET,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': GOOGLE_REDIRECT_URI,
    }
    try:
        response = requests.post(GOOGLE_TOKEN_URL, data=data)
        response.raise_for_status() # Lanza una excepción para errores HTTP
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error al obtener token de Google: {e}")
        return None

def get_user_info(access_token):
    """Obtiene la información del usuario usando el token de acceso."""
    headers = {'Authorization': f'Bearer {access_token}'}
    try:
        response = requests.get(GOOGLE_USERINFO_URL, headers=headers)
        response.raise_for_status() # Lanza una excepción para errores HTTP
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error al obtener información del usuario: {e}")
        return None

def handle_oauth_callback():
    """Maneja la redirección de OAuth y procesa el código de autorización."""
    query_params = st.query_params

    if 'code' in query_params:
        code = query_params['code']
        state = query_params.get('state')

        # Validar el estado para seguridad CSRF
        if 'oauth_state' not in st.session_state or st.session_state.oauth_state != state:
            st.error("❌ Error de seguridad: El estado de OAuth no coincide. Posible ataque CSRF.")
            st.query_params.clear()
            return

        token_data = exchange_code_for_token(code)
        if token_data and 'access_token' in token_data:
            user_info = get_user_info(token_data['access_token'])
            if user_info:
                st.session_state.user_authenticated = True
                st.session_state.user_info = user_info
                st.session_state.access_token = token_data['access_token']
                st.session_state.user_id = user_info.get('id', user_info.get('email')) # Usa el ID de Google o email como ID de usuario
                st.query_params.clear() # Limpia los parámetros de la URL
                st.rerun() # Vuelve a ejecutar la aplicación para reflejar el estado de autenticación
            else:
                st.error("Error obteniendo información del usuario.")
        else:
            st.error("Error al autenticar con Google.")
    elif 'error' in query_params:
        st.error(f"Error de autenticación: {query_params['error_description']}")
        st.query_params.clear() # Limpia los parámetros de la URL
        st.rerun()

def login_screen():
    """Muestra la pantalla de inicio de sesión."""
    st.markdown("<div style='text-align:center;margin-top:100px;'>", unsafe_allow_html=True)
    st.markdown("<h1>🛒 Gestor de Compras del Supermercado</h1>", unsafe_allow_html=True)
    st.markdown("<h3>¡Bienvenido!</h3>", unsafe_allow_html=True)
    st.markdown("Inicia sesión con tu cuenta de Google para gestionar tus listas de compras personalizadas.")
    auth_url = get_google_auth_url()
    # Usar un botón con estilo personalizado para el login de Google
    st.markdown(f"""
    <div class="st-emotion-cache-1r6dm1x">
        <a href="{auth_url}" target="_self" class="login-button">
            <img src="data:image/svg+xml;base64,{base64.b64encode(open('google_logo.svg', 'rb').read()).decode()}" alt="Google logo">
            Iniciar Sesión con Google
        </a>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# --- Datos y configuraciones de la aplicación ---

# Categorías predefinidas con emojis y colores
CATEGORIES = {
    "Lácteos y Huevos": {"emoji": "🥛🥚", "color": "#FFDDC1"},
    "Verduras y Frutas": {"emoji": "🍎🥦", "color": "#D4EDDA"},
    "Carnes y Pescados": {"emoji": "🥩🐟", "color": "#FFC0CB"},
    "Panadería y Repostería": {"emoji": "🍞🍰", "color": "#F0E68C"},
    "Despensa y Enlatados": {"emoji": "🥫🍚", "color": "#E0FFFF"},
    "Bebidas": {"emoji": "🥤☕", "color": "#ADD8E6"},
    "Congelados": {"emoji": "🧊🍕", "color": "#E6E6FA"},
    "Limpieza del Hogar": {"emoji": "🧼🧹", "color": "#F5DEB3"},
    "Cuidado Personal": {"emoji": "🧴🛀", "color": "#FFE4B5"},
    "Mascotas": {"emoji": "🐾🦴", "color": "#D8BFD8"},
    "Snacks y Dulces": {"emoji": "🍬🍫", "color": "#FFDEAD"},
    "Especias y Condimentos": {"emoji": "🌶️🧂", "color": "#FAFAD2"},
    "Otros": {"emoji": "📦❓", "color": "#D3D3D3"},
}

# --- Funciones de persistencia (Opcional, la app es transitoria por defecto) ---
# Si se desea persistencia, se debe descomentar y adaptar estas funciones
# y llamar a `load_data` al inicio y `save_data` al guardar.

# def get_user_data_path(user_id, filename):
#     """Genera la ruta del archivo de datos para un usuario específico."""
#     data_dir = os.path.join("data", user_id)
#     os.makedirs(data_dir, exist_ok=True)
#     return os.path.join(data_dir, filename)

# def load_data(user_id, filename, default_value):
#     """Carga datos de un archivo JSON específico del usuario."""
#     path = get_user_data_path(user_id, filename)
#     if os.path.exists(path):
#         with open(path, 'r', encoding='utf-8') as f:
#             return json.load(f)
#     return default_value

# def save_data(user_id, data, filename):
#     """Guarda datos en un archivo JSON específico del usuario."""
#     path = get_user_data_path(user_id, filename)
#     with open(path, 'w', encoding='utf-8') as f:
#         json.dump(data, f, ensure_ascii=False, indent=4)

# --- Inicialización del estado de la sesión ---
def initialize_session_state():
    """Inicializa todas las variables de estado de la sesión."""
    if 'user_authenticated' not in st.session_state:
        st.session_state.user_authenticated = False
    if 'user_info' not in st.session_state:
        st.session_state.user_info = {}
    if 'access_token' not in st.session_state:
        st.session_state.access_token = None
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None # Se establecerá después de la autenticación

    # Datos de la aplicación, transitorios por sesión
    if 'master_list' not in st.session_state:
        st.session_state.master_list = [] # [{'id': 'uuid', 'name': 'Leche', 'category': 'Lácteos y Huevos'}]
        # Si se desea persistencia:
        # if st.session_state.user_id:
        #     st.session_state.master_list = load_data(st.session_state.user_id, 'lista_maestra.json', [])

    if 'current_selection' not in st.session_state:
        st.session_state.current_selection = {} # {'item_id': True/False} para checkboxes
    if 'product_quantities' not in st.session_state:
        st.session_state.product_quantities = {} # {'item_id': quantity} para cantidades

    if 'weekly_selections' not in st.session_state:
        st.session_state.weekly_selections = [] # [{'date': 'YYYY-MM-DD HH:MM', 'items': [{'id': 'uuid', 'name': 'Leche', 'category': 'Lácteos', 'quantity': 2}]}]
        # Si se desea persistencia:
        # if st.session_state.user_id:
        #     st.session_state.weekly_selections = load_data(st.session_state.user_id, 'selecciones_semanales.json', [])

    if 'current_date' not in st.session_state:
        st.session_state.current_date = datetime.now().date()

    # Variables para filtros
    if 'filter_name' not in st.session_state:
        st.session_state.filter_name = ""
    if 'filter_category' not in st.session_state:
        st.session_state.filter_category = "Todas"
    if 'filter_status' not in st.session_state:
        st.session_state.filter_status = "Todos"

# --- Funciones de gestión de la lista maestra ---

def add_product():
    """Añade un producto a la lista maestra."""
    product_name = st.session_state.new_product_name.strip()
    product_category = st.session_state.new_product_category

    if product_name:
        # Evitar duplicados por nombre y categoría
        if any(p['name'].lower() == product_name.lower() and p['category'] == product_category for p in st.session_state.master_list):
            st.warning(f"'{product_name}' ya existe en la categoría '{product_category}'.")
        else:
            new_id = str(len(st.session_state.master_list) + 1) # ID simple, se podría usar UUID
            st.session_state.master_list.append({
                'id': new_id,
                'name': product_name,
                'category': product_category
            })
            st.session_state.new_product_name = "" # Limpiar el input
            st.success(f"'{product_name}' añadido a la lista maestra.")
            # Si se desea persistencia:
            # save_data(st.session_state.user_id, st.session_state.master_list, 'lista_maestra.json')
    else:
        st.error("Por favor, introduce un nombre para el producto.")

def delete_product(product_id):
    """Elimina un producto de la lista maestra."""
    st.session_state.master_list = [p for p in st.session_state.master_list if p['id'] != product_id]
    st.session_state.current_selection.pop(product_id, None) # Eliminar de la selección actual si existe
    st.session_state.product_quantities.pop(product_id, None) # Eliminar la cantidad si existe
    st.success("Producto eliminado.")
    # Si se desea persistencia:
    # save_data(st.session_state.user_id, st.session_state.master_list, 'lista_maestra.json')

def clear_master_list():
    """Limpia toda la lista maestra."""
    st.session_state.master_list = []
    st.session_state.current_selection = {}
    st.session_state.product_quantities = {}
    st.success("Lista maestra limpiada.")
    # Si se desea persistencia:
    # save_data(st.session_state.user_id, st.session_state.master_list, 'lista_maestra.json')

def update_product(product_id, new_name, new_category):
    """Actualiza un producto existente en la lista maestra."""
    for product in st.session_state.master_list:
        if product['id'] == product_id:
            product['name'] = new_name.strip()
            product['category'] = new_category
            st.success(f"Producto '{new_name}' actualizado.")
            # Si se desea persistencia:
            # save_data(st.session_state.user_id, st.session_state.master_list, 'lista_maestra.json')
            break

# --- Funciones de gestión de selección semanal ---

def save_current_selection():
    """Guarda la selección actual como una lista semanal."""
    selected_items = []
    for item_id, is_selected in st.session_state.current_selection.items():
        if is_selected:
            # Encuentra el producto en la lista maestra
            product = next((p for p in st.session_state.master_list if p['id'] == item_id), None)
            if product:
                quantity = st.session_state.product_quantities.get(item_id, 1) # Cantidad por defecto 1
                selected_items.append({
                    'id': product['id'],
                    'name': product['name'],
                    'category': product['category'],
                    'quantity': quantity
                })

    if selected_items:
        new_selection_entry = {
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'items': selected_items
        }
        st.session_state.weekly_selections.insert(0, new_selection_entry) # Añadir al principio
        st.success(f"Lista de compras guardada para {new_selection_entry['date']}.")
        # Si se desea persistencia:
        # save_data(st.session_state.user_id, st.session_state.weekly_selections, 'selecciones_semanales.json')
    else:
        st.warning("No hay productos seleccionados para guardar.")

def export_list_to_text(items_to_export):
    """Exporta una lista de productos a un formato de texto legible."""
    if not items_to_export:
        return "No hay productos para exportar."

    grouped_by_category = {}
    for item in items_to_export:
        category = item['category']
        if category not in grouped_by_category:
            grouped_by_category[category] = []
        grouped_by_category[category].append(f"- {item['name']} (x{item['quantity']})")

    export_text = "🛒 Lista de Compras:\n\n"
    for category, items in grouped_by_category.items():
        emoji = CATEGORIES.get(category, {}).get("emoji", "")
        export_text += f"--- {emoji} {category} ---\n"
        export_text += "\n".join(items) + "\n\n"
    return export_text

def reuse_selection(selection_index):
    """Reutiliza una selección histórica como base para la selección actual."""
    if 0 <= selection_index < len(st.session_state.weekly_selections):
        historical_selection = st.session_state.weekly_selections[selection_index]
        st.session_state.current_selection = {item['id']: True for item in historical_selection['items']}
        st.session_state.product_quantities = {item['id']: item['quantity'] for item in historical_selection['items']}
        st.success(f"Lista del {historical_selection['date']} cargada para edición.")
    else:
        st.error("Índice de selección no válido.")

def delete_weekly_selection(selection_index):
    """Elimina una selección semanal del historial."""
    if 0 <= selection_index < len(st.session_state.weekly_selections):
        deleted_date = st.session_state.weekly_selections[selection_index]['date']
        del st.session_state.weekly_selections[selection_index]
        st.success(f"Lista del {deleted_date} eliminada del historial.")
        # Si se desea persistencia:
        # save_data(st.session_state.user_id, st.session_state.weekly_selections, 'selecciones_semanales.json')
    else:
        st.error("Índice de selección no válido.")

# --- Interfaz de usuario principal de la aplicación ---

def main_app():
    """Función principal de la aplicación una vez autenticado el usuario."""
    initialize_session_state() # Asegura que el estado esté inicializado para el usuario autenticado

    user_name = st.session_state.user_info.get('name', 'Usuario')
    user_email = st.session_state.user_info.get('email', '')
    user_id_display = st.session_state.user_id # Mostrar el ID completo del usuario

    st.sidebar.title("Menú")
    st.sidebar.markdown(f"👋 **¡Hola {user_name}!**")
    st.sidebar.markdown(f"📧 {user_email}")
    st.sidebar.markdown(f"🆔 ID de Usuario: `{user_id_display}`") # Mostrar ID completo

    if st.sidebar.button("Cerrar Sesión", key="logout_button"):
        st.session_state.clear() # Limpia todo el estado de la sesión
        st.rerun()

    st.title("🛒 Gestor de Compras del Supermercado")

    tab1, tab2, tab3 = st.tabs(["📋 Lista Maestra", "📝 Selección Semanal", "⏳ Historial de Selecciones"])

    with tab1:
        st.header("Lista Maestra de Productos")
        st.markdown("Gestiona tu inventario de productos disponibles para tus listas de compras.")

        # Formulario para añadir productos
        with st.form("add_product_form", clear_on_submit=True):
            col_name, col_cat = st.columns([3, 2])
            with col_name:
                new_product_name = st.text_input("Nombre del Producto", key="new_product_name", placeholder="Ej: Leche, Pan, Manzanas")
            with col_cat:
                new_product_category = st.selectbox("Categoría", options=list(CATEGORIES.keys()), key="new_product_category")
            
            st.form_submit_button("➕ Añadir Producto", on_click=add_product)

        st.subheader("Productos en tu Lista Maestra")

        if not st.session_state.master_list:
            st.info("No hay productos en tu lista maestra. ¡Añade algunos!")
        else:
            # Mostrar la lista maestra en un DataFrame editable
            df_master = pd.DataFrame(st.session_state.master_list)
            df_master['Categoría'] = df_master['category'].apply(lambda x: f"{CATEGORIES.get(x, {}).get('emoji', '')} {x}")
            df_master['Nombre'] = df_master['name']
            df_master_display = df_master[['Nombre', 'Categoría']]

            edited_df = st.data_editor(
                df_master_display,
                column_config={
                    "Nombre": st.column_config.TextColumn("Nombre", width="medium"),
                    "Categoría": st.column_config.SelectboxColumn(
                        "Categoría",
                        options=[f"{CATEGORIES.get(cat, {}).get('emoji', '')} {cat}" for cat in CATEGORIES.keys()],
                        width="medium",
                        required=True
                    )
                },
                hide_index=True,
                num_rows="dynamic",
                use_container_width=True,
                key="master_list_editor"
            )

            # Procesar las ediciones del data_editor
            if st.button("Guardar Cambios en Lista Maestra", key="save_master_changes"):
                updated_master_list = []
                for i, row in edited_df.iterrows():
                    original_product_id = st.session_state.master_list[i]['id']
                    updated_name = row['Nombre']
                    # Extraer el nombre de la categoría del string con emoji
                    updated_category = row['Categoría'].split(' ', 1)[1].strip() if ' ' in row['Categoría'] else row['Categoría']
                    updated_master_list.append({
                        'id': original_product_id,
                        'name': updated_name,
                        'category': updated_category
                    })
                st.session_state.master_list = updated_master_list
                st.success("Cambios en la lista maestra guardados.")
                # Si se desea persistencia:
                # save_data(st.session_state.user_id, st.session_state.master_list, 'lista_maestra.json')
                st.rerun() # Recargar para reflejar cambios

            # Botones de acción para la lista maestra
            col_del, col_clear = st.columns(2)
            with col_del:
                product_to_delete_name = st.selectbox(
                    "Selecciona producto para eliminar",
                    options=[""] + [p['name'] for p in st.session_state.master_list],
                    key="product_to_delete_name"
                )
                if st.button("🗑️ Eliminar Producto Seleccionado", key="delete_single_product"):
                    if product_to_delete_name:
                        product_id_to_delete = next((p['id'] for p in st.session_state.master_list if p['name'] == product_to_delete_name), None)
                        if product_id_to_delete:
                            delete_product(product_id_to_delete)
                            st.rerun()
                        else:
                            st.warning("Producto no encontrado.")
                    else:
                        st.warning("Por favor, selecciona un producto para eliminar.")
            with col_clear:
                st.markdown("<br>", unsafe_allow_html=True) # Espacio para alinear
                if st.button("🗑️ Limpiar Toda la Lista Maestra", key="clear_all_master_list"):
                    if st.warning("¿Estás seguro de que quieres limpiar toda la lista maestra? Esta acción es irreversible."):
                        if st.button("Confirmar Limpiar Lista Maestra", key="confirm_clear_master_list"):
                            clear_master_list()
                            st.rerun()

    with tab2:
        st.header("Selección Semanal")
        st.markdown("Selecciona los productos que necesitas para esta semana y asigna cantidades.")

        # Filtros para la selección semanal
        col_filter1, col_filter2, col_filter3 = st.columns(3)
        with col_filter1:
            st.text_input("Filtrar por nombre", key="filter_name", on_change=lambda: st.session_state.update(filter_name=st.session_state.filter_name))
        with col_filter2:
            st.selectbox("Filtrar por categoría", options=["Todas"] + list(CATEGORIES.keys()), key="filter_category", on_change=lambda: st.session_state.update(filter_category=st.session_state.filter_category))
        with col_filter3:
            st.selectbox("Filtrar por estado", options=["Todos", "Seleccionados", "No Seleccionados"], key="filter_status", on_change=lambda: st.session_state.update(filter_status=st.session_state.filter_status))

        filtered_master_list = st.session_state.master_list
        # Aplicar filtro por nombre
        if st.session_state.filter_name:
            filtered_master_list = [
                p for p in filtered_master_list
                if st.session_state.filter_name.lower() in p['name'].lower()
            ]
        # Aplicar filtro por categoría
        if st.session_state.filter_category != "Todas":
            filtered_master_list = [
                p for p in filtered_master_list
                if p['category'] == st.session_state.filter_category
            ]

        # Mostrar productos para selección
        st.subheader("Productos Disponibles")
        if not filtered_master_list:
            st.info("No hay productos que coincidan con los filtros o la lista maestra está vacía.")
        else:
            total_products = len(filtered_master_list)
            selected_count = 0

            # Usar columnas para una mejor disposición de los elementos
            cols = st.columns(4) # Ajusta el número de columnas según el tamaño de la pantalla

            for i, product in enumerate(filtered_master_list):
                col_idx = i % 4
                with cols[col_idx]:
                    is_selected = st.checkbox(
                        f"{CATEGORIES.get(product['category'], {}).get('emoji', '')} {product['name']}",
                        value=st.session_state.current_selection.get(product['id'], False),
                        key=f"select_{product['id']}"
                    )
                    st.session_state.current_selection[product['id']] = is_selected

                    # Mostrar input de cantidad solo si está seleccionado
                    if is_selected:
                        selected_count += 1
                        current_quantity = st.session_state.product_quantities.get(product['id'], 1)
                        quantity = st.number_input(
                            "Cantidad",
                            min_value=1,
                            value=int(current_quantity), # Asegurarse de que el valor inicial sea un entero
                            key=f"qty_{product['id']}"
                        )
                        st.session_state.product_quantities[product['id']] = quantity
                    else:
                        # Asegurarse de que la cantidad se resetee si se deselecciona
                        st.session_state.product_quantities.pop(product['id'], None)

            # Aplicar filtro por estado (después de que los checkboxes hayan actualizado current_selection)
            if st.session_state.filter_status == "Seleccionados":
                filtered_master_list = [p for p in filtered_master_list if st.session_state.current_selection.get(p['id'], False)]
            elif st.session_state.filter_status == "No Seleccionados":
                filtered_master_list = [p for p in filtered_master_list if not st.session_state.current_selection.get(p['id'], False)]

            # Recalcular el progreso después de aplicar el filtro de estado
            if total_products > 0:
                progress_percent = (selected_count / total_products) * 100
                st.markdown(f"**Progreso de Selección:** {selected_count} de {total_products} productos seleccionados")
                st.progress(progress_percent / 100)
            else:
                st.info("No hay productos en la lista maestra para seleccionar.")

            st.markdown("---")
            col_save, col_export = st.columns(2)
            with col_save:
                if st.button("💾 Guardar Selección Actual", key="save_current_selection_button"):
                    save_current_selection()
            with col_export:
                current_selected_items_for_export = []
                for item_id, is_selected in st.session_state.current_selection.items():
                    if is_selected:
                        product = next((p for p in st.session_state.master_list if p['id'] == item_id), None)
                        if product:
                            current_selected_items_for_export.append({
                                'id': product['id'],
                                'name': product['name'],
                                'category': product['category'],
                                'quantity': st.session_state.product_quantities.get(item_id, 1)
                            })
                
                export_text_content = export_list_to_text(current_selected_items_for_export)
                st.download_button(
                    label="📄 Exportar Lista Actual (.txt)",
                    data=export_text_content,
                    file_name=f"lista_compras_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                    mime="text/plain",
                    key="export_current_list_button"
                )

    with tab3:
        st.header("Historial de Selecciones")
        st.markdown("Revisa, reutiliza o elimina tus listas de compras guardadas.")

        if not st.session_state.weekly_selections:
            st.info("No hay listas de compras guardadas en el historial.")
        else:
            for i, selection_entry in enumerate(st.session_state.weekly_selections):
                expander_title = f"Lista del {selection_entry['date']} ({len(selection_entry['items'])} productos)"
                with st.expander(expander_title):
                    df_selection = pd.DataFrame(selection_entry['items'])
                    df_selection['Categoría'] = df_selection['category'].apply(lambda x: f"{CATEGORIES.get(x, {}).get('emoji', '')} {x}")
                    df_selection['Producto'] = df_selection['name']
                    df_selection['Cantidad'] = df_selection['quantity']
                    st.dataframe(df_selection[['Producto', 'Categoría', 'Cantidad']], hide_index=True, use_container_width=True)

                    col_hist1, col_hist2, col_hist3 = st.columns(3)
                    with col_hist1:
                        if st.button(f"🔄 Reutilizar (ID: {i})", key=f"reuse_{i}"):
                            reuse_selection(i)
                            st.rerun()
                    with col_hist2:
                        export_hist_content = export_list_to_text(selection_entry['items'])
                        st.download_button(
                            label=f"⬇️ Descargar (ID: {i})",
                            data=export_hist_content,
                            file_name=f"lista_compras_historial_{selection_entry['date'].replace(' ', '_').replace(':', '')}.txt",
                            mime="text/plain",
                            key=f"download_hist_{i}"
                        )
                    with col_hist3:
                        if st.button(f"🗑️ Eliminar (ID: {i})", key=f"delete_hist_{i}"):
                            # Confirmación simple antes de eliminar
                            if st.warning(f"¿Estás seguro de que quieres eliminar la lista del {selection_entry['date']}?"):
                                if st.button(f"Confirmar Eliminación (ID: {i})", key=f"confirm_delete_hist_{i}"):
                                    delete_weekly_selection(i)
                                    st.rerun()


# --- Punto de entrada de la aplicación ---
if __name__ == "__main__":
    # Crear un archivo SVG de Google Logo si no existe
    # Esto es para el botón de login, puedes reemplazarlo con una URL de imagen si prefieres
    google_logo_svg_content = """
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="24px" height="24px">
        <path fill="#FFC107" d="M43.611,20.083H42V20H24v8h11.303c-1.649,4.657-6.08,8-11.303,8c-6.627,0-12-5.373-12-12c0-6.627,5.373-12,12-12c3.059,0,5.842,1.154,8.065,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C12.955,4,4,12.955,4,24c0,11.045,8.955,20,20,20c11.045,0,20-8.955,20-20C44,22.659,43.862,21.35,43.611,20.083z"/>
        <path fill="#FF3D00" d="M6.306,14.691l6.571,4.819C14.655,15.108,18.961,12,24,12c3.059,0,5.842,1.154,8.065,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C12.955,4,4,12.955,4,24c0,3.951,1.186,7.674,3.251,10.71l6.571-4.819C12.756,29.882,12,26.069,12,24C12,20.732,13.341,17.795,15.518,15.518z"/>
        <path fill="#4CAF50" d="M24,44c5.166,0,9.86-1.977,13.409-5.192l-6.19-5.238C29.211,35.091,26.715,36,24,36c-5.202,0-9.619-3.317-11.283-7.946l-6.571,4.819C11.186,40.326,15.049,44,24,44z"/>
        <path fill="#1976D2" d="M43.611,20.083H42V20H24v8h11.303c-0.792,2.237-2.231,4.166-4.087,5.571c0.001-0.001,0.002-0.001,0.003-0.002l6.19,5.238C36.971,39.205,44,34,44,24C44,22.659,43.862,21.35,43.611,20.083z"/>
    </svg>
    """
    if not os.path.exists('google_logo.svg'):
        with open('google_logo.svg', 'w') as f:
            f.write(google_logo_svg_content)

    # Llama a la función principal de manejo de OAuth
    handle_oauth_callback()

    # Decide qué pantalla mostrar
    if not st.session_state.user_authenticated:
        login_screen()
    else:
        main_app()
