from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CatchAPIView, PlayerPokemonViewSet, PlayerViewSet, PokedexViewSet, PokemonViewSet

router = DefaultRouter()
router.register(r"pokemon", PokemonViewSet, basename="pokemon")
router.register(r"player", PlayerViewSet, basename="player")
router.register(r"user-pokemon", PlayerPokemonViewSet, basename="user-pokemon")
router.register(r"pokedex", PokedexViewSet, basename="pokedex")

urlpatterns = [
    path("", include(router.urls)),
    path("catch/", CatchAPIView.as_view(), name="catch"),
]
