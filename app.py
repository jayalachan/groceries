import streamlit as st
import json
import os
from datetime import datetime, timedelta
import pandas as pd

# Configuración de la página
st.set_page_config(
    page_title="🛒 Gestor de Compras",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Archivos para persistencia
MASTER_LIST_FILE = "lista_maestra.json"
WEEKLY_SELECTIONS_FILE = "selecciones_semanales.json"

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
</style>
""", unsafe_allow_html=True)

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

def get_current_week():
    """Obtener la semana actual en formato string"""
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    return monday.strftime("%Y-%m-%d")

def get_week_display(week_key):
    """Convertir la clave de semana a formato legible"""
    date = datetime.strptime(week_key, "%Y-%m-%d")
    return date.strftime("Semana del %d de %B, %Y")

def get_products_by_category(master_list):
    """Organizar productos por categoría"""
    products_by_category = {}
    for product, category in master_list.items():
        if category not in products_by_category:
            products_by_category[category] = []
        products_by_category[category].append(product)
    return products_by_category

def main():
    # Título principal
    st.markdown('<h1 class="main-header">🛒 Gestor de Compras del Supermercado</h1>', 
                unsafe_allow_html=True)
    
    # Inicializar state
    if 'master_list' not in st.session_state:
        st.session_state.master_list = load_master_list()
    
    if 'weekly_selections' not in st.session_state:
        st.session_state.weekly_selections = load_weekly_selections()
    
    if 'current_week' not in st.session_state:
        st.session_state.current_week = get_current_week()
    
    if 'current_selection' not in st.session_state:
        week_key = st.session_state.current_week
        if week_key in st.session_state.weekly_selections:
            st.session_state.current_selection = st.session_state.weekly_selections[week_key]
        else:
            st.session_state.current_selection = []
    
    # Información de la semana actual
    week_display = get_week_display(st.session_state.current_week)
    st.markdown(f'<div class="week-info">{week_display}</div>', 
                unsafe_allow_html=True)
    
    # Sidebar para controles
    with st.sidebar:
        st.header("🎛️ Controles")
        
        # Botón para nueva semana
        if st.button("🔄 Nueva Semana", help="Reinicia la selección para una nueva semana"):
            st.session_state.current_week = get_current_week()
            st.session_state.current_selection = []
            st.rerun()
        
        # Botón para guardar selección
        if st.button("💾 Guardar Selección", help="Guarda la selección actual"):
            st.session_state.weekly_selections[st.session_state.current_week] = st.session_state.current_selection
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
            st.metric("Seleccionados", selected_products, help="Productos seleccionados esta semana")
        
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
                st.session_state.current_selection = []
                save_master_list(st.session_state.master_list)
                st.success("✅ Productos seleccionados eliminados!")
                st.rerun()
        
        if st.button("🗑️ Limpiar Lista Maestra", help="Elimina todos los productos"):
            if st.session_state.master_list:
                st.session_state.master_list = {}
                st.session_state.current_selection = []
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
                selected_by_category[category].append(product)
            
            shopping_list = f"Lista de Compras - {get_week_display(st.session_state.current_week)}\n"
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
                file_name=f"lista_compras_{st.session_state.current_week}.txt",
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
                # Botones para seleccionar/deseleccionar todo
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Seleccionar Todo Visible"):
                        for products in products_by_category.values():
                            st.session_state.current_selection = list(set(st.session_state.current_selection + products))
                        st.rerun()
                with col2:
                    if st.button("❌ Deseleccionar Todo Visible"):
                        for products in products_by_category.values():
                            st.session_state.current_selection = [p for p in st.session_state.current_selection if p not in products]
                        st.rerun()
                
                # Mostrar por categorías
                for category in sorted(products_by_category.keys()):
                    products = products_by_category[category]
                    if products:
                        emoji = CATEGORY_EMOJIS.get(category, "📦")
                        selected_in_category = [p for p in products if p in st.session_state.current_selection]
                        
                        st.markdown(f'<div class="category-header">{emoji} {category} ({len(selected_in_category)}/{len(products)})</div>', 
                                    unsafe_allow_html=True)
                        
                        # Botones para categoría específica
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button(f"✅ Seleccionar {category}", key=f"select_cat_{category}"):
                                st.session_state.current_selection = list(set(st.session_state.current_selection + products))
                                st.rerun()
                        with col2:
                            if st.button(f"❌ Deseleccionar {category}", key=f"deselect_cat_{category}"):
                                st.session_state.current_selection = [p for p in st.session_state.current_selection if p not in products]
                                st.rerun()
                        
                        # Lista de productos con checkboxes
                        for product in sorted(products):
                            col1, col2 = st.columns([4, 1])
                            with col1:
                                is_selected = product in st.session_state.current_selection
                                checkbox_key = f"checkbox_{product}"
                                
                                if st.checkbox(
                                    product, 
                                    value=is_selected, 
                                    key=checkbox_key,
                                    help=f"{'✅ Seleccionado' if is_selected else '⬜ No seleccionado'}"
                                ):
                                    if product not in st.session_state.current_selection:
                                        st.session_state.current_selection.append(product)
                                else:
                                    if product in st.session_state.current_selection:
                                        st.session_state.current_selection.remove(product)
                            
                            with col2:
                                if st.button("🗑️", key=f"delete_{product}", help=f"Eliminar '{product}' de la lista maestra"):
                                    del st.session_state.master_list[product]
                                    if product in st.session_state.current_selection:
                                        st.session_state.current_selection.remove(product)
                                    save_master_list(st.session_state.master_list)
                                    st.rerun()
                        
                        st.divider()
            else:
                st.info("No se encontraron productos que coincidan con tu búsqueda.")
        
        with tab2:
            st.header("Lista Maestra de Productos")
            
            if st.session_state.master_list:
                # Mostrar productos en formato de tabla
                products_data = []
                for product, category in st.session_state.master_list.items():
                    emoji = CATEGORY_EMOJIS.get(category, "📦")
                    products_data.append({
                        'Producto': product,
                        'Categoría': f"{emoji} {category}",
                        'En lista actual': '✅' if product in st.session_state.current_selection else '⬜'
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
                            if product_to_edit in st.session_state.current_selection:
                                st.session_state.current_selection.remove(product_to_edit)
                                st.session_state.current_selection.append(new_name)
                            
                            save_master_list(st.session_state.master_list)
                            st.success(f"✅ Producto actualizado!")
                            st.rerun()
            else:
                st.info("No hay productos en la lista maestra.")
        
        with tab3:
            st.header("Historial de Compras")
            
            if st.session_state.weekly_selections:
                # Mostrar historial
                for week_key in sorted(st.session_state.weekly_selections.keys(), reverse=True):
                    week_display = get_week_display(week_key)
                    products = st.session_state.weekly_selections[week_key]
                    
                    with st.expander(f"{week_display} ({len(products)} productos)"):
                        if products:
                            # Organizar por categorías
                            products_by_category = {}
                            for product in products:
                                category = st.session_state.master_list.get(product, "Otro")
                                if category not in products_by_category:
                                    products_by_category[category] = []
                                products_by_category[category].append(product)
                            
                            # Crear texto para copiar
                            copy_text = f"{week_display}\n{'='*50}\n\n"
                            
                            for category in sorted(products_by_category.keys()):
                                emoji = CATEGORY_EMOJIS.get(category, "📦")
                                copy_text += f"{emoji} {category.upper()}\n"
                                for product in sorted(products_by_category[category]):
                                    copy_text += f"• {product}\n"
                                copy_text += "\n"  # Salto de línea después de cada categoría
                            
                            # Mostrar visualmente
                            for category in sorted(products_by_category.keys()):
                                emoji = CATEGORY_EMOJIS.get(category, "📦")
                                st.write(f"**{emoji} {category}**")
                                for product in sorted(products_by_category[category]):
                                    st.write(f"• {product}")
                                st.write("")
                            
                            # Botón para copiar al portapapeles
                            if st.button("📋 Copiar lista al portapapeles", key=f"copy_{week_key}"):
                                st.session_state.copied_text = copy_text
                                st.success("¡Lista copiada al portapapeles! Puedes pegarla en WhatsApp o donde la necesites.")
                            
                            # Mostrar el texto que se copiará (opcional)
                            st.text_area("Texto a copiar:", value=copy_text, height=300, key=f"text_{week_key}")
                            
                            # Botón de descarga como alternativa
                            st.download_button(
                                label="📥 Descargar Lista",
                                data=copy_text,
                                file_name=f"historial_compras_{week_key}.txt",
                                mime="text/plain",
                                key=f"download_{week_key}"
                            )
                        else:
                            st.write("No se seleccionaron productos esta semana.")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button(f"🔄 Reutilizar selección", key=f"reuse_{week_key}"):
                                st.session_state.current_selection = products.copy()
                                st.success("✅ Selección reutilizada!")
                                st.rerun()
                        
                        with col2:
                            if st.button(f"🗑️ Eliminar", key=f"delete_{week_key}"):
                                del st.session_state.weekly_selections[week_key]
                                save_weekly_selections(st.session_state.weekly_selections)
                                st.success("✅ Registro eliminado!")
                                st.rerun()
            else:
                st.info("No hay historial de compras guardado.")



if __name__ == "__main__":
    main()