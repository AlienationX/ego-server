from django.contrib.auth.models import User
from django.db import models


class Player(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="player", verbose_name="关联用户")
    nickname = models.CharField(max_length=100, blank=True, null=True, verbose_name="昵称")
    coins = models.IntegerField(default=1000, verbose_name="金币")
    pokeballs = models.IntegerField(default=50, verbose_name="精灵球数量")
    berries = models.IntegerField(default=10, verbose_name="树果数量")

    class Meta:
        verbose_name = "玩家信息"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.nickname}'s Player"


class Ability(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="唯一标识")
    name = models.CharField(max_length=100, blank=True, null=True, verbose_name="名称")
    name_zh = models.CharField(max_length=100, blank=True, null=True, verbose_name="中文名称")
    name_en = models.CharField(max_length=100, blank=True, null=True, verbose_name="英文名称")
    name_jp = models.CharField(max_length=100, blank=True, null=True, verbose_name="日文名称")
    flavor_text_zh = models.TextField(blank=True, null=True, verbose_name="中文描述")
    flavor_text_en = models.TextField(blank=True, null=True, verbose_name="英文描述")
    flavor_text_jp = models.TextField(blank=True, null=True, verbose_name="日文描述")
    effect_zh = models.TextField(blank=True, null=True, verbose_name="中文效果")
    effect_en = models.TextField(blank=True, null=True, verbose_name="英文效果")
    effect_jp = models.TextField(blank=True, null=True, verbose_name="日文效果")
    meta = models.JSONField(default=dict, verbose_name="元数据")

    class Meta:
        verbose_name = "特性"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name_zh


class Move(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="唯一标识")
    name = models.CharField(max_length=100, blank=True, null=True, verbose_name="名称")
    name_zh = models.CharField(max_length=100, blank=True, null=True, verbose_name="中文名称")
    name_en = models.CharField(max_length=100, blank=True, null=True, verbose_name="英文名称")
    name_jp = models.CharField(max_length=100, blank=True, null=True, verbose_name="日文名称")
    flavor_text_zh = models.TextField(blank=True, null=True, verbose_name="中文描述")
    flavor_text_en = models.TextField(blank=True, null=True, verbose_name="英文描述")
    flavor_text_jp = models.TextField(blank=True, null=True, verbose_name="日文描述")
    type_name = models.CharField(max_length=50, verbose_name="属性")  # fire, water, etc.
    power = models.CharField(max_length=20, null=True, blank=True, verbose_name="威力")  # Sometimes "—" or "变化"
    pp = models.IntegerField(null=True, blank=True, verbose_name="PP值")
    accuracy = models.CharField(max_length=20, null=True, blank=True, verbose_name="命中率")
    damage_class = models.CharField(max_length=50, verbose_name="伤害分类")  # physical, special, status
    meta = models.JSONField(default=dict, verbose_name="元数据")

    class Meta:
        verbose_name = "技能"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name_zh


class Item(models.Model):
    id = models.AutoField(primary_key=True, verbose_name="唯一标识")
    name = models.CharField(max_length=100, blank=True, null=True, verbose_name="名称")
    name_zh = models.CharField(max_length=100, blank=True, null=True, verbose_name="中文名称")
    name_en = models.CharField(max_length=100, blank=True, null=True, verbose_name="英文名称")
    name_jp = models.CharField(max_length=100, blank=True, null=True, verbose_name="日文名称")
    flavor_text_zh = models.TextField(blank=True, null=True, verbose_name="中文描述")
    flavor_text_en = models.TextField(blank=True, null=True, verbose_name="英文描述")
    flavor_text_jp = models.TextField(blank=True, null=True, verbose_name="日文描述")
    cost = models.IntegerField(default=0, verbose_name="价格")
    category = models.CharField(max_length=100, blank=True, null=True, verbose_name="分类")

    sprite = models.ImageField(upload_to="pocket/items/", blank=True, null=True, verbose_name="道具图片")
    meta = models.JSONField(default=dict, verbose_name="元数据")

    class Meta:
        verbose_name = "道具"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name_zh


class Type(models.Model):
    name = models.CharField(max_length=100, verbose_name="名称")
    name_zh = models.CharField(max_length=100, verbose_name="中文名称")
    name_en = models.CharField(max_length=100, verbose_name="英文名称")
    name_jp = models.CharField(max_length=100, verbose_name="日文名称")

    class Meta:
        verbose_name = "属性"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class Color(models.Model):
    name = models.CharField(max_length=100, verbose_name="名称")
    name_zh = models.CharField(max_length=100, verbose_name="中文名称")
    name_en = models.CharField(max_length=100, verbose_name="英文名称")
    name_jp = models.CharField(max_length=100, verbose_name="日文名称")

    class Meta:
        verbose_name = "颜色"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class Habitat(models.Model):
    name = models.CharField(max_length=100, verbose_name="名称")
    name_zh = models.CharField(max_length=100, verbose_name="中文名称")
    name_en = models.CharField(max_length=100, verbose_name="英文名称")
    name_jp = models.CharField(max_length=100, verbose_name="日文名称")

    class Meta:
        verbose_name = "栖息地"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class Shape(models.Model):
    name = models.CharField(max_length=100, verbose_name="名称")
    name_zh = models.CharField(max_length=100, verbose_name="中文名称")
    name_en = models.CharField(max_length=100, verbose_name="英文名称")
    name_jp = models.CharField(max_length=100, verbose_name="日文名称")

    class Meta:
        verbose_name = "体型"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class Genera(models.Model):
    name = models.CharField(max_length=100, verbose_name="名称")
    name_zh = models.CharField(max_length=100, verbose_name="中文名称")
    name_en = models.CharField(max_length=100, verbose_name="英文名称")
    name_jp = models.CharField(max_length=100, verbose_name="日文名称")

    class Meta:
        verbose_name = "属类"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class Pokemon(models.Model):
    index = models.CharField(max_length=10, unique=True, verbose_name="图鉴编号")
    name = models.CharField(max_length=100, blank=True, null=True, verbose_name="名称")
    name_zh = models.CharField(max_length=100, blank=True, null=True, verbose_name="中文名称")
    name_en = models.CharField(max_length=100, blank=True, null=True, verbose_name="英文名称")
    name_jp = models.CharField(max_length=100, blank=True, null=True, verbose_name="日文名称")
    description = models.TextField(blank=True, null=True, verbose_name="简要描述")
    profile = models.TextField(blank=True, null=True, verbose_name="详细简介")
    prototype = models.TextField(blank=True, null=True, verbose_name="设计原型")
    detail = models.TextField(blank=True, null=True, verbose_name="细节相关")
    flavor_text_zh = models.TextField(blank=True, null=True, verbose_name="中文风味文本")
    flavor_text_en = models.TextField(blank=True, null=True, verbose_name="英文风味文本")
    flavor_text_jp = models.TextField(blank=True, null=True, verbose_name="日文风味文本")

    # 雌性概率。-1表示无性别；0表示100%雄性；8表示100%雌性；中间值如1表示12.5%雌性（1/8）。
    gender_ratio = models.IntegerField(blank=True, null=True, verbose_name="性别比例")
    height = models.CharField(max_length=10, blank=True, null=True, verbose_name="身高")
    weight = models.CharField(max_length=10, blank=True, null=True, verbose_name="体重")

    genera = models.CharField(max_length=50, blank=True, null=True, verbose_name="属类")
    color = models.ForeignKey(Color, on_delete=models.CASCADE, verbose_name="颜色")
    habitat = models.ForeignKey(Habitat, on_delete=models.CASCADE, verbose_name="栖息地")
    shape = models.ForeignKey(Shape, on_delete=models.CASCADE, verbose_name="体型")
    base_happiness = models.IntegerField(default=0, verbose_name="基础亲密度")
    egg_groups = models.JSONField(default=list, blank=True, null=True, verbose_name="蛋组")

    evolution_chains = models.JSONField(default=list, blank=True, null=True, verbose_name="进化链")

    is_legendary = models.BooleanField(default=False, verbose_name="是否传说")
    is_mythical = models.BooleanField(default=False, verbose_name="是否神话")

    stats = models.JSONField(default=list, verbose_name="种族值")
    capture_rate = models.IntegerField(default=0, verbose_name="捕获率")  # 捕获率基础值（0-255），值越高越容易被精灵球捕获。
    base_experience = models.IntegerField(blank=True, null=True, verbose_name="基础经验")
    hatch_counter = models.IntegerField(default=0, verbose_name="孵化步数")
    generation = models.CharField(max_length=50, blank=True, null=True, verbose_name="世代")

    types = models.ManyToManyField(Type, related_name="pokemons", verbose_name="属性列表")
    abilities = models.ManyToManyField(Ability, related_name="pokemons", verbose_name="特性列表")
    moves = models.ManyToManyField(Move, related_name="pokemons", verbose_name="技能列表")

    image = models.ImageField(upload_to="pocket/pokemon/", blank=True, null=True, verbose_name="图片")
    meta = models.JSONField(default=dict, verbose_name="元数据")

    class Meta:
        verbose_name = "宝可梦"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"[{self.index}] {self.name}"


class PlayerPokemon(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="pokemons", verbose_name="持有者")
    pokemon = models.ForeignKey(Pokemon, on_delete=models.CASCADE, verbose_name="宝可梦")
    nickname = models.CharField(max_length=100, blank=True, null=True, verbose_name="昵称")
    friendship = models.IntegerField(default=0, verbose_name="亲密度")
    iv = models.IntegerField(default=0, verbose_name="个体值(IV)")
    catch_time = models.DateTimeField(auto_now_add=True, verbose_name="捕获时间")
    gender = models.CharField(max_length=10, blank=True, null=True, verbose_name="性别")
    is_shiny = models.BooleanField(default=False, verbose_name="是否闪光")
    gender = models.CharField(max_length=10, default="", verbose_name="性别")

    class Meta:
        verbose_name = "玩家持有的宝可梦"
        verbose_name_plural = verbose_name
        db_table = "pocket_player_pokemon"
        db_table_comment = verbose_name

    def __str__(self):
        return f"{self.player.nickname}'s {self.pokemon.name}"


class Pokedex(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="pokedex", verbose_name="玩家")
    pokemon = models.ForeignKey(Pokemon, on_delete=models.CASCADE, related_name="pokedex", verbose_name="宝可梦")
    is_seen = models.BooleanField(default=False, verbose_name="是否见过")
    is_caught = models.BooleanField(default=False, verbose_name="是否捕获")

    class Meta:
        unique_together = ("player", "pokemon")
        verbose_name = "个人图鉴记录"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.player.nickname} - {self.pokemon.name} (Seen: {self.is_seen}, Caught: {self.is_caught})"
