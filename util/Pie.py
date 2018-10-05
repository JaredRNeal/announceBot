from matplotlib import pyplot

def bake(sub, info, title, size='x-large', show_labels=True, title_size=20):
    empty = []
    colors = {
        "Approved": 'green',
        "Denied": '#B20000',
        "Submitted": 'orange',

        "Desktop": 'blue',
        "Linux": '#B20000',
        "iOS": 'orange',
        "Android": 'green',


        "Verified Bugs": 'green',
        "Discord Verified Bugs": 'blue',
        "Reopened": 'purple',
        "Cannot Reproduce": 'orange'
    }

    for k, v in info.items():
        if v == 0:
            empty.append(k)
    for e in empty:
        info.pop(e)
    empty = []
    for k in colors.keys():
        if k not in info.keys():
            empty.append(k)
    for e in empty:
        colors.pop(e)
    wedges, labels, labels2 = sub.pie(info.values(), labels=info.keys() if show_labels else None, autopct='%1.1f%%',
                                      explode=[0.05] * len(info.keys()), colors=colors.values() if len(real_colors) == len(info) else None)
    for i in range(len(info)):
        if len(colors) == len(info):
            labels[i].set_color(list(colors.values())[i])
        labels[i].set_size(size)
        labels2[i].set_size(size)
    pyplot.title(title, fontsize=title_size, color="grey")
