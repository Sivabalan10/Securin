import ijson

with open('US_recipes_null.json','r') as f:
    for key, item in ijson.kvitems(f,''):
        title = item.get("title")
        cuisine = item.get("cuisine")

        print(title ,"-", cuisine)
        print(item.get("nutrients",{}))
        break


