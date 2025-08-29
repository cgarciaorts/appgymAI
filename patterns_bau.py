# from patterns import PATTERNS
# patterns_bau.py
# Plantillas basadas en Baumovment:
# - Calentamiento: movilidad + activación + (1) pliometría/lanzamiento + series de aproximación
# - Bloque pesado / potencia
# - Accesorios combinando patrones (empuje-tracción, d. rodilla-d. cadera) en CircuitoPar
# - Finisher opcional (metabólico) o cinta/carrera
#
# Requiere planner.py (v4) que ya trae: Calentamiento*, Pliometrico, CircuitoPar, Caminar, Carrera.

PATTERNS = {
    "Lunes": {
        "meta": {"titulo": "Upper: Pecho/Espalda + Espalda/Hombro + Cinta"},
        "orden": [
            "Calentamiento Torso",
            "Potencia (Torso) / Bloque Pesado",
            "Circuito A: Empuje horizontal + Tracción horizontal",
            "Circuito B: Empuje diagonal/vertical + Tracción vertical/ligera",
            "Caminar en cinta"
        ],
        "reglas": {
            # --- Calentamiento Torso ---
            "Calentamiento Torso": {
                "tipo": "Calentamiento",
                # planner selecciona Movilidad/Activación: hombro + tóracica + escápula
                "tipo_ejercicio": "Movilidad",
                "patrones": ["hombro", "torácica", "escápula", "core"],
                "tags_incluye": ["movilidad"],
                "n": 4  # 3-4 movilidad/activación + 1 pliometría/lanzamiento (planner ya la añade si hay)
            },
            # --- Potencia/ Pesado Torso (1-2 ejercicios pesados) ---
            "Potencia (Torso) / Bloque Pesado": {
                "tipo": "CircuitoPar",
                "series_circuito": 3,
                "reps": "4-6",
                "RPE": (7, 9),
                "descanso_entre_ej": 0,
                "descanso_entre_series": 90,
                "parejas": [
                    # Empuje pesado + Tracción pesada
                    (
                        {"tipo_ejercicio": "Compuesto", "patrones": ["empuje","banca","flexion","militar"], "prioridad": 1, "series": (3,4), "reps": "3-6", "RPE": (8,9)},
                        {"tipo_ejercicio": "Compuesto", "patrones": ["traccion","remo","dominada","jalon"], "prioridad": 1, "series": (3,4), "reps": "3-6", "RPE": (8,9)}
                    )
                ]
            },
            # --- Circuito A (empuje h. + tracción h. + core/salto entre series) ---
            "Circuito A: Empuje horizontal + Tracción horizontal": {
                "tipo": "CircuitoPar",
                "series_circuito": 3,
                "reps": "8-12",
                "RPE": (7,8),
                "descanso_entre_ej": 0,
                "descanso_entre_series": 60,
                "parejas": [
                    (
                        {"tipo_ejercicio": "Accesorio", "patrones": ["empuje","horizontal","pecho","flexion","press"], "prioridad": 2},
                        {"tipo_ejercicio": "Accesorio", "patrones": ["traccion","horizontal","remo","polea","mancuerna"], "prioridad": 2}
                    )
                ]
            },
            # --- Circuito B (empuje diagonal/vertical + tracción vertical ligera) ---
            "Circuito B: Empuje diagonal/vertical + Tracción vertical/ligera": {
                "tipo": "CircuitoPar",
                "series_circuito": 3,
                "reps": "8-12",
                "RPE": (7,8),
                "descanso_entre_ej": 0,
                "descanso_entre_series": 60,
                "parejas": [
                    (
                        {"tipo_ejercicio": "Accesorio", "patrones": ["empuje","diagonal","landmine","militar","hombro"], "prioridad": 2},
                        {"tipo_ejercicio": "Accesorio", "patrones": ["traccion","vertical","jalon","dominada"], "prioridad": 2}
                    )
                ]
            },
            # --- Cinta (caminar) como en tus fotos ---
            "Caminar en cinta": {
                "tipo": "Caminar",
                "duracion_min": 12,
                "inclinacion": (3,6),
                "ritmo_kmh": (5.0, 5.6)
            },
        }
    },

    "Martes": {
        "meta": {"titulo": "Pierna: Dominante de Rodilla Pesado + Accesorios + Core"},
        "orden": [
            "Calentamiento Pierna",
            "Bloque Pesado Rodilla",
            "Circuito A: D. rodilla + D. cadera",
            "Accesorios Pierna / Finisher (opcional)"
        ],
        "reglas": {
            "Calentamiento Pierna": {
                "tipo": "Calentamiento",
                "tipo_ejercicio": "Movilidad",
                "patrones": ["cadera","tobillo","torácica","core"],
                "tags_incluye": ["movilidad"],
                "n": 4
            },
            "Bloque Pesado Rodilla": {
                "tipo": "CircuitoPar",
                "series_circuito": 3,
                "reps": "3-6",
                "RPE": (8,9),
                "descanso_entre_ej": 0,
                "descanso_entre_series": 120,
                "parejas": [
                    (
                        {"tipo_ejercicio": "Compuesto", "patrones": ["dominante de rodilla","sentadilla","bulgara","zancada","goblet"], "prioridad": 1},
                        {"tipo_ejercicio": "Core", "patrones": ["core","antirotacion","anti-extension"], "prioridad": 2}
                    )
                ]
            },
            "Circuito A: D. rodilla + D. cadera": {
                "tipo": "CircuitoPar",
                "series_circuito": 3,
                "reps": "8-12",
                "RPE": (7,8),
                "descanso_entre_ej": 0,
                "descanso_entre_series": 60,
                "parejas": [
                    (
                        {"tipo_ejercicio": "Accesorio", "patrones": ["dominante de rodilla","zancada","cajon","split"], "prioridad": 2},
                        {"tipo_ejercicio": "Accesorio", "patrones": ["dominante de cadera","peso muerto","puente","hip thrust","hinge"], "prioridad": 2}
                    )
                ]
            },
            "Accesorios Pierna / Finisher (opcional)": {
                "tipo": "CircuitoPar",
                "series_circuito": 2,
                "reps": "10-15",
                "RPE": (7,8),
                "descanso_entre_ej": 0,
                "descanso_entre_series": 45,
                "parejas": [
                    (
                        {"tipo_ejercicio": "Aislamiento", "patrones": ["cuadriceps","extensiones","sissy","step"], "prioridad": 3},
                        {"tipo_ejercicio": "Aislamiento", "patrones": ["isquio","femoral","curl nordico","puente","hip"], "prioridad": 3}
                    )
                ]
            }
        }
    },

    "Miércoles": {
        "meta": {"titulo": "Tracciones: Espalda/Bíceps + Movilidad cadera (compensatorio)"},
        "orden": [
            "Calentamiento Torso",
            "Potencia (Torso) / Bloque Pesado Tracción",
            "Circuito A: Tracción diagonal + Core/Salto",
            "Circuito B: Tracción horizontal + vertical ligera"
        ],
        "reglas": {
            "Calentamiento Torso": {
                "tipo": "Calentamiento",
                "tipo_ejercicio": "Movilidad",
                "patrones": ["hombro","torácica","escápula","core"],
                "tags_incluye": ["movilidad"],
                "n": 4
            },
            "Potencia (Torso) / Bloque Pesado Tracción": {
                "tipo": "CircuitoPar",
                "series_circuito": 3,
                "reps": "3-6",
                "RPE": (8,9),
                "parejas": [
                    (
                        {"tipo_ejercicio": "Compuesto", "patrones": ["traccion","dominada","remo pesado","pendlay"], "prioridad": 1},
                        {"tipo_ejercicio": "Accesorio", "patrones": ["empuje","ligero","flexion","press landmine"], "prioridad": 2}
                    )
                ]
            },
            "Circuito A: Tracción diagonal + Core/Salto": {
                "tipo": "CircuitoPar",
                "series_circuito": 3,
                "reps": "8-12",
                "RPE": (7,8),
                "parejas": [
                    (
                        {"tipo_ejercicio": "Accesorio", "patrones": ["traccion","diagonal","landmine row","cable row"], "prioridad": 2},
                        {"tipo_ejercicio": "Core", "patrones": ["core","anti-rotacion","anti extension","lanzamiento"], "prioridad": 2}
                    )
                ]
            },
            "Circuito B: Tracción horizontal + vertical ligera": {
                "tipo": "CircuitoPar",
                "series_circuito": 3,
                "reps": "8-12",
                "RPE": (7,8),
                "parejas": [
                    (
                        {"tipo_ejercicio": "Accesorio", "patrones": ["traccion","horizontal","remo","polea"], "prioridad": 2},
                        {"tipo_ejercicio": "Accesorio", "patrones": ["traccion","vertical","jalon","dominada asistida"], "prioridad": 2}
                    )
                ]
            }
        }
    },

    "Jueves": {
        "meta": {"titulo": "Pliometría + Intervalos de carrera"},
        "orden": ["Calentamiento Pierna", "Pliometría", "Carrera (intervalos)"],
        "reglas": {
            "Calentamiento Pierna": {
                "tipo": "Calentamiento",
                "tipo_ejercicio": "Movilidad",
                "patrones": ["cadera","tobillo","pie","core"],
                "tags_incluye": ["movilidad"],
                "n": 4
            },
            "Pliometría": {"tipo": "Pliometrico", "n": 2},
            "Carrera (intervalos)": {
                "tipo": "Carrera",
                "sesion": "6x400m Z4 rec 2'"
            }
        }
    },

    "Viernes": {
        "meta": {"titulo": "Pierna: Dominante de Cadera Pesado + Accesorios + Core"},
        "orden": [
            "Calentamiento Pierna",
            "Bloque Pesado Cadera",
            "Circuito A: D. cadera + D. rodilla",
            "Accesorios Pierna / Finisher (opcional)"
        ],
        "reglas": {
            "Calentamiento Pierna": {
                "tipo": "Calentamiento",
                "tipo_ejercicio": "Movilidad",
                "patrones": ["cadera","tobillo","core"],
                "tags_incluye": ["movilidad"],
                "n": 4
            },
            "Bloque Pesado Cadera": {
                "tipo": "CircuitoPar",
                "series_circuito": 3,
                "reps": "3-6",
                "RPE": (8,9),
                "parejas": [
                    (
                        {"tipo_ejercicio": "Compuesto", "patrones": ["dominante de cadera","peso muerto","hip thrust","hinge"], "prioridad": 1},
                        {"tipo_ejercicio": "Core", "patrones": ["core","antirotacion","anti-extension"], "prioridad": 2}
                    )
                ]
            },
            "Circuito A: D. cadera + D. rodilla": {
                "tipo": "CircuitoPar",
                "series_circuito": 3,
                "reps": "8-12",
                "RPE": (7,8),
                "parejas": [
                    (
                        {"tipo_ejercicio": "Accesorio", "patrones": ["dominante de cadera","gluteo","isquio","aductor"], "prioridad": 2},
                        {"tipo_ejercicio": "Accesorio", "patrones": ["dominante de rodilla","zancada","cajon","sentadilla goblet"], "prioridad": 2}
                    )
                ]
            },
            "Accesorios Pierna / Finisher (opcional)": {
                "tipo": "CircuitoPar",
                "series_circuito": 2,
                "reps": "10-15",
                "RPE": (7,8),
                "parejas": [
                    (
                        {"tipo_ejercicio": "Aislamiento", "patrones": ["isometrico","curl nordico","isquio"], "prioridad": 3},
                        {"tipo_ejercicio": "Aislamiento", "patrones": ["gemelo","pantorrilla","tibial"], "prioridad": 3}
                    )
                ]
            }
        }
    },

    "Sábado": {
        "meta": {"titulo": "Full Body / Metabólico"},
        "orden": [
            "Calentamiento Mixto",
            "Circuito A: Empuje + D. rodilla + Core",
            "Circuito B: Tracción + D. cadera + Core",
            "Finisher Metabólico (opcional)"
        ],
        "reglas": {
            "Calentamiento Mixto": {
                "tipo": "Calentamiento",
                "tipo_ejercicio": "Movilidad",
                "patrones": ["hombro","torácica","cadera","tobillo","core"],
                "tags_incluye": ["movilidad"],
                "n": 4
            },
            "Circuito A: Empuje + D. rodilla + Core": {
                "tipo": "CircuitoPar",
                "series_circuito": 3,
                "reps": "8-12",
                "RPE": (7,8),
                "parejas": [
                    (
                        {"tipo_ejercicio": "Accesorio", "patrones": ["empuje","press","flexion"], "prioridad": 2},
                        {"tipo_ejercicio": "Accesorio", "patrones": ["dominante de rodilla","zancada","sentadilla"], "prioridad": 2}
                    )
                ]
            },
            "Circuito B: Tracción + D. cadera + Core": {
                "tipo": "CircuitoPar",
                "series_circuito": 3,
                "reps": "8-12",
                "RPE": (7,8),
                "parejas": [
                    (
                        {"tipo_ejercicio": "Accesorio", "patrones": ["traccion","remo","jalon"], "prioridad": 2},
                        {"tipo_ejercicio": "Accesorio", "patrones": ["dominante de cadera","peso muerto","hip thrust","hinge"], "prioridad": 2}
                    )
                ]
            },
            "Finisher Metabólico (opcional)": {
                "tipo": "CircuitoPar",
                "series_circuito": 2,
                "reps": "20''/40''",
                "RPE": (7,8),
                "parejas": [
                    (
                        {"tipo_ejercicio": "Aislamiento", "patrones": ["metabolico","hiit","tabata"], "prioridad": 3},
                        {"tipo_ejercicio": "Core", "patrones": ["core"], "prioridad": 2}
                    )
                ]
            }
        }
    },

    "Domingo": {
        "meta": {"titulo": "Recuperación Activa + Movilidad"},
        "orden": ["Calentamiento Suave", "Caminar suave"],
        "reglas": {
            "Calentamiento Suave": {
                "tipo": "Calentamiento",
                "tipo_ejercicio": "Movilidad",
                "patrones": ["movilidad","respiracion","neurocognitivo","hombro","cadera","tobillo","torácica"],
                "tags_incluye": ["movilidad"],
                "n": 4
            },
            "Caminar suave": {
                "tipo": "Caminar",
                "duracion_min": 20,
                "inclinacion": (1,3),
                "ritmo_kmh": (4.5, 5.2)
            }
        }
    }
}
