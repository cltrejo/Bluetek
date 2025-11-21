from django.urls import path
from .views import registro, login, VerifyTokenView, lista_zonas, lista_thermostatos, lista_mediciones, detalle_zona, historico_thermostato, simular_temperatura, sensores_por_zona, dashboard_zona, predecir_temperatura

urlpatterns = [
    path('api/registro/', registro, name='registro'),
    path('api/login/', login, name='login'),
    path("api/verify-token/", VerifyTokenView, name="verify_token"),
    path("api/lista_zonas/", lista_zonas, name="lista_zonas"),
    path("api/lista_thermostatos/", lista_thermostatos, name="lista_thermostatos"),
    path("api/lista_mediciones/", lista_mediciones, name="lista_mediciones"),
    path("api/detalle_zona/<int:id>/", detalle_zona, name="detalle_zona"),
    path("api/thermostatos/<int:id>/mediciones/", historico_thermostato, name="historico_thermostato"),
    path("api/simular_temperatura/", simular_temperatura, name="simular_temperatura"),
    path('api/habitaciones/<int:id_zona>/sensores/', sensores_por_zona, name="sensores_por_zona"),
    path('api/dashboard_zona/<int:id_zona>/', dashboard_zona, name='dashboard_zona'),
    path("modelo/predecir_temperatura/", predecir_temperatura, name="predecir_temperatura"),
]