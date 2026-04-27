from rest_framework import serializers
from .models import Player, PlayerPokemon, Pokedex, Pokemon, Ability, Move, Type


class TypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Type
        fields = ["id", "name", "name_zh", "name_en", "name_jp"]


class AbilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Ability
        fields = ["id", "name", "name_zh", "name_en", "name_jp", "flavor_text_zh", "effect_zh"]


class AbilityBriefSerializer(serializers.ModelSerializer):
    """轻量版特性序列化器，仅用于列表"""
    class Meta:
        model = Ability
        fields = ["id", "name_zh"]


class MoveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Move
        fields = ["id", "name", "name_zh", "name_en", "name_jp", "flavor_text_zh", "type_name", "power", "pp", "accuracy", "damage_class"]


class PlayerSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Player
        fields = ["id", "username", "coins", "pokeballs", "berries"]


# ========== Pokemon 列表序列化器（轻量） ==========
class PokemonListSerializer(serializers.ModelSerializer):
    """列表接口：只返回必要字段，不含 moves"""
    owned_count = serializers.IntegerField(read_only=True, default=0)
    types_detail = TypeSerializer(source="types", many=True, read_only=True)
    color_name = serializers.CharField(source="color.name_zh", read_only=True)

    class Meta:
        model = Pokemon
        fields = [
            "id", "index", "name", "name_zh", "name_en",
            "image", "genera", "generation",
            "types_detail", "color_name", "owned_count",
        ]


# ========== Pokemon 详情序列化器（完整） ==========
class PokemonDetailSerializer(serializers.ModelSerializer):
    """详情接口：返回全部字段，含 abilities 和 moves"""
    owned_count = serializers.IntegerField(read_only=True, default=0)
    types_detail = TypeSerializer(source="types", many=True, read_only=True)
    abilities_detail = AbilitySerializer(source="abilities", many=True, read_only=True)
    moves_detail = MoveSerializer(source="moves", many=True, read_only=True)

    color_name = serializers.CharField(source="color.name_zh", read_only=True)
    habitat_name = serializers.CharField(source="habitat.name_zh", read_only=True)
    shape_name = serializers.CharField(source="shape.name_zh", read_only=True)

    class Meta:
        model = Pokemon
        fields = "__all__"


# ========== PlayerPokemon 列表序列化器（轻量） ==========
class PlayerPokemonListSerializer(serializers.ModelSerializer):
    """用户持有列表：pokemon 只带基础信息"""
    pokemon_index = serializers.CharField(source="pokemon.index", read_only=True)
    pokemon_name_zh = serializers.CharField(source="pokemon.name_zh", read_only=True)
    pokemon_name_en = serializers.CharField(source="pokemon.name_en", read_only=True)
    pokemon_image = serializers.ImageField(source="pokemon.image", read_only=True)
    pokemon_id = serializers.IntegerField(source="pokemon.id", read_only=True)

    class Meta:
        model = PlayerPokemon
        fields = [
            "id", "pokemon", "pokemon_id", "pokemon_index",
            "pokemon_name_zh", "pokemon_name_en", "pokemon_image",
            "nickname", "iv", "catch_time",
        ]


# ========== PlayerPokemon 详情序列化器 ==========
class PlayerPokemonDetailSerializer(serializers.ModelSerializer):
    """用户持有详情：嵌套完整 Pokemon 信息"""
    pokemon_info = PokemonDetailSerializer(source="pokemon", read_only=True)

    class Meta:
        model = PlayerPokemon
        fields = ["id", "pokemon", "pokemon_info", "nickname", "iv", "catch_time"]


# ========== Pokedex ==========
class PokedexSerializer(serializers.ModelSerializer):
    pokemon_index = serializers.CharField(source="pokemon.index", read_only=True)
    pokemon_name_zh = serializers.CharField(source="pokemon.name_zh", read_only=True)
    pokemon_name_en = serializers.CharField(source="pokemon.name_en", read_only=True)
    pokemon_image = serializers.ImageField(source="pokemon.image", read_only=True)

    class Meta:
        model = Pokedex
        fields = [
            "id", "pokemon", "pokemon_index",
            "pokemon_name_zh", "pokemon_name_en", "pokemon_image",
            "is_seen", "is_caught",
        ]
