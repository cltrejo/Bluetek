import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from "recharts";
import Header from "../components/Header";
import './DetalleSensor.css';
import endpoints from "../api";

export function Dashboard() {
  const { id } = useParams();
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("1h");
  const [chartData, setChartData] = useState([]);
  const [predicciones, setPredicciones] = useState([]);
  const [cargandoPredicciones, setCargandoPredicciones] = useState(false);

  useEffect(() => {
    async function fetchDashboardData() {
      setLoading(true);
      try {
        const { data } = await endpoints.zonas.dashboard(id);
        console.log("Dashboard data recibida:", data);
        
        setDashboardData(data);
        
        // Procesar datos para el gráfico
        processChartData(data, filter);
        
        // 🔥 Cargar predicciones automáticamente
        cargarPredicciones(data);
        
      } catch (err) {
        console.error("Error fetching dashboard:", err);
      }
      setLoading(false);
    }

    fetchDashboardData();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // 🔥 Función para cargar predicciones
  const cargarPredicciones = async (data) => {
    if (!data || !data.zona) return;
    
    setCargandoPredicciones(true);
    try {
      const ahora = new Date();
      const timestampActual = new Date(ahora.getTime() - (3 * 60 * 60 * 1000)).toISOString();
      const datosPrediccion = {
        timestamp: timestampActual
      };

      console.log("Solicitando predicciones con:", datosPrediccion);
      
      const response = await endpoints.predicciones.predecirTemperatura(datosPrediccion);
      console.log("Predicciones recibidas:", response.data);
      
      setPredicciones(response.data.predicciones || []);
      
    } catch (error) {
      console.error("Error cargando predicciones:", error);
      setPredicciones([]);
    }
    setCargandoPredicciones(false);
  };

  // 🔥 Función para formatear las predicciones para el gráfico
  const formatearPredicciones = (preds) => {
    return preds.map(pred => ({
      timestamp: new Date(pred.timestamp_prediccion).toLocaleTimeString([], { 
        hour: '2-digit', 
        minute: '2-digit' 
      }),
      prediccion: parseFloat(pred.temperatura_predicha),
      tipo: 'prediccion',
      minutos: pred.minutos_desde_base,
      rh: pred.rh_utilizado
    }));
  };

  const processChartData = (data, currentFilter) => {
    if (!data.thermostatos || data.thermostatos.length === 0) {
      setChartData([]);
      return;
    }

    // Tomamos las mediciones del primer thermostato
    const mediciones = data.thermostatos[0].mediciones;

    const now = new Date();
    let cutoff;
    if (currentFilter === "1h") cutoff = new Date(now - 1 * 60 * 60 * 1000);
    else if (currentFilter === "6h") cutoff = new Date(now - 6 * 60 * 60 * 1000);
    else if (currentFilter === "24h") cutoff = new Date(now - 24 * 60 * 60 * 1000);
    else if (currentFilter === "7d") cutoff = new Date(now - 7 * 24 * 60 * 60 * 1000);

    // Filtramos datos recientes
    const filtered = mediciones.filter(m => new Date(m.timestamp) >= cutoff);

    // Determinamos el intervalo de agrupación
    let intervalMs;
    if (currentFilter === "1h") intervalMs = 1 * 60 * 1000;         // cada minuto
    else if (currentFilter === "6h") intervalMs = 5 * 60 * 1000;     // cada 5 min
    else if (currentFilter === "24h") intervalMs = 30 * 60 * 1000;   // cada 30 min
    else if (currentFilter === "7d") intervalMs = 3 * 60 * 60 * 1000; // cada 3 horas

    // Agrupar por intervalos
    const grouped = {};
    filtered.forEach(m => {
      const ts = new Date(m.timestamp);
      const bucket = Math.floor(ts.getTime() / intervalMs) * intervalMs;
      if (!grouped[bucket]) grouped[bucket] = [];
      grouped[bucket].push(parseFloat(m.valor));
    });

    // Calcular promedios por grupo
    const datosReales = Object.entries(grouped).map(([bucket, values]) => ({
      timestamp: new Date(parseInt(bucket)).toLocaleTimeString([], { 
        hour: '2-digit', 
        minute: '2-digit' 
      }),
      valor: values.reduce((a, b) => a + b, 0) / values.length,
      tipo: 'real'
    }));

    // 🔥 Combinar datos reales con predicciones
    const prediccionesFormateadas = formatearPredicciones(predicciones);
    const datosCombinados = [...datosReales, ...prediccionesFormateadas];

    // Ordenar por timestamp para mejor visualización
    datosCombinados.sort((a, b) => {
      const timeA = new Date(a.timestamp.includes('T') ? a.timestamp : `1970-01-01T${a.timestamp}`);
      const timeB = new Date(b.timestamp.includes('T') ? b.timestamp : `1970-01-01T${b.timestamp}`);
      return timeA - timeB;
    });

    setChartData(datosCombinados);
  };

  // 🔥 Efecto para reprocesar datos cuando cambian las predicciones
  useEffect(() => {
    if (dashboardData) {
      processChartData(dashboardData, filter);
    }
  }, [filter, dashboardData, predicciones]);

  // 🔥 Función para renderizar tooltip personalizado
  const renderTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      
      return (
        <div className="custom-tooltip">
          <p className="tooltip-label">{`Hora: ${label}`}</p>
          {data.tipo === 'prediccion' ? (
            <>
              <p className="tooltip-value" style={{ color: '#ff7f0e' }}>
                {`Predicción: ${data.prediccion}°C`}
              </p>
              <p className="tooltip-detail">{`En ${data.minutos} minutos`}</p>
              <p className="tooltip-detail">{`RH: ${data.rh}%`}</p>
            </>
          ) : (
            <p className="tooltip-value" style={{ color: '#007BFF' }}>
              {`Temperatura: ${data.valor}°C`}
            </p>
          )}
        </div>
      );
    }
    return null;
  };

  if (loading) return <p>Cargando dashboard...</p>;
  if (!dashboardData) return <p>No se pudo cargar el dashboard</p>;

  const { zona, materiales, thermostatos, sensores } = dashboardData;

  return (
    <div className="dashboard-content">
      <Header />
      <div className="dashboard-wrapper">
        <h2 className="zona-title">{zona.nombre || "Zona desconocida"}</h2>

        {/* 🔥 Botón para recargar predicciones */}
        <div className="predicciones-header">
          <div className="filters">
            {["1h", "6h", "24h", "7d"].map((f) => (
              <button
                key={f}
                className={`filter-btn ${filter === f ? "active" : ""}`}
                onClick={() => setFilter(f)}
              >
                Últimas {f}
              </button>
            ))}
          </div>
          
          <button 
            className="btn-predicciones"
            onClick={() => cargarPredicciones(dashboardData)}
            disabled={cargandoPredicciones}
          >
            {cargandoPredicciones ? "Cargando..." : "🔄 Actualizar Predicciones"}
          </button>
        </div>

        {/* 🔹 Indicadores rápidos */}
        <div className="stats-grid">
          <div className="stat-card">
            <h3>Temperatura Actual</h3>
            <p className="stat-value">
              {zona.temperatura_actual ? `${zona.temperatura_actual}°C` : "N/D"}
            </p>
          </div>

          <div className="stat-card">
            <h3>Predicciones Activas</h3>
            <p className="stat-value">
              {predicciones.length > 0 ? `${predicciones.length} pronósticos` : "Sin datos"}
            </p>
          </div>

          <div className="stat-card">
            <h3>Material principal</h3>
            <p>{materiales[0]?.nombre || "Desconocido"}</p>
          </div>

          <div className="stat-card">
            <h3>Superficie</h3>
            <p>{zona.superficie_m3 || "Desconocido"} m³</p>
          </div>
        </div>

        {/* 🔹 Gráfico histórico con predicciones */}
        <div className="chart-section">
          <h3>Evolución de la temperatura {predicciones.length > 0 && "(con predicciones)"}</h3>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="timestamp" />
              <YAxis label={{ value: 'Temperatura (°C)', angle: -90, position: 'insideLeft' }} />
              <Tooltip content={renderTooltip} />
              <Legend />
              
              {/* Línea de datos reales */}
              <Line 
                type="monotone" 
                dataKey="valor" 
                stroke="#007BFF" 
                strokeWidth={2}
                dot={{ r: 3 }}
                activeDot={{ r: 6 }}
                name="Temperatura Real"
                connectNulls
              />
              
              {/* 🔥 Línea de predicciones */}
              <Line 
                type="monotone" 
                dataKey="prediccion" 
                stroke="#ff7f0e" 
                strokeWidth={3}
                strokeDasharray="5 5"
                dot={{ r: 5, fill: "#ff7f0e" }}
                activeDot={{ r: 8, fill: "#ff7f0e" }}
                name="Predicción"
                connectNulls
              />
            </LineChart>
          </ResponsiveContainer>
          
          {/* 🔥 Leyenda de predicciones */}
          {predicciones.length > 0 && (
            <div className="predicciones-info">
              <h4>Próximas Predicciones:</h4>
              <div className="predicciones-grid">
                {predicciones.map((pred, index) => (
                  <div key={index} className="prediccion-item">
                    <span className="pred-time">{pred.intervalo}:</span>
                    <span className="pred-temp">{pred.temperatura_predicha}°C</span>
                    <span className="pred-rh">(RH: {pred.rh_utilizado}%)</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Resto del código permanece igual */}
        {thermostatos && thermostatos.length > 0 && (
          <div className="thermostats-section">
            <h3>Thermostatos</h3>
            <div className="thermostats-grid">
              {thermostatos.map(thermo => (
                <div key={thermo.id_thermostato} className="thermo-card">
                  <h4>{thermo.nombre}</h4>
                  <p>Mediciones recientes: {thermo.mediciones.length}</p>
                </div>
              ))}
            </div>
          </div>
        )}
        
        <hr />
        
        {sensores && sensores.length > 0 && (
          <div className="sensors-section">
            <h3>Sensores de Energía</h3>
            <div className="sensors-grid">
              {sensores.map(sensor => (
                <div key={sensor.id_sensor} className="sensor-card">
                  <h4>{sensor.nombre}</h4>
                  <p>Tipo: {sensor.tipo}</p>
                  <p>Última medición: {sensor.mediciones[0]?.valor || "N/D"} {sensor.mediciones[0]?.unidad || ""}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default Dashboard;