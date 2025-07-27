
import streamlit as st
import json
import os
import secrets
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests
from collections import Counter # Para las recomendaciones

# --- Configuración de OAuth de Google ---
# Las credenciales ahora se obtienen de st.secrets
# Verifica si los secretos están configurados
if not ("GOOGLE_CLIENT_ID" in st.secrets and "GOOGLE_CLIENT_SECRET" in st.secrets):
    st.error("❌ Error: Las credenciales de Google OAuth (GOOGLE_CLIENT_ID y GOOGLE_CLIENT_SECRET) no se encontraron en Streamlit Secrets. Por favor, configura tus secretos en Streamlit Cloud.")
    st.info("Para configurarlos, ve a los ajustes de tu aplicación en Streamlit Cloud -> Secrets y añade:")
    st.code("""
GOOGLE_CLIENT_ID = "tu_client_id.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "tu_client_secret"
# Opcional si necesitas el ID del proyecto en el flujo OAuth:
# GOOGLE_PROJECT_ID = "tu-project-id"
    """, language="toml")
    st.stop() # Detener la aplicación si las credenciales no están

# === INICIO DE LA CORRECCIÓN ===
# URI para despliegue en Streamlit Cloud.
# IMPORTANTE: Esta URL debe coincidir EXACTAMENTE con la que configuraste
# en la Google Cloud Console para tu OAuth Client ID.
REDIRECT_URI_FOR_FLOW = "https://groceries-00.streamlit.app/"

# Construir el diccionario de configuración del cliente OAuth a partir de st.secrets
# Esto simula la estructura de client_secret.json para Flow.from_client_config
client_config = {
    "web": {
        "client_id": st.secrets["GOOGLE_CLIENT_ID"],
        "project_id": st.secrets.get("GOOGLE_PROJECT_ID", "streamlit-app"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_secret": st.secrets["GOOGLE_CLIENT_SECRET"],
        "redirect_uris": [
            # URI para desarrollo local
            "http://localhost:8501/",
            # URI para despliegue en Streamlit Cloud
            REDIRECT_URI_FOR_FLOW
        ]
    }
}
# === FIN DE LA CORRECCIÓN ===

# Define los SCOPES que necesitas para tu aplicación
SCOPES = ['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile']

# --- Inicialización de st.session_state ---
if 'user_email' not in st.session_state:
    st.session_state.user_email = None
if 'user_info' not in st.session_state:
    st.session_state.user_info = None
if 'master_list' not in st.session_state:
    st.session_state.master_list = {}
if 'weekly_selections' not in st.session_state:
    st.session_state.weekly_selections = {}
if 'current_selection' not in st.session_state:
    st.session_state.current_selection = []
if 'current_selection_data' not in st.session_state:
    st.session_state.current_selection_data = {}
if 'current_category_filter' not in st.session_state:
    st.session_state.current_category_filter = 'Todas'
if 'all_users_data' not in st.session_state:
    st.session_state.all_users_data = {}

# Nombre del archivo para guardar todos los datos de los usuarios
ALL_USERS_DATA_FILE = "all_users_data.json"

# --- Funciones de Gestión de Datos ---
def load_all_users_data():
    """Carga todos los datos de los usuarios desde el archivo JSON."""
    try:
        if os.path.exists(ALL_USERS_DATA_FILE):
            with open(ALL_USERS_DATA_FILE, 'r', encoding='utf-8') as f:
                st.session_state.all_users_data = json.load(f)
        else:
            st.session_state.all_users_data = {}
            with open(ALL_USERS_DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump({}, f)
    except json.JSONDecodeError:
        st.error("❌ Error al decodificar el archivo de datos. Parece que está corrupto. Se inicializará con datos vacíos.")
        st.session_state.all_users_data = {}
        with open(ALL_USERS_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f)
    except Exception as e:
        st.error(f"❌ Error inesperado al cargar los datos: {e}. Se inicializará con datos vacíos.")
        st.session_state.all_users_data = {}
        with open(ALL_USERS_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f)

def save_all_users_data():
    """Guarda todos los datos de los usuarios al archivo JSON."""
    try:
        with open(ALL_USERS_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(st.session_state.all_users_data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        st.error(f"❌ Error al guardar los datos: {e}. Asegúrate de tener permisos de escritura en la carpeta donde se ejecuta la aplicación.")

def load_user_data():
    """
    Carga los datos del usuario actual (lista maestra y selecciones semanales)
    desde la estructura general de datos de todos los usuarios.
    """
    email = st.session_state.user_email
    if email and email in st.session_state.all_users_data:
        user_data = st.session_state.all_users_data[email]
        st.session_state.master_list = user_data.get('master_list', {})
        st.session_state.weekly_selections = user_data.get('weekly_selections', {})
    else:
        st.session_state.master_list = {}
        st.session_state.weekly_selections = {}
        if email:
            st.session_state.all_users_data[email] = {
                'master_list': {},
                'weekly_selections': {}
            }
            save_all_users_data()

def save_user_data():
    """
    Guarda los datos del usuario actual (lista maestra y selecciones semanales)
    en la estructura general de datos de todos los usuarios y luego en el archivo.
    """
    email = st.session_state.user_email
    if email:
        st.session_state.all_users_data[email] = {
            'master_list': st.session_state.master_list,
            'weekly_selections': st.session_state.weekly_selections
        }
        save_all_users_data()

load_all_users_data()

# --- Funciones de Autenticación de Google ---
def google_oauth_login():
    """Inicia el flujo de autenticación de Google OAuth."""
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI_FOR_FLOW
    )
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    st.session_state['oauth_state'] = state
    st.markdown(f'<a href="{authorization_url}" target="_top" style="display: inline-block; padding: 10px 20px; background-color: #4285F4; color: white; text-align: center; text-decoration: none; border-radius: 5px; font-weight: bold;">Iniciar sesión con Google</a>', unsafe_allow_html=True)
    
   
def handle_oauth_callback():
    """Maneja el callback de la autenticación de Google."""
    query_params = st.query_params
    if 'code' in query_params and 'state' in query_params and query_params['state'] == st.session_state.get('oauth_state'):
        code = query_params['code']
        state_param = query_params['state']

        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            state=state_param,
            redirect_uri=REDIRECT_URI_FOR_FLOW
        )
        try:
            flow.fetch_token(code=code)
            credentials = flow.credentials
            id_info = id_token.verify_oauth2_token(
                credentials.id_token, requests.Request(), st.secrets["GOOGLE_CLIENT_ID"])
            st.session_state.user_email = id_info['email']
            st.session_state.user_info = id_info
            st.success(f"¡Inicio de sesión exitoso como {st.session_state.user_email}!")
            st.query_params.clear()
            return True
        except Exception as e:
            st.error(f"Error durante el manejo de la autenticación de Google: {e}. Por favor, inténtalo de nuevo.")
            if 'oauth_state' in st.session_state:
                del st.session_state['oauth_state']
            st.query_params.clear()
            return False
    elif 'state' in query_params and query_params['state'] != st.session_state.get('oauth_state'):
        st.warning("¡Estado de OAuth inválido! Intenta iniciar sesión de nuevo.")
        if 'oauth_state' in st.session_state:
            del st.session_state['oauth_state']
        st.query_params.clear()
        return False
    elif 'error' in query_params:
        st.error(f"Error de OAuth: {query_params['error_description'] if 'error_description' in query_params else query_params['error']}")
        st.query_params.clear()
        return False
    return None

def logout():
    """Cierra la sesión del usuario."""
    st.session_state.user_email = None
    st.session_state.user_info = None
    st.session_state.master_list = {}
    st.session_state.weekly_selections = {}
    st.session_state.current_selection = []
    st.session_state.current_selection_data = {}
    st.session_state.current_category_filter = 'Todas'
    if 'oauth_state' in st.session_state:
        del st.session_state['oauth_state']
    st.success("Sesión cerrada correctamente.")
    st.rerun()

# --- Funciones de Lógica de la Aplicación ---
def add_product_to_master(name, category, quantity_type):
    """Añade un nuevo producto a la lista maestra."""
    name = name.strip()
    if not name:
        st.warning("El nombre del producto no puede estar vacío.")
        return False
    if name in st.session_state.master_list:
        st.warning("⚠️ ¡Este producto ya existe en tu lista maestra!")
        return False
    st.session_state.master_list[name] = {
        "category": category,
        "quantity_type": quantity_type
    }
    save_user_data()
    st.success(f"✅ '{name}' añadido a la lista maestra.")
    return True

def add_to_weekly_selection(product_name, quantity):
    """Añade o actualiza un producto en la selección semanal."""
    if product_name not in st.session_state.master_list:
        st.error(f"Error: '{product_name}' no se encontró en tu lista maestra.")
        return
    if product_name not in st.session_state.weekly_selections:
        st.session_state.weekly_selections[product_name] = {
            "quantity": 0,
            "category": st.session_state.master_list[product_name]["category"],
            "quantity_type": st.session_state.master_list[product_name]["quantity_type"]
        }
    st.session_state.weekly_selections[product_name]["quantity"] += quantity
    save_user_data()
    st.success(f"➕ '{product_name}' actualizado en la selección semanal.")

def remove_from_weekly_selection(product_name):
    """Elimina un producto de la selección semanal."""
    if product_name in st.session_state.weekly_selections:
        del st.session_state.weekly_selections[product_name]
        save_user_data()
        st.success(f"➖ '{product_name}' eliminado de la selección semanal.")

def clear_weekly_selection():
    """Limpia completamente la selección semanal."""
    st.session_state.weekly_selections = {}
    save_user_data()
    st.success("✅ Lista de selección semanal limpiada.")

def get_master_list_categories():
    """Retorna una lista de todas las categorías únicas en la lista maestra."""
    return sorted(list(set([details['category'] for details in st.session_state.master_list.values()])))

def get_filtered_master_products(filter_category='Todas'):
    """Retorna una lista de productos de la lista maestra, opcionalmente filtrada por categoría."""
    if filter_category == 'Todas':
        return sorted(list(st.session_state.master_list.keys()))
    else:
        return sorted([
            p for p in st.session_state.master_list.keys()
            if st.session_state.master_list[p]['category'] == filter_category
        ])

def get_frequent_purchases_recommendations(num_recommendations=5):
    """Genera recomendaciones básicas de productos no seleccionados."""
    potential_recommendations = [
        p for p in st.session_state.master_list.keys()
        if p not in st.session_state.weekly_selections
    ]
    return sorted(potential_recommendations)[:num_recommendations]

# --- Interfaz de Usuario de Streamlit ---
st.set_page_config(
    page_title="Gestor de Compras Inteligente",
    page_icon="🛒",
    layout="centered"
)
st.title("🛒 Gestor de Compras Inteligente")

auth_success = handle_oauth_callback()
if auth_success:
    load_user_data()
    st.rerun()
elif auth_success is False:
    st.stop()

if not st.session_state.user_email:
    st.info("Por favor, inicia sesión con Google para usar la aplicación.")
    google_oauth_login()
else:
    user_name = st.session_state.user_info.get('name', st.session_state.user_email)
    st.sidebar.success(f"¡Hola, {user_name}! 👋")
    st.sidebar.button("Cerrar Sesión", on_click=logout)

    tab1, tab2 = st.tabs(["🛍️ Selección Semanal", "🗂️ Gestión de Lista Maestra"])

    with tab1:
        st.header("🛍️ Selección Semanal")
        if not st.session_state.master_list:
            st.warning("Tu lista maestra está vacía. ¡Ve a 'Gestión de Lista Maestra' para añadir productos!")
        else:
            categories = get_master_list_categories()
            categories.insert(0, 'Todas')
            st.session_state.current_category_filter = st.selectbox(
                "Filtrar por Categoría:",
                categories,
                key="category_filter",
                index=categories.index(st.session_state.current_category_filter)
            )

            st.subheader("Añadir Productos a la Selección Semanal")
            col1, col2, col3 = st.columns([0.6, 0.2, 0.2])
            available_products = get_filtered_master_products(st.session_state.current_category_filter)

            if available_products:
                with col1:
                    selected_product = st.selectbox(
                        "Producto:",
                        available_products,
                        key="product_selection_add"
                    )
                if selected_product:
                    quantity_type = st.session_state.master_list[selected_product]['quantity_type']
                    with col2:
                        quantity_input = st.number_input(
                            f"Cantidad ({quantity_type}):",
                            min_value=1, value=1, key="quantity_input"
                        )
                    with col3:
                        st.write("")
                        st.write("")
                        if st.button("➕ Añadir", key="add_to_weekly_btn"):
                            add_to_weekly_selection(selected_product, quantity_input)
                            st.rerun()
            else:
                st.info("No hay productos disponibles en esta categoría.")
            
            st.divider()

            st.subheader("💡 Productos Sugeridos")
            recommendations = get_frequent_purchases_recommendations()
            if recommendations:
                st.info("Considera añadir a tu lista:")
                for rec_product in recommendations:
                    st.write(f"- {rec_product}")
            else:
                st.info("¡Todos tus productos frecuentes ya están en la lista semanal!")

            st.divider()

            st.subheader("Tu Selección Semanal")
            if st.session_state.weekly_selections:
                sorted_selections = sorted(st.session_state.weekly_selections.items(), key=lambda item: item[1]['category'])
                grouped_selections = {}
                for product, details in sorted_selections:
                    category = details['category']
                    if category not in grouped_selections:
                        grouped_selections[category] = []
                    grouped_selections[category].append((product, details))
                
                for category, items in grouped_selections.items():
                    st.markdown(f"**{category}**")
                    for product, details in items:
                        col_disp1, col_disp2 = st.columns([0.8, 0.2])
                        with col_disp1:
                            st.write(f"- **{product}**: {details['quantity']} {details['quantity_type']}")
                        with col_disp2:
                            if st.button("➖ Quitar", key=f"remove_{product}"):
                                remove_from_weekly_selection(product)
                                st.rerun()
                
                st.divider()
                if st.button("🗑️ Limpiar Toda la Selección Semanal", key="clear_all_weekly_btn"):
                    clear_weekly_selection()
                    st.rerun()
            else:
                st.info("Tu selección semanal está vacía.")

    with tab2:
        st.header("🗂️ Gestión de Lista Maestra")
        
        with st.expander("➕ Añadir Nuevo Producto", expanded=True):
            with st.form("new_product_form", clear_on_submit=True):
                new_product_name = st.text_input("Nombre del Producto:").strip()
                new_product_category = st.text_input("Categoría:").strip()
                new_product_quantity_type = st.selectbox(
                    "Tipo de Cantidad:",
                    ["unidades", "kg", "litros", "paquetes", "gramos", "ml", "botellas", "latas", "cajas"]
                )
                submitted = st.form_submit_button("✅ Guardar Producto")
                if submitted:
                    if new_product_name and new_product_category:
                        if add_product_to_master(new_product_name, new_product_category, new_product_quantity_type):
                            st.rerun()
                    else:
                        st.error("❌ Por favor, introduce el nombre y la categoría del producto.")

        st.divider()

        st.subheader("📝 Editar/Eliminar Productos Existentes")
        if not st.session_state.master_list:
            st.info("Tu lista maestra está vacía. ¡Añade algunos productos!")
        else:
            for product, details in list(st.session_state.master_list.items()):
                col_p1, col_p2 = st.columns([0.8, 0.2])
                with col_p1:
                    st.write(f"**{product}** (Cat: {details['category']}, Tipo: {details['quantity_type']})")
                with col_p2:
                    if st.button("🗑️ Eliminar", key=f"delete_single_{product}"):
                        if product in st.session_state.master_list:
                            del st.session_state.master_list[product]
                        if product in st.session_state.weekly_selections:
                            del st.session_state.weekly_selections[product]
                        save_user_data()
                        st.success(f"✅ '{product}' eliminado permanentemente.")
                        st.rerun()
            
            st.divider()

            st.subheader("🔥 Zona de Peligro")
            if st.checkbox("Confirmar eliminación masiva de productos"):
                selected_to_delete = st.multiselect(
                    "Selecciona productos para eliminar masivamente:",
                    options=list(st.session_state.master_list.keys())
                )
                if st.button("🔴 Eliminar Seleccionados", disabled=not selected_to_delete):
                    for product in selected_to_delete:
                        if product in st.session_state.master_list:
                            del st.session_state.master_list[product]
                        if product in st.session_state.weekly_selections:
                            del st.session_state.weekly_selections[product]
                    save_user_data()
                    st.success("✅ Productos seleccionados eliminados.")
                    st.rerun()

            if st.checkbox("Confirmar limpieza COMPLETA de la lista maestra"):
                if st.button("🔥🔥 Limpiar TODA la Lista Maestra AHORA"):
                    st.session_state.master_list.clear()
                    st.session_state.weekly_selections.clear()
                    save_user_data()
                    st.success("✅ ¡Lista maestra y selección semanal completamente limpiadas!")
                    st.rerun()