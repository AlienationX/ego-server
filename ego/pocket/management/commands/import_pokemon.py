import json
from django.core.management.base import BaseCommand
from pocket.models import Pokemon

class Command(BaseCommand):
    help = 'Imports pokemon data from pokemon_full_list.json'

    def handle(self, *args, **options):
        file_path = '/Users/tangzy/code/python/ego-server/pokemon-dataset-zh/data/pokemon_full_list.json'
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        count = 0
        self.stdout.write('Starting import...')
        
        # We might have regional forms (same index) in the dataset. Let's make index + form a unique identifier if needed, 
        # but the model only has `index` as unique=True. 
        # In pokemon_full_list.json, regional forms have the same index but different names or types.
        # Let's adjust our logic to handle this. If it's a duplicate index, maybe append a suffix or just skip for MVP.
        # Actually, let's just keep the first one encountered or skip duplicates.
        
        seen_indexes = set()
        
        # Or even better, let's clear the Pokemon table and bulk insert
        Pokemon.objects.all().delete()
        
        pokemon_objects = []
        for item in data:
            index = item.get('index')
            if index in seen_indexes:
                continue # Skip regional forms for MVP
            
            seen_indexes.add(index)
            
            pokemon_objects.append(Pokemon(
                index=index,
                name=item.get('name'),
                name_jp=item.get('name_jp'),
                name_en=item.get('name_en'),
                generation=item.get('generation'),
                types=item.get('types', []),
                meta=item.get('meta', {})
            ))
            count += 1
            
        Pokemon.objects.bulk_create(pokemon_objects)
        
        self.stdout.write(self.style.SUCCESS(f'Successfully imported {count} pokemon.'))
