import streamlit as st
import json
import os
import secrets
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests
from collections import Counter # Para las recomendaciones

# --- Configuración de OAuth de Google ---
CLIENT_SECRETS_FILE = "client_secret.json" # Asegúrate de que este archivo esté en la misma carpeta
SCOPES = ['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile']

# Usar un puerto dinámico si es necesario, o un puerto fijo como 8501
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8501") # Asegúrate de que este coincida con lo configurado en Google Cloud

# Verificar si el archivo client_secret.json existe
if not os.path.exists(CLIENT_SECRETS_FILE):
    st.error(f"❌ Error: El archivo '{CLIENT_SECRETS_FILE}' no se encontró. Necesitas configurar tus credenciales de Google OAuth. Consulta el README o la documentación para obtener instrucciones.")
    st.stop() # Detener la aplicación si las credenciales no están

# --- Inicialización de st.session_state ---
# Es importante inicializar estas variables para que Streamlit sepa de su existencia
# y mantenga su estado entre reruns.
if 'user_email' not in st.session_state:
    st.session_state.user_email = None
if 'user_info' not in st.session_state:
    st.session_state.user_info = None
if 'master_list' not in st.session_state:
    st.session_state.master_list = {}
if 'weekly_selections' not in st.session_state:
    st.session_state.weekly_selections = {}
if 'current_selection' not in st.session_state: # Para la selección de eliminación masiva en lista maestra
    st.session_state.current_selection = []
if 'current_selection_data' not in st.session_state: # No se usa directamente con la nueva UI de eliminación masiva
    st.session_state.current_selection_data = {}
if 'current_category_filter' not in st.session_state: # Filtro de categoría en selección semanal
    st.session_state.current_category_filter = 'Todas'
if 'all_users_data' not in st.session_state: # Contiene todos los datos cargados del JSON
    st.session_state.all_users_data = {}

# Nombre del archivo para guardar todos los datos de los usuarios
ALL_USERS_DATA_FILE = "all_users_data.json"

# --- Funciones de Gestión de Datos (similares a data_manager.py) ---
def load_all_users_data():
    """Carga todos los datos de los usuarios desde el archivo JSON."""
    try:
        if os.path.exists(ALL_USERS_DATA_FILE):
            with open(ALL_USERS_DATA_FILE, 'r', encoding='utf-8') as f:
                st.session_state.all_users_data = json.load(f)
        else:
            st.session_state.all_users_data = {}
            # Crear un archivo JSON vacío si no existe
            with open(ALL_USERS_DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump({}, f)
    except json.JSONDecodeError:
        st.error("❌ Error al decodificar el archivo de datos. Parece que está corrupto. Se inicializará con datos vacíos.")
        st.session_state.all_users_data = {}
        # Intentar sobrescribir el archivo corrupto con uno vacío para evitar futuros errores
        with open(ALL_USERS_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f)
    except Exception as e:
        st.error(f"❌ Error inesperado al cargar los datos: {e}. Se inicializará con datos vacíos.")
        st.session_state.all_users_data = {}
        # Intentar sobrescribir el archivo para evitar futuros errores
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
        # Si el usuario es nuevo o no tiene datos, inicializa vacíos
        st.session_state.master_list = {}
        st.session_state.weekly_selections = {}
        # Y asegúrate de que haya una entrada para este usuario en all_users_data
        if email:
            st.session_state.all_users_data[email] = {
                'master_list': {},
                'weekly_selections': {}
            }
            save_all_users_data() # Guardar el nuevo usuario en el archivo

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

# Cargar todos los datos al inicio de la aplicación
load_all_users_data()

# --- Funciones de Autenticación de Google (similares a auth_manager.py) ---
def google_oauth_login():
    """
    Inicia el flujo de autenticación de Google OAuth.
    """
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent' # Fuerza la pantalla de consentimiento para obtener refresh_token
    )
    st.session_state['oauth_state'] = state
    st.markdown(f'<a href="{authorization_url}" target="_self" style="display: inline-block; padding: 10px 20px; background-color: #4285F4; color: white; text-align: center; text-decoration: none; border-radius: 5px; font-weight: bold;">Iniciar sesión con Google</a>', unsafe_allow_html=True)

def handle_oauth_callback():
    """
    Maneja el callback de la autenticación de Google después de que el usuario aprueba.
    Retorna True si el inicio de sesión fue exitoso, False si hubo un error, y None si no hay callback.
    """
    query_params = st.query_params

    if 'code' in query_params and 'state' in query_params and query_params['state'] == st.session_state.get('oauth_state'):
        code = query_params['code']
        state_param = query_params['state']

        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            state=state_param,
            redirect_uri=REDIRECT_URI
        )

        try:
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            id_info = id_token.verify_oauth2_token(
                credentials.id_token, requests.Request(), flow.client_config['web']['client_id'])
            
            st.session_state.user_email = id_info['email']
            st.session_state.user_info = id_info
            
            st.success(f"¡Inicio de sesión exitoso como {st.session_state.user_email}!")
            st.query_params.clear() # Limpiar los parámetros de la URL
            return True

        except Exception as e:
            st.error(f"Error durante el manejo de la autenticación de Google: {e}. Por favor, inténtalo de nuevo.")
            if 'oauth_state' in st.session_state:
                del st.session_state['oauth_state']
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
    return None # No hay callback para procesar

def logout():
    """
    Cierra la sesión del usuario, limpiando todas las variables de sesión relevantes.
    """
    st.session_state.user_email = None
    st.session_state.user_info = None
    # Asegurarse de que las listas de datos del usuario también se limpien al cerrar sesión
    st.session_state.master_list = {}
    st.session_state.weekly_selections = {}
    st.session_state.current_selection = []
    st.session_state.current_selection_data = {}
    st.session_state.current_category_filter = 'Todas'
    if 'oauth_state' in st.session_state:
        del st.session_state['oauth_state']
    st.success("Sesión cerrada correctamente.")
    st.rerun() # Recargar la aplicación para reflejar el estado de no logueado

# --- Funciones de Lógica de la Aplicación (similares a app_logic.py) ---
def add_product_to_master(name, category, quantity_type):
    """
    Añade un nuevo producto a la lista maestra del usuario.
    Retorna True si se añadió, False si no (por ejemplo, si ya existe o el nombre está vacío).
    """
    name = name.strip()
    if not name:
        st.warning("El nombre del producto no puede estar vacío.")
        return False
    if name in st.session_state.master_list:
        st.warning("⚠️ ¡Este producto ya existe en tu lista maestra! Considera usar un nombre diferente o actualizar el existente.")
        return False
    
    st.session_state.master_list[name] = {
        "category": category,
        "quantity_type": quantity_type
    }
    save_user_data()
    st.success(f"✅ '{name}' añadido a la lista maestra.")
    return True

def add_to_weekly_selection(product_name, quantity):
    """
    Añade o actualiza un producto en la selección semanal del usuario.
    """
    if product_name not in st.session_state.master_list:
        st.error(f"Error: '{product_name}' no se encontró en tu lista maestra. Por favor, añádelo primero.")
        return

    if product_name not in st.session_state.weekly_selections:
        st.session_state.weekly_selections[product_name] = {
            "quantity": 0,
            "category": st.session_state.master_list[product_name]["category"],
            "quantity_type": st.session_state.master_list[product_name]["quantity_type"]
        }
    st.session_state.weekly_selections[product_name]["quantity"] += quantity
    save_user_data()
    st.success(f"➕ '{product_name}' actualizado en la selección semanal ({st.session_state.weekly_selections[product_name]['quantity']} {st.session_state.weekly_selections[product_name]['quantity_type']}).")

def remove_from_weekly_selection(product_name):
    """
    Elimina un producto de la selección semanal del usuario.
    """
    if product_name in st.session_state.weekly_selections:
        del st.session_state.weekly_selections[product_name]
        save_user_data()
        st.success(f"➖ '{product_name}' eliminado de la selección semanal.")
    else:
        st.info(f"'{product_name}' no estaba en la selección semanal.")

def clear_weekly_selection():
    """
    Limpia completamente la selección semanal del usuario.
    """
    st.session_state.weekly_selections = {}
    save_user_data()
    st.success("✅ Lista de selección semanal limpiada.")

def get_master_list_categories():
    """
    Retorna una lista de todas las categorías únicas en la lista maestra.
    """
    return sorted(list(set([details['category'] for details in st.session_state.master_list.values()])))

def get_filtered_master_products(filter_category='Todas'):
    """
    Retorna una lista de productos de la lista maestra, opcionalmente filtrada por categoría.
    """
    if filter_category == 'Todas':
        return sorted(list(st.session_state.master_list.keys()))
    else:
        return sorted([
            p for p in st.session_state.master_list.keys()
            if st.session_state.master_list[p]['category'] == filter_category
        ])

def get_frequent_purchases_recommendations(num_recommendations=5):
    """
    Genera recomendaciones básicas de productos de la lista maestra que no están
    en la selección semanal actual. Esto es más un recordatorio que una recomendación compleja.
    """
    potential_recommendations = []
    for product_name in st.session_state.master_list.keys():
        if product_name not in st.session_state.weekly_selections:
            potential_recommendations.append(product_name)

    return sorted(potential_recommendations)[:num_recommendations]

# --- Interfaz de Usuario de Streamlit ---
st.set_page_config(
    page_title="Gestor de Compras Inteligente",
    page_icon="🛒",
    layout="centered"
)

st.title("🛒 Gestor de Compras Inteligente")

# --- Lógica de Autenticación y Carga/Guardado ---
# Intenta manejar el callback de OAuth si hay parámetros en la URL
auth_success = handle_oauth_callback()
if auth_success:
    # Si el inicio de sesión fue exitoso, carga los datos específicos del usuario
    load_user_data()
    st.rerun() # Recargar para asegurar que la UI se actualice con los datos del usuario logueado
elif auth_success is False: # Hubo un error en el callback
    st.stop() # Detener la ejecución si hubo un error crítico en el auth

# --- Renderizado Condicional de la UI ---
if not st.session_state.user_email:
    # Si el usuario no está logueado, muestra el botón de inicio de sesión
    st.info("Por favor, inicia sesión con Google para usar la aplicación.")
    google_oauth_login()
else:
    # Si el usuario está logueado, muestra la aplicación principal
    user_name = st.session_state.user_info.get('name', st.session_state.user_email)
    st.sidebar.success(f"¡Hola, {user_name}! 👋")
    if st.sidebar.button("Cerrar Sesión", on_click=logout):
        pass # La función `logout` ya maneja el `rerun`

    # Tabs de navegación
    tab1, tab2 = st.tabs(["🛍️ Selección Semanal", "🗂️ Gestión de Lista Maestra"])

    with tab1:
        st.header("🛍️ Selección Semanal")

        master_list = st.session_state.master_list
        weekly_selections = st.session_state.weekly_selections

        if not master_list:
            st.warning("Tu lista maestra está vacía. ¡Ve a la pestaña 'Gestión de Lista Maestra' para añadir productos!")
        else:
            categories = get_master_list_categories()
            categories.insert(0, 'Todas')
            
            st.session_state.current_category_filter = st.selectbox(
                "Filtrar por Categoría:",
                categories,
                key="category_filter",
                index=categories.index(st.session_state.current_category_filter)
            )

            # Mostrar productos para añadir a la selección semanal
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
                    quantity_type = master_list[selected_product]['quantity_type']
                    with col2:
                        quantity_input = st.number_input(
                            f"Cantidad ({quantity_type}):",
                            min_value=1,
                            value=1,
                            key="quantity_input"
                        )
                    with col3:
                        st.write("") # Espaciador
                        st.write("") # Espaciador
                        if st.button("➕ Añadir", key="add_to_weekly_btn"):
                            add_to_weekly_selection(selected_product, quantity_input)
                            st.rerun()
            else:
                st.info("No hay productos disponibles en esta categoría o en la lista maestra.")

            st.divider()

            # --- Recomendaciones (mejora simple) ---
            st.subheader("💡 Productos Sugeridos")
            recommendations = get_frequent_purchases_recommendations(num_recommendations=5)
            if recommendations:
                st.info("Considera añadir a tu lista:")
                for rec_product in recommendations:
                    st.write(f"- {rec_product}")
            else:
                st.info("No hay sugerencias por ahora. Añade más productos a tu lista maestra y selección semanal para ver sugerencias aquí.")
            
            st.divider()

            # Mostrar selección semanal
            st.subheader("Tu Selección Semanal")
            if weekly_selections:
                sorted_selections = sorted(weekly_selections.items(), key=lambda item: item[1]['category'])
                
                # Agrupar por categoría para una mejor visualización
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
                st.subheader("Opciones de la Selección Semanal")
                
                confirm_clear_weekly = st.checkbox("Confirmar limpieza de toda la selección semanal", key="confirm_clear_weekly_checkbox")
                if confirm_clear_weekly:
                    if st.button("🗑️ Limpiar Toda la Selección Semanal AHORA", key="clear_all_weekly_btn"):
                        clear_weekly_selection()
                        st.rerun()
                else:
                    st.info("Marca la casilla para habilitar el botón de limpieza de la selección semanal.")
            else:
                st.info("Tu selección semanal está vacía.")

    with tab2:
        st.header("🗂️ Gestión de Lista Maestra")
        
        # Añadir nuevo producto
        st.subheader("➕ Añadir Nuevo Producto")
        new_product_name = st.text_input("Nombre del Producto:", key="new_product_name_input").strip()
        
        # Validación de existencia para feedback inmediato
        if new_product_name and new_product_name in st.session_state.master_list:
            st.warning("⚠️ ¡Este producto ya existe en tu lista maestra! Considera usar un nombre diferente o actualizar el existente.")

        new_product_category = st.text_input("Categoría:", key="new_product_category_input").strip()
        new_product_quantity_type = st.selectbox(
            "Tipo de Cantidad:",
            ["unidades", "kg", "litros", "paquetes", "gramos", "ml", "botellas", "latas", "cajas"],
            key="new_product_quantity_type_select"
        )
        if st.button("✅ Guardar Producto", key="save_new_product_btn"):
            if new_product_name and new_product_category:
                if add_product_to_master(new_product_name, new_product_category, new_product_quantity_type):
                    # Limpiar los campos después de añadir para una mejor UX
                    st.session_state.new_product_name_input = "" 
                    st.session_state.new_product_category_input = ""
                    st.rerun() # Recargar para reflejar la lista actualizada y limpiar inputs
            else:
                st.error("❌ Por favor, introduce el nombre y la categoría del producto.")

        st.divider()

        # Mostrar y gestionar productos existentes
        st.subheader("📝 Editar/Eliminar Productos Existentes")
        master_list_display = st.session_state.master_list.copy()

        if not master_list_display:
            st.info("Tu lista maestra está vacía. ¡Añade algunos productos!")
        else:
            all_categories = get_master_list_categories()
            all_categories.insert(0, 'Todas')
            
            filter_category_master = st.selectbox(
                "Filtrar lista maestra por Categoría:",
                all_categories,
                key="filter_master_category"
            )

            # Filtrar productos para mostrar
            filtered_products_for_display = get_filtered_master_products(filter_category_master)

            if filtered_products_for_display:
                st.markdown("---")
                st.markdown("### Selecciona productos para eliminar masivamente:")
                
                # Usar un set para un manejo más eficiente de la selección múltiple
                selected_products_set = set(st.session_state.current_selection)

                # Mostrar productos con checkboxes para selección y botón de eliminación individual
                for product in filtered_products_for_display:
                    col_p1, col_p2, col_p3 = st.columns([0.6, 0.2, 0.2]) # Columna 3 reservada por si se quiere añadir editar
                    
                    is_selected = product in selected_products_set
                    
                    with col_p1:
                        checkbox_state = st.checkbox(
                            f"**{product}** (Cat: {master_list_display[product]['category']}, Tipo: {master_list_display[product]['quantity_type']})",
                            value=is_selected,
                            key=f"select_to_delete_{product}"
                        )
                    
                    # Actualizar el set de selección basada en el checkbox
                    if checkbox_state and not is_selected:
                        selected_products_set.add(product)
                    elif not checkbox_state and is_selected:
                        selected_products_set.discard(product)

                    # Botón para eliminar un solo producto
                    with col_p2:
                        if st.button(f"🗑️ Eliminar", key=f"delete_single_{product}"):
                            if product in st.session_state.master_list:
                                del st.session_state.master_list[product]
                                # También eliminarlo de la selección semanal si está ahí
                                if product in st.session_state.weekly_selections:
                                    del st.session_state.weekly_selections[product]
                                selected_products_set.discard(product) # Asegurar que no esté en la selección
                                save_user_data()
                                st.success(f"✅ '{product}' eliminado de la lista maestra y de la selección semanal.")
                                st.rerun()
                
                # Actualizar la lista de selección en st.session_state
                st.session_state.current_selection = list(selected_products_set)

                st.markdown("---")

                # Opciones para la selección actual (eliminación masiva)
                if st.session_state.current_selection:
                    st.subheader("Opciones de Productos Seleccionados")
                    st.warning(f"⚠️ Estás a punto de eliminar permanentemente **{len(st.session_state.current_selection)}** productos seleccionados de tu lista maestra. Esta acción no se puede deshacer.")
                    
                    confirm_delete_selected = st.checkbox("Confirmar eliminación de productos seleccionados", key="confirm_delete_selected_checkbox")
                    
                    if confirm_delete_selected:
                        if st.button("🔴 Eliminar TODOS los Seleccionados AHORA", key="delete_all_selected_confirmed"):
                            products_to_delete_from_master = st.session_state.current_selection.copy()
                            for product in products_to_delete_from_master:
                                if product in st.session_state.master_list:
                                    del st.session_state.master_list[product]
                                # También eliminarlo de la selección semanal si está ahí
                                if product in st.session_state.weekly_selections:
                                    del st.session_state.weekly_selections[product]
                            st.session_state.current_selection_data = {} # Limpia la selección actual
                            st.session_state.current_selection = [] # Actualiza la lista de seleccionados
                            save_user_data()
                            st.success("✅ Productos seleccionados eliminados de la lista maestra y de la selección semanal!")
                            st.rerun()
                    else:
                        st.info("Marca la casilla para habilitar el botón de eliminación masiva.")
                else:
                    st.info("No hay productos seleccionados para acciones masivas.")

            else:
                st.info("No hay productos en esta categoría en tu lista maestra.")

            st.divider()

            # --- Limpiar Toda la Lista Maestra (con confirmación) ---
            st.subheader("🗑️ Limpiar Toda la Lista Maestra")
            st.warning("⚠️ Esta acción eliminará **TODOS** los productos de tu lista maestra. ¡Úsala con extrema precaución!")
            
            confirm_clear_master = st.checkbox("Confirmar limpieza completa de la lista maestra", key="confirm_clear_master_checkbox")

            if confirm_clear_master:
                if st.button("🔥 Limpiar TODA la Lista Maestra AHORA", key="clear_master_confirmed"):
                    if st.session_state.master_list:
                        st.session_state.master_list.clear() # Vacía el diccionario
                        st.session_state.weekly_selections.clear() # También limpia la selección semanal asociada
                        st.session_state.current_selection_data = {}
                        st.session_state.current_selection = []
                        save_user_data()
                        st.success("✅ ¡Lista maestra y selección semanal completamente limpiadas!")
                        st.rerun()
                    else:
                        st.info("La lista maestra ya está vacía.")
            else:
                st.info("Marca la casilla para habilitar el botón de limpieza total.")