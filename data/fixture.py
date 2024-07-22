import json

file = open('data/ingredients.json', 'r')
content = file.read()
data = json.loads(content)
new_file = open('data/new.json', 'w')
new_file.write('[')
for i in range(len(data)):
    new_file.write('{"model": "recipes.ingredient", "pk": ')
    new_file.write(f'{i+1}, "fields": ')
    new_file.write(f'{data[i]}')
    new_file.write('}, ')
new_file.write(']')
new_file.close
