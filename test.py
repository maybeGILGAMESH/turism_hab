def check_accuracy(solver, images, path):
    s_true, s_done = 0, 0
    
    for key, val in images.items():
        for image in val[:-3]:
            output = solve.search(f"{path}{image[:5]}/{image}")
            s_done += 1
            if output == key:
                s_true += 1

    return s_true/s_done


base = {}
path = "/Users/romanvisotsky/Downloads/dataset_sber/images/"
obj = os.listdir(path)
obj.remove('.DS_Store') if '.DS_Store' in obj else None

for folder in obj:
    base[folder] = sorted(os.listdir(f"/Users/romanvisotsky/Downloads/dataset_sber/images/{folder}"))



print(check_accuracy(None, base, path))