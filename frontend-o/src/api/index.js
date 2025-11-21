import api from "./axios";

const endpoints = {
    auth: {
        login: (data) => api.post("/api/login/", data),
        verifyToken: (token) =>
            api.post("/api/verify-token/", null, {
                headers: { Authorization: `Token ${token}` },
        }),
        registro: (data) => api.post("/api/registro/", data),
    },

    zonas: {
        listar: () => api.get("/api/lista_zonas/"),
        dashboard: (id) => api.get(`/api/dashboard_zona/${id}/`),
        sensores: (id) => api.get(`/api/habitaciones/${id}/sensores/`),
    },

    simulacion: {
        temperatura: (data) => api.post("/api/simular_temperatura/", data),
    },

    predicciones: {
        predecirTemperatura: (data) => api.post("/modelo/predecir_temperatura/", data),
    },
};

export default endpoints;