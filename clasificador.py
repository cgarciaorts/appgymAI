import pandas as pd

# --- CONFIGURACIÓN DE PALABRAS CLAVE ---
# Puedes añadir más palabras clave aquí para mejorar la precisión
PALABRAS_COMPUESTO = ['press banca', 'sentadilla', 'peso muerto', 'dominada', 'remo con barra', 'fondos', 'press militar']
PALABRAS_AISLAMIENTO = ['curl', 'extension', 'elevacion', 'apertura', 'patada', 'press frances', 'pullover']
PALABRAS_PLIOMETRICO = ['salto', 'jump', 'lanzamiento', 'bound', 'hop', 'plyo']

def clasificar_ejercicio(nombre_ejercicio):
    """
    Toma el nombre de un ejercicio y devuelve su tipo y prioridad estimados.
    """
    nombre_lower = str(nombre_ejercicio).lower()
    
    # Clasificación por tipo de ejercicio
    if any(palabra in nombre_lower for palabra in PALABRAS_PLIOMETRICO):
        return 'Pliometrico', 1
    elif any(palabra in nombre_lower for palabra in PALABRAS_COMPUESTO):
        return 'Compuesto', 1
    elif any(palabra in nombre_lower for palabra in PALABRAS_AISLAMIENTO):
        return 'Aislamiento', 3
    # Si no es ninguno de los anteriores, por defecto es un Accesorio de prioridad 2
    else:
        # Aquí podrías añadir más lógica para 'Movilidad', 'Core', etc. si quieres
        return 'Accesorio', 2

# --- SCRIPT PRINCIPAL ---
NOMBRE_ARCHIVO_ENTRADA = "datos.xlsx"
NOMBRE_ARCHIVO_SALIDA = "datos_clasificado.xlsx"

print(f"Cargando el archivo '{NOMBRE_ARCHIVO_ENTRADA}'...")
try:
    df = pd.read_excel(NOMBRE_ARCHIVO_ENTRADA)
except FileNotFoundError:
    print(f"ERROR: No se encontró el archivo. Asegúrate de que '{NOMBRE_ARCHIVO_ENTRADA}' está en la carpeta.")
    exit()

print("Archivo cargado. Empezando clasificación automática...")

# Aplicamos la función de clasificación a cada fila del DataFrame
# Los resultados se guardan en dos nuevas listas temporales
resultados = df['ejercicio'].apply(clasificar_ejercicio)
df['tipo_ejercicio'] = [res[0] for res in resultados]
df['prioridad'] = [res[1] for res in resultados]

print("Clasificación completada.")

# Guardamos el DataFrame con las nuevas columnas en un NUEVO archivo Excel
df.to_excel(NOMBRE_ARCHIVO_SALIDA, index=False)

print(f"¡Éxito! Tu base de datos ha sido clasificada y guardada en '{NOMBRE_ARCHIVO_SALIDA}'.")
print("Ahora puedes revisar ese archivo, hacer los ajustes finales y usarlo en la app principal.")