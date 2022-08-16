a = 'mmKjj22222j..'
punctuation_marks = ['.', ',', ':', ';', '"', '{', '}', '[', ']', '!', '@', '#', '<', '>', '(', ')', '*', '^', '%', '$', '&', '?', '№']
list = []
if not a.lower():
    print('ok')

print(a.islower())
for i in a:
    if i.isdigit():
        list.append(i)
        break
for i in punctuation_marks:
    if i in a:
        list.append(i)
        break
print(list)
