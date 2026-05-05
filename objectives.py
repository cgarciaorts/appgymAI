# objectives.py
from typing import Dict, List

# Palabras clave que suman puntos si están en categoria/subcategoria/ejercicio
OBJ_PROFILES: Dict[str, Dict] = {
    "General (BAU)": {
        "keywords": ["movilidad","core","empuje","traccion","dominante de rodilla","dominante de cadera","cardio","hiit","metabolico"],
        "rep_rpe_overrides": {},   # usa lo de tus reglas por defecto
        "weekly_repeat_penalty": True,
    },
    "Pérdida de grasa": {
        "keywords": ["hiit","metabolico","circuito","core","cardio","caminar","carrera","pliometria","tabata"],
        "rep_rpe_overrides": {
            "CircuitoPar": {"reps": "12-15", "RPE": (7,8)},
            "Caminar": {}, "Carrera": {},
        },
        "weekly_repeat_penalty": True,
    },
    "Fuerza torso": {
        "keywords": ["empuje","press","banca","militar","traccion","remo","dominada","jalon","hombro","espalda","pecho","biceps","triceps"],
        "rep_rpe_overrides": {
            "CircuitoPar": {"reps": "3-6", "RPE": (8,9)},
        },
        "weekly_repeat_penalty": True,
    },
    "Movilidad / Rehabilitación": {
        "keywords": ["movilidad","torácica","escápula","cadera","tobillo","respiracion","isometrico","neurocognitivo"],
        "rep_rpe_overrides": {
            "CircuitoPar": {"reps": "8-10", "RPE": (6,7)},
        },
        "weekly_repeat_penalty": False,
    },
}
