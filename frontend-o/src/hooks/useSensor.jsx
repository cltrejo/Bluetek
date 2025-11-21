import { useState, useEffect } from "react";
import endpoints from "../api";

export function useSensor() {
    const [zonas, setZonas] = useState([]);
    const [idZonaSeleccionada, setIdZonaSeleccionada] = useState(null);
    const [cargando, setCargando] = useState(true);

    // Derivar la habitación seleccionada directamente desde habitaciones
    const zonaSeleccionada = zonas.find(
        h => h.id_zona  === idZonaSeleccionada
    );

    useEffect(() => {
        obtenerZonas();

        const intervaloSimulacion = setInterval(() => {
            simularCambiosTemperatura();
        }, 300000);

        return () => clearInterval(intervaloSimulacion);
    }, []);

    const obtenerZonas = async () => {
        try {
            setCargando(true);
            const { data } = await endpoints.zonas.listar();

            console.log("Zonas recibidas:", data);
            setZonas(data);

            if (data.length > 0 && !idZonaSeleccionada) {
                setIdZonaSeleccionada(data[0].id_zona);
                console.log("Zona inicial seleccionada:", data[0].nombre);
            }
        } catch (error) {
            console.log("Error obteniendo zonas:", error)
            if (error.response?.status === 401){
                console.warn("Token invalido")
            }
        } finally {
            setCargando(false)
        }
    };

    const simularCambiosTemperatura = async () => {
        try {
            console.log("🔄 Simulando cambios de temperatura...");

            await endpoints.simulacion.temperatura();

            const { data } = await endpoints.zonas.listar();
            setZonas(data);

        } catch (error) {
            console.error("Error simulando temperatura:", error);
        }
    };

    return {
        zonas,
        zonaSeleccionada,
        idZonaSeleccionada,
        setIdZonaSeleccionada,
        cargando,
        obtenerZonas,
        simularCambiosTemperatura
    };
}
