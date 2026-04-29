import random

from django.contrib.auth.models import User
from django.db.models import Count, Q
from rest_framework import permissions, status, views, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .models import (
    Ability, Color, Habitat, Item, Player, PlayerPokemon, 
    Pokedex, Pokemon, Shape, Type
)
from .serializers import (
    PlayerPokemonDetailSerializer,
    PlayerPokemonListSerializer,
    PlayerSerializer,
    PokedexSerializer,
    PokemonDetailSerializer,
    PokemonListSerializer,
)


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


# We mock a default user for MVP since no auth is fully set up yet.
def get_default_user():
    user, _ = User.objects.get_or_create(username="default_player")
    Player.objects.get_or_create(user=user)
    return user


class PokemonViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    pagination_class = StandardPagination
    lookup_field = "index"

    def get_serializer_class(self):
        """列表用轻量序列化器，详情用完整序列化器"""
        if self.action == "retrieve":
            return PokemonDetailSerializer
        return PokemonListSerializer

    def get_queryset(self):
        user = get_default_user()
        qs = Pokemon.objects.select_related("color", "habitat", "shape").prefetch_related("types")

        # 详情接口才预加载 abilities 和 moves
        if self.action == "retrieve":
            qs = qs.prefetch_related("abilities", "moves")

        # Annotate owned_count
        qs = qs.annotate(
            owned_count=Count("playerpokemon", filter=Q(playerpokemon__player=user.player))
        )

        # ===== 搜索过滤 =====
        search = self.request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(name_zh__icontains=search)
                | Q(name_en__icontains=search)
                | Q(index__icontains=search)
            )

        # 按属性过滤
        type_filter = self.request.query_params.get("type", "").strip()
        if type_filter:
            qs = qs.filter(types__name_zh=type_filter)

        # 按世代过滤
        generation = self.request.query_params.get("generation", "").strip()
        if generation:
            qs = qs.filter(generation=generation)

        # 按栖息地过滤
        habitat_filter = self.request.query_params.get("habitat", "").strip()
        if habitat_filter:
            qs = qs.filter(habitat__name_zh=habitat_filter)

        return qs.distinct().order_by("id")

    @action(detail=False, methods=["get"])
    def metadata(self, request):
        types = Type.objects.all().values("name", "name_zh", "name_en", "name_jp", "effectiveness")
        habitats = Habitat.objects.all().values("name", "name_zh", "name_en")
        return Response({
            "types": list(types),
            "habitats": list(habitats)
        })


class PlayerViewSet(viewsets.GenericViewSet):
    serializer_class = PlayerSerializer
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=["get"])
    def me(self, request):
        # Use default user for MVP
        user = get_default_user()
        player = user.player
        serializer = self.get_serializer(player)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """返回丰富的个人中心统计数据"""
        user = get_default_user()
        player = user.player

        total_pokemon = Pokemon.objects.count()
        caught_count = Pokedex.objects.filter(player=player, is_caught=True).count()
        seen_count = Pokedex.objects.filter(player=player, is_seen=True).count()
        owned_total = PlayerPokemon.objects.filter(player=player).count()

        # 最近捕获的宝可梦（最多6只），使用 select_related 避免 N+1
        recent_catches = (
            PlayerPokemon.objects.filter(player=player)
            .select_related("pokemon")
            .order_by("-catch_time")[:6]
        )
        recent_data = []
        for pp in recent_catches:
            recent_data.append({
                "id": pp.id,
                "pokemon_id": pp.pokemon.id,
                "pokemon_index": pp.pokemon.index,
                "pokemon_name_zh": pp.pokemon.name_zh,
                "pokemon_name_en": pp.pokemon.name_en,
                "pokemon_image": request.build_absolute_uri(pp.pokemon.image.url) if pp.pokemon.image else "",
                "nickname": pp.nickname,
                "iv": pp.iv,
                "catch_time": pp.catch_time,
            })

        return Response({
            "player": self.get_serializer(player).data,
            "total_pokemon": total_pokemon,
            "caught_count": caught_count,
            "seen_count": seen_count,
            "owned_total": owned_total,
            "pokedex_progress": round(caught_count / total_pokemon * 100, 1) if total_pokemon > 0 else 0,
            "recent_catches": recent_data,
        })

    @action(detail=False, methods=["post"])
    def buy_pokeballs(self, request):
        user = get_default_user()
        player = user.player
        amount = int(request.data.get("amount", 10))
        cost = amount * 10  # 10 coins per pokeball

        if player.coins >= cost:
            player.coins -= cost
            player.pokeballs += amount
            player.save()
            return Response(self.get_serializer(player).data)
        return Response({"error": "Not enough coins"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def buy_berries(self, request):
        user = get_default_user()
        player = user.player
        amount = int(request.data.get("amount", 2))
        cost = amount * 5  # 5 coins per berry

        if player.coins >= cost:
            player.coins -= cost
            player.berries += amount
            player.save()
            return Response(self.get_serializer(player).data)
        return Response({"error": "Not enough coins"}, status=status.HTTP_400_BAD_REQUEST)


class PlayerPokemonViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.AllowAny]
    pagination_class = StandardPagination

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PlayerPokemonDetailSerializer
        return PlayerPokemonListSerializer

    def get_queryset(self):
        user = get_default_user()
        qs = PlayerPokemon.objects.filter(player=user.player).select_related("pokemon")
        
        # ===== 搜索过滤 =====
        search = self.request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(pokemon__name_zh__icontains=search)
                | Q(pokemon__name_en__icontains=search)
                | Q(pokemon__index__icontains=search)
                | Q(nickname__icontains=search)
            )

        # 按属性过滤
        type_filter = self.request.query_params.get("type", "").strip()
        if type_filter:
            qs = qs.filter(pokemon__types__name_zh=type_filter)

        # 按栖息地过滤
        habitat_filter = self.request.query_params.get("habitat", "").strip()
        if habitat_filter:
            qs = qs.filter(pokemon__habitat__name_zh=habitat_filter)

        if self.action == "retrieve":
            qs = qs.select_related("pokemon__color", "pokemon__habitat", "pokemon__shape")
            qs = qs.prefetch_related("pokemon__types", "pokemon__abilities", "pokemon__moves")

        return qs.distinct().order_by("-catch_time")


class PokedexViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PokedexSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = StandardPagination

    def get_queryset(self):
        user = get_default_user()
        return Pokedex.objects.filter(player=user.player).select_related("pokemon")


class CatchAPIView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # Generate random weather
        weathers = ["Sunny", "Rainy", "Snowy", "Cloudy"]
        weather_types_map = {
            "Sunny": ["火", "草", "地面"],
            "Rainy": ["水", "电", "虫"],
            "Snowy": ["冰", "钢"],
            "Cloudy": ["一般", "格斗", "毒"],
        }
        current_weather = random.choice(weathers)
        bonus_types = weather_types_map.get(current_weather, [])

        count = Pokemon.objects.count()
        if count == 0:
            return Response({"error": "No pokemon available"}, status=status.HTTP_404_NOT_FOUND)

        # 50% chance to encounter a weather-boosted pokemon
        pokemon = None
        if random.random() < 0.5 and bonus_types:
            # Try to find a pokemon with matching type
            pokemon = Pokemon.objects.filter(types__name_zh__in=bonus_types).order_by("?").first()

        if not pokemon:
            pokemon = Pokemon.objects.order_by("?").first()

        if not pokemon:
            return Response({"error": "No pokemon found"}, status=status.HTTP_404_NOT_FOUND)

        # Mark as seen in pokedex
        user = get_default_user()
        pokedex_entry, created = Pokedex.objects.get_or_create(player=user.player, pokemon=pokemon)
        if not pokedex_entry.is_seen:
            pokedex_entry.is_seen = True
            pokedex_entry.save()

        # 使用详情序列化器（预加载关联）
        pokemon = (
            Pokemon.objects.select_related("color", "habitat", "shape")
            .prefetch_related("types", "abilities", "moves")
            .get(id=pokemon.id)
        )
        serializer = PokemonDetailSerializer(pokemon)
        return Response({"pokemon": serializer.data, "weather": current_weather})

    def post(self, request):
        # Attempt to catch
        pokemon_id = request.data.get("pokemon_id")
        use_berry = request.data.get("use_berry", False)
        weather = request.data.get("weather", "")
        nickname = request.data.get("nickname", "")

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

        if use_berry and player.berries <= 0:
            return Response({"error": "No berries left!"}, status=status.HTTP_400_BAD_REQUEST)

        # Consume 1 pokeball
        player.pokeballs -= 1

        # Base probability
        catch_chance = 0.5
        message_extras = []

        # Apply berry bonus
        if use_berry:
            player.berries -= 1
            catch_chance += 0.2
            message_extras.append("Berry effect (+20%)")

        player.save()

        # Apply weather bonus
        weather_types_map = {
            "Sunny": ["火", "草", "地面"],
            "Rainy": ["水", "电", "虫"],
            "Snowy": ["冰", "钢"],
            "Cloudy": ["一般", "格斗", "毒"],
        }
        bonus_types = weather_types_map.get(weather, [])
        if pokemon.types.filter(name_zh__in=bonus_types).exists():
            catch_chance += 0.1
            message_extras.append("Weather match (+10%)")

        success = random.random() < catch_chance

        if success:
            # Generate IV (0-31)
            iv = random.randint(0, 31)
            player_pokemon = PlayerPokemon.objects.create(
                player=user.player, pokemon=pokemon, nickname=nickname if nickname else None, iv=iv
            )

            # Update Pokedex
            pokedex_entry, _ = Pokedex.objects.get_or_create(player=user.player, pokemon=pokemon)
            pokedex_entry.is_seen = True
            pokedex_entry.is_caught = True
            pokedex_entry.save()

            msg = f"Gotcha! {pokemon.name} was caught!"
            if message_extras:
                msg += f" (Bonuses: {', '.join(message_extras)})"

            # 用轻量序列化器返回捕获结果
            return Response(
                {
                    "success": True,
                    "message": msg,
                    "data": PlayerPokemonListSerializer(player_pokemon).data,
                    "player": PlayerSerializer(player).data,
                }
            )
        else:
            msg = f"Oh no! {pokemon.name} broke free!"
            if message_extras:
                msg += f" (Bonuses: {', '.join(message_extras)})"

            return Response({"success": False, "message": msg, "player": PlayerSerializer(player).data})
