from django.contrib import admin

from .models import Ability, Color, Genera, Habitat, Item, Move, Player, PlayerPokemon, Pokedex, Pokemon, Shape, Type


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ("user", "nickname", "coins", "pokeballs", "berries")
    search_fields = ("nickname", "user__username")


@admin.register(Ability)
class AbilityAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name_zh",
        "name_en",
        "name_jp",
        "flavor_text_zh",
        "flavor_text_en",
        "flavor_text_jp",
        "effect_zh",
        "effect_en",
        "effect_jp",
    )
    search_fields = ("name_zh", "name_en")


@admin.register(Move)
class MoveAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name_zh",
        "name_en",
        "name_jp",
        "flavor_text_zh",
        "flavor_text_en",
        "flavor_text_jp",
        "type_name",
        "power",
        "pp",
        "accuracy",
        "damage_class",
        "meta",
    )
    search_fields = ("name_zh", "name_en")
    list_filter = ("type_name", "damage_class")


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name_zh",
        "name_en",
        "name_jp",
        "flavor_text_zh",
        "flavor_text_en",
        "flavor_text_jp",
        "cost",
        "category",
        "meta",
    )
    search_fields = ("name_zh", "name_en")
    list_filter = ("category",)


@admin.register(Type)
class TypeAdmin(admin.ModelAdmin):
    list_display = ("name", "name_zh", "name_en", "name_jp")
    search_fields = ("name", "name_zh")


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ("name", "name_zh", "name_en", "name_jp")


@admin.register(Habitat)
class HabitatAdmin(admin.ModelAdmin):
    list_display = ("name", "name_zh", "name_en", "name_jp")


@admin.register(Shape)
class ShapeAdmin(admin.ModelAdmin):
    list_display = ("name", "name_zh", "name_en", "name_jp")


@admin.register(Genera)
class GeneraAdmin(admin.ModelAdmin):
    list_display = ("name", "name_zh", "name_en", "name_jp")


@admin.register(Pokemon)
class PokemonAdmin(admin.ModelAdmin):
    list_display = (
        "index",
        "name_zh",
        "name_en",
        "name_jp",
        "flavor_text_zh",
        "flavor_text_en",
        "flavor_text_jp",
        "is_legendary",
        "is_mythical",
        "generation",
        "color",
        "shape",
        "habitat",
        "genera",
        "height",
        "weight",
        "base_happiness",
        "meta",
    )
    search_fields = ("index", "name_zh", "name_en")
    list_filter = ("is_legendary", "is_mythical", "generation", "color", "shape")
    filter_horizontal = ("types", "abilities", "moves")


@admin.register(PlayerPokemon)
class PlayerPokemonAdmin(admin.ModelAdmin):
    list_display = ("player", "pokemon", "nickname", "friendship", "is_shiny", "catch_time")
    search_fields = ("player__nickname", "pokemon__name_zh", "nickname")
    list_filter = ("is_shiny",)


@admin.register(Pokedex)
class PokedexAdmin(admin.ModelAdmin):
    list_display = ("player", "pokemon", "is_seen", "is_caught")
    search_fields = ("player__nickname", "pokemon__name_zh")
    list_filter = ("is_seen", "is_caught")
