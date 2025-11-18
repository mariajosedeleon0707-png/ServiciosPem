import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import sqlite3
import json
import datetime 
import pandas as pd 
from PIL import Image 

# --- Configuración de la apariencia ---
# ⭐️ CAMBIO: Se establece el modo "Light" para tener un fondo blanco
ctk.set_appearance_mode("Light") 
ctk.set_default_color_theme("blue")

# --- Constantes y Configuración de DB ---
DB_NAME = "reportes_camiones.db"
# Definición de los ítems del checklist (Tomado del formato PEM 360)
CHECKLIST_ITEMS = [
    ("Niveles", ["Líquido refrigerante", "Líquido de frenos", "Nivel de aceite", "Nivel líquido hidráulico", "Depósito limpiaparabrisas"]),
    ("Pedales", ["Acelerador", "Embrague (clutch)", "Freno (agarre/firmeza)"]),
    ("Luces", ["Luces (alta, media y baja)", "Direccionales", "Emergencia", "Luces de freno", "Testigos de tablero", "Luz de reversa", "Luz interior cabina"]),
    ("Equipo", ["Llanta de repuesto", "Triángulos/conos", "Llave de pernos", "Tricket"]),
    ("General", ["Llantas (presión, desgaste)", "Batería (Estado borner, corrosión)", "Parabrisas", "Aros (golpes o fisuras)", "Cinturones de Seguridad", "Espejos", "Freno de Mano", "Retrovisores", "Plumillas/Limpiabrisas", "Bocina"]),
    ("Audio", ["Amplificador", "Radio", "Memoria (Spots y/o música)", "Micrófono", "Bocinas exteriores"]),
    ("Imagen", ["Pintura", "Faldones", "Valla (ambos lados)"])
]

def inicializar_db():
    """Crea las tablas necesarias y usuarios por defecto."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Tabla de usuarios (con el ID del vehículo asignado)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        full_name TEXT,
        role TEXT NOT NULL DEFAULT 'piloto',
        is_active INTEGER NOT NULL DEFAULT 1, 
        assigned_vehicle_plate TEXT, 
        FOREIGN KEY (assigned_vehicle_plate) REFERENCES vehicles (plate)
    )
    """)
    
    # 2. Tabla de vehículos (Catálogo de vehículos)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vehicles (
        plate TEXT PRIMARY KEY NOT NULL, 
        brand TEXT,
        promotion TEXT, 
        assigned_to_user_id INTEGER, 
        FOREIGN KEY (assigned_to_user_id) REFERENCES users (id)
    )
    """)

    # 3. Tabla de reportes de inspección
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        driver_id INTEGER NOT NULL,
        report_date TEXT NOT NULL,
        vehicle_plate TEXT,
        km_actual TEXT,
        header_data TEXT,
        checklist_data TEXT,
        observations TEXT,
        signature_confirmation TEXT,
        FOREIGN KEY (driver_id) REFERENCES users (id)
    )
    """)
    
    # Crear usuario Admin de ejemplo si no existe
    try:
        cursor.execute("INSERT INTO users (username, password, full_name, role) VALUES (?, ?, ?, ?)", 
                       ("admin", "super", "Administrador", "admin"))
    except sqlite3.IntegrityError:
        pass 
        
    # Crear usuario Piloto de ejemplo si no existe
    try:
        cursor.execute("INSERT INTO users (username, password, full_name, role, assigned_vehicle_plate) VALUES (?, ?, ?, ?, ?)", 
                       ("piloto1", "1234", "Juan Pérez", "piloto", "C123456"))
    except sqlite3.IntegrityError:
        pass 
        
    # Crear vehículo de ejemplo si no existe y asignarlo al piloto1
    try:
        # Buscamos el ID del piloto1
        cursor.execute("SELECT id FROM users WHERE username = 'piloto1'")
        piloto1_id_result = cursor.fetchone()
        if piloto1_id_result:
            piloto1_id = piloto1_id_result[0]
            cursor.execute("INSERT INTO vehicles (plate, brand, promotion, assigned_to_user_id) VALUES (?, ?, ?, ?)", 
                           ("C123456", "FOTON", "Promo A (Lanzamiento)", piloto1_id))
    except sqlite3.IntegrityError:
        pass

    conn.commit()
    conn.close()

# --- Ventana de Detalles de Reporte (Para Admin) ---

class ReportDetailWindow(ctk.CTkToplevel):
    def __init__(self, master, report_data):
        super().__init__(master)
        self.title(f"Detalles del Reporte ID: {report_data['ID']}")
        self.geometry("700x600")
        self.transient(master)  
        self.report_data = report_data
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.scrollable_frame = ctk.CTkScrollableFrame(self)
        self.scrollable_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.scrollable_frame.grid_columnconfigure(0, weight=1)

        self.display_report()

    def create_detail_label(self, parent, text, value, row, column=0, font_size=14, weight="normal"):
        """Función auxiliar para crear etiquetas de detalle."""
        label_text = f"{text}:"
        label = ctk.CTkLabel(parent, text=label_text, font=ctk.CTkFont(size=font_size, weight="bold"))
        label.grid(row=row, column=column, padx=10, pady=(5, 0), sticky="nw")
        
        value_label = ctk.CTkLabel(parent, text=value, font=ctk.CTkFont(size=font_size, weight=weight), wraplength=500, justify="left")
        value_label.grid(row=row, column=column + 1, padx=10, pady=(5, 0), sticky="nw")

    def display_report(self):
        """Muestra la información detallada del reporte."""
        
        # --- Sección de Encabezado ---
        header = self.report_data['header_data']
        header_frame = ctk.CTkFrame(self.scrollable_frame, border_width=2)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        header_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(header_frame, text="Detalles del Vehículo y Piloto", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=2, pady=10)

        row_counter = 1
        # Mapeo de campos técnicos a nombres amigables
        field_map = {
            "placa": "Placa", "marca": "Marca", "promocion": "Promoción", "fecha": "Fecha", 
            "km_actual": "Km Actual", "piloto_nombre": "Piloto", "piloto_id": "ID Piloto"
        }
        
        for key, display_name in field_map.items():
            value = header.get(key, 'N/A')
            self.create_detail_label(header_frame, display_name, str(value), row_counter, 0)
            row_counter += 1

        # --- Sección de Checklist ---
        checklist_data = self.report_data['checklist_data']
        checklist_frame = ctk.CTkFrame(self.scrollable_frame, border_width=2)
        checklist_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        checklist_frame.grid_columnconfigure(0, weight=3)
        checklist_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(checklist_frame, text="Checklist de Inspección", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=2, pady=10)
        
        # Encabezados de la tabla
        ctk.CTkLabel(checklist_frame, text="Item", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, sticky="w", padx=10)
        ctk.CTkLabel(checklist_frame, text="Resultado", font=ctk.CTkFont(weight="bold")).grid(row=1, column=1, sticky="w", padx=10)
        
        row_counter = 2
        
        # Reagrupar los ítems por categoría para una mejor visualización
        categorized_checklist = {}
        for cat, items in CHECKLIST_ITEMS:
            for item in items:
                if item in checklist_data:
                    if cat not in categorized_checklist:
                        categorized_checklist[cat] = {}
                    categorized_checklist[cat][item] = checklist_data[item]

        for categoria, items in categorized_checklist.items():
            # Etiqueta de Categoría
            ctk.CTkLabel(checklist_frame, text=f"--- {categoria.upper()} ---", 
                         font=ctk.CTkFont(weight="bold", size=13), text_color="gray").grid(row=row_counter, column=0, columnspan=2, sticky="w", padx=10, pady=(5, 0))
            row_counter += 1

            for item, status in items.items():
                ctk.CTkLabel(checklist_frame, text=item, anchor="w").grid(row=row_counter, column=0, sticky="w", padx=10, pady=2)
                
                # Color del estado: N/A en azul
                color = "green" if status == "Buen estado" else "red" if status == "Mal estado" else "blue"
                ctk.CTkLabel(checklist_frame, text=status, text_color=color, font=ctk.CTkFont(weight="bold")).grid(row=row_counter, column=1, sticky="w", padx=10, pady=2)
                row_counter += 1

        # --- Sección de Observaciones y Confirmación ---
        obs_conf_frame = ctk.CTkFrame(self.scrollable_frame, border_width=2)
        obs_conf_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        obs_conf_frame.grid_columnconfigure(0, weight=1)

        # Observaciones
        ctk.CTkLabel(obs_conf_frame, text="Observaciones", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 5))
        obs_text = self.report_data['observations'] if self.report_data['observations'] else "Sin observaciones adicionales."
        ctk.CTkLabel(obs_conf_frame, text=obs_text, justify="left", wraplength=600).grid(row=1, column=0, sticky="w", padx=10, pady=(0, 10))

        # Confirmación
        ctk.CTkLabel(obs_conf_frame, text="Confirmación de Piloto (Firma)", font=ctk.CTkFont(size=16, weight="bold")).grid(row=2, column=0, sticky="w", padx=10, pady=(10, 5))
        ctk.CTkLabel(obs_conf_frame, text=self.report_data['signature_confirmation'], justify="left", wraplength=600, text_color="green").grid(row=3, column=0, sticky="w", padx=10, pady=(0, 10))


# --- Clase de la Interfaz de Administración ---

class AdminFrame(ctk.CTkFrame):
    def __init__(self, master, app_instance):
        super().__init__(master)
        self.app = app_instance
        self.grid(row=0, column=0, sticky="nsew") 
        self.grid_columnconfigure(0, weight=1)
        
        # --- Frame del encabezado (para el logo y el botón de Logout) ---
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 0))
        header_frame.grid_columnconfigure(0, weight=0) # Logo
        header_frame.grid_columnconfigure(1, weight=1) # Título
        header_frame.grid_columnconfigure(2, weight=0) # Botón Logout

        # ⭐️ Logo en Admin
        if self.app.logo_image:
            ctk.CTkLabel(header_frame, text="", image=self.app.logo_image).grid(row=0, column=0, rowspan=2, padx=(0, 15), sticky="w")
        
        # Título 
        ctk.CTkLabel(header_frame, text=f"Administrador: {self.app.current_user_name}", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=1, sticky="w")
        
        # Botón de Cerrar Sesión 
        ctk.CTkButton(header_frame, text="Cerrar Sesión", command=self.app.logout, fg_color="darkred", hover_color="red").grid(row=0, column=2, sticky="e")


        # Crear Tabs (Empiezan en la fila 1)
        self.tabview = ctk.CTkTabview(self, width=850, height=650)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)
        
        self.tabview.add("Gestión de Pilotos")
        self.tabview.add("Gestión de Vehículos") 
        self.tabview.add("Revisión de Reportes")
        
        self.setup_pilot_management_tab()
        self.setup_vehicle_management_tab() 
        self.setup_report_review_tab()

    # --- Pestaña de Gestión de Pilotos ---

    def setup_pilot_management_tab(self):
        tab = self.tabview.tab("Gestión de Pilotos")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        # Frame para la tabla de usuarios
        self.pilot_table_frame = ctk.CTkScrollableFrame(tab, label_text="Usuarios del Sistema")
        self.pilot_table_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.pilot_table_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1) 

        # Frame para las acciones (Añadir/Editar/Desactivar/Eliminar)
        action_frame = ctk.CTkFrame(tab, border_width=1)
        action_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        action_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6), weight=1) 

        ctk.CTkLabel(action_frame, text="ID Usuario (Editar/Desactivar/Eliminar):").grid(row=0, column=0, padx=5, pady=5)
        self.entry_user_id = ctk.CTkEntry(action_frame, width=50)
        self.entry_user_id.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        ctk.CTkLabel(action_frame, text="Nombre Completo:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.entry_full_name = ctk.CTkEntry(action_frame)
        self.entry_full_name.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(action_frame, text="Usuario (login):").grid(row=1, column=3, padx=5, pady=5, sticky="w")
        self.entry_username = ctk.CTkEntry(action_frame)
        self.entry_username.grid(row=1, column=4, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(action_frame, text="Contraseña:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.entry_password = ctk.CTkEntry(action_frame)
        self.entry_password.grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky="ew")

        # Botones de Acción
        ctk.CTkButton(action_frame, text="Añadir Nuevo Piloto", command=lambda: self.manage_user("add")).grid(row=3, column=0, padx=5, pady=10, sticky="ew")
        ctk.CTkButton(action_frame, text="Actualizar Datos", command=lambda: self.manage_user("update")).grid(row=3, column=1, padx=5, pady=10, sticky="ew")
        ctk.CTkButton(action_frame, text="Desactivar", fg_color="red", command=lambda: self.toggle_user_status(0)).grid(row=3, column=3, padx=5, pady=10, sticky="ew")
        ctk.CTkButton(action_frame, text="Activar", fg_color="green", command=lambda: self.toggle_user_status(1)).grid(row=3, column=4, padx=5, pady=10, sticky="ew")
        
        # Nuevo botón de ELIMINAR
        ctk.CTkButton(action_frame, text="ELIMINAR PILOTO", fg_color="darkred", hover_color="red", command=self.delete_user).grid(row=3, column=5, padx=5, pady=10, sticky="ew")
        
        self.load_pilot_data()

    def load_pilot_data(self):
        """Carga y muestra la tabla de usuarios."""
        for widget in self.pilot_table_frame.winfo_children():
            widget.destroy()

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        # Incluimos la placa asignada
        cursor.execute("SELECT id, full_name, username, role, is_active, assigned_vehicle_plate FROM users ORDER BY id")
        users = cursor.fetchall()
        conn.close()

        # Encabezados de la tabla
        headers = ["ID", "Nombre Completo", "Usuario", "Rol", "Estado", "Vehículo Asignado"]
        for col, header in enumerate(headers):
            self.pilot_table_frame.grid_columnconfigure(col, weight=1)
            ctk.CTkLabel(self.pilot_table_frame, text=header, font=ctk.CTkFont(weight="bold")).grid(row=0, column=col, padx=10, pady=5, sticky="w")

        # Filas de datos
        for row, user in enumerate(users):
            status = "ACTIVO" if user[4] == 1 else "INACTIVO (Deshabilitado)"
            status_color = "green" if user[4] == 1 else "red"
            placa = user[5] if user[5] else "Ninguno"

            # Columnas 0 a 3 (ID, Nombre, Usuario, Rol)
            for col, data in enumerate(user[:4]):
                ctk.CTkLabel(self.pilot_table_frame, text=str(data)).grid(row=row + 1, column=col, padx=10, pady=2, sticky="w")
            
            # Columna 4 (Estado)
            ctk.CTkLabel(self.pilot_table_frame, text=status, text_color=status_color, font=ctk.CTkFont(weight="bold")).grid(row=row + 1, column=4, padx=10, pady=2, sticky="w")
            
            # Columna 5 (Vehículo Asignado)
            ctk.CTkLabel(self.pilot_table_frame, text=placa).grid(row=row + 1, column=5, padx=10, pady=2, sticky="w")


    def manage_user(self, action):
        """Añade o actualiza un usuario (Piloto)."""
        user_id = self.entry_user_id.get()
        full_name = self.entry_full_name.get()
        username = self.entry_username.get()
        password = self.entry_password.get()

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        try:
            if action == "add":
                if not all([full_name, username, password]):
                    raise ValueError("Faltan datos para añadir un nuevo piloto.")
                cursor.execute("INSERT INTO users (full_name, username, password, role) VALUES (?, ?, ?, 'piloto')", 
                               (full_name, username, password))
                messagebox.showinfo("Éxito", f"Piloto '{username}' añadido correctamente.")
            
            elif action == "update":
                if not user_id:
                    raise ValueError("Ingrese un ID para actualizar.")
                
                updates = []
                params = []
                if full_name:
                    updates.append("full_name = ?")
                    params.append(full_name)
                if username:
                    updates.append("username = ?")
                    params.append(username)
                if password:
                    updates.append("password = ?")
                    params.append(password)

                if not updates:
                    raise ValueError("No hay campos para actualizar.")
                
                params.append(user_id)
                cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", tuple(params))
                
                if cursor.rowcount == 0:
                    raise ValueError(f"No se encontró usuario con ID {user_id}.")

                messagebox.showinfo("Éxito", f"Usuario ID {user_id} actualizado correctamente.")
            
            conn.commit()
            self.load_pilot_data()
            self.entry_user_id.delete(0, 'end')
            self.entry_full_name.delete(0, 'end')
            self.entry_username.delete(0, 'end')
            self.entry_password.delete(0, 'end')

        except ValueError as e:
            messagebox.showerror("Error de Validación", str(e))
        except sqlite3.IntegrityError:
            messagebox.showerror("Error de DB", f"El usuario '{username}' ya existe.")
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error inesperado: {e}")
        finally:
            conn.close()

    def toggle_user_status(self, status):
        """Activa o desactiva un usuario por ID."""
        user_id = self.entry_user_id.get()
        if not user_id:
            messagebox.showerror("Error", "Ingrese un ID de usuario para cambiar el estado.")
            return

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        try:
            # Evita desactivar al admin (ID 1 es por defecto el admin en la primera ejecución)
            cursor.execute("UPDATE users SET is_active = ? WHERE id = ? AND role = 'piloto' AND id != 1", (status, user_id))
            if cursor.rowcount == 0:
                messagebox.showerror("Error", f"No se encontró un piloto con ID {user_id} o está intentando modificar al administrador principal.")
            else:
                conn.commit()
                self.load_pilot_data()
                action = "activado" if status == 1 else "deshabilitado"
                messagebox.showinfo("Éxito", f"Piloto ID {user_id} ha sido {action}.")
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error: {e}")
        finally:
            conn.close()

    def delete_user(self):
        """Elimina un piloto solo si no tiene reportes ni vehículos asignados."""
        user_id = self.entry_user_id.get()
        if not user_id:
            messagebox.showerror("Error", "Ingrese un ID de usuario para ELIMINAR.")
            return

        if not messagebox.askyesno("Confirmar Eliminación", 
                                   f"ADVERTENCIA: ¿Está seguro de que desea ELIMINAR permanentemente al piloto ID {user_id}? "
                                   "Esto no se puede deshacer. (Recomendado solo si no tiene reportes históricos)."):
            return

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        try:
            user_id_int = int(user_id)
            
            # 1. Verificar si es el administrador
            cursor.execute("SELECT role FROM users WHERE id = ?", (user_id_int,))
            user_data = cursor.fetchone()
            if not user_data or user_data[0] == 'admin':
                raise ValueError(f"No se puede eliminar el usuario ID {user_id}. Es el administrador principal o no existe.")

            # 2. Verificar reportes existentes
            cursor.execute("SELECT COUNT(*) FROM reports WHERE driver_id = ?", (user_id_int,))
            if cursor.fetchone()[0] > 0:
                raise ValueError(f"No se puede eliminar al piloto ID {user_id_int}. Tiene reportes históricos asociados. Use 'Desactivar'.")

            # 3. Verificar vehículo asignado
            cursor.execute("SELECT assigned_vehicle_plate FROM users WHERE id = ?", (user_id_int,))
            assigned_plate = cursor.fetchone()[0]
            if assigned_plate:
                # Si está asignado, primero lo desasigna del vehículo para evitar errores de FK
                cursor.execute("UPDATE vehicles SET assigned_to_user_id = NULL WHERE assigned_to_user_id = ?", (user_id_int,))
            
            # 4. Eliminar el usuario
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id_int,))
            
            if cursor.rowcount > 0:
                conn.commit()
                messagebox.showinfo("Éxito", f"Piloto ID {user_id} ELIMINADO permanentemente.")
                self.load_pilot_data()
                self.entry_user_id.delete(0, 'end')
            else:
                raise ValueError(f"No se encontró un piloto con ID {user_id}.")

        except ValueError as e:
            messagebox.showerror("Error de Eliminación", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error inesperado: {e}")
        finally:
            conn.close()
            
    # --- Función de Validación para Placas ---
    def validate_placa(self, var):
        """Asegura que la placa comience con 'C', esté en mayúsculas y tenga un máximo de 7 caracteres."""
        current_value = var.get()
        corrected_value = current_value.upper()

        # 1. Asegurar que comience con 'C'
        if not corrected_value.startswith('C'):
            # Si el usuario intenta borrar la 'C' inicial, la reponemos o la corregimos
            corrected_value = 'C' + corrected_value.lstrip('C')
            if not corrected_value: # Si por alguna razón se queda vacío, forzar a 'C'
                corrected_value = 'C'

        # 2. Limitar a 7 caracteres (C + 6 más)
        if len(corrected_value) > 7:
            corrected_value = corrected_value[:7]

        if corrected_value != current_value:
            var.set(corrected_value)


    # --- Pestaña de Gestión de Vehículos ---

    def setup_vehicle_management_tab(self):
        tab = self.tabview.tab("Gestión de Vehículos")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        # --- Variables de Placa con Validación ---
        self.placa_var = ctk.StringVar(value="C")
        self.placa_var._trace_name = self.placa_var.trace_add("write", lambda name, index, mode, var=self.placa_var: self.validate_placa(var))
        # Se elimina self.placa_asignar_var 
        # ----------------------------------------------------


        # Frame para la tabla de vehículos
        self.vehicle_table_frame = ctk.CTkScrollableFrame(tab, label_text="Catálogo de Vehículos")
        # NOTA: Se ajusta el número de columnas a 4 (Placa, Marca, Promoción, Piloto Asignado)
        self.vehicle_table_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.vehicle_table_frame.grid_columnconfigure((0, 1, 2, 3), weight=1) 

        # Frame para las acciones (Añadir/Editar/Eliminar)
        action_frame = ctk.CTkFrame(tab, border_width=1)
        action_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        action_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1) 

        # Controles para añadir y editar vehículo
        ctk.CTkLabel(action_frame, text="Placa:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.entry_placa = ctk.CTkEntry(action_frame, width=100, textvariable=self.placa_var)
        self.entry_placa.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(action_frame, text="Marca:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.entry_marca_vehiculo = ctk.CTkEntry(action_frame, width=100)
        self.entry_marca_vehiculo.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(action_frame, text="Promoción:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.entry_promocion = ctk.CTkEntry(action_frame, width=300)
        self.entry_promocion.grid(row=1, column=1, columnspan=3, padx=5, pady=5, sticky="ew")

        # Control para eliminar (Eliminada la segunda entrada de texto para la placa de eliminación)
        # ctk.CTkLabel(action_frame, text="Eliminar Vehículo (Placa):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        # self.entry_placa_eliminar = ctk.CTkEntry(action_frame, width=100)
        # self.entry_placa_eliminar.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkButton(action_frame, text="Añadir Vehículo", command=lambda: self.manage_vehicle("add")).grid(row=0, column=5, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(action_frame, text="Actualizar Promoción/Marca", command=lambda: self.manage_vehicle("update")).grid(row=1, column=5, padx=5, pady=5, sticky="ew")
        
        # El botón de ELIMINAR sigue usando la posición anterior
        ctk.CTkButton(action_frame, text="ELIMINAR VEHÍCULO", fg_color="darkred", hover_color="red", command=self.delete_vehicle).grid(row=2, column=5, padx=5, pady=5, sticky="ew")
        
        # Se eliminaron los controles de asignación manual
        
        self.load_vehicle_data()

    def load_vehicle_data(self):
        """Carga y muestra la tabla de vehículos, incluyendo ComboBox para asignación."""
        for widget in self.vehicle_table_frame.winfo_children():
            widget.destroy()

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # --- NUEVO: Obtener lista de pilotos para el ComboBox ---
        # Se buscan solo pilotos activos
        cursor.execute("SELECT id, full_name FROM users WHERE role = 'piloto' AND is_active = 1 ORDER BY full_name")
        pilots = cursor.fetchall()
        
        # Mapeo: Nombre Completo -> ID
        # Opciones ComboBox: Lista de nombres, incluyendo "SIN ASIGNAR"
        self.pilot_id_map = {"SIN ASIGNAR": None}
        combo_options = ["SIN ASIGNAR"]
        for id, full_name in pilots:
            self.pilot_id_map[full_name] = id
            combo_options.append(full_name)
        # ----------------------------------------------------

        # Traemos todos los vehículos y el nombre del piloto asignado
        query = """
        SELECT v.plate, v.brand, v.promotion, u.id, u.full_name
        FROM vehicles v
        LEFT JOIN users u ON v.assigned_to_user_id = u.id
        ORDER BY v.plate
        """
        cursor.execute(query)
        vehicles = cursor.fetchall()
        conn.close()

        # Encabezados de la tabla (Ajustado para 4 columnas: Placa, Marca, Promoción, Piloto Asignado)
        headers = ["Placa", "Marca", "Promoción", "Piloto Asignado"] 
        for col, header in enumerate(headers):
            self.vehicle_table_frame.grid_columnconfigure(col, weight=1)
            ctk.CTkLabel(self.vehicle_table_frame, text=header, font=ctk.CTkFont(weight="bold")).grid(row=0, column=col, padx=10, pady=5, sticky="w")

        # Filas de datos
        for row, vehicle in enumerate(vehicles):
            placa, marca, promocion, piloto_id, piloto_nombre = vehicle
            
            # --- NUEVO: Usar ComboBox ---
            current_pilot_name = piloto_nombre if piloto_nombre else "SIN ASIGNAR"

            # Columnas 0 a 2 (Placa, Marca, Promoción)
            data_to_display = [placa, marca, promocion]
            
            for col, data in enumerate(data_to_display):
                ctk.CTkLabel(self.vehicle_table_frame, text=str(data), anchor="w").grid(row=row + 1, column=col, padx=10, pady=2, sticky="w")

            # Columna 3 (Piloto Asignado - ComboBox)
            combobox = ctk.CTkComboBox(self.vehicle_table_frame, values=combo_options, 
                                       command=lambda selection, plate=placa: self.update_vehicle_assignment(plate, selection))
            combobox.set(current_pilot_name) # Establecer el valor actual
            combobox.grid(row=row + 1, column=3, padx=10, pady=2, sticky="ew")
    
    def manage_vehicle(self, action):
        """Añade o actualiza un vehículo."""
        placa = self.placa_var.get().strip()
        marca = self.entry_marca_vehiculo.get().strip()
        promocion = self.entry_promocion.get().strip()

        if len(placa) != 7:
            messagebox.showerror("Error", "La Placa debe tener exactamente 7 caracteres (ej. C123456).")
            return

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        try:
            if action == "add":
                if not marca or not promocion:
                    raise ValueError("La Marca y la Promoción son obligatorias para añadir un vehículo.")
                cursor.execute("INSERT INTO vehicles (plate, brand, promotion) VALUES (?, ?, ?)", (placa, marca, promocion))
                messagebox.showinfo("Éxito", f"Vehículo con placa {placa} añadido.")
            
            elif action == "update":
                updates = []
                params = []
                if marca:
                    updates.append("brand = ?")
                    params.append(marca)
                if promocion:
                    updates.append("promotion = ?")
                    params.append(promocion)
                
                if not updates:
                    raise ValueError("No hay campos (Marca o Promoción) para actualizar.")
                
                params.append(placa)
                cursor.execute(f"UPDATE vehicles SET {', '.join(updates)} WHERE plate = ?", tuple(params))
                
                if cursor.rowcount == 0:
                    raise ValueError(f"No se encontró vehículo con placa {placa} para actualizar.")

                messagebox.showinfo("Éxito", f"Vehículo con placa {placa} actualizado.")
            
            conn.commit()
            self.load_vehicle_data()
            self.placa_var.set("C") 
            self.entry_marca_vehiculo.delete(0, 'end')
            self.entry_promocion.delete(0, 'end')

        except ValueError as e:
            messagebox.showerror("Error de Validación", str(e))
        except sqlite3.IntegrityError:
            messagebox.showerror("Error de DB", f"La placa '{placa}' ya existe.")
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error inesperado: {e}")
        finally:
            conn.close()

    def update_vehicle_assignment(self, plate, pilot_name):
        """
        Asigna o desasigna un vehículo a un piloto basado en la selección del ComboBox.
        Esta función reemplaza a 'assign_vehicle' y maneja la lógica de 1 a 1.
        """
        
        # 1. Obtener el ID del piloto (será None si se selecciona "SIN ASIGNAR")
        piloto_id = self.pilot_id_map.get(pilot_name) 

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        try:
            # Lógica para hacer cumplir la relación 1 a 1:

            # 2. Si hay un piloto, desasignar CUALQUIER otro vehículo que tenga asignado.
            if piloto_id:
                # Actualiza la tabla vehicles: Desasigna cualquier OTRO vehículo que este piloto pudiera tener
                cursor.execute("UPDATE vehicles SET assigned_to_user_id = NULL WHERE assigned_to_user_id = ? AND plate != ?", (piloto_id, plate))
            
            # 3. Desasignar el vehículo 'plate' de CUALQUIER otro piloto.
            # En users: Si piloto_id es None, se desasigna de todos.
            cursor.execute("UPDATE users SET assigned_vehicle_plate = NULL WHERE assigned_vehicle_plate = ? AND id != ?", (plate, piloto_id if piloto_id else 0)) 
                
            # 4. Asignar/Desasignar (Actualizar ambas tablas)
            
            # Asignación de vehículo al piloto (si piloto_id es None, se asigna NULL, desasignando)
            cursor.execute("UPDATE users SET assigned_vehicle_plate = ? WHERE id = ?", (plate, piloto_id))
            
            # Asignación de piloto al vehículo (si piloto_id es None, se asigna NULL, desasignando)
            cursor.execute("UPDATE vehicles SET assigned_to_user_id = ? WHERE plate = ?", (piloto_id, plate))
            
            # 5. Commit y notificar
            conn.commit()
            
            if piloto_id:
                messagebox.showinfo("Éxito", f"Vehículo {plate} asignado a {pilot_name}.")
            else:
                messagebox.showinfo("Éxito", f"Vehículo {plate} ha sido desasignado (SIN ASIGNAR).")
            
            # Recargar la tabla de vehículos y pilotos
            self.load_vehicle_data()
            # ⭐️ CORRECCIÓN: Llamar directamente al método de la clase AdminFrame
            self.load_pilot_data() 

        except Exception as e:
            messagebox.showerror("Error de Asignación", f"Ocurrió un error inesperado: {e}")
        finally:
            conn.close()

    def delete_vehicle(self):
        """Elimina un vehículo solo si no tiene reportes asociados, usando la placa del campo principal."""
        
        # ⭐️ CAMBIO AQUÍ: Usamos la placa del campo principal (self.placa_var)
        placa = self.placa_var.get().strip() 
        
        if len(placa) != 7: 
            messagebox.showerror("Error", "Ingrese una Placa de vehículo válida (ej. C123456) en el campo 'Placa:' superior para ELIMINAR.")
            return

        if not messagebox.askyesno("Confirmar Eliminación", 
                                   f"ADVERTENCIA: ¿Está seguro de que desea ELIMINAR permanentemente el vehículo {placa}? "
                                   "Esto no se puede deshacer. (Recomendado solo si no tiene reportes históricos)."):
            return

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        try:
            # 1. Verificar reportes existentes
            cursor.execute("SELECT COUNT(*) FROM reports WHERE vehicle_plate = ?", (placa,))
            if cursor.fetchone()[0] > 0:
                raise ValueError(f"No se puede eliminar el vehículo {placa}. Tiene reportes históricos asociados.")

            # 2. Desasignar el vehículo de cualquier piloto (actualiza users)
            cursor.execute("UPDATE users SET assigned_vehicle_plate = NULL WHERE assigned_vehicle_plate = ?", (placa,))
            
            # 3. Eliminar el vehículo (actualiza vehicles)
            cursor.execute("DELETE FROM vehicles WHERE plate = ?", (placa,))
            
            if cursor.rowcount > 0:
                conn.commit()
                messagebox.showinfo("Éxito", f"Vehículo {placa} ELIMINADO permanentemente.")
                self.load_vehicle_data()
                self.tabview.tab("Gestión de Pilotos").load_pilot_data() 
                
                # ⭐️ CAMBIO AQUÍ: Limpiamos el campo de placa principal
                self.placa_var.set("C") 
            else:
                raise ValueError(f"No se encontró un vehículo con placa {placa}.")

        except ValueError as e:
            messagebox.showerror("Error de Eliminación", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error inesperado: {e}")
        finally:
            conn.close()

# --- Función de Exportación Automática a JSON ---

def export_all_reports_to_json():
    """
    Consulta todos los reportes de la DB, convierte las cadenas JSON a objetos
    y exporta el conjunto completo de datos a un archivo JSON estático.
    Este archivo se sobrescribe con el estado actual de la DB en cada llamada.
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # 1. Obtener todos los reportes
        cursor.execute("SELECT * FROM reports")
        rows = cursor.fetchall()
        
        # 2. Obtener los nombres de las columnas
        col_names = [description[0] for description in cursor.description]
        reports_list = []

        # 3. Procesar y Deserializar JSON
        for row in rows:
            report_dict = {}
            for i, col_name in enumerate(col_names):
                value = row[i]
                
                # Deserializar las cadenas JSON para que sean objetos JSON reales
                if col_name in ('header_data', 'checklist_data') and value:
                    try:
                        report_dict[col_name] = json.loads(value)
                    except json.JSONDecodeError:
                        report_dict[col_name] = f"ERROR DE JSON: {value}" 
                else:
                    report_dict[col_name] = value
            
            reports_list.append(report_dict)

        conn.close()

        # 4. Escribir en el archivo JSON (Nombre fijo para que siempre se sobrescriba)
        file_name = "reportes_camiones_auto.json"

        with open(file_name, 'w', encoding='utf-8') as f:
            # Usamos indent=4 para una fácil lectura y ensure_ascii=False para acentos
            json.dump(reports_list, f, ensure_ascii=False, indent=4)
        
        # Opcional: puedes descomentar esto para ver una confirmación en la consola
        # print(f"Exportación automática exitosa. Total reportes: {len(reports_list)}. Archivo: {file_name}")

    except Exception:
        # En caso de error, fallamos silenciosamente para no interrumpir al piloto
        pass
    
def setup_report_review_tab(self):
        tab = self.tabview.tab("Revisión de Reportes")
        tab.grid_columnconfigure(0, weight=1)
        
        # ⭐️ CAMBIO CRÍTICO: La Fila 1 (lista de reportes) toma todo el espacio vertical.
        tab.grid_rowconfigure(1, weight=1) 
        # Se elimina la línea 'tab.grid_rowconfigure(0, weight=1)' que empujaba el contenido hacia abajo.

        # ⭐️ NUEVO: Frame de Búsqueda
        search_frame = ctk.CTkFrame(tab)
        # ⭐️ CAMBIO: Reducir pady superior de 10 a 5.
        search_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(5, 5)) 
        search_frame.grid_columnconfigure(0, weight=0)
        search_frame.grid_columnconfigure(1, weight=1)
        search_frame.grid_columnconfigure(2, weight=0)

        ctk.CTkLabel(search_frame, text="Buscar Placa o Piloto:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="Ej: C123456 o Juan Pérez")
        self.search_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        
        ctk.CTkButton(search_frame, text="🔍 Buscar", command=self.load_report_data).grid(row=0, column=2, padx=10, pady=5)
        # -------------------------------------


        # Usamos un frame para contener la tabla y botones (Ahora en fila 1)
        self.report_container = ctk.CTkFrame(tab)
        # ⭐️ CAMBIO: Reducir pady inferior de 10 a 5.
        self.report_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=(5, 5)) 
        self.report_container.grid_columnconfigure(0, weight=1)
        self.report_container.grid_rowconfigure(0, weight=1)

        self.report_data_frame = None 

        action_frame = ctk.CTkFrame(tab)
        # ⭐️ CAMBIO: Reducir pady superior de 10 a 5.
        action_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(5, 10)) # Ahora en fila 2
        action_frame.grid_columnconfigure((0, 1), weight=1)
        
        ctk.CTkButton(action_frame, text="Ver Detalles del Reporte Seleccionado", command=self.show_report_details).grid(row=0, column=1, padx=10, pady=5, sticky="e")
        # ⭐️ CAMBIO: Botón Recargar ahora limpia la búsqueda
        ctk.CTkButton(action_frame, text="Recargar Reportes (Limpiar Búsqueda)", command=lambda: (self.search_entry.delete(0, 'end'), self.load_report_data())).grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.load_report_data()

def load_report_data(self):
        """Carga los reportes desde la DB y los muestra en una tabla, aplicando un filtro de búsqueda si existe."""
        
        # ⭐️ NUEVO: Obtener término de búsqueda
        search_term = self.search_entry.get().strip()
        
        if self.report_data_frame:
            self.report_data_frame.destroy()
        
        self.report_data_frame = ctk.CTkScrollableFrame(self.report_container, label_text="Reportes Enviados")
        self.report_data_frame.grid(row=0, column=0, sticky="nsew")
        
        self.report_selection_var = ctk.StringVar(value="0") 
        self.selected_report_id = None
        
        conn = sqlite3.connect(DB_NAME)
        
        # Construcción de la consulta SQL y parámetros
        query = """
        SELECT 
            r.id, 
            u.full_name AS piloto, 
            r.vehicle_plate, 
            r.report_date, 
            r.km_actual,
            r.header_data,
            r.checklist_data,
            r.observations,
            r.signature_confirmation
        FROM reports r
        LEFT JOIN users u ON r.driver_id = u.id 
        """
        params = []
        
        if search_term:
            # Añadir la cláusula WHERE para buscar en placa o nombre del piloto (case-insensitive usando UPPER)
            query += """
            WHERE UPPER(r.vehicle_plate) LIKE ? OR UPPER(u.full_name) LIKE ?
            """
            search_pattern = f"%{search_term.upper()}%"
            params.append(search_pattern)
            params.append(search_pattern)
            
        query += " ORDER BY r.id DESC"
        
        # Ejecutar la consulta con parámetros
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        if df.empty:
            if search_term:
                 ctk.CTkLabel(self.report_data_frame, text=f"No se encontraron reportes para '{search_term}'.").pack(padx=20, pady=20)
            else:
                 ctk.CTkLabel(self.report_data_frame, text="No hay reportes para mostrar.").pack(padx=20, pady=20)
            self.report_df = None
            return

        self.report_df = df 
        
        # Headers y configuración de columnas para la tabla
        table_headers = ["", "ID", "Piloto", "Placa", "Fecha", "Km Actual"]
        
        for col, header in enumerate(table_headers):
            self.report_data_frame.grid_columnconfigure(col, weight=1)
            ctk.CTkLabel(self.report_data_frame, text=header, font=ctk.CTkFont(weight="bold")).grid(row=0, column=col, padx=10, pady=5, sticky="w" if col > 0 else "")

        
        # Mapeamos las filas del DataFrame a widgets
        for row_index, row_data in self.report_df.iterrows():
            
            # Crear RadioButton (cuadrado) para selección de fila
            rb = ctk.CTkRadioButton(self.report_data_frame, text="", variable=self.report_selection_var, value=str(row_data['id']), 
                                    command=lambda id=row_data['id']: self.select_report(id))
            rb.grid(row=row_index + 1, column=0, padx=10, pady=2) 
            
            piloto_nombre = row_data['piloto'] if pd.notna(row_data['piloto']) else "PILOTO ELIMINADO"
            
            data_to_display = [
                row_data['id'],
                piloto_nombre,
                row_data['vehicle_plate'],
                row_data['report_date'],
                row_data['km_actual']
            ]
            
            for col_index, data in enumerate(data_to_display):
                display_col = col_index + 1 
                label = ctk.CTkLabel(self.report_data_frame, text=str(data), anchor="w")
                label.grid(row=row_index + 1, column=display_col, padx=10, pady=2, sticky="w")
            

def select_report(self, report_id):
        """Maneja la selección de un reporte en la tabla."""
        self.selected_report_id = report_id
        
def show_report_details(self):
        """Abre la ventana de detalles para el reporte seleccionado."""
        if not self.selected_report_id:
            messagebox.showerror("Error", "Seleccione un reporte de la lista para ver los detalles.")
            return

        selected_row = self.report_df[self.report_df['id'] == int(self.selected_report_id)].iloc[0]
        
        report_data_for_display = {
            'ID': selected_row['id'],
            'header_data': json.loads(selected_row['header_data']),
            'checklist_data': json.loads(selected_row['checklist_data']),
            'observations': selected_row['observations'] if pd.notna(selected_row['observations']) else "",
            'signature_confirmation': selected_row['signature_confirmation']
        }
        
        ReportDetailWindow(self.app, report_data_for_display)


# --- Clase de la Interfaz de Piloto (Formulario) ---

class PilotFrame(ctk.CTkFrame):
    def __init__(self, master, app_instance):
        super().__init__(master)
        self.app = app_instance
        self.grid(row=0, column=0, sticky="nsew") 
        self.grid_columnconfigure(0, weight=1)

        self.signature_confirmation_text = None 
        self.signature_process_completed = False 
        self.assigned_vehicle = {} 

        # --- Encabezado y Botón de Cerrar Sesión ---
        header_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        header_frame.pack(fill="x", pady=(20, 10), padx=20)
        header_frame.grid_columnconfigure(0, weight=0) # Logo
        header_frame.grid_columnconfigure(1, weight=1) # Título/Piloto
        header_frame.grid_columnconfigure(2, weight=0) # Botón Logout

        # ⭐️ Logo en Piloto
        if self.app.logo_image:
            ctk.CTkLabel(header_frame, text="", image=self.app.logo_image).grid(row=0, column=0, rowspan=2, padx=(0, 15), sticky="w")

        # Título y Piloto (en la columna 1)
        title_label = ctk.CTkLabel(header_frame, text="Check List Inspección 360 Vehicular", font=ctk.CTkFont(size=18, weight="bold"))
        title_label.grid(row=0, column=1, sticky="w")
        
        self.welcome_label = ctk.CTkLabel(header_frame, text=f"Piloto: {self.app.current_user_name}")
        self.welcome_label.grid(row=1, column=1, sticky="w")
        
        # Botón de Cerrar Sesión (en la columna 2)
        ctk.CTkButton(header_frame, text="Cerrar Sesión", command=self.app.logout, fg_color="darkred", hover_color="red").grid(row=0, column=2, rowspan=2, sticky="e")
        # -----------------------------------------------

        self.load_assigned_vehicle() 
        
        if not self.assigned_vehicle.get('plate'):
             self.show_no_vehicle_warning()
             return

        # --- Frame de Vehículo Asignado ---
        vehicle_info_frame = ctk.CTkFrame(self)
        vehicle_info_frame.pack(fill="x", padx=20, pady=5)
        vehicle_info_frame.columnconfigure((0, 1, 2, 3, 4, 5), weight=1)
        
        ctk.CTkLabel(vehicle_info_frame, text="VEHÍCULO ASIGNADO", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=6, pady=(5, 0))

        self.placa_label = ctk.CTkLabel(vehicle_info_frame, text=f"Placa: {self.assigned_vehicle.get('plate', 'N/A')}", font=ctk.CTkFont(size=14))
        self.placa_label.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        
        self.marca_label = ctk.CTkLabel(vehicle_info_frame, text=f"Marca: {self.assigned_vehicle.get('brand', 'N/A')}", font=ctk.CTkFont(size=14))
        self.marca_label.grid(row=1, column=2, columnspan=2, padx=10, pady=5, sticky="w")
        
        promo_text = self.assigned_vehicle.get('promotion', 'SIN PROMOCIÓN')
        self.promo_label = ctk.CTkLabel(vehicle_info_frame, text=f"Promoción: {promo_text}", font=ctk.CTkFont(size=14, weight="bold"), text_color="yellow")
        self.promo_label.grid(row=1, column=4, columnspan=2, padx=10, pady=5, sticky="w")

        # --- Frame para datos del vehículo (Campos manuales) ---
        data_frame = ctk.CTkFrame(self)
        data_frame.pack(fill="x", padx=20, pady=5)
        data_frame.columnconfigure((0, 1, 2, 3), weight=1)

        self.entry_placa = ctk.CTkEntry(data_frame, placeholder_text="Placa del Vehículo", state="readonly") 
        self.entry_placa.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        self.entry_fecha = ctk.CTkEntry(data_frame, placeholder_text="Fecha de Reporte (YYYY-MM-DD)")
        self.entry_fecha.insert(0, datetime.date.today().strftime("%Y-%m-%d"))
        self.entry_fecha.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        self.entry_km = ctk.CTkEntry(data_frame, placeholder_text="Km actual (OBLIGATORIO)")
        self.entry_km.grid(row=0, column=2, padx=5, pady=5, sticky="ew")
        
        # Pre-llenar la placa
        self.entry_placa.configure(state="normal")
        self.entry_placa.insert(0, self.assigned_vehicle['plate'])
        self.entry_placa.configure(state="readonly")
        
        # --- Frame Principal del Checklist (Scrollable) ---
        self.checklist_frame = ctk.CTkScrollableFrame(self)
        self.checklist_frame.pack(fill="both", expand=True, padx=20, pady=10)
        self.checklist_frame.grid_columnconfigure(0, weight=1)

        self.checklist_items = {} 
        self.create_checklist()

        # --- Observaciones ---
        obs_label = ctk.CTkLabel(self, text="Observaciones Adicionales:", font=ctk.CTkFont(size=14, weight="bold"))
        obs_label.pack(anchor="w", padx=20, pady=(5,0))
        
        self.obs_textbox = ctk.CTkTextbox(self, height=80)
        self.obs_textbox.pack(fill="x", padx=20, pady=5)

        # --- Botones de Acción ---
        action_frame_buttons = ctk.CTkFrame(self)
        action_frame_buttons.pack(fill="x", padx=20, pady=10)
        action_frame_buttons.grid_columnconfigure((0, 1), weight=1)

        self.confirm_button = ctk.CTkButton(action_frame_buttons, text="1. Confirmar Reporte (Firma)", command=self.confirm_report_dialog)
        self.confirm_button.grid(row=0, column=0, padx=10, sticky="ew")

        self.save_button = ctk.CTkButton(action_frame_buttons, text="2. Guardar Reporte", command=self.save_report, state="disabled", fg_color="green")
        self.save_button.grid(row=0, column=1, padx=10, sticky="ew")

    def show_no_vehicle_warning(self):
        """Muestra un mensaje de advertencia si no hay vehículo asignado."""
        warning_frame = ctk.CTkFrame(self, fg_color="red")
        warning_frame.pack(fill="both", expand=True, padx=50, pady=50)
        warning_frame.grid_rowconfigure((0, 1), weight=1)
        warning_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(warning_frame, text="⛔ ¡ATENCIÓN! ⛔", font=ctk.CTkFont(size=30, weight="bold")).grid(row=0, column=0, pady=(50, 10))
        ctk.CTkLabel(warning_frame, text=f"Piloto {self.app.current_user_name}, no tiene un vehículo asignado.", 
                     font=ctk.CTkFont(size=18)).grid(row=1, column=0, pady=10)
        ctk.CTkLabel(warning_frame, text="Contacte a su administrador para que le asigne una placa y poder generar reportes.", 
                     font=ctk.CTkFont(size=18)).grid(row=2, column=0, pady=(10, 50))
        
        ctk.CTkButton(warning_frame, text="Cerrar Sesión", command=self.app.logout, fg_color="darkred", hover_color="red").grid(row=3, column=0, pady=20)


    def load_assigned_vehicle(self):
        """Busca el vehículo asignado al piloto actual."""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("SELECT assigned_vehicle_plate FROM users WHERE id = ?", (self.app.current_user_id,))
        assigned_plate_result = cursor.fetchone()
        assigned_plate = assigned_plate_result[0] if assigned_plate_result else None
        
        if assigned_plate:
            cursor.execute("SELECT plate, brand, promotion FROM vehicles WHERE plate = ?", (assigned_plate,))
            vehicle_data = cursor.fetchone()
            if vehicle_data:
                self.assigned_vehicle = {
                    'plate': vehicle_data[0],
                    'brand': vehicle_data[1],
                    'promotion': vehicle_data[2]
                }
            else:
                self.assigned_vehicle = {}
                cursor.execute("UPDATE users SET assigned_vehicle_plate = NULL WHERE id = ?", (self.app.current_user_id,))
                conn.commit()
                messagebox.showwarning("Atención", "Su vehículo asignado no existe. Se ha desasignado automáticamente. Contacte al administrador.")
        else:
            self.assigned_vehicle = {}
            
        conn.close()

    def create_checklist(self):
        """Crea dinámicamente los items del checklist."""
        
        # Frame de Encabezado (para Buen/Mal/N/A)
        # Se usa fg_color="gray20" (dark grey) para resaltar las columnas en Light mode (fondo blanco)
        header_frame = ctk.CTkFrame(self.checklist_frame, fg_color="gray80")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        
        header_frame.grid_columnconfigure(0, weight=3) # Item
        header_frame.grid_columnconfigure((1, 2, 3), weight=1) # Buen, Mal, N/A

        ctk.CTkLabel(header_frame, text="Item a evaluar", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=5, sticky="w")
        ctk.CTkLabel(header_frame, text="Buen estado", font=ctk.CTkFont(weight="bold")).grid(row=0, column=1, padx=5)
        ctk.CTkLabel(header_frame, text="Mal estado", font=ctk.CTkFont(weight="bold")).grid(row=0, column=2, padx=5)
        ctk.CTkLabel(header_frame, text="N/A", font=ctk.CTkFont(weight="bold")).grid(row=0, column=3, padx=5)
        
        row_counter = 1
        global CHECKLIST_ITEMS
        for categoria, sub_items in CHECKLIST_ITEMS:
            # Etiqueta de Categoría
            cat_label = ctk.CTkLabel(self.checklist_frame, text=categoria.upper(), font=ctk.CTkFont(size=14, weight="bold"))
            cat_label.grid(row=row_counter, column=0, sticky="w", padx=5, pady=(10, 5))
            row_counter += 1
            
            for item_name in sub_items:
                self.add_checklist_row(item_name, row_counter)
                row_counter += 1
                
    def add_checklist_row(self, item_name, row):
        """Añade una fila individual al checklist, con botones centrados y color N/A azul."""
        
        item_frame = ctk.CTkFrame(self.checklist_frame, fg_color="transparent")
        item_frame.grid(row=row, column=0, sticky="ew", pady=2)
        
        item_frame.grid_columnconfigure(0, weight=3) # Item (para el label)
        item_frame.grid_columnconfigure((1, 2, 3), weight=1) # Buen, Mal, N/A (para los radio buttons)

        var = ctk.StringVar(value="N/A")
        self.checklist_items[item_name] = var 
        
        # Etiqueta del Item
        label = ctk.CTkLabel(item_frame, text=item_name, anchor="w")
        label.grid(row=0, column=0, padx=5, sticky="w")
        
        # --- Botones de Opción Cuadrados CENTRADOS ---
        
        # Columna 1: Buen estado
        rb_bueno = ctk.CTkRadioButton(item_frame, text="", variable=var, value="Buen estado", 
                                     width=20, height=20, border_width_checked=5, border_width_unchecked=2, fg_color="green")
        rb_bueno.grid(row=0, column=1, padx=5, sticky="") # sticky="" centra

        # Columna 2: Mal estado
        rb_malo = ctk.CTkRadioButton(item_frame, text="", variable=var, value="Mal estado",
                                    width=20, height=20, border_width_checked=5, border_width_unchecked=2, fg_color="red")
        rb_malo.grid(row=0, column=2, padx=5, sticky="") # sticky="" centra

        # Columna 3: N/A - COLOR AZUL
        rb_na = ctk.CTkRadioButton(item_frame, text="", variable=var, value="N/A",
                                  width=20, height=20, border_width_checked=5, border_width_unchecked=2, fg_color="blue")
        rb_na.grid(row=0, column=3, padx=5, sticky="") # sticky="" centra

    def confirm_report_dialog(self):
        """Muestra un diálogo de confirmación (Firma)."""
        
        self.signature_process_completed = False
        self.signature_confirmation_text = None
        self.save_button.configure(state="disabled")
        original_color = ctk.ThemeManager.theme["CTkButton"]["fg_color"]
        self.confirm_button.configure(text="1. Confirmar Reporte (Firma)", fg_color=original_color)

        if not self.assigned_vehicle.get('plate'):
            messagebox.showerror("Error", "No puede confirmar el reporte. No tiene un vehículo asignado en el sistema.")
            return

        # Validación rápida para Km
        km = self.entry_km.get().strip()
        if not km or not km.isdigit():
             messagebox.showerror("Error", "Debe ingresar el kilometraje actual y debe ser un número.")
             return

        msg = (f"DECLARACIÓN DE RESPONSABILIDAD\n\n"
               f"Yo, {self.app.current_user_name} (ID: {self.app.current_user_id}), confirmo bajo mi responsabilidad "
               f"que la inspección 360 del vehículo con placa **{self.assigned_vehicle['plate']}** "
               "se ha realizado y que los datos y el estado de los ítems en este reporte son verídicos y correctos. \n\n"
               "Haga clic en 'Sí' para confirmar y habilitar la opción de Guardar.")
        
        respuesta = messagebox.askyesno("Confirmación de Piloto (Firma)", msg)
        
        if respuesta:
            self.signature_process_completed = True
            
            now = datetime.datetime.now()
            self.signature_confirmation_text = f"CONFIRMADO | Piloto: {self.app.current_user_name} | ID: {self.app.current_user_id} | Fecha/Hora: {now.strftime('%Y-%m-%d %H:%M:%S')}"
            
            self.save_button.configure(state="normal")
            self.confirm_button.configure(text="¡Reporte Confirmado!", fg_color="green")
        else:
            messagebox.showinfo("Cancelado", "Reporte no confirmado. No se puede guardar hasta que confirme.")


    def save_report(self):
        """Recopila todos los datos y los guarda en la base de datos."""
        
        placa = self.assigned_vehicle.get('plate')
        fecha = self.entry_fecha.get().strip()
        km = self.entry_km.get().strip()
        
        if not self.signature_process_completed:
            messagebox.showerror("Confirmación Requerida", "Debe confirmar el reporte (Paso 1) antes de guardarlo.")
            return
        
        if not placa or not fecha or not km:
            messagebox.showerror("Error", "Faltan datos en el encabezado (Placa, Fecha o Km).")
            return

        # 1. Recopilar datos del checklist
        checklist_data = {item: var.get() for item, var in self.checklist_items.items()}
        
        # 2. Recopilar datos del encabezado
        header_data = {
            "placa": placa,
            "marca": self.assigned_vehicle.get('brand', 'N/A'),
            "promocion": self.assigned_vehicle.get('promotion', 'N/A'),
            "fecha": fecha,
            "km_actual": km,
            "piloto_nombre": self.app.current_user_name,
            "piloto_id": self.app.current_user_id
        }
        
        # 3. Observaciones
        observations = self.obs_textbox.get("1.0", "end-1c").strip()

        # 4. Guardar en DB
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO reports (driver_id, report_date, vehicle_plate, km_actual, header_data, checklist_data, observations, signature_confirmation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.app.current_user_id,
                fecha,
                placa,
                km,
                json.dumps(header_data),
                json.dumps(checklist_data),
                observations,
                self.signature_confirmation_text
            ))
            
            conn.commit()
            
            # ⭐️ INSERCIÓN CLAVE: Actualiza el archivo JSON
            export_all_reports_to_json() 
            
            messagebox.showinfo("Éxito", "Reporte de inspección guardado correctamente.")
            
            # Resetear el formulario
            self.entry_km.delete(0, 'end')
            self.obs_textbox.delete("1.0", "end")
            self.signature_process_completed = False
            self.signature_confirmation_text = None
            self.save_button.configure(state="disabled")
            original_color = ctk.ThemeManager.theme["CTkButton"]["fg_color"]
            self.confirm_button.configure(text="1. Confirmar Reporte (Firma)", fg_color=original_color)
            
            # Resetear los radio buttons a N/A
            for var in self.checklist_items.values():
                var.set("N/A")

        except Exception as e:
            messagebox.showerror("Error de Guardado", f"Error al guardar el reporte: {e}")
        finally:
            conn.close()


# --- Clase de la Aplicación Principal ---

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Sistema de Reportes de Inspección 360 y Gestión de Vehículos")
        self.geometry("900x700")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.current_user_id = None
        self.current_user_name = ""
        self.current_user_role = ""
        
        # ⭐️ Cargar el logo al inicio de la aplicación
        self.logo_image = self.load_logo("logo.png", size=(100, 50))
        
        self.show_login_frame()

    def load_logo(self, path, size):
        """Carga y redimensiona la imagen del logo."""
        try:
            # Si el modo es Light (fondo blanco), asegura que el fondo del logo sea manejado si es transparente.
            return ctk.CTkImage(light_image=Image.open(path),
                                dark_image=Image.open(path),
                                size=size)
        except FileNotFoundError:
            # Si el archivo no existe, no es un error fatal, solo advertimos
            # messagebox.showwarning("Advertencia de Logo", f"No se encontró el archivo de logo en la ruta: {path}. La aplicación continuará sin logo.")
            return None
        except Exception as e:
            messagebox.showerror("Error de Imagen", f"Error al cargar el logo: {e}")
            return None

    def show_login_frame(self):
        """Muestra la pantalla de inicio de sesión."""
        self.clear_frame()
        self.login_frame = ctk.CTkFrame(self)
        self.login_frame.grid(row=0, column=0, padx=100, pady=150)

        # ⭐️ Mostrar el logo en el login
        if self.logo_image:
            ctk.CTkLabel(self.login_frame, text="", image=self.logo_image).pack(pady=(10, 5))

        label = ctk.CTkLabel(self.login_frame, text="Inicio de Sesión", font=ctk.CTkFont(size=20, weight="bold"))
        label.pack(pady=(0, 20))

        self.username_entry = ctk.CTkEntry(self.login_frame, placeholder_text="Usuario (ej: piloto1 o admin)", width=250)
        self.username_entry.pack(pady=12, padx=20)

        self.password_entry = ctk.CTkEntry(self.login_frame, placeholder_text="Contraseña", show="*", width=250)
        self.password_entry.pack(pady=12, padx=20)

        login_button = ctk.CTkButton(self.login_frame, text="Ingresar", command=self.attempt_login)
        login_button.pack(pady=20, padx=20)
        
        self.bind("<Return>", lambda event: self.attempt_login())

    def clear_frame(self):
        """Destruye todos los widgets hijos para cambiar de vista."""
        for widget in self.winfo_children():
            widget.destroy()

    def attempt_login(self):
        """Intenta iniciar sesión y redirige al usuario."""
        username = self.username_entry.get()
        password = self.password_entry.get()

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        query = "SELECT id, full_name, role, is_active FROM users WHERE username = ? AND password = ?"
        cursor.execute(query, (username, password))
        user_data = cursor.fetchone()
        conn.close()

        if user_data:
            user_id, full_name, role, is_active = user_data
            
            if is_active == 0:
                messagebox.showerror("Error de Sesión", "Su cuenta ha sido deshabilitada. Contacte al administrador.")
                return

            self.current_user_id = user_id
            self.current_user_name = full_name
            self.current_user_role = role
            self.unbind("<Return>") # Deshabilitar el Enter para login
            self.show_main_interface(role)
        else:
            messagebox.showerror("Error de Sesión", "Usuario o contraseña incorrectos.")

    def logout(self):
        """Cierra la sesión del usuario y vuelve a la pantalla de login."""
        self.current_user_id = None
        self.current_user_name = ""
        self.current_user_role = ""
        self.show_login_frame()

    def show_main_interface(self, role):
        """Muestra la interfaz principal según el rol."""
        self.clear_frame()
        if role == 'admin':
            AdminFrame(self, self)
        elif role == 'piloto':
            PilotFrame(self, self)
        else:
            messagebox.showerror("Error de Rol", "Rol de usuario no reconocido.")
            self.show_login_frame()


# --- Ejecución ---
if __name__ == "__main__":
    try:
        inicializar_db()
    except sqlite3.OperationalError as e:
        print(f"Error de DB durante inicialización: {e}")
        
    app = App()
    app.mainloop()