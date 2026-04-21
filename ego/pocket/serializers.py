from rest_framework import serializers
from .models import Player, Pokemon, UserPokemon, Pokedex


class PlayerSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Player
        fields = ['id', 'username', 'coins', 'pokeballs']


class PokemonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pokemon
        fields = '__all__'


class UserPokemonSerializer(serializers.ModelSerializer):
    pokemon_info = PokemonSerializer(source='pokemon', read_only=True)

    class Meta:
        model = UserPokemon
        fields = ['id', 'pokemon', 'pokemon_info', 'nickname', 'iv', 'catch_time']


class PokedexSerializer(serializers.ModelSerializer):
    pokemon_info = PokemonSerializer(source='pokemon', read_only=True)

    class Meta:
        model = Pokedex
        fields = ['id', 'pokemon', 'pokemon_info', 'is_seen', 'is_caught']
