import random
from rest_framework import viewsets, permissions, status, views
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth.models import User
from .models import Player, Pokemon, UserPokemon, Pokedex
from .serializers import PlayerSerializer, PokemonSerializer, UserPokemonSerializer, PokedexSerializer

# We mock a default user for MVP since no auth is fully set up yet.
def get_default_user():
    user, _ = User.objects.get_or_create(username="default_player")
    Player.objects.get_or_create(user=user)
    return user

class PokemonViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Pokemon.objects.all().order_by('id')
    serializer_class = PokemonSerializer
    permission_classes = [permissions.AllowAny]

class PlayerViewSet(viewsets.GenericViewSet):
    serializer_class = PlayerSerializer
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=['get'])
    def me(self, request):
        # Use default user for MVP
        user = get_default_user()
        player = user.player
        serializer = self.get_serializer(player)
        return Response(serializer.data)
        
    @action(detail=False, methods=['post'])
    def buy_pokeballs(self, request):
        user = get_default_user()
        player = user.player
        amount = int(request.data.get('amount', 10))
        cost = amount * 10 # 10 coins per pokeball
        
        if player.coins >= cost:
            player.coins -= cost
            player.pokeballs += amount
            player.save()
            return Response(self.get_serializer(player).data)
        return Response({"error": "Not enough coins"}, status=status.HTTP_400_BAD_REQUEST)

class UserPokemonViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserPokemonSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        user = get_default_user()
        return UserPokemon.objects.filter(user=user).order_by('-catch_time')

class PokedexViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PokedexSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        user = get_default_user()
        return Pokedex.objects.filter(user=user)

class CatchAPIView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # Encounter a random pokemon
        # For a real game, this might be based on weather, location, etc.
        count = Pokemon.objects.count()
        if count == 0:
            return Response({"error": "No pokemon available"}, status=status.HTTP_404_NOT_FOUND)
            
        random_index = random.randint(0, count - 1)
        pokemon = Pokemon.objects.all()[random_index]
        
        # Mark as seen in pokedex
        user = get_default_user()
        pokedex_entry, created = Pokedex.objects.get_or_create(user=user, pokemon=pokemon)
        if not pokedex_entry.is_seen:
            pokedex_entry.is_seen = True
            pokedex_entry.save()
            
        serializer = PokemonSerializer(pokemon)
        return Response(serializer.data)

    def post(self, request):
        # Attempt to catch
        pokemon_id = request.data.get('pokemon_id')
        if not pokemon_id:
            return Response({"error": "pokemon_id is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            pokemon = Pokemon.objects.get(id=pokemon_id)
        except Pokemon.DoesNotExist:
            return Response({"error": "Pokemon not found"}, status=status.HTTP_404_NOT_FOUND)
            
        user = get_default_user()
        player = user.player
        
        if player.pokeballs <= 0:
            return Response({"error": "No pokeballs left!"}, status=status.HTTP_400_BAD_REQUEST)
            
        # Consume 1 pokeball
        player.pokeballs -= 1
        player.save()
        
        # Simple probability algorithm: 50% chance to catch
        # Later we can add weather modifiers, berry modifiers, etc.
        catch_chance = 0.5
        success = random.random() < catch_chance
        
        if success:
            # Generate IV (0-31)
            iv = random.randint(0, 31)
            user_pokemon = UserPokemon.objects.create(
                user=user,
                pokemon=pokemon,
                iv=iv
            )
            
            # Update Pokedex
            pokedex_entry, _ = Pokedex.objects.get_or_create(user=user, pokemon=pokemon)
            pokedex_entry.is_seen = True
            pokedex_entry.is_caught = True
            pokedex_entry.save()
            
            return Response({
                "success": True, 
                "message": f"Gotcha! {pokemon.name} was caught!",
                "data": UserPokemonSerializer(user_pokemon).data,
                "player": PlayerSerializer(player).data
            })
        else:
            return Response({
                "success": False, 
                "message": f"Oh no! {pokemon.name} broke free!",
                "player": PlayerSerializer(player).data
            })
