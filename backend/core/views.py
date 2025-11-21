import random
from django.shortcuts import render
from django.utils import timezone

# Create your views here.
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model
from .serializers import ZonaSerializer, MedicionSerializer, ThermostatoSerializer, UserSerializer, LoginSerializer
from rest_framework.permissions import IsAuthenticated
from .models import ZONA, MEDICION_THERMOSTATO, THERMOSTATO, SENSOR, MEDICION_SENSOR, MATERIAL_ZONA
import pandas as pd
import joblib
import os
from django.conf import settings
from django.http import JsonResponse
import numpy as np

User = get_user_model()


try:
    model_path = 'C:/Users/PC/Desktop/Capstone/backend/modelo/modelo_temp.pkl'
    model = joblib.load(model_path)    
    MODEL_LOADED = True
    print("✅ Modelo cargado exitosamente")
except Exception as e:
    model = None
    MODEL_LOADED = False
    print(f"❌ Error cargando modelo: {e}")

import numpy as np
import pandas as pd
from django.http import JsonResponse


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def predecir_temperatura(request):
    """
    Endpoint para hacer predicciones con el modelo para las próximas 3 horas
    en intervalos de 30 minutos
    """
    if not MODEL_LOADED:
        return JsonResponse({
            'error': 'Modelo no disponible'
        }, status=500)
    
    try:
        # Obtener datos del request
        data = request.data
        timestamp = data.get('timestamp')
        zoneName = data.get('zoneName', 'Juegos')
        
        if not timestamp:
            return JsonResponse({
                'error': 'Se requiere el campo timestamp'
            }, status=400)
        
        # Convertir timestamp base a datetime
        timestamp_base = pd.to_datetime(timestamp)
        
        # Crear lista de timestamps para las próximas 3 horas (cada 30 minutos)
        timestamps_futuros = []
        for minutos in [20, 40, 60, 80]:  # 0.5h, 1h, 1.5h, 2h, 2.5h, 3h
            timestamps_futuros.append(timestamp_base + pd.Timedelta(minutes=minutos))
        
        # Crear DataFrame con todos los timestamps futuros
        df_futuro = pd.DataFrame({'timestamp': timestamps_futuros})
        
        # Extraer características temporales para cada timestamp futuro
        df_futuro['año'] = df_futuro['timestamp'].dt.year
        df_futuro['mes'] = df_futuro['timestamp'].dt.month
        df_futuro['dia'] = df_futuro['timestamp'].dt.day
        df_futuro['hora'] = df_futuro['timestamp'].dt.hour
        df_futuro['minuto'] = df_futuro['timestamp'].dt.minute
        df_futuro['dia_semana'] = df_futuro['timestamp'].dt.dayofweek  # 0=Lunes, 6=Domingo
        
        # Mapeo de RH por hora (basado en tus datos)
        rh_por_hora = {
            0: 25, 1: 21, 2: 21, 3: 21, 4: 21, 5: 21,
            6: 21, 7: 22, 8: 23, 9: 25, 10: 26, 11: 28,
            12: 30, 13: 30, 14: 32, 15: 34, 16: 37, 17: 40,
            18: 42, 19: 42, 20: 42, 21: 37, 22: 33, 23: 30
        }
        
        # Agregar zoneName y rh (usando la hora para el mapeo)
        df_futuro['zoneName'] = zoneName
        df_futuro['rh'] = df_futuro['hora'].map(rh_por_hora)
        
        # Verificar que no hay valores nulos en rh
        if df_futuro['rh'].isna().any():
            print("Advertencia: Algunas horas no tienen mapeo de RH")
            # Usar valor promedio como fallback
            promedio_rh = sum(rh_por_hora.values()) / len(rh_por_hora)
            df_futuro['rh'] = df_futuro['rh'].fillna(promedio_rh)
        
        # Transformar ciclos
        df_futuro["hora_sin"] = np.sin(2 * np.pi * df_futuro["hora"] / 24)
        df_futuro["hora_cos"] = np.cos(2 * np.pi * df_futuro["hora"] / 24)
        
        df_futuro["minuto_sin"] = np.sin(2 * np.pi * df_futuro["minuto"] / 60)
        df_futuro["minuto_cos"] = np.cos(2 * np.pi * df_futuro["minuto"] / 60)
        
        df_futuro["dia_sem_sin"] = np.sin(2 * np.pi * df_futuro["dia_semana"] / 7)
        df_futuro["dia_sem_cos"] = np.cos(2 * np.pi * df_futuro["dia_semana"] / 7)
        
        df_futuro["mes_sin"] = np.sin(2 * np.pi * df_futuro["mes"] / 12)
        df_futuro["mes_cos"] = np.cos(2 * np.pi * df_futuro["mes"] / 12)
        
        # Eliminar columnas originales
        df_futuro = df_futuro.drop(columns=['timestamp', 'hora', 'minuto', 'dia_semana', 'mes'])
        
        # Convertir zoneName a categoría
        df_futuro['zoneName'] = df_futuro['zoneName'].astype('category')
        
        # Verificar estructura final
        print("Estructura del DataFrame para predicciones futuras:")
        print(df_futuro.info())
        print(f"\nSe harán {len(df_futuro)} predicciones")
        
        
        # Hacer predicciones para todos los timestamps futuros
        predicciones = model.predict(df_futuro)
        
        # Crear respuesta con las predicciones organizadas por tiempo
        respuesta = {
            'timestamp_base': timestamp,
            'zoneName': zoneName,
            'predicciones': []
        }
        
        # Intervalos de tiempo en minutos
        intervalos = [20, 40, 60, 80]
        
        for i, (minutos, prediccion, rh_val) in enumerate(zip(intervalos, predicciones, df_futuro['rh'])):
            # Calcular timestamp futuro
            timestamp_futuro = (timestamp_base + pd.Timedelta(minutes=minutos)).strftime('%Y-%m-%dT%H:%M:%S')
            
            respuesta['predicciones'].append({
                'minutos_desde_base': minutos,
                'timestamp_prediccion': timestamp_futuro,
                'temperatura_predicha': float(prediccion),
                'rh_utilizado': float(rh_val),
                'intervalo': f"{minutos//60}h {minutos%60}min" if minutos >= 60 else f"{minutos}min"
            })
        
        respuesta['status'] = 'success'
        
        return JsonResponse(respuesta)
        
    except Exception as e:
        return JsonResponse({
            'error': f'Error en la predicción: {str(e)}'
        }, status=400)




@api_view(['POST'])
#ENDPOINT PREVIAMENTE CON AUTENTICACION REQUERIDA @permission_classes((IsAuthenticated,))
def registro(request):
    # Datos del request
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    nombre = request.data.get('first_name', '')
    apellido = request.data.get('last_name', '')
    tipo_usuario = request.data.get('tipo_usuario', 'COMUN')  # Por defecto

    # Validaciones básicas
    if not username or not password:
        return Response({'error': 'Debe ingresar un nombre de usuario y contraseña.'}, status=400)

    if User.objects.filter(username=username).exists():
        return Response({'error': 'El usuario ya existe.'}, status=400)

    # Crear usuario común
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        nombre=nombre,
        apellido=apellido,
        tipo_usuario=tipo_usuario
    )

    token, created = Token.objects.get_or_create(user=user)

    return Response({
        'token': token.key,
        'user': UserSerializer(user).data
    }, status=200)

@api_view(['POST'])
def login(request):
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user': UserSerializer(user).data
        })
    return Response(serializer.errors, status=400)

@api_view(['POST'])
def VerifyTokenView(request):
    token = request.headers.get("Authorization")
    if not token:
        return Response({"valid": False}, status=status.HTTP_401_UNAUTHORIZED)

    token = token.replace("Token ", "")
    try:
        token_obj = Token.objects.get(key=token)
        return Response({"valid": True, "user": token_obj.user.username}, status=status.HTTP_200_OK)
    except Token.DoesNotExist:
        return Response({"valid": False}, status=status.HTTP_401_UNAUTHORIZED)
    

# Endpoints a desarrollar (documentación)

@api_view(['GET', 'POST'])
@permission_classes((IsAuthenticated,))
def lista_zonas(request):
    if request.method == 'GET':
        query = ZONA.objects.all()
        serializer = ZonaSerializer(query, many = True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    elif request.method == 'POST':
        serializer = ZonaSerializer(data = request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.data, status=status.HTTP_400_BAD_REQUEST)
    

@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes((IsAuthenticated,))
def detalle_zona(request, id):
    try:
        zona = ZONA.objects.get(id_zona = id)
    except ZONA.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    if request.method == 'GET':
        serializer = ZonaSerializer(zona)
        return Response(serializer.data)
    elif request.method == 'PATCH':
        serializer = ZonaSerializer(zona, data = request.data, partial = True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    elif request.method == 'DELETE':
        zona.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
        
        
@api_view(['GET', 'POST'])
@permission_classes((IsAuthenticated,))
def lista_thermostatos(request):
    if request.method == 'GET':
        query = THERMOSTATO.objects.all()
        serializer = ThermostatoSerializer(query, many = True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    elif request.method == 'POST':
        serializer = ThermostatoSerializer(data = request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.data, status=status.HTTP_400_BAD_REQUEST)
        
@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def historico_thermostato( request, id):
    try:
        thermostato = THERMOSTATO.objects.get(id_thermostato = id)

        mediciones = MEDICION_THERMOSTATO.objects.filter(id_thermostato = id)

        serializer = MedicionSerializer(mediciones, many = True)

        return Response(serializer.data, status=status.HTTP_200_OK)
    
    except THERMOSTATO.DoesNotExist:
        
        return Response({'error': 'Sensor no encontrado'}, status=status.HTTP_404_NOT_FOUND)
    
@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def sensores_por_zona(request, id_zona):
    try:
        thermostatos = THERMOSTATO.objects.filter(id_zona=id_zona)
        if not thermostatos.exists():
            return Response(
                {"error": "No hay sensores asociados a esta zona"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ThermostatoSerializer(thermostatos, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    except ZONA.DoesNotExist:
        return Response(
            {"error": "Zona no encontrada"},
            status=status.HTTP_404_NOT_FOUND
        )


'''
POSIBLES ACTUALIZACIONES

@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def historico_sensor(request, id):
    try:
        sensor = Sensor.objects.get(id=id)
        
        # Opcional: parámetros para filtrar por fecha o límite
        limit = request.GET.get('limit')  # /api/sensores/1/mediciones/?limit=50
        since = request.GET.get('since')  # /api/sensores/1/mediciones/?since=2024-01-01
        
        mediciones = Medicion.objects.filter(sensor=id)
        
        # Filtrar por fecha si se proporciona
        if since:
            mediciones = mediciones.filter(timestamp__gte=since)
        
        # Ordenar por timestamp (más recientes primero) y limitar si se especifica
        mediciones = mediciones.order_by('-timestamp')
        
        if limit:
            mediciones = mediciones[:int(limit)]
        
        serializer = MedicionSerializer(mediciones, many=True)
        return Response({
            'sensor': SensorSerializer(sensor).data,
            'mediciones': serializer.data,
            'total': mediciones.count()
        }, status=status.HTTP_200_OK)
        
    except Sensor.DoesNotExist:
        return Response(
            {'error': 'Sensor no encontrado'}, 
            status=status.HTTP_404_NOT_FOUND
        )

'''

        
@api_view(['GET', 'POST'])
@permission_classes((IsAuthenticated,))
def lista_mediciones(request):
    if request.method == 'GET':
        query = MEDICION_THERMOSTATO.objects.all()
        serializer = MedicionSerializer(query, many = True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    elif request.method == 'POST':
        serializer = MedicionSerializer(data = request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.data, status=status.HTTP_400_BAD_REQUEST)
        

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def simular_temperatura(request):
    """
    Simula cambios de temperatura para todos los sensores activos
    """
    thermostatos = THERMOSTATO.objects.all()
    
    for thermostato in thermostatos:
        # Simular temperatura entre 18°C y 30°C con variación realista
        temperatura_anterior = MEDICION_THERMOSTATO.objects.filter(id_thermostato=thermostato).last()
        
        if temperatura_anterior:
            temp_anterior = float(temperatura_anterior.valor)
            # Variación de ±2°C respecto a la anterior
            nueva_temperatura = temp_anterior + random.uniform(-2.0, 2.0)
            nueva_temperatura = max(18.0, min(30.0, nueva_temperatura))  # Limitar entre 18-30
        else:
            nueva_temperatura = random.uniform(20.0, 25.0)  # Temperatura inicial

        nueva_temperatura = round(nueva_temperatura, 2)

        # 🔹 Fecha actual sin microsegundos ni tzinfo
        timestamp = timezone.now().replace(microsecond=0, tzinfo=None)  
        
        MEDICION_THERMOSTATO.objects.create(
            id_thermostato=thermostato,
            valor=nueva_temperatura,
            unidad='°C',
            timestamp=timestamp
        )

        zona_thermostato = thermostato.id_zona
        sensores_activos = SENSOR.objects.filter(id_zona=zona_thermostato, activo=True)
        
        for sensor in sensores_activos:
            # Calcular consumo de energía basado en la temperatura
            if nueva_temperatura <= 21.0:
                # Temperatura baja - consumo mínimo o cero
                consumo_energia = 0.0
            elif nueva_temperatura <= 24.0:
                # Temperatura moderada - consumo bajo
                consumo_energia = random.uniform(0.1, 0.5)
            else:
                # Temperatura alta - consumo alto (enfriamiento activo)
                consumo_energia = random.uniform(0.6, 1.2)
            
            consumo_energia = round(consumo_energia, 2)
            
            # Crear medición del sensor de energía
            MEDICION_SENSOR.objects.create(
                id_sensor=sensor,
                valor=consumo_energia,
                unidad='kWh',  # o la unidad que uses para energía
                timestamp=timestamp
            )
    
    return Response({"message": f"Temperaturas simuladas para {thermostatos.count()} sensores"})

@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def dashboard_zona(request, id_zona):
    try:
        # 1. Obtener información básica de la zona
        zona = ZONA.objects.select_related('id_tipozona').get(id_zona=id_zona)
        
        # 2. Obtener materiales de la zona
        materiales = MATERIAL_ZONA.objects.filter(id_zona=id_zona).values('nombre', 'cantidad_m2')
        
        # 3. Obtener thermostatos de la zona y sus últimas mediciones
        thermostatos = THERMOSTATO.objects.filter(id_zona=id_zona)
        mediciones_thermostatos = MEDICION_THERMOSTATO.objects.filter(
            id_thermostato__in=thermostatos
        ).order_by('timestamp')
        
        # 4. Obtener sensores activos de la zona y sus últimas mediciones
        sensores = SENSOR.objects.filter(id_zona=id_zona, activo=True)
        mediciones_sensores = MEDICION_SENSOR.objects.filter(
            id_sensor__in=sensores
        ).order_by('timestamp')
        
        # 5. Temperatura actual (última medición del thermostato)
        temperatura_actual = None
        ultima_medicion = mediciones_thermostatos.first()
        if ultima_medicion:
            temperatura_actual = ultima_medicion.valor
        
        # 6. Construir respuesta consolidada
        response_data = {
            'zona': {
                'id_zona': zona.id_zona,
                'nombre': zona.nombre,
                'descripcion': zona.descripcion,
                'orientacion': zona.orientacion,
                'superficie_m3': zona.superficie_m3,
                'cantidad_equipos': zona.cantidad_equipos,
                'forma_svg': zona.forma_svg,
                'temperatura_actual': temperatura_actual,
                'tipo_zona': zona.id_tipozona.nombre if zona.id_tipozona else None
            },
            'materiales': list(materiales),
            'thermostatos': [
                {
                    'id_thermostato': t.id_thermostato,
                    'nombre': t.nombre,
                    'mediciones': [
                        {
                            'valor': m.valor,
                            'unidad': m.unidad,
                            'timestamp': m.timestamp
                        } for m in mediciones_thermostatos if m.id_thermostato == t
                    ]
                } for t in thermostatos
            ],
            'sensores': [
                {
                    'id_sensor': s.id_sensor,
                    'tipo': s.tipo,
                    'nombre': s.nombre,
                    'mediciones': [
                        {
                            'valor': m.valor,
                            'unidad': m.unidad,
                            'timestamp': m.timestamp
                        } for m in mediciones_sensores if m.id_sensor == s
                    ]
                } for s in sensores
            ]
        }
        
        return Response(response_data)
        
    except ZONA.DoesNotExist:
        return Response({"error": "Zona no encontrada"}, status=404)