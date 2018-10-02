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

    real_colors = []
    for k, v in info.items():
        if v == 0:
            empty.append(k)
        elif k in colors.keys():
            real_colors.append(colors[k])
    for e in empty:
        info.pop(e)
    wedges, labels, labels2 = sub.pie(info.values(), labels=info.keys() if show_labels else None, autopct='%1.1f%%',
                                      explode=[0.05] * len(info.keys()), colors=real_colors if len(real_colors) == len(info) else None)
    for i in range(len(info)):
        if len(colors) == len(info):
            labels[i].set_color(list(colors.values())[i])
        labels[i].set_size(size)
        labels2[i].set_size(size)
    pyplot.title(title, fontsize=title_size, color="grey")