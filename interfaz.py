import tkinter as tk
import random
import string

def crear_ventana():
    ventana = tk.Tk()
    ventana.title("Generador de Contraseñas")
    ventana.geometry("640x480")
    
    bg_principal = "#2d2d2d"    
    bg_secundario = "#3c3c3c"   
    bg_terciario = "#4a4a4a"  
    bg_input = "#555555"          
    texto_principal = "#e0e0e0"   
    texto_secundario = "#b0b0b0"  
    acento_verde = "#66bb6a"      
    acento_azul = "#42a5f5"       
    borde = "#555555"             
    
    ventana.configure(bg=bg_principal)
    
    # Título
    titulo = tk.Label(ventana, text="Generador de Contraseñas Seguras", 
                      font=("Arial", 16, "bold"), 
                      bg=bg_principal, fg=texto_principal)
    titulo.pack(pady=20)
    
    # Frame para la contraseña generada
    frame_password = tk.Frame(ventana, bg=bg_secundario, relief="solid", bd=1)
    frame_password.pack(pady=10, padx=20, fill="x")
    
    # Variable para guardar la contraseña
    contrasena_var = tk.StringVar()
    contrasena_var.set("Haz clic en Generar")
    
    # Label que muestra la contraseña
    label_contrasena = tk.Label(frame_password, textvariable=contrasena_var, 
                                font=("Arial", 18, "bold"), 
                                bg=bg_input, fg=texto_principal,
                                relief="flat", padx=20, pady=10, width=30)
    label_contrasena.pack(pady=15, padx=15, fill="both")
    
    # Frame para controles
    frame_controles = tk.Frame(ventana, bg=bg_secundario, relief="solid", bd=1)
    frame_controles.pack(pady=10, padx=20, fill="x")
    
    # Longitud de la contraseña
    label_longitud = tk.Label(frame_controles, text="Longitud:", 
                              bg=bg_secundario, fg=texto_principal, 
                              font=("Arial", 12))
    label_longitud.grid(row=0, column=0, padx=10, pady=15)
    
    longitud_var = tk.IntVar(value=12)
    spin_longitud = tk.Spinbox(frame_controles, from_=4, to=30, 
                               textvariable=longitud_var, 
                               width=5, font=("Arial", 12),
                               bg=bg_input, fg=texto_principal,
                               relief="flat", buttonbackground=bg_terciario)
    spin_longitud.grid(row=0, column=1, padx=5, pady=15)
    
    # Frame para checkboxes
    frame_checkboxes = tk.Frame(ventana, bg=bg_secundario, relief="solid", bd=1)
    frame_checkboxes.pack(pady=10, padx=20, fill="x")
    
    usar_mayusculas = tk.BooleanVar(value=True)
    usar_numeros = tk.BooleanVar(value=True)
    usar_simbolos = tk.BooleanVar(value=True)
    
    # Checkboxes con estilo dark
    cb_mayusculas = tk.Checkbutton(frame_checkboxes, text="Mayusculas", 
                                   variable=usar_mayusculas, 
                                   bg=bg_secundario, fg=texto_principal,
                                   selectcolor=bg_terciario,
                                   font=("Arial", 10), relief="flat")
    cb_mayusculas.grid(row=0, column=0, padx=20, pady=10)
    
    cb_numeros = tk.Checkbutton(frame_checkboxes, text="Numeros", 
                                variable=usar_numeros, 
                                bg=bg_secundario, fg=texto_principal,
                                selectcolor=bg_terciario,
                                font=("Arial", 10), relief="flat")
    cb_numeros.grid(row=0, column=1, padx=20, pady=10)
    
    cb_simbolos = tk.Checkbutton(frame_checkboxes, text="Simbolos", 
                                 variable=usar_simbolos, 
                                 bg=bg_secundario, fg=texto_principal,
                                 selectcolor=bg_terciario,
                                 font=("Arial", 10), relief="flat")
    cb_simbolos.grid(row=0, column=2, padx=20, pady=10)
    
    # Función para generar contraseña
    def generar_contrasena():
        longitud = longitud_var.get()
        caracteres = string.ascii_lowercase
        
        if usar_mayusculas.get():
            caracteres += string.ascii_uppercase
        if usar_numeros.get():
            caracteres += string.digits
        if usar_simbolos.get():
            caracteres += "!@#$%^&*()-_=+"
        
        if not caracteres:
            contrasena_var.set("ERROR: Selecciona al menos una opcion")
            return
        
        contrasena = ''.join(random.choice(caracteres) for _ in range(longitud))
        contrasena_var.set(contrasena)
    
    # Botón Generar (verde suave)
    boton_generar = tk.Button(ventana, text="Generar Contraseña", 
                              command=generar_contrasena, 
                              font=("Arial", 14, "bold"), 
                              bg=acento_verde, fg=bg_principal,
                              relief="flat", padx=20, pady=10,
                              activebackground="#81c784", 
                              activeforeground=bg_principal)
    boton_generar.pack(pady=15)
    
    # Función para copiar
    def copiar_contrasena():
        contrasena = contrasena_var.get()
        if contrasena and contrasena != "Haz clic en Generar" and contrasena != "ERROR: Selecciona al menos una opcion":
            ventana.clipboard_clear()
            ventana.clipboard_append(contrasena)
            # Feedback visual
            label_contrasena.config(bg="#2e7d32")  # Verde oscuro
            ventana.after(1000, lambda: label_contrasena.config(bg=bg_input))
    
    # Botón Copiar (azul suave)
    boton_copiar = tk.Button(ventana, text="Copiar", 
                             command=copiar_contrasena, 
                             font=("Arial", 12), 
                             bg=acento_azul, fg=bg_principal,
                             relief="flat", padx=15, pady=5,
                             activebackground="#64b5f6",
                             activeforeground=bg_principal)
    boton_copiar.pack(pady=5)
    
    # Footer
    footer = tk.Label(ventana, text="Contraseña segura generada localmente", 
                      font=("Arial", 9), 
                      bg=bg_principal, fg=texto_secundario)
    footer.pack(side=tk.BOTTOM, pady=20)
    
    ventana.mainloop()