import json
import re
import shutil
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from loguru import logger
from pocket.models import Pokemon, Ability, Move, Item, Type, Color, Habitat, Shape

TYPES_DATA = {
    "Water": {"zh": "水", "jp": "みず", "effectiveness": {"Fire": 2, "Ground": 2, "Rock": 2, "Water": 0.5, "Grass": 0.5, "Dragon": 0.5}},
    "Grass": {"zh": "草", "jp": "くさ", "effectiveness": {"Water": 2, "Ground": 2, "Rock": 2, "Fire": 0.5, "Grass": 0.5, "Poison": 0.5, "Flying": 0.5, "Bug": 0.5, "Dragon": 0.5, "Steel": 0.5}},
    "Electric": {"zh": "电", "jp": "でんき", "effectiveness": {"Water": 2, "Flying": 2, "Electric": 0.5, "Grass": 0.5, "Dragon": 0.5, "Ground": 0}},
    "Ice": {"zh": "冰", "jp": "こおり", "effectiveness": {"Grass": 2, "Ground": 2, "Flying": 2, "Dragon": 2, "Fire": 0.5, "Water": 0.5, "Ice": 0.5, "Steel": 0.5}},
    "Fighting": {"zh": "格斗", "jp": "かくとう", "effectiveness": {"Normal": 2, "Ice": 2, "Rock": 2, "Dark": 2, "Steel": 2, "Poison": 0.5, "Flying": 0.5, "Psychic": 0.5, "Bug": 0.5, "Fairy": 0.5, "Ghost": 0}},
    "Poison": {"zh": "毒", "jp": "どく", "effectiveness": {"Grass": 2, "Fairy": 2, "Poison": 0.5, "Ground": 0.5, "Rock": 0.5, "Ghost": 0.5, "Steel": 0}},
    "Ground": {"zh": "地面", "jp": "じめん", "effectiveness": {"Fire": 2, "Electric": 2, "Poison": 2, "Rock": 2, "Steel": 2, "Grass": 0.5, "Bug": 0.5, "Flying": 0}},
    "Flying": {"zh": "飞行", "jp": "ひこう", "effectiveness": {"Grass": 2, "Fighting": 2, "Bug": 2, "Electric": 0.5, "Rock": 0.5, "Steel": 0.5}},
    "Psychic": {"zh": "超能力", "jp": "エスパー", "effectiveness": {"Fighting": 2, "Poison": 2, "Psychic": 0.5, "Steel": 0.5, "Dark": 0}},
    "Bug": {"zh": "虫", "jp": "むし", "effectiveness": {"Grass": 2, "Psychic": 2, "Dark": 2, "Fire": 0.5, "Fighting": 0.5, "Poison": 0.5, "Flying": 0.5, "Ghost": 0.5, "Steel": 0.5, "Fairy": 0.5}},
    "Rock": {"zh": "岩石", "jp": "いわ", "effectiveness": {"Fire": 2, "Ice": 2, "Flying": 2, "Bug": 2, "Fighting": 0.5, "Ground": 0.5, "Steel": 0.5}},
    "Ghost": {"zh": "幽灵", "jp": "ゴースト", "effectiveness": {"Psychic": 2, "Ghost": 2, "Dark": 0.5, "Normal": 0}},
    "Dragon": {"zh": "龙", "jp": "ドラゴン", "effectiveness": {"Dragon": 2, "Steel": 0.5, "Fairy": 0}},
    "Dark": {"zh": "恶", "jp": "あく", "effectiveness": {"Psychic": 2, "Ghost": 2, "Fighting": 0.5, "Dark": 0.5, "Fairy": 0.5}},
    "Steel": {"zh": "钢", "jp": "はがね", "effectiveness": {"Ice": 2, "Rock": 2, "Fairy": 2, "Fire": 0.5, "Water": 0.5, "Electric": 0.5, "Steel": 0.5}},
    "Fairy": {"zh": "妖精", "jp": "フェアリー", "effectiveness": {"Fighting": 2, "Dragon": 2, "Dark": 2, "Fire": 0.5, "Poison": 0.5, "Steel": 0.5}},
    "Normal": {"zh": "一般", "jp": "ノーマル", "effectiveness": {"Rock": 0.5, "Steel": 0.5, "Ghost": 0}},
    "Fire": {"zh": "火", "jp": "ほのお", "effectiveness": {"Fire": 0.5, "Water": 0.5, "Grass": 2, "Ice": 2, "Bug": 2, "Rock": 0.5, "Dragon": 0.5, "Steel": 2}},
}

class Command(BaseCommand):
    help = 'Import Pokemon data from local dataset with performance optimizations'

    def add_arguments(self, parser):
        parser.add_argument('--path', type=str, default='../pokemon-dataset-zh', help='Path to the dataset directory')

    def handle(self, *args, **options):
        # 统一路径处理
        dataset_path = Path(options['path']).resolve()
        if not dataset_path.exists():
            # 尝试绝对路径
            dataset_path = Path('/Users/tangzy/code/python/ego-server/pokemon-dataset-zh').resolve()

        if not dataset_path.exists():
            logger.error(f"Dataset path not found: {dataset_path}")
            return

        logger.info(f"Starting optimized import from {dataset_path}")

        try:
            with transaction.atomic():
                # 1. 导入基础属性 (Props)
                self.import_props(dataset_path)

                # 2. 导入特性 (Abilities)
                self.import_abilities(dataset_path)

                # 3. 导入技能 (Moves)
                self.import_moves(dataset_path)

                # 4. 导入道具 (Items)
                self.import_items(dataset_path)

                # 5. 导入宝可梦 (Pokemons)
                self.import_pokemons(dataset_path)

            logger.success("All data imported successfully!")
        except Exception as e:
            logger.exception(f"Import failed: {e}")

    def import_props(self, base_path: Path):
        logger.info("Importing props (Types, Colors, Shapes, Habitats)...")
        # 清除旧数据以支持重新导入
        Type.objects.all().delete()
        Color.objects.all().delete()
        Shape.objects.all().delete()
        Habitat.objects.all().delete()

        pokemon_dir = base_path / 'data' / 'pokemon'
        
        types_set = set()
        colors_set = set()
        shapes_set = set()

        for json_file in pokemon_dir.glob('*.json'):
            with json_file.open('r', encoding='utf-8') as f:
                data = json.load(f)
                for form in data.get('forms', []):
                    for t in form.get('types', []):
                        types_set.add(t)
                    if form.get('color'):
                        colors_set.add(form.get('color'))
                    if form.get('shape'):
                        shapes_set.add(form.get('shape'))

        # 获取已存在的数据，避免重复
        existing_types = set(Type.objects.values_list('name_zh', flat=True))
        existing_colors = set(Color.objects.values_list('name_zh', flat=True))
        existing_shapes = set(Shape.objects.values_list('name_zh', flat=True))
        existing_habitats = set(Habitat.objects.values_list('name_zh', flat=True))

        # 直接创建，因为上面已经清空了
        type_objs = []
        for name_en, info in TYPES_DATA.items():
            type_objs.append(Type(
                name=name_en.lower(),
                name_zh=info['zh'],
                name_en=name_en,
                name_jp=info['jp'],
                effectiveness=info['effectiveness']
            ))
        Type.objects.bulk_create(type_objs)
        
        Color.objects.bulk_create([Color(name_zh=n, name=n, name_en='', name_jp='') for n in sorted(list(colors_set))])
        Shape.objects.bulk_create([Shape(name_zh=n, name=n, name_en='', name_jp='') for n in sorted(list(shapes_set))])

        habitats = ["洞穴", "森林", "草地", "山地", "水边", "城市", "海洋", "荒漠", "草原"]
        Habitat.objects.bulk_create([Habitat(name_zh=n, name=n, name_en='', name_jp='') for n in habitats])
        logger.info("Props import check completed.")

    def import_abilities(self, base_path: Path):
        logger.info("Importing abilities...")
        ability_file = base_path / 'data' / 'ability_list.json'
        if not ability_file.exists():
            return

        with ability_file.open('r', encoding='utf-8') as f:
            abilities_data = json.load(f)
            
            ability_objs = []
            for item in abilities_data:
                aid = item.get('id')
                if not str(aid).isdigit():
                    continue
                
                ability_objs.append(Ability(
                    id=int(aid),
                    name=item.get('name_en', ''),
                    name_zh=item.get('name_zh', ''),
                    name_en=item.get('name_en', ''),
                    name_jp=item.get('name_ja', ''),
                    flavor_text_zh=item.get('description', ''),
                ))
            
            # 使用 ignore_conflicts=True 处理 ID 冲突
            Ability.objects.bulk_create(ability_objs, ignore_conflicts=True)
            logger.info(f"Loaded {len(ability_objs)} abilities.")

    def import_moves(self, base_path: Path):
        logger.info("Importing moves...")
        move_file = base_path / 'data' / 'move_list.json'
        if not move_file.exists():
            return

        with move_file.open('r', encoding='utf-8') as f:
            moves_data = json.load(f)
            move_objs = []
            for item in moves_data:
                mid = item.get('id')
                if not str(mid).isdigit():
                    continue
                
                move_objs.append(Move(
                    id=int(mid),
                    name=item.get('name_en', ''),
                    name_zh=item.get('name_zh', ''),
                    name_en=item.get('name_en', ''),
                    name_jp=item.get('name_ja', ''),
                    flavor_text_zh=item.get('description', ''),
                    type_name=item.get('type', ''),
                    power=str(item.get('power', '')),
                    pp=self.safe_int(item.get('pp')),
                    accuracy=str(item.get('accuracy', '')),
                    damage_class=item.get('category', ''),
                ))
            
            Move.objects.bulk_create(move_objs, ignore_conflicts=True)
            logger.info(f"Loaded {len(move_objs)} moves.")

    def import_items(self, base_path: Path):
        logger.info("Importing items...")
        item_file = base_path / 'data' / 'item_list.json'
        if not item_file.exists():
            return

        with item_file.open('r', encoding='utf-8') as f:
            items_raw = json.load(f)
            flattened = []

            def flatten(data, category=""):
                if isinstance(data, list):
                    for i in data: flatten(i, category)
                elif data.get('type') == 'category':
                    flatten(data.get('children', []), data.get('name', category))
                elif data.get('type') == 'item':
                    data['category'] = category
                    flattened.append(data)

            flatten(items_raw)
            
            existing_names = set(Item.objects.values_list('name_zh', flat=True))
            item_objs = []
            for item in flattened:
                if item['name_zh'] in existing_names:
                    continue
                item_objs.append(Item(
                    name_zh=item['name_zh'],
                    name=item.get('name_en', ''),
                    name_en=item.get('name_en', ''),
                    name_jp=item.get('name_ja', ''),
                    flavor_text_zh=str(item.get('description', '')),
                    category=item.get('category', ''),
                ))
                existing_names.add(item['name_zh'])
            
            Item.objects.bulk_create(item_objs, ignore_conflicts=True)
            logger.info(f"Loaded {len(item_objs)} items.")

    def import_pokemons(self, base_path: Path):
        logger.info("Importing pokemons...")
        pokemon_dir = base_path / 'data' / 'pokemon'
        official_images_dir = base_path / 'data' / 'images' / 'official'
        target_images_dir = Path(settings.MEDIA_ROOT) / 'pocket' / 'pokemon'
        target_images_dir.mkdir(parents=True, exist_ok=True)
        
        # 预加载映射
        types_map = {t.name_zh: t.id for t in Type.objects.all()}
        abilities_map = {a.name_zh: a.id for a in Ability.objects.all()}
        moves_map = {m.name_zh: m.id for m in Move.objects.all()}
        colors_map = {c.name_zh: c.id for c in Color.objects.all()}
        shapes_map = {s.name_zh: s.id for s in Shape.objects.all()}
        habitat_id = Habitat.objects.first().id if Habitat.objects.exists() else None

        pokemon_objs = []
        m2m_types = []
        m2m_abilities = []
        m2m_moves = []

        json_files = sorted(list(pokemon_dir.glob('*.json')))
        
        # 先删除已存在的宝可梦数据，以便全量覆盖更新
        Pokemon.objects.all().delete() 

        for json_file in json_files:
            with json_file.open('r', encoding='utf-8') as f:
                data = json.load(f)
                idx = data.get('pokedex_id')
                if not idx: continue

                form = data['forms'][0] if data.get('forms') else {}
                
                # 获取世代 (Generation)
                generation = ""
                if data.get('pokedex_entries'):
                    generation = data['pokedex_entries'][0].get('name', '')
                
                # 获取风味文本 (Flavor Text)
                flavor_zh = ""
                if data.get('pokedex_entries') and data['pokedex_entries'][0].get('versions'):
                    flavor_zh = data['pokedex_entries'][0]['versions'][0].get('text', '')

                # 数值转换
                height = form.get('height', '')
                weight = form.get('weight', '')
                
                gr = form.get('gender_ratio', {})
                female_rate = gr.get('female', 0)
                gender_ratio = -1 if (female_rate == 0 and gr.get('male', 0) == 0) else int(female_rate / 12.5)

                # 种族值
                stats = []
                if data.get('stats'):
                    sd = data['stats'][0].get('data', {})
                    stats = [
                        {"base_stat": int(sd.get('hp', 0)), "stat": {"name": "hp"}},
                        {"base_stat": int(sd.get('attack', 0)), "stat": {"name": "attack"}},
                        {"base_stat": int(sd.get('defense', 0)), "stat": {"name": "defense"}},
                        {"base_stat": int(sd.get('sp_attack', 0)), "stat": {"name": "special-attack"}},
                        {"base_stat": int(sd.get('sp_defense', 0)), "stat": {"name": "special-defense"}},
                        {"base_stat": int(sd.get('speed', 0)), "stat": {"name": "speed"}},
                    ]

                # 处理图片
                image_name = f"{idx}-{data.get('name_zh')}.png"
                image_path = official_images_dir / image_name
                db_image_path = ""
                if image_path.exists():
                    new_image_name = f"{idx}.png"
                    shutil.copy(image_path, target_images_dir / new_image_name)
                    db_image_path = f"pocket/pokemon/{new_image_name}"
                else:
                    logger.warning(f"Image not found: {image_path}")

                p_obj = Pokemon(
                    index=idx,
                    name=data.get('name_en', ''),
                    name_zh=data.get('name_zh', ''),
                    name_en=data.get('name_en', ''),
                    name_jp=data.get('name_ja', ''),
                    description=data.get('description', ''),
                    profile=data.get('profile', ''),
                    prototype=data.get('prototype', ''),
                    detail=data.get('detail', ''),
                    flavor_text_zh=flavor_zh,
                    gender_ratio=gender_ratio,
                    height=height,
                    weight=weight,
                    capture_rate=self.extract_int(form.get('catch_rate', '0')),
                    base_experience=self.safe_int(form.get('base_exp', 0)),
                    hatch_counter=self.extract_int(form.get('egg_cycles', '0')),
                    stats=stats,
                    color_id=colors_map.get(form.get('color')),
                    shape_id=shapes_map.get(form.get('shape')),
                    habitat_id=habitat_id,
                    genera=form.get('category', ''),
                    generation=generation,
                    egg_groups=form.get('egg_groups', []),
                    evolution_chains=data.get('evolution_chains', []),
                    image=db_image_path,
                )
                pokemon_objs.append(p_obj)

                # M2M
                for t_name in form.get('types', []):
                    if t_name in types_map: m2m_types.append((idx, types_map[t_name]))
                for a_data in form.get('abilities', []):
                    a_name = a_data.get('name')
                    if a_name in abilities_map: m2m_abilities.append((idx, abilities_map[a_name]))
                
                move_names = set()
                for key in ['learnable_moves', 'machine_moves', 'egg_moves', 'tutor_moves']:
                    for group in data.get(key, []):
                        for m in group.get('data', []):
                            move_names.add(m['name'])
                for mn in move_names:
                    if mn in moves_map: m2m_moves.append((idx, moves_map[mn]))

        # 批量写入 Pokemon
        logger.info(f"Bulk creating {len(pokemon_objs)} pokemons...")
        with transaction.atomic():
            # 清空旧数据（级联删除会清理 M2M 表）
            Pokemon.objects.all().delete()
            Pokemon.objects.bulk_create(pokemon_objs)
            
            # 重新获取 ID 映射
            index_to_id = {p.index: p.id for p in Pokemon.objects.filter(index__in=[o.index for o in pokemon_objs])}
            
            logger.info("Bulk creating M2M relationships...")
            
            # 使用 set() 去重，防止 IntegrityError (duplicate key)
            TypeThrough = Pokemon.types.through
            TypeThrough.objects.bulk_create([
                TypeThrough(pokemon_id=index_to_id[idx], type_id=tid)
                for idx, tid in sorted(list(set(m2m_types))) if idx in index_to_id
            ])

            AbilityThrough = Pokemon.abilities.through
            AbilityThrough.objects.bulk_create([
                AbilityThrough(pokemon_id=index_to_id[idx], ability_id=aid)
                for idx, aid in sorted(list(set(m2m_abilities))) if idx in index_to_id
            ])

            MoveThrough = Pokemon.moves.through
            MoveThrough.objects.bulk_create([
                MoveThrough(pokemon_id=index_to_id[idx], move_id=mid)
                for idx, mid in sorted(list(set(m2m_moves))) if idx in index_to_id
            ])

        logger.info("Pokemons and relationships imported successfully.")

    def safe_int(self, val):
        if val is None: return 0
        s = str(val).strip()
        return int(s) if s.isdigit() else 0

    def extract_int(self, val):
        if not val: return 0
        m = re.search(r'\d+', str(val))
        return int(m.group()) if m else 0
