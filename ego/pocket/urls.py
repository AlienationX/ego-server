from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PokemonViewSet, PlayerViewSet, UserPokemonViewSet, PokedexViewSet, CatchAPIView

router = DefaultRouter()
router.register(r'pokemon', PokemonViewSet, basename='pokemon')
router.register(r'player', PlayerViewSet, basename='player')
router.register(r'user-pokemon', UserPokemonViewSet, basename='user-pokemon')
router.register(r'pokedex', PokedexViewSet, basename='pokedex')

urlpatterns = [
    path('', include(router.urls)),
    path('catch/', CatchAPIView.as_view(), name='catch'),
]
