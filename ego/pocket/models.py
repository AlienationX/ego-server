from django.db import models
from django.contrib.auth.models import User


class Player(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="player")
    coins = models.IntegerField(default=1000)
    pokeballs = models.IntegerField(default=50)

    def __str__(self):
        return f"{self.user.username}'s Player"


class Pokemon(models.Model):
    index = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    name_jp = models.CharField(max_length=100, blank=True, null=True)
    name_en = models.CharField(max_length=100, blank=True, null=True)
    generation = models.CharField(max_length=50, blank=True, null=True)
    types = models.JSONField(default=list)
    meta = models.JSONField(default=dict)

    def __str__(self):
        return f"[{self.index}] {self.name}"


class UserPokemon(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="pokemons")
    pokemon = models.ForeignKey(Pokemon, on_delete=models.CASCADE)
    nickname = models.CharField(max_length=100, blank=True, null=True)
    iv = models.IntegerField(default=0)  # Total IV, or could be a JSON field for detailed IVs
    catch_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s {self.pokemon.name}"


class Pokedex(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="pokedex")
    pokemon = models.ForeignKey(Pokemon, on_delete=models.CASCADE)
    is_seen = models.BooleanField(default=False)
    is_caught = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'pokemon')

    def __str__(self):
        return f"{self.user.username} - {self.pokemon.name} (Seen: {self.is_seen}, Caught: {self.is_caught})"
